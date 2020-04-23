#!/usr/bin/env python3


# TODO:
# find out remaining types of lines
# useful command for that:
    # find . -name *.RPP -size -100k -exec py ~/Documents/git-scythe/git-scythe.py tree {} > /dev/null \;
# what about 'TAKE'?
# handle empty input files gracefully
# tbfo == "to be fleshed out"


import sys
import os
import subprocess
import re
import pathlib
import shlex
from glob import glob
from itertools import filterfalse
import argparse


class ReaperProject:
    def __init__(self, inputstr = None):
        if inputstr:
            generator = (line for line in inputstr.splitlines())
            try:
                return ReaperProject.fromGenerator(generator)
            except AssertionError:
                sys.exit('this does not seem to be a reaper project')  # tbfo
    
    @classmethod
    def fromFilepath(cls, filepath):
        if not os.path.exists(filepath):
            sys.exit(f'{filepath} does not exist')  # tbfo
        elif not os.path.isfile(filepath):
            sys.exit(f'{filepath} is not a regular file (i.e. a directory or mount point or the like)')  # tbfo
        with open(filepath) as file:
            try:
                instance = cls.fromGenerator(file)
            except AssertionError:
                sys.exit(f'{filepath} does not seem to be a reaper project')  # tbfo
            instance.encoding = file.encoding
            instance.line_terminator = file.newlines
            return instance
    
    @classmethod
    def fromGenerator(cls, generator):
        firstline = next(generator)
        assert firstline.startswith('<REAPER_PROJECT'), 'not a reaper project'
        reaperProject = cls()
        reaperProject.root = Node(firstline, generator)
        return reaperProject
    
    def find(self, *args, **kwargs):
        return next(self.findall(*args, **kwargs))
    
    def findall(self, query, recursive = False):
        if '/' in query:
            head, _, query = query.partition('/')
            if head == self.root.name:
                return self.root.findall(query, recursive = False)
            else:
                return []
        else:
            return self.root.findall(query, recursive)
    
    def get_source_paths(self):
        paths = []
        for source in self.findall('SOURCE', recursive = True):
            # you will also need to account for tags FILE, RENDER_FILE and RECORD_PATH
            # attributes: FILE (of tag SOURCE)
            # tags: RENDER_FILE, RECORD_PATH
            if 'FILE' in source:
                sourcefile = source['FILE'][0]
                if '/' in sourcefile:
                    path = pathlib.PurePosixPath(sourcefile)
                elif '\\' in sourcefile:
                    path = pathlib.PureWindowsPath(sourcefile)
                else:
                    path = pathlib.PurePath(sourcefile)
                paths.append(path)
        return paths
    
    def __len__(self):
        return len(self.root)
    
    def print(self, file = sys.stdout):
        self.root.print(file = file)


