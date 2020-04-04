#!/usr/bin/env python3


# TODO:
# find out remaining types of lines
# useful command for that:
#	find . -name *.RPP -size -100k -exec py ~/Documents/git-scythe/git-scythe.py tree {} > /dev/null \;
# what about 'TAKE'?


import sys
import re
from shlex import split
import argparse


class Tree:
	def __init__(self, inputstr = None):
		if inputstr:
			generator = (line for line in inputstr.splitlines())
			return Tree.fromGenerator(generator)
	
	@classmethod
	def fromFilepath(cls, filepath):
		with open(filepath) as file:
			return cls.fromGenerator(file)
	
	@classmethod
	def fromGenerator(cls, generator):
		firstline = next(generator)
		if firstline.startswith('<REAPER_PROJECT'):
			tree_instance = cls()
			tree_instance.root = Node(firstline, generator)
			return tree_instance
		else:
			sys.exit('this does not seem to be a reaper file')
	
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


def tree(arguments):
	parser = argparse.ArgumentParser()
	parser.add_argument('input')
	args = parser.parse_args(arguments)
	
	Tree.fromFilepath(args.input).print()


if __name__ == '__main__':
	if sys.argv[1] == 'tree':
		tree(sys.argv[2:])
