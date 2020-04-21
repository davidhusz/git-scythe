#!/usr/bin/env python3


# TODO:
# find out remaining types of lines
# useful command for that:
#	find . -name *.RPP -size -100k -exec py ~/Documents/git-scythe/git-scythe.py tree {} > /dev/null \;
# what about 'TAKE'?
# handle empty input files gracefully


import sys
import os
import subprocess
import re
import shlex
from glob import glob
import argparse


class Tree:
	def __init__(self, inputstr = None):
		if inputstr:
			generator = (line for line in inputstr.splitlines())
			try:
				return Tree.fromGenerator(generator)
			except AssertionError:
				sys.exit('this does not seem to be a reaper project')

	@classmethod
	def fromFilepath(cls, filepath):
		with open(filepath) as file:
			try:
				return cls.fromGenerator(file)
			except AssertionError:
				sys.exit(f'{filepath} does not seem to be a reaper project')

	@classmethod
	def fromGenerator(cls, generator):
		firstline = next(generator)
		assert firstline.startswith('<REAPER_PROJECT'), 'not a reaper project'
		tree = cls()
		tree.root = Node(firstline, generator)
		return tree
	
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

	def print(self):
		self.root.print()


class Node:
	def __init__(self, firstline, generator):
		self.name, self.tags = re.match('^ *<([A-Z0-9_]+)(.*)$', firstline).groups()
		self.contents = [firstline]
		self.tags = shlex.split(self.tags)
		self.attributes = {}
#		self.attributes = []

		for line in generator:
			opening_tag = re.match('^ *<([A-Z0-9_]+)(.*)$', line)
			closing_tag = re.match('^ *>$', line)

			if opening_tag:
				child = Node(line, generator)
				self.contents.append(child)
			elif closing_tag:
				self.contents.append(line)
				break
			else:
				self.contents.append(line)
				self.parse_line(line)

	def parse_line(self, line):
		attribute = re.match('^ +([A-Z0-9_]+) (.*)$', line)
		base64 = re.match('^ +[A-Za-z0-9+/]+={0,2}$', line)
		midi = re.match('^ +([Ee]) (.*)$', line)
		code = re.match('^ +\|(.*)$', line)
		fx_params = re.match('^ +(.*)(?:- )+$', line)

		if midi:
			pass
		elif attribute:
			name, values = attribute.groups()
			values = shlex.split(values)
			self.attributes[name] = values
#			new_attribute = Attribute(name, values)
#			self.attributes.append(new_attribute)
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
	
	def __getitem__(self, key):
		if key in self.attributes:
			attribute = self.attributes[key]
			if len(attribute) == 1:
				return attribute[0]
			else:
				return attribute
		else:
			raise KeyError('ya dun goofed')
	
	def __contains__(self, key):
		return key in self.attributes
	
	def __getattr__(self, name):
		# return self.__getitem__(name)
		pass

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

	# def print(self, level = 0):
		# print(
		# 	'  ' * level +
		# 	'<' + self.name +
		# 	' ' + ' '.join(self.tags)
		# )
		# for name, values in self.attributes.items():
		# 	print(
		# 		'  ' * (level + 1) +
		# 		name +
		# 		' ' + ' '.join(values)
		# 	)
		# for child in self.children:
		# 	child.print(level + 1)
		# print('  ' * level + '>')
	
	def print(self):
		for content in self.contents:
			if isinstance(content, type(self)):
				content.print()
			else:
				print(content, end = '')


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
				capture_output = True,
				check = True
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
	def tree():
		args = ScytheParser().parse_args()

		tree = Tree.fromFilepath(args.input)
		print(f'Tree for {args.input}:')
		tree.print()

	@staticmethod
	def paths():
		parser = ScytheParser()
		parser.add_argument('--relativize', action = 'store_true')
		parser.add_argument('--depth', type = int, default = 1)
		args = parser.parse_args()

		tree = Tree.fromFilepath(args.input)
		print(f'File paths found in {args.input}:')
		for source in tree.findall('REAPER_PROJECT/TRACK/ITEM/SOURCE'):  # need to account for tags FILE, RENDER_FILE and RECORD_PATH
		# alternatively:
		# for source in tree.findall('SOURCE', recursive = True):
			if 'FILE' in source:
				print(source['FILE'])

	@staticmethod
	def help(file = sys.stdout):
		print('help page should be printed here', file = file)


if __name__ == '__main__':
	if len(sys.argv) > 1:
		module = sys.argv[1]
	else:
		module = 'help'

	if module == 'tree':
		modules.tree()
	elif module == 'paths':
		modules.paths()
	elif module == 'help':
		modules.help()
	else:
		print('unknown module:', module, file = sys.stderr)
		modules.help(file = sys.stderr)