class Node:
    def __init__(self, firstline, generator, line_number = 1):
        self.name, self.tags = re.match(r'^ *<([A-Z0-9_]+)(.*)$', firstline).groups()
        self.contents = [firstline]
        self.tags = shlex.split(self.tags)
        self.attributes = {}
        self.start_in_file = line_number
        # self.attributes = []
        
        for line in generator:
            line_number += 1
            opening_tag = re.match(r'^ *<([A-Z0-9_]+)(.*)$', line)
            closing_tag = re.match(r'^ *>$', line)
            
            if opening_tag:
                child = Node(line, generator, line_number)
                self.contents.append(child)
                line_number += len(child) - 1  # we have to subtract one here
                                               # because we already added one
                                               # at the start of the loop
            elif closing_tag:
                self.contents.append(line)
                self.end_in_file = line_number
                break
            else:
                self.contents.append(line)
                self.parse_line(line)
    
    def parse_line(self, line):
        attribute = re.match(r'^ +([A-Z0-9_]+) (.*)$', line)
        base64 = re.match(r'^ +[A-Za-z0-9+/]+={0,2}$', line)
        midi = re.match(r'^ +([Ee]) (.*)$', line)
        code = re.match(r'^ +\|(.*)$', line)
        fx_params = re.match(r'^ +(.*)(?:- )+$', line)
        
        if midi:
            pass
        elif attribute:
            name, values = attribute.groups()
            values = shlex.split(values)
            self.attributes[name] = values
            # new_attribute = Attribute(name, values)
            # self.attributes.append(new_attribute)
        elif base64:
            pass
        elif code:
            pass
        elif fx_params:
            pass
        else:
            print('could not parse the following line:\n' + line, file = sys.stderr)
    
    @property
    def children(self):
        return filter(lambda x: isinstance(x, type(self)), self.contents)
    
    @property
    def position_in_file(self):
        return self.start_in_file, self.end_in_file
    
    def __getitem__(self, key):
        if key in self.attributes:
            # attribute = self.attributes[key]
            # if len(attribute) == 1:
            #     return attribute[0]
            # else:
            #     return attribute
            return self.attributes[key]
        else:
            raise KeyError(f"item '{self.name}' contains no attribute '{key}'")  # tbfo
    
    def __contains__(self, key):
        return key in self.attributes
    
    def __getattr__(self, name):
        # return self.__getitem__(name)
        pass
    
    def __len__(self):
        return self.end_in_file - self.start_in_file + 1  # here we have to add
                                                          # one because otherwise
                                                          # we'd just be describing
                                                          # the range
    
    def __repr__(self):
        return f'<Node "{self.name}">'
    
    def findall(self, query, recursive = False):
        if '/' in query:
            topitem, query = query.split('/', maxsplit = 1)
            for topmatch in self.findall(topitem):
                for match in topmatch.findall(query):
                    yield match
        else:
            for child in self.children:
                if recursive:
                    for match in child.findall(query, recursive = True):
                        yield match
                if child.name == query:
                    yield child
    
    def print(self, file):
        for content in self.contents:
            if isinstance(content, type(self)):
                content.print(file = file)
            else:
                print(content, end = '', file = file)


class Attribute:
    def __init__(self, name, values):
        self.name = name
        self.values = values
    
    def __repr__(self):
        return f'<Attribute "{self.name}">'


class ScytheParser(argparse.ArgumentParser):
    def __init__(self, module_name):
        super().__init__(prog = 'git scythe ' + module_name, add_help = False)
        self.add_argument('input', nargs = '?')
        self.add_argument('-q', '--quiet', action = 'store_true')
        self.add_argument('--help', action = 'help')
    
    def parse_args(self):
        args = super().parse_args(sys.argv[2:])
        
        if not args.input:
            missinginputwarning = config.get('missinginputwarning', default = 'true')
            if missinginputwarning == 'true':
                print(
                    'you did not specify an input file, will use last accessed file\n'
                    'you can turn off this warning with\n'
                    'git config scythe.missinginputwarning false',
                    file = sys.stderr
                )
            
            files = filter(os.path.isfile, glob('*.RPP'))
            args.input = max(files, key = os.path.getatime)
        
        return args


class config:
    # this class works similarly to the class modules,
    # see that class's docstring
    @staticmethod
    def get(key, default):
        try:
            value = subprocess.run(
                ['git', 'config', '--get', 'scythe.' + key],
                capture_output = True,
                text = True,
                check = True
            ).stdout.strip()
        except subprocess.CalledProcessError:
            subprocess.run(
                ['git', 'config', '--add', 'scythe.' + key, default],
                capture_output = True
            )
            value = default
        
        return value


