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
import time
import dbManager

VERSION = '1.21'

FORMAT = None
HTML = 1	# values for FORMAT:
TAB = 2
TEXT = 3

# default to the production mirror
parms = { 'database' : 'mgd',
	'server' : 'DEV_MGI',
	'sql' : '',
	'format' : 'html',
	}

TIME = time.time()

def resetTime ():
	global TIME
	TIME = time.time()
	return

def elapsedTime ():
	return time.time() - TIME

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
		if (not self.rows) or (len(self.rows) == 0):
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
		if (not self.rows) or (len(self.rows) == 0):
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

class MP_Table (Table):
	def __init__ (self, columns, rows):
		self.cols = columns
		self.rows = rows
		return

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
	dbms = 'postgres'
	server = parms ['server']
	database = parms ['database']
	script = os.path.basename (os.environ['SCRIPT_NAME'])
	lines = [ '<FORM ACTION="%s" METHOD=POST NAME="frm" onReset="doReset()">' % script,
		'<INPUT TYPE=submit>',
		'<INPUT TYPE=reset VALUE="Reset this Page">',
		"<INPUT TYPE=button onClick='window.location.href=%s' VALUE='Start Over'>"\
			% ('"%s"' % script),
		'<INPUT TYPE=hidden NAME=origdbms VALUE=%s>' % dbms,
		'<INPUT TYPE=hidden NAME=origserver VALUE=%s>' % server,
		'<INPUT TYPE=hidden NAME=origdatabase VALUE=%s>' % database,
		'<TABLE BORDER=0 WIDTH=90%><TR>',
		'  <TD align=center>Server: %s' % pulldowns.server (dbms,
			server),
		'  <TD align=center>Database: %s' % pulldowns.database (dbms,
			server, database),
		'  <TD align=center>Output As: <SELECT NAME=format>',
		'    <OPTION VALUE="html" SELECTED>HTML',
		'    <OPTION VALUE="tab">Tab-delimited',
		'    <OPTION VALUE="text">Text',
		'    </SELECT>',
		'  </TR><TR>',
		'  <TD align=center> SQL (separate commands by ||):',
		'''  <TD align="center">SchemaSpy: 
			<a href="http://firien.informatics.jax.org/usrlocalmgi/live/schemaSpy/mgd/" target="_blank">mgd</a> | 
			<a href="http://firien.informatics.jax.org/usrlocalmgi/live/schemaSpy/fe/" target="_blank">fe</a> | 
			<a href="http://firien.informatics.jax.org/usrlocalmgi/live/schemaSpy/snp/" target="_blank">snp</a> | 
			<a href="http://firien.informatics.jax.org/usrlocalmgi/live/schemaSpy/radar/" target="_blank">radar</a></TD>''',
		'  <TD align=center> <I>Example: select * from mrk_marker ' + \
			'limit 15</I><BR>',
		'  <TR><TD colspan=3 align=center>',
		'    <TEXTAREA NAME=sql rows=%s cols=%s>%s</TEXTAREA>' % \
			(config.lookup ('HEIGHT'), config.lookup ('WIDTH'),
			sql),
		'</TABLE>',
		'</FORM>'
		]
	return string.join (lines, '\n')
	
def jsUpdate(i, total):
	s = '''<script>document.getElementById("status").innerHTML="Working on command %d of %d...";</script>''' % (i, total)
	return s

def jsFinal():
	s = '''<script>document.getElementById("status").innerHTML="Finished commands";</script>'''
	return s

def jsTable(timings):
	total = 0
	list = []
	list.append('<B>Timings:</B><br/>Shorter timings have lighter shades; click the query number to go down to its results.<P>')
	for (i, timing) in timings:
		total = total + timing

	list.append(legend(total))

	for (i, timing) in timings:
		list.append(bar(i, timing, total))
		list.append('<br/>')
	s = '''<script>document.getElementById("status").innerHTML='%s';</script>''' % ' '.join(list)
	return s

