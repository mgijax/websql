#!./python

# allows generic web-based queries and formats results in table(s)

import os
import cgi
import sys
import types
import string
import traceback

if '.' not in sys.path:
	sys.path.insert (0, '.')

import config
import Pulldowns
import ServerMap
import db

VERSION = '1.0'

FORMAT = None
HTML = 1	# values for FORMAT:
TAB = 2
TEXT = 3

parms = { 'database' : 'mgd_release',
	'server' : 'MGD_DEV',
	'sql' : '',
	'format' : 'html',
	}

def alternate (s):
	# for fieldname 's', return the portion to the right of a '.', or just
	# 's' if it contains no period

	p = string.find (s, '.')
	if p < 0:
		return s
	return s[p+1:]

def fields (sql, reskeys):
	# produce a list of fields that's sorted as much as possible based on
	# the contents of 'sql'

	sql = string.strip (sql)

	if string.lower (sql[:6]) != 'select':	
		return reskeys
	elif string.lower (sql[:11]) == 'select into':
		sql = sql[11:]
	else:
		sql = sql[6:]

	p = string.find (string.lower (sql), 'from')
	if p < 0:
		return reskeys
	list = map (string.strip, string.split (sql[:p], ','))

	front = []
	for field in list:			# try ordering from front
		if field in reskeys:
			front.append (field)
			reskeys.remove (field)
		else:
			alt = alternate(field)
			if alt in reskeys:
				front.append (alt)
				reskeys.remove (alt)
			else:
				break		# roadblock from front
	end = []
	list.reverse()				# now try ordering from back
	for field in list:
		if field in reskeys:
			end.insert (0, field)
			reskeys.remove (field)
		else:
			alt = alternate(field)
			if alt in reskeys:
				end.insert (0, alt)
				reskeys.remove (alt)
			else:
				break		# roadblock from back

	return front + reskeys + end

def tabjoin (list):
	return string.join (list, '\t')

class Table:
	def __init__ (self, query, result_set):
		if len(result_set) == 0:
			self.cols = []
			self.rows = []
			return
		self.cols = fields (query, result_set[0].keys())
		self.rows = []
		for dict in result_set:
			row = []
			for col in self.cols:
				if dict[col] is None:
					row.append ('null')
				else:
					row.append (dict[col])
			self.rows.append (row)
		return

	def html (self):
		if len(self.rows) == 0:
			return ''

		lines = [ '%d records returned' % len (self.rows),
			'<TABLE border=1>' ]

		s = '<TR><TH>Row #'
		for col in self.cols:
			s = s + '<TH>%s' % col
		lines.append (s)

		ct = 0
		for row in self.rows:
			s = '<TR>'
			ct = ct + 1
			s = s + '<TD>%d' % ct
			for col in range (0, len(self.cols)):
				val_type = type (row[col])
				if val_type == types.IntType:
					s = s + '<TD align=right>%d' % \
						row[col]
				elif val_type == types.FloatType:
					s = s + '<TD align=right>%f' % \
						row[col]
				else:
					s = s + '<TD>%s' % \
						cgi.escape(str(row[col]))
			lines.append (s)
		lines.append ('</TABLE>')
		return string.join (lines, '\n')

	def tab (self):
		if len(self.rows) == 0:
			return ''

		headers = [ 'Row #' ]
		for col in self.cols:
			headers.append (col)

		datarows = []
		ct = 0
		for row in self.rows:
			ct = ct + 1
			newrow = [ str(ct) ]
			for col in range (0, len(self.cols)):
				newrow.append (str (row[col]))
			datarows.append (newrow)

		lines = [ tabjoin (headers) ] + map (tabjoin, datarows)
		return string.join (lines, '\n')

	def text (self):
		if len(self.rows) == 0:
			return ''

		headers = [ 'Row #' ]
		for col in self.cols:
			headers.append (col)

		datarows = []
		maxlens = map (len, headers)
		ct = 0
		for row in self.rows:
			ct = ct + 1
			newrow = [ str(ct) ]
			for col in range (0, len(self.cols)):
				newrow.append (str (row[col]))
				maxlens[col+1] = max (maxlens[col+1],
					len(str (row[col])))
			datarows.append (newrow)

		# build each line here using maxlens

		lines = []
		for line in [ headers ] + datarows:
			s = ''
			for i in range(len(line)):
				s = '%s %s' % (s, string.ljust (line[i], \
					maxlens[i]))
			lines.append (s)
		return string.join (lines, '\n')

class Traceback:
	def __init__ (self, tb, tracebackType = None, tracebackValue = None):
		self.traceback = tb
		self.tracebackType = tracebackType
		self.tracebackValue = tracebackValue
		return

	def html (self):
		lines = [ 'Error.  Traceback follows...<P>', ]

		needP = 0

		if self.tracebackType:
			needP = 1
			lines.append ("<B>Exception type:</B> %s<BR>" % \
				self.tracebackType)
		if self.tracebackValue:
			needP = 1
			lines.append ("<B>Exception value:</B> %s<BR>" % \
				self.tracebackValue)

		if needP == 1:
			lines.append ("<P>")

		lines = lines + [
			'<TABLE border=1>',
			'<TR><TH>File<TH>Line #<TH>Function<TH>Line'
			]
		for entry in self.traceback:
			lines.append ('<TR><TD>%s<TD>%s<TD>%s<TD>%s' % entry)
		lines.append ('</TABLE>')
		return string.join (lines, '\n')

	def text (self):
		lines = [ 'Error. Traceback follows...\n\n' ]

		needP = 0

		if self.tracebackType:
			needP = 1
			lines.append ("Exception type: %s" % \
				self.tracebackType)
		if self.tracebackValue:
			needP = 1
			lines.append ("Exception value: %s" % \
				self.tracebackValue)

		if needP == 1:
			lines.append ("\n")

		for (file, line, fn, text) in self.traceback:
			lines.append ('File:     %s' % file)
			lines.append ('Line #:   %d' % line)
			lines.append ('Function: %s' % fn)
			lines.append ('Line:     %s\n' % text)
		return string.join (lines, '\n')

