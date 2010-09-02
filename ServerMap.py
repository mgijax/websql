# library for working with server-database mapping files...

import copy
import string
import sys

class ServerMap:
	def __init__ (self, filename):
		self.data = {}
		self.def_dbms = ''
		self.def_server = ''
		self.def_database = ''
		try:
			fp = open (filename, 'r')
			lines = map (string.strip, fp.readlines())
			fp.close ()
		except IOError:
			lines = []

		dbms = ''
		for line in lines:
			if len(line) == 0 or line[0] == '#':
				continue
			if line[0] == '[':
				dbms = line[1:-1]
				continue
			[ server, other ] = string.split (line, ':')
			server = string.strip (server)
			databases = string.split (other)

			if not self.data.has_key (dbms):
				self.data[dbms] = {}
			if not self.data[dbms].has_key (server):
				self.data[dbms][server] = {}
			for db in databases:
				if db[0] == '*':
					db = db[1:]
					self.def_server = server
					self.def_database = db
					self.def_dbms = dbms
				self.data[dbms][server][db] = 1
		return

	def default_dbms (self):
		return self.def_dbms

	def default_server (self):
		return self.def_server

	def default_database (self):
		return self.def_database

	def valid (self, dbms, server, database):
		if not self.data.has_key(dbms):
			return 0
		if not self.data[dbms].has_key (server):
			return 0
		return self.data[dbms][server].has_key (database)

	def list (self):
		list = []
		dbms_list = self.data.keys()
		for dbms in dbms_list:
			servers = self.data[dbms].keys()
			servers.sort ()
			for server in servers:
				databases = self.data[dbms][server].keys()
				databases.sort ()
				for db in databases:
					list.append ('%s:%s:%s' % (dbms,
						server, db))
		return list

	def html_list (self):
		items = map (lambda s: '<LI> %s' % s, self.list())
		return [ '<UL>' ] + items + [ '</UL>' ]

	def nested_dict (self):
		return copy.deepcopy (self.data)
