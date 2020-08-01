#!/usr/bin/env python3
# requires python version >= 3.6


# TODO:
# find out remaining types of lines
# useful command for that:
    # find . -name '*.rpp' -size -100k -exec git scythe test {} > /dev/null \;
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
from collections import OrderedDict
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
        return [Path(source['FILE'][0]) \
                for source in self.findall('SOURCE', recursive = True) \
                if 'FILE' in source]
    
    def __len__(self):
        return len(self.root)
    
    def dump(self, file = sys.stdout):
        self.root.dump(file = file)


class GenericNode:
    def __new__(cls, firstline, *args, **kwargs):
        node_name = re.match(r'^ *<([A-Z0-9_]+)', firstline).group(1)
        node_class = {'TRACK': Track
                     }.get(node_name, Node)
        return node_class(firstline, *args, **kwargs)


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
                child = GenericNode(line, generator, line_number)
                self.contents.append(child)
                line_number += len(child) - 1
                    # we have to subtract one here because we already added one
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
        fx_params = re.match(r'^ +(.*)(?:- )+-?$', line)
        
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
        return filter(lambda x: isinstance(x, Node), self.contents)
    
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
        return self.end_in_file - self.start_in_file + 1
            # here we have to add one because otherwise we'd just be describing
            # the range
    
    def __repr__(self):
        return f'<{type(self).__name__} "{self.name}">'
    
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
    
    def dump(self, file):
        for content in self.contents:
            if isinstance(content, Node):
                content.dump(file = file)
            else:
                print(content, end = '', file = file)


class Track(Node):
    pass


class Path:
    def __new__(cls, pathstr):
        # perhaps you should handle the inference of the type of path globally
        # instead of separately for each path
        if '/' in pathstr:
            return pathlib.PurePosixPath(pathstr)
        elif '\\' in pathstr:
            return pathlib.PureWindowsPath(pathstr)
        elif pathstr:
            return pathlib.PurePath(pathstr)
        else:
            return None


class Attribute:
    def __init__(self, name, values):
        self.name = name
        self.values = values
    
    def __repr__(self):
        return f'<Attribute "{self.name}">'


class ScytheParser(argparse.ArgumentParser):
    def __init__(self, cmd, *args, **kwargs):
        super().__init__(*args, **kwargs, add_help = False)
        self.cmd = cmd
        self.add_argument('input', nargs = '?')
    
    def parse_args(self):
        self.add_argument('-q', '--quiet', action = 'store_true')
        self.add_argument('--help', action = 'help')
        # putting these two arguments here rather than in __init__ because we'd
        # like them to appear at the end
        args = super().parse_args(sys.argv[2:])
        
        if not args.input:
            rpp_files = glob('*.rpp') + glob('*.RPP')
            if len(rpp_files) == 1:
                args.input = rpp_files[0]
            elif len(rpp_files) == 0:
                sys.exit('there are no reaper files in the current directory, please specify an input file')
            else:
                sys.exit('there are multiple reaper files in the current directory, please specify an input file')
        
        return args
    
    def run(self):
        self.cmd(self)


class config:
    # this class works similarly to the class subcommands,
    # see that class's docstring
    @staticmethod
    def get(key, default):
        try:
            value = subprocess.run(
                ['git', 'config', '--get', 'scythe.' + key],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                universal_newlines = True,
                check = True
            ).stdout.strip()
        except subprocess.CalledProcessError:
            subprocess.run(
                ['git', 'config', '--add', 'scythe.' + key, default],
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                universal_newlines = True
            )
            value = default
        
        return value