def results (parms):
	dbms = 'postgres'

	if dbms == 'postgres':
		dbm = dbManager.postgresManager (parms['server'],
			parms['database'], config.lookup('POSTGRES_USER'),
			config.lookup('POSTGRES_PASSWORD') )

	i = 0
	list = []

	if FORMAT == HTML:
		list.append ('<HR>')
	else:
		list.append ('')

	if FORMAT == HTML:
		list.append ('Results from %s..%s' % (parms['server'], parms['database']))
		list.append('<hr/>')
		list.append('<div id="status">Working on...</div>')
	else:
		list.append ('Results from %s..%s' % (parms['server'], parms['database']))

	queries = string.split (parms['sql'], '||')
	if len(queries) == 1 and queries[0] == '':
		queries = []

	timings = []

    	print '\n'.join(list)
	sys.stdout.flush()
	list = []

	for query in queries:
	    i = i + 1 
	    if FORMAT == HTML:
		    print jsUpdate(i, len(queries))
		    sys.stdout.flush()

	    try:
		title = 'Result Set %d' % i
		half = (78 - len(title)) / 2

		cmds = [ 'SQL command:' ] + string.split(query.strip(), '\n')

		if FORMAT == HTML:
			list.append ('<HR><a name="%d">%s</a> (back to <a href="#top">top</a>)<BR>' % (i,title))
			list.append ('<PRE>%s</PRE>' % '\n'.join(cmds))
		else:
			list.append ('=' * half + title + '=' * (78 - half))
			list = list + cmds
			list.append ('')

		resetTime()

		columns, rows = dbm.execute (query)
		if rows:
			count = len(rows)
		else:
			count = 0
		tbl = MP_Table(columns, rows)

		t = elapsedTime()
		stats = '%d rows returned, %4.3f seconds' % (count, t)
		timings.append ( (i, t) )

		if FORMAT == HTML:
			list.append ('<FONT SIZE="-1">%s</FONT><P>' % stats)
			list.append (tbl.html())

		elif FORMAT == TAB:
			list.append (stats)
			list.append ('')
			list.append (tbl.tab())

		elif FORMAT == TEXT:
			list.append (stats)
			list.append ('')
			list.append (tbl.text())

	    	print '\n'.join(list)
		sys.stdout.flush()
		list = []
	    except:
		tb = Traceback (traceback.extract_tb (sys.exc_traceback),
					sys.exc_type, sys.exc_value)
		if FORMAT == HTML:
			list.append (tb.html())
		else:
			list.append (tb.text())

		return '\n'.join (list)

	if FORMAT == HTML:
		print jsFinal()
		print jsTable(timings)

	return '\n'.join (list)

maxWidth = 1000			# pixels for graph width

def legend(total):
	divs = []
	divs.append('<div style="width:25px; border-right: solid thin black; text-align: right; display: inline-block;">&nbsp;</div>')
	width = ((maxWidth - 5) / 8.0) - 5
	for i in range(1,9):
		t = i * total / 8.0
		divs.append('<div style="width:%dpx; border-bottom: solid thin black; border-right: solid thin black; text-align: right; display: inline-block; padding-right: 5px;">%0.2f sec</div>' % (width, t))
	divs.insert(0, '<div>')
	divs.append('</div>')
	return ''.join(divs)

def pixels(subset, total, maxWidth):
	return int(1.0 * subset / total * maxWidth)

sofar = 0
def bar (i, timing, total):
	global sofar

	green = hex(255 - int((timing / total) * 255))
	if green == '0x0':
		green = '0xff'

	color = '#00%s00' % green[-2:]

	s = '<div style="width: %dpx; display: inline-block; text-align: right; padding-right: 5px"><a href="#%d">%s</a></div>' + \
		'<div style="display:inline-block; background-color: %s; width: %dpx">&nbsp;</div>'
	s = s % (20 + pixels(sofar, total, maxWidth), i, i, color,
		pixels(timing, total, maxWidth))
	sofar = sofar + timing
	return s 

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
header = '<HTML><HEAD><TITLE>%s</TITLE></HEAD><BODY><H3><a name="top">%s</a></H3>' % \
	(title, title)
footer = '</BODY></HTML>'

if __name__ == '__main__':
	servermap = ServerMap.ServerMap (config.lookup ('MAPFILE'))
	pulldowns = Pulldowns.Pulldowns (servermap)

	parms['DBMS1'] = 'postgres'
	if servermap.default_server() != '':
		parms['server'] = servermap.default_server()
	if servermap.default_database() != '':
		parms['database'] = servermap.default_database()

	process_parms()

	noDriver = None
	if (parms['DBMS1'] == 'postgres') and (not dbManager.LOADED_POSTGRES_DRIVER):
		noDriver = 'Could not find the psycopg2 module for Postgres'

	if noDriver:
		print 'Content-type: text/html\n'
		print header
		print 'Failed: "%s"' % noDriver
		print footer
		sys.exit(0)

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
