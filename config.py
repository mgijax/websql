# Name: config.py
# Purpose: provide access to parameters defined in a Configuration file
# On Import: 
#	1. searches back up through up to five directory levels to find the
#		nearest instance of a "Configuration" file.
#	2. tests to see if a pickled version of the file exists and is at
#		least as recent as the plain text one
#	3. if so, loads the pickled version
#	4. if not, loads the plain text one and save a pickled version
#	5. adds the WI_PATH/lib/python directory to sys.path
#
# Notes: As regular expressions are a bit slow, I decided to store a pickled
#	version of the data structure which contains the configuration info.
#	This way, as long as it is kept up-to-date, we don't need to parse
#	the config file each time this module is imported -- only once after
#	each update to the config file.  In other instances, we can just
#	load in the data structure directly without regular expression
#	parsing.

import os
import sys
import regex
import pickle
import string

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
PICKLE_FILE = TEXT_FILE + '.pkl'		# path to pickled version
CONFIG = {}					# configuration info


def generate_Pickle_File (
	source,		# pathname to config file to read
	dest		# pathname to overwrite with pickled config data
	):
	# Purpose: read the configuration file at 'source', parse it,
	#	store values in a dictionary, and pickle it out to 'dest'
	# Returns: the dictionary parsed from 'source'
	# Assumes: 'source' exists, and 'dest' is writeable
	# Effects: overwrites 'dest'
	# Throws: IOError if there are problems reading/writing

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
	fp = open (dest, 'w')
	pickle.dump (dict, fp)				# save to pickled file
	fp.close ()
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

# See if the pickled config file is missing or is out-of-date.  If so, re-
# generate it.  If not, just load the data structure from the file.

if (not os.path.exists (PICKLE_FILE)) or \
		(os.stat (TEXT_FILE)[8] > os.stat (PICKLE_FILE)[8]):
	CONFIG = generate_Pickle_File (TEXT_FILE, PICKLE_FILE)
else:
	fp = open (PICKLE_FILE, 'r')
	CONFIG = pickle.load (fp)
	fp.close ()

# add the database directory library directory to the python path

if lookup('DBDIR') not in sys.path:
	sys.path.insert (0, lookup('DBDIR'))

# export the SYBASE and LD_LIBRARY_PATH variables

for var in [ 'SYBASE', 'LD_LIBRARY_PATH' ]:
	if lookup(var) != None:
		os.environ[var] = lookup(var)

# ********** end of module initialization **********
