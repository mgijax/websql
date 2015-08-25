# Name: config.py
# Purpose: provide access to parameters defined in a Configuration file
# On Import: 
#	1. searches back up through up to five directory levels to find the
#		nearest instance of a "Configuration" file.
#	2. loads the config file
#	3. adds the WI_PATH/lib/python directory to sys.path

import os
import sys
import string

# if possible, find the standard MGI libraries and import the module that
# turns off deprecation errors

try:
	fp = open('library.path', 'r')
	line = fp.readline()
	fp.close()

	sys.path.append (string.strip (line))

	import ignoreDeprecation
except:
	pass

import regex

def find_path (
	s = 'Configuration',	# string pathname for which we're looking
	max = 5			# number of parent directory levels to search
	):
	# Purpose: find a relative path to the "nearest" instance of 's', up
	#	to 'max' parent directories away
	# Returns: relative path to 's'
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing
	# Notes: This is a recursive function.  If 's' exists, we simply
	#	return it.  If not, and if 'max' is zero, then we've searched
	#	far enough, and we just return None.  Otherwise, look in the
	#	parent directory of 's'.

	if os.path.exists (s):
		return s
	elif max == 0:
		return None
	else:
		return find_path (os.path.join (os.pardir, s), max - 1)

# global variables:
# -----------------

TEXT_FILE = find_path ('Configuration')		# path to config file
CONFIG = {}					# configuration info


def readConfigFile (
	source		# pathname to config file to read
	):
	# Purpose: read the configuration file at 'source', parse it,
	#	store values in a dictionary
	# Returns: the dictionary parsed from 'source'
	# Assumes: 'source' exists
	# Effects: reads from the file system
	# Throws: IOError if there are problems reading

	fp = open (source, 'r')
	lines = fp.readlines ()
	fp.close ()

	ignore_line = regex.compile ('[ \t]*#')		# comment line
	data_line = regex.compile ('[ \t]*'
				'\([^ \t]+\)'
				'[ \t]*\(.*\)')	
	dict = {}

	for line in lines:
		if ignore_line.match (line) == -1:
			if data_line.match (line) != -1:
				(parameter, value) = data_line.group (1,2)
				dict [string.upper (parameter)] = value
	return dict


def lookup (
	parameter	# string parameter name to look up
	):
	# Purpose: lookup the value of the specified 'parameter'
	# Returns: string parameter value, or None if that parameter does not
	#	exist in the config file
	# Assumes: nothing
	# Effects: nothing
	# Throws: nothing

	parm = string.upper (parameter)
	if CONFIG.has_key (parm):
		return CONFIG [parm]
	else:
		return None


# ********** begin module initialization **********

# if we didn't file a config file, then TEXT_FILE will be None.  Let's just
# make sure that it exists...

if (TEXT_FILE is None) or (not os.path.exists (TEXT_FILE)):
	print "missing config file in %s" % TEXT_FILE
	sys.exit (-1)

CONFIG = readConfigFile (TEXT_FILE)

# add the database directory library directory to the python path

if lookup('DBDIR') not in sys.path:
	sys.path.insert (0, lookup('DBDIR'))

# ********** end of module initialization **********
