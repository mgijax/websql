# defines functions to create javascript-enabled pulldowns:

import string

class Pulldowns:
	def __init__ (self, servermap):
		# servermap should be a ServerMap object

		self.data = servermap.nested_dict()
		return

	def database (self, selected_server = None, selected_database = None):
		servers = self.data.keys()
		servers.sort()
		if selected_server is None:
			selected_server = servers[0]
		databases = self.data[selected_server].keys()
		databases.sort ()
		if selected_database is None:
			selected_database = databases[0]
		list = [ '<SELECT NAME=database>' ]
		for db in databases:
			if db == selected_database:
				list.append ('<OPTION SELECTED> %s' % db)
			else:
				list.append ('<OPTION> %s' % db)
		list.append ('</SELECT>')
		return string.join (list, '\n')

	def server (self, selected_server = None):
		servers = self.data.keys()
		servers.sort()
		if selected_server is None:
			selected_server = servers[0]
		list = [ '<SELECT NAME=server onChange="do_server(server.options[server.selectedIndex].text)">' ]
		servers = self.data.keys()
		servers.sort()
		for srv in servers:
			if srv == selected_server:
				list.append ('<OPTION SELECTED> %s' % srv)
			else:
				list.append ('<OPTION> %s' % srv)
		list.append ('</SELECT>')
		return string.join (list, '\n')

	def code (self):
		js = [	'<SCRIPT>',
			'function populate (dbs, values) {',
			' // dbs is a select object for the databases',
			' // values is an Array of strings',
			' var selectedItem = dbs.options[dbs.options.selectedIndex].text',
			' var selectedAny = false',
			' for (var i=dbs.options.length - 1; i >= 0; i--) {',
			'  dbs.options[i] = null',
			' }',
			' for (var i=0; i < values.length; i++) {',
			'  dbs.options[i] = new Option(values[i],values[i])',
			'  if (values[i] == selectedItem) {',
			'   dbs.options[i].selected = true',
			'   selectedAny = true',
			'  }',
			' }',
			' if ((dbs.options.length >= 1) && !selectedAny) {',
			'  dbs.options[0].selected=true',
			' }',
			'}',
			'',
			'function do_server (server) {',
			' // server is a string identifying which server',
			' var dbs = document.forms[0].database',
			]

		for server in self.data.keys():
			databases = self.data[server].keys()
			databases.sort()
			js.append (' if (server=="%s") {' % server)
			js.append ('  populate (dbs, new Array ("%s"))' % \
				string.join (databases, '","'))
			js.append (' }')
		js.append ('}')
		js = js + [
			'function doReset () {',
			'  do_server (document.forms[0].origserver.value)',
			'}',
			]
		js.append ('</SCRIPT>')
		return string.join (js, '\n')

