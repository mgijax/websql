# defines functions to create javascript-enabled pulldowns:

import string
import sys

class Pulldowns:
	def __init__ (self, servermap):
		# servermap should be a ServerMap object

		self.data = servermap.nested_dict()
		return

	def database (self,
		selected_dbms = None,
		selected_server = None, 
		selected_database = None
		):
		if selected_dbms is None:
			dbms_list = self.data.keys()
			dbms_list.sort()
			selected_dbms = dbms_list[0]

		if selected_server is None:
			servers = self.data[selected_dbms].keys()
			servers.sort()
			selected_server = servers[0]
		
		databases = self.data[selected_dbms][selected_server].keys()
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

	def server (self,
		selected_dbms = None,
		selected_server = None
		):
		if selected_dbms is None:
			dbms_list = self.data.keys()
			dbms_list.sort()
			selected_dbms = dbms_list[0]

		servers = self.data[selected_dbms].keys()
		servers.sort()
		if selected_server is None:
			selected_server = servers[0]

		list = [ '<SELECT NAME=server onChange="do_server(DBMS1.options[DBMS1.selectedIndex].text, server.options[server.selectedIndex].text)">' ]
		servers = self.data[selected_dbms].keys()
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
			'function set (dbs, value) {',
			' for (var i=0; i < dbs.options.length; i++) {',
			'  if (dbs.options[i].text == value) {',
			'   dbs.options[i].selected=true;',
			'   }',
			'  }',
			' }',
			'function populate (dbs, values) {',
			' // dbs is a select object for the databases or servers',
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
			'function do_server (dbms, server) {',
			' // server is a string identifying which server',
			' var dbs = document.forms[0].database',
			]

		for dbms in self.data.keys():
		    for server in self.data[dbms].keys():
			databases = self.data[dbms][server].keys()
			databases.sort()
			js.append (' if ((dbms == "%s") && (server=="%s")) {' % (dbms, server))
			js.append ('  populate (dbs, new Array ("%s"))' % \
				string.join (databases, '","'))
			js.append (' }')
		js.append ('}')

		js = js + [
			'function do_dbms (dbms) {',
			' // dbms is a string identifying which RDBMS',
			' var servers = document.forms[0].server',
			]
		for dbms in self.data.keys():
			servers = self.data[dbms].keys()
			servers.sort()
			js.append (' if (dbms=="%s") { ' % dbms)
			js.append ('  populate (servers, new Array ("%s"))' %\
				'","'.join (servers))
			js.append (' }')
		js.append (' do_server(document.forms[0].DBMS1.options[document.forms[0].DBMS1.selectedIndex].text, document.forms[0].server.options[document.forms[0].server.selectedIndex].text);')
		js.append ('}')

		js = js + [
			'function doReset () {',
			'  do_dbms (document.forms[0].origdbms.value);',
			'  do_server (document.forms[0].origdbms.value, document.forms[0].origserver.value)',
			'  set (databases, document.forms[0].origdatabase.value)',
			'}',
			'function browse() {',
			'var r = "rdbms=" + document.forms[0].DBMS1.options[document.forms[0].DBMS1.selectedIndex].text;',
			'var d = "&database=" + document.forms[0].database.options[document.forms[0].database.selectedIndex].text;',
			'var s = "&server=" + document.forms[0].server.options[document.forms[0].server.selectedIndex].text;',
			'window.open ("browse.cgi?" + r + d + s);',
			'}',
			]
		js.append ('</SCRIPT>')
		return string.join (js, '\n')

