# library for working with server-database mapping files...

import copy
import string

class ServerMap:
	def __init__ (self, filename):
		self.data = {}
		self.def_server = ''
		self.def_database = ''
		try:
			fp = open (filename, 'r')
			lines = map (string.strip, fp.readlines())
			fp.close ()
		except IOError:
			lines = []
		for line in lines:
			if len(line) == 0 or line[0] == '#':
				continue
			[ server, other ] = string.split (line, ':')
			server = string.strip (server)
			databases = string.split (other)

			if not self.data.has_key (server):
				self.data [server] = {}
			for db in databases:
				if db[0] == '*':
					db = db[1:]
					self.def_server = server
					self.def_database = db
				self.data [server][db] = 1
		return

	def default_server (self):
		return self.def_server

	def default_database (self):
		return self.def_database

	def valid (self, server, database):
		if not self.data.has_key (server):
			return 0
		return self.data[server].has_key (database)

	def list (self):
		list = []
		servers = self.data.keys()
		servers.sort ()
		for server in servers:
			databases = self.data[server].keys()
			databases.sort ()
			for db in databases:
				list.append ('%s:%s' % (server, db))
		return list

	def html_list (self):
		items = map (lambda s: '<LI> %s' % s, self.list())
		return [ '<UL>' ] + items + [ '</UL>' ]

	def nested_dict (self):
		return copy.deepcopy (self.data)