class subcommands:
    '''
    this class serves only as a sort of grouping
    for the functions associated with the various
    command line options. Hence the lowercase name
    and all the methods being static
    '''
    @staticmethod
    def add_track(parser):
        parser.add_argument('name', nargs = '?')
            # if not provided, present a numbered list of all tracks and let the
            # user choose by number
        args = parser.parse_args()
        
        # what you have to do here:
        # - run `git show HEAD:{args.input}` (make sure you understand what HEAD
        #   is first)
        # - take the output of that and store it in `rpp_HEAD` or sth like that
        # - get the contents of args.input and store them (unparsed) in
        #   `rpp_now`
        #   (or sth like that)
        # - use the `difflib` library to create a diff of the two
        # - extract the part with the node of the track requested by the user
        #   (use `Node.position_in_file` to find the line range of the track)
        # - run `git apply --cached -` (maybe with `-v` option) and use the diff
        #   as stdin for that (pay attention to line terminators and encoding!
        #   in other words, you're gonna have to make sure `text = False`)
        #
        # or alternatively:
        # - get the diff between the HEAD state and the current state of
        #   `args.input` by running `git diff --no-color {args.input}`
        # - extract the part with... (proceed as described above)
        #
        # whether you can use the ease of the second one or will have to resort
        # to the first option will depend on how much the difflib library
        # offers. if it offers full-on high-level diff objects then it would
        # probably be smartest to use those
        
        reaperProject = ReaperProject.fromFilepath(args.input)
        
        for match in reaperProject.findall('TRACK', recursive = True):
            if match['NAME'] == [args.name]:
                track = match
    
    @staticmethod
    def paths(parser):
        parser.add_argument('-a', '--absolute', action = 'store_true')
        parser.add_argument('-r', '--relative', action = 'store_true')
        parser.add_argument('-s', '--sort', action = 'store_true')
            # this is a case-insensitive sort
        parser.add_argument('-u', '--remove-duplicates', action = 'store_true')
        parser.add_argument('--render-file', action = 'store_true')
        parser.add_argument('--record-path', action = 'store_true')
        parser.add_argument('--all', action = 'store_true')
            # equivalent to `--render-file --record-path`
        parser.add_argument('-f', '--format', action = 'store', type = str.upper, choices = ['POSIX', 'UNIX', 'DOS', 'WINDOWS'])
            # POSIX/UNIX or DOS/WINDOWS
            # default value same as in input, otherwise dependent on operating system
            # have a look at maybe using the class argparse.ArgumentError
            # for when it receives disallowed input
            # you should be able to achieve this by just converting the PurePath
            # instances to a PurePosixPath or a PureWindowsPath, respectively
        parser.add_argument('-d', '--delimiter', action = 'store', default = '\n')
        parser.add_argument('-e', '--escape', action = 'store_true')
            # it should be noted that this only really works for the UNIX shell
        args = parser.parse_args()
        
        def format(path):
            if path is not None:
                if args.format in ('POSIX', 'UNIX'):
                    formatted = str(pathlib.PurePosixPath(path))
                elif args.format in ('DOS', 'WINDOWS'):
                    formatted = str(pathlib.PureWindowsPath(path))
                else:
                    formatted = str(path)
                if args.escape:
                    formatted = shlex.quote(formatted)
            else:
                formatted = '' if args.quiet else '<empty path>'
            return formatted
        
        reaperProject = ReaperProject.fromFilepath(args.input)
        source_paths = reaperProject.get_source_paths()
        
        if args.sort:
            source_paths.sort()
                # perhaps you should sort the list inluding render_path and
                # record_path or, if that's too difficult, put a disclaimer in
                # the help message that things like --sort, --remove-duplicates,
                # --absolute and --relative don't affect the render file and the
                # record path
        if args.remove_duplicates:
            source_paths = list(OrderedDict.fromkeys(source_paths))
                # this removes duplicates while maintaining order
        
        if args.all:
            args.render_file = True
            args.record_path = True
        
        if args.render_file:
            render_path = Path(reaperProject.root['RENDER_FILE'][0])
        if args.record_path:
            primary_recording_path = Path(reaperProject.root['RECORD_PATH'][0])
            secondary_recording_path = Path(reaperProject.root['RECORD_PATH'][1])
        
        if args.absolute:
            source_paths = filter(pathlib.PurePath.is_absolute, source_paths)
        elif args.relative:
            source_paths = filterfalse(pathlib.PurePath.is_absolute, source_paths)
        
        if args.render_file:
            if not args.quiet:
                print(f'Render file: ' + format(render_path))
            elif render_path:
                print(format(render_path), end = args.delimiter)
        if args.record_path:
            if not args.quiet:
                print(f'Primary recording path: ' + format(primary_recording_path))
                print(f'Secondary recording path: ' + format(secondary_recording_path))
            else:
                if primary_recording_path:
                    print(format(primary_recording_path), end = args.delimiter)
                if secondary_recording_path:
                    print(format(secondary_recording_path), end = args.delimiter)
        
        if not args.quiet:
            print(f'File paths found in {args.input}:')
        print(args.delimiter.join(map(format, source_paths)))
            # for some reason, if this is called with `-d ' '` or `-d $'\n'`, it
            # raises an error: git scythe paths: error: argument -d/--delimiter:
            # expected one argument
    
    @staticmethod
    def cleanup(parser):
        parser.add_argument('directory', nargs = '?', default = '.')
            # default should actually be the path of the rpp file i suppose
        parser.add_argument('--dry-run', action = 'store_true')
        args = parser.parse_args()
        
        reaperProject = ReaperProject.fromFilepath(args.input)
        source_paths = reaperProject.get_source_paths()
        render_path = reaperProject.root['RENDER_FILE'][0]
        
        for dirpath, dirnames, filenames in os.walk(args.directory):
            # what you're gonna have to do here:
            # canonicalize both `filenames` as well as `source_paths` and
            # `render_path`, then check which `filenames` do not appear in
            # `source_paths` or match `render_path`. perhaps provide an option
            # to restrict the search to media files (based on the file
            # extension)
            pass
    
    @staticmethod
    def test(parser):
        args = parser.parse_args()
        output = args.input + '.copy'
        
        print(f'Parsing {args.input}...')
        reaperProject = ReaperProject.fromFilepath(args.input)
        print(f'Creating {output}...')
        with open(output, mode = 'x', encoding = reaperProject.encoding, newline = reaperProject.line_terminator) as file:
            reaperProject.dump(file = file)
        
        diff = subprocess.run(
            ['diff', '-qs', args.input, output],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            universal_newlines = True
        )
        if diff.returncode == 0:
            print('Success!', diff.stdout.strip())
            os.remove(output)
        else:
            print('Oh no! Diff failed with the following output:')
            sys.exit(diff.stdout.strip())

if __name__ == '__main__':
    parser = argparse.ArgumentParser('git scythe', add_help = False)
    parser.add_argument('--version', version = '0.0', action = 'version')
    parser.add_argument('--help', action = 'help')
    
    commands = {'add-track': subcommands.add_track,
                'paths': subcommands.paths,
                'cleanup': subcommands.cleanup,
                'test': subcommands.test}
    subparsers = parser.add_subparsers(parser_class = ScytheParser, metavar = '|'.join(commands))
    for command_name, command in commands.items():
        subparser = subparsers.add_parser(command_name, cmd = command)
        subparser.set_defaults(which = subparser)
    
    if len(sys.argv) == 1 or sys.argv[1] == 'help':
        parser.print_help()
        exit()
    
    args, rest = parser.parse_known_args()
    if hasattr(args, 'which'):
        args.which.run()
    else:
        parser.parse_args(rest)
