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
from shlex import split
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

	def print(self):
		self.root.print()


class Node:
	def __init__(self, firstline, generator):
		self.name, self.tags = re.match('^ *<([A-Z0-9_]+)(.*)$', firstline).groups()
		self.tags = split(self.tags)
		self.attributes = {}
#		self.attributes = []
		self.children = []

		for line in generator:
			opening_tag = re.match('^ *<([A-Z0-9_]+)(.*)$', line)
			closing_tag = re.match('^ *>$', line)

			if opening_tag:
				child = Node(line, generator)
				self.children.append(child)
			elif closing_tag:
				break
			else:
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
			values = split(values)
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

	def __repr__(self):
		return f'<Node "{self.name}">'

	def find(self, query, recursive = False):
		if '/' in query:
			topitem, query = query.split('/', maxsplit = 1)
			for topmatch in self.find(topitem):
				for match in topmatch.find(query):
					yield match
		else:
			for child in self.children:
				if recursive:
					for match in child.find(query, recursive = True):
						yield match
				if child.name == query:
					yield child

	def print(self, level = 0):
		print(
			'  ' * level +
			'<' + self.name +
			' ' + ' '.join(self.tags)
		)
		for name, values in self.attributes.items():
			print(
				'  ' * (level + 1) +
				name +
				' ' + ' '.join(values)
			)
		for child in self.children:
			child.print(level + 1)
		print('  ' * level + '>')


class Attribute:
	def __init__(self, name, values):
		self.name = name
		self.values = values

	def __repr__(self):
		return f'<Attribute "{self.name}">'


class ScytheParser(argparse.ArgumentParser):
	def __init__(self):
		super().__init__(add_help = False)
		self.add_argument('input', nargs = '?')

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
		for source in tree.root.find('TRACK/ITEM/SOURCE'):
			if 'FILE' in source.attributes:
				print(source.attributes['FILE'][0])

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
		print('unknown module', file = sys.stderr)
		modules.help(file = sys.stderr)
