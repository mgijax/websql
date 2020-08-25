# defines functions to create javascript-enabled pulldowns:

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
                        dbms_list = list(self.data.keys())
                        dbms_list.sort()
                        selected_dbms = dbms_list[0]

                if selected_server is None:
                        servers = list(self.data[selected_dbms].keys())
                        servers.sort()
                        selected_server = servers[0]
                
                databases = list(self.data[selected_dbms][selected_server].keys())
                databases.sort ()
                if selected_database is None:
                        selected_database = databases[0]

                myList = [ '<SELECT NAME=database>' ]
                for db in databases:
                        if db == selected_database:
                                myList.append ('<OPTION SELECTED> %s' % db)
                        else:
                                myList.append ('<OPTION> %s' % db)
                myList.append ('</SELECT>')
                return '\n'.join (myList)

        def server (self,
                selected_dbms = None,
                selected_server = None
                ):
                if selected_dbms is None:
                        dbms_list = list(self.data.keys())
                        dbms_list.sort()
                        selected_dbms = dbms_list[0]

                servers = list(self.data[selected_dbms].keys())
                servers.sort()
                if selected_server is None:
                        selected_server = servers[0]

                myList = [ '<SELECT NAME=server onChange="do_server(server.options[server.selectedIndex].text)">' ]
                servers = list(self.data[selected_dbms].keys())
                servers.sort()
                for srv in servers:
                        if srv == selected_server:
                                myList.append ('<OPTION SELECTED> %s' % srv)
                        else:
                                myList.append ('<OPTION> %s' % srv)
                myList.append ('</SELECT>')
                return '\n'.join (myList)

        def code (self):
                js = [  '<SCRIPT>',
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
                        'function do_server (server) {',
                        ' // server is a string identifying which server',
                        ' var dbs = document.forms[0].database',
                        ]

                for dbms in list(self.data.keys()):
                    for server in list(self.data[dbms].keys()):
                        databases = list(self.data[dbms][server].keys())
                        databases.sort()
                        js.append (' if (server=="%s") {' % server)
                        js.append ('  populate (dbs, new Array ("%s"))' % \
                                '","'.join (databases))
                        js.append (' }')
                js.append ('}')

                js = js + [
                        'function doReset () {',
                        '  do_server (document.forms[0].origdbms.value, document.forms[0].origserver.value)',
                        '  set (databases, document.forms[0].origdatabase.value)',
                        '}',
                        ]
                js.append ('</SCRIPT>')
                return '\n'.join (js)