class modules:
    '''
    this class serves only as a sort of grouping
    for the functions associated with the various
    command line options. Hence the lowercase name
    and all the methods being static
    '''
    @staticmethod
    def paths():
        parser = ScytheParser('paths')
        parser.add_argument('-a', '--absolute', action = 'store_true')
        parser.add_argument('-r', '--relative', action = 'store_true')
        parser.add_argument('-s', '--sort', action = 'store_true')
        parser.add_argument('--render-file', action = 'store_true')
        parser.add_argument('--record-path', action = 'store_true')
        parser.add_argument('--all', action = 'store_true')  # equivalent to `--render-file --record-path`
        parser.add_argument('-f', '--format', action = 'store')
            # POSIX/UNIX or DOS/WINDOWS
            # default value same as in input, otherwise dependent on operating system
            # have a look at maybe using the class argparse.ArgumentError
            # for when it receives disallowed input
        parser.add_argument('-d', '--delimiter', action = 'store', default = '\n')
        parser.add_argument('-e', '--escape', action = 'store_true')  # it should be noted that this only really works for the UNIX shell
        args = parser.parse_args()
        
        reaperProject = ReaperProject.fromFilepath(args.input)
        source_paths = reaperProject.get_source_paths()  # default: <empty path>
        if args.sort:
            source_paths.sort()
        
        if args.render_file or args.all:
            render_path = reaperProject.root['RENDER_FILE'][0]
        if args.record_path or args.all:
            primary_recording_path, secondary_recording_path = reaperProject.root['RECORD_PATH']
        
        if args.absolute:
            source_paths = filter(pathlib.PurePath.is_absolute, source_paths)
        elif args.relative:
            source_paths = filterfalse(pathlib.PurePath.is_absolute, source_paths)
        
        source_paths = map(str, source_paths)
        if args.escape:
            source_paths = map(shlex.quote, source_paths)
        
        if args.render_file or args.all:
            if not args.quiet:
                print('Render path:', end = ' ')
            print(render_path)
        if args.record_path or args.all:
            if not args.quiet:
                print('Primary recording path:', end = ' ')
            print(primary_recording_path)
            if not args.quiet:
                print('Secondary recording path:', end = ' ')
            print(secondary_recording_path)
        
        if not args.quiet:
            print(f'File paths found in {args.input}:')
        print(args.delimiter.join(source_paths))
            # for some reason, if this is called with `-d ' '`, it raises an error:
            # git scythe paths: error: argument -d/--delimiter: expected one argument
    
    @staticmethod
    def cleanup():
        parser = ScytheParser('cleanup')
        parser.add_argument('directory', nargs = '?', default = '.')  # default should actually be the path of the rpp file i suppose
        parser.add_argument('--dry', action = 'store_true')  # dry run argument, might rename it still
        args = parser.parse_args()
        
        reaperProject = ReaperProject.fromFilepath(args.input)
        source_paths = reaperProject.get_source_paths()
        
        for dirpath, dirnames, filenames in os.walk(args.directory):
            # what you're gonna have to do here:
            # canonicalize both `filenames` as well as `source_paths`
            # (maybe rename that latter variable to something more explicit),
            # then check which `filenames` do not appear in `source_paths`.
            # perhaps provide an option to restrict the search to media files
            # (based on the file extension)
            pass
    
    @staticmethod
    def test():
        parser = ScytheParser('test')
        args = parser.parse_args()
        output = args.input + '.copy'
        
        print(f'Parsing {args.input}...')
        reaperProject = ReaperProject.fromFilepath(args.input)
        print(f'Creating {output}...')
        with open(output, mode = 'x', encoding = reaperProject.encoding, newline = reaperProject.line_terminator) as file:
            reaperProject.print(file = file)
        
        diff = subprocess.run(
            ['diff', '-s', args.input, output],
            capture_output = True,
            text = True
        )
        if diff.returncode == 0:
            print('Success!', diff.stdout.strip())
            os.remove(output)
        else:
            print('Oh no! Diff failed with the following output:')
            sys.exit(diff.stdout.strip())
    
    @staticmethod
    def help(file = sys.stdout):
        print('help page should be printed here', file = file)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        module = sys.argv[1]
    else:
        module = 'help'
    
    if module == 'paths':
        modules.paths()
    elif module == 'cleanup':
        modules.cleanup()
    elif module == 'test':
        modules.test()
    elif module == 'help':
        modules.help()
    elif module == '--version':
        print('0.0')
        sys.exit()
    else:
        print('unknown module:', module, file = sys.stderr)
        modules.help(file = sys.stderr)
