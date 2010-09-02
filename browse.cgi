#!./python

# allows simple, generic table browsing for Sybase, Postgres, and MySQL
# databases

import os
import cgi
import sys
import types
import string
import traceback

if '.' not in sys.path:
	sys.path.insert (0, '.')

import config
import db
import dbManager

VERSION = '1.1'			# WebSQL version

RDBMS = None			# sybase, postgres, or mysql
SERVER = None			# database server name
DATABASE = None			# name of particular database
TABLE = None			# name of database table

class Table:
	def __init__ (self, columns, rows):
		self.cols = columns
		self.rows = rows
		return

	def html (self):
		if len(self.rows) == 0:
			return ''

		lines = [ '<TABLE border=1>' ]

		s = '<TR><TH>Row #'
		for col in self.cols:
			s = s + '<TH>%s' % col
		lines.append (s)

		ct = 0
		for row in self.rows:
			s = '<TR>'
			ct = ct + 1
			s = s + '<TD>%d' % ct
#			print self.cols
#			print '<HR>'
#			print self.rows
			for col in range (0, len(self.cols)):
				val_type = type (row[col])
				if val_type == types.IntType:
					s = s + '<TD align=right>%d' % \
						row[col]
				elif val_type == types.FloatType:
					s = s + '<TD align=right>%f' % \
						row[col]
				elif val_type == types.NoneType:
					s = s + '<TD>null'
				elif self.cols[col] == 'tableName':
					s = s + '<TD><A HREF="browse.cgi?rdbms=%s&server=%s&database=%s&table=%s">%s</A>' % (RDBMS, SERVER, DATABASE, row[col], row[col])
				else:
					s = s + '<TD>%s' % \
						cgi.escape(str(row[col]))
			lines.append (s)
		lines.append ('</TABLE>')
		return string.join (lines, '\n')

def results (tableObj):
	list = []
	if TABLE:
		list.append ('%s table:' % TABLE)
	else:
		list.append ('All tables:')
	list.append (tableObj.html())

	return '\n'.join (list)

def sybaseResults():
	db.set_sqlLogin (config.lookup('SYBASE_USER'),
		config.lookup('SYBASE_PASSWORD'), SERVER, DATABASE)
	db.useOneConnection(1)

	if not TABLE:
		cmd = '''select name as tableName
			from sysobjects
			where type = "U"
			order by name'''
		columns = [ 'tableName' ]
	else:
		cmd = '''select o.name as tableName,
			    o.id as tableID,
			    c.name as columnName,
			    c.colid as columnId,
			    ltrim(convert(char(3), c.length)) as size,
			    t.name as columnType,
			    nullable = case
				when c.status = 0 then 'not null'
				when c.status != 0 then 'null'
				end
			from sysobjects o, syscolumns c, systypes t
			where o.name = "%s"
				and o.type = "U"
				and o.id = c.id
				and c.userType = t.userType
			order by c.colid''' % TABLE
		columns = [ 'columnName', 'columnType', 'nullable' ]

	resultset = db.sql (cmd, 'auto')

	rows = [] 
	if TABLE:
		for r in resultset:
			row = []
			row.append (r['columnName'])
			if r['columnType'].lower() in [ 'char', 'varchar' ]:
				row.append ('%s(%s)' % (r['columnType'],
					r['size']) )
			else:
				row.append (r['columnType'])
			row.append (r['nullable'])
			rows.append (row)
	else:
		for r in resultset:
			rows.append ([ r['tableName'] ])

	return results(Table(columns, rows))

def mysqlResults():
	dbm = dbManager.mysqlManager (SERVER, DATABASE,
		config.lookup('MYSQL_USER'),
		config.lookup('MYSQL_PASSWORD') )
	if not TABLE:
		# returns 1 field
		cmd = 'show tables'
		columns = [ 'tableName' ]
	else:
		cmd = 'desc %s' % TABLE
		columns = [ 'columnName', 'columnType', 'nullable' ]

	resultColumns, resultRows = dbm.execute (cmd)

	rows = []

	if TABLE:
		for r in resultRows:
			f = resultColumns.index ('Field')
			t = resultColumns.index ('Type')
			n = resultColumns.index ('Null')

			row = [ r[f], r[t] ]
			if r[n].lower() == 'no':
				row.append ('not null')
			else:
				row.append ('null')

			rows.append (row)
	else:
		rows = resultRows

	return results(Table(columns, rows)) 

def postgresResults():
	dbm = dbManager.postgresManager (SERVER, DATABASE,
		config.lookup('POSTGRES_USER'),
		config.lookup('POSTGRES_PASSWORD') )

	if not TABLE:
		cmd = '''select table_name
			from information_schema.tables
			where table_type = 'BASE TABLE'
				and table_schema = 'public'
			order by table_name'''
		columns = [ 'tableName' ]
	else:
		cmd = '''select column_name, ordinal_position, is_nullable,
				udt_name, character_maximum_length
			from information_schema.columns
			where table_name = '%s'
				and table_schema = 'public'
			order by ordinal_position''' % TABLE
		columns = [ 'columnName', 'columnType', 'nullable' ]

	resultColumns, resultRows = dbm.execute (cmd)

	rows = []

	if TABLE:
		for r in resultRows:
			c = resultColumns.index ('column_name')
			d = resultColumns.index ('udt_name')
			n = resultColumns.index ('is_nullable')
			m = resultColumns.index ('character_maximum_length')

			row = [ r[c] ]
			if r[d].lower() in [ 'char', 'varchar' ]:
				row.append ('%s(%s)' % (r[d], r[m]))
			else:
				row.append (r[d])

			if r[n].lower() == 'no':
				row.append ('not null')
			else:
				row.append ('null')

			rows.append (row)
	else:
		rows = resultRows

	return results(Table(columns, rows)) 

def process_parms ():
	global RDBMS, SERVER, DATABASE, TABLE

	fs = cgi.FieldStorage()
	for k in fs.keys():
		val = fs[k].value

		if k == 'rdbms':
			RDBMS = val
		elif k == 'server':
			SERVER = val
		elif k == 'database':
			DATABASE = val
		elif k == 'table':
			TABLE = val
	return

title = 'websql %s mini-browser' % VERSION
header = '<HTML><HEAD><TITLE>%s</TITLE></HEAD><BODY><H3>%s</H3>' % \
	(title, title)
footer = '</BODY></HTML>'

if __name__ == '__main__':
	print 'Content-type: text/html\n'

	process_parms()

	noDriver = None
	if (RDBMS == 'mysql') and (not dbManager.LOADED_MYSQL_DRIVER):
		noDriver = 'Could not find the MySQLdb module'
	elif (RDBMS == 'postgres') and \
			(not dbManager.LOADED_POSTGRES_DRIVER):
		noDriver = 'Could not find the psycopg2 module for Postgres'

	if noDriver:
		print header
		print 'Failed: "%s"' % noDriver
		print footer
		sys.exit(0)

	print header
	print 'Browsing %s : %s..%s' % (RDBMS, SERVER, DATABASE)
	print '<HR>'

	if RDBMS == 'sybase':
		print sybaseResults()
	elif RDBMS == 'mysql':
		print mysqlResults()
	elif RDBMS == 'postgres':
		print postgresResults()
	if TABLE:
		print '<HR>Back to <A HREF="browse.cgi?rdbms=%s&server=%s&database=%s">All Tables</A>' % (RDBMS, SERVER, DATABASE)
	print footer