def form (parms, pulldowns):
	sql = parms ['sql']
	server = parms ['server']
	database = parms ['database']
	script = os.path.basename (os.environ['SCRIPT_NAME'])
	lines = [ '<FORM ACTION="%s" METHOD=POST NAME="frm" onReset="doReset()">' % script,
		'<INPUT TYPE=submit>',
		'<INPUT TYPE=reset VALUE="Reset this Page">',
		"<INPUT TYPE=button onClick='window.location.href=%s' VALUE='Start Over'>"\
			% ('"%s"' % script),
		'<TABLE BORDER=0 WIDTH=90%><TR>',
		'  <TD align=center>Server: %s' % pulldowns.server (server),
		'  <TD align=center>Database: %s' % \
			pulldowns.database (server, database),
		'  <TD align=center>Output As: <SELECT NAME=format>',
		'    <OPTION VALUE="html" SELECTED>HTML',
		'    <OPTION VALUE="tab">Tab-delimited',
		'    <OPTION VALUE="text">Text',
		'    </SELECT>',
		'</TABLE>',
		'<INPUT TYPE=hidden NAME=origserver VALUE=%s>' % server,
		'<TABLE BORDER=0 WIDTH=90%><TR>',
		'  <TD align=left> SQL (separate commands by ||):',
		'  <TD align=right> <I>Example: set rowcount 15 || ' + \
			'select * from MRK_Marker</I><BR>',
		'  <TR><TD colspan=2 align=center>',
		'    <TEXTAREA NAME=sql rows=%s cols=%s>%s</TEXTAREA>' % \
			(config.lookup ('HEIGHT'), config.lookup ('WIDTH'),
			sql),
		'</TABLE>',
		'</FORM>'
		]
	return string.join (lines, '\n')
	
def results (parms):
	db.set_sqlLogin (config.lookup('DBUSER'), config.lookup('DBPASSWORD'),
		parms['server'], parms['database'])
	queries = string.split (parms['sql'], '||')
	try:
		if queries != ['']:
			resultsets = db.sql (queries, 'auto')
		else:
			resultsets = []
	except:
		tb = Traceback (traceback.extract_tb (sys.exc_traceback),
			sys.exc_type, sys.exc_value)
		if FORMAT == HTML:
			return tb.html()
		elif FORMAT == TAB:
			return tb.text()
		else:
			return tb.text()

	list = []
	for i in range (0, len(resultsets)):

		if FORMAT == HTML:
			list.append ('<HR>Result Set %d<P>' % (i + 1))
			list.append (Table (queries[i], resultsets[i]).html())

		elif FORMAT == TAB:
			title = 'Result Set %d' % (i + 1)
			half = (78 - len(title)) / 2
			list.append ('=' * half + title + '=' * (78 - half))
			list = list + map (lambda s : 'SQL: %s' % s,
				string.split (string.strip(queries[i]), '\n'))
			list.append ('')
			list.append (Table (queries[i], resultsets[i]).tab())

		elif FORMAT == TEXT:
			title = 'Result Set %d' % (i + 1)
			half = (78 - len(title)) / 2
			list.append ('=' * half + title + '=' * (78 - half))
			list = list + map (lambda s : 'SQL: %s' % s,
				string.split (string.strip(queries[i]), '\n'))
			list.append ('')
			list.append (Table (queries[i], resultsets[i]).text())

	return string.join (list, '\n')

def process_parms ():
	global parms, FORMAT
	fs = cgi.FieldStorage()
	for k in fs.keys():
		parms[k] = fs[k].value

	if parms['format'] == 'html':
		FORMAT = HTML
	elif parms['format'] == 'tab':
		FORMAT = TAB
	elif parms['format'] == 'text':
		FORMAT = TEXT
	return

title = 'websql %s' % VERSION
header = '<HTML><HEAD><TITLE>%s</TITLE></HEAD><BODY><H3>%s</H3>' % \
	(title, title)
footer = '</BODY></HTML>'
if __name__ == '__main__':
	subnet = os.environ['REMOTE_ADDR'][0:10]
	subnetNew = os.environ['REMOTE_ADDR'][0:11] 
	if subnet not in [ '192.233.43', '192.233.41'] and \
	    subnetNew != '209.222.209':
		print 'Content-type: text/html\n'
		print header
		print 'Permission denied.  You need to be in the Jax domain'
		print '<BR>Subnet: %s' % subnet
		print footer
		sys.exit (0)

	servermap = ServerMap.ServerMap (config.lookup ('MAPFILE'))
	pulldowns = Pulldowns.Pulldowns (servermap)

	if servermap.default_server() != '':
		parms['server'] = servermap.default_server()
	if servermap.default_database() != '':
		parms['database'] = servermap.default_database()

	process_parms()
	if FORMAT == HTML:
		print 'Content-type: text/html\n'
		print header
		print pulldowns.code()
		print form(parms, pulldowns)
		print results(parms)
		print footer

	elif FORMAT == TAB or FORMAT == TEXT:
		print 'Content-type: text/plain\n'
		print results(parms)

	else:
		print 'Content-type: text/html\n'
		print header
		print 'Unrecognized output format: "%s"' % parms['format']
		print footer
