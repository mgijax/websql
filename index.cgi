#!./python

# allows generic web-based queries and formats results in table(s)

import os
import cgi
import sys
import types
import traceback
import urllib.request, urllib.parse, urllib.error

if '.' not in sys.path:
        sys.path.insert (0, '.')

fp = open('library.path', 'r')
line = fp.readline().strip()
fp.close()
sys.path.insert(0, line)

import Configuration
import Pulldowns
import ServerMap
import time
import dbManager

VERSION = '1.22'

FORMAT = None
HTML = 1        # values for FORMAT:
TAB = 2
TEXT = 3

TABLE_COUNT = 0

config = Configuration.get_Configuration('Configuration')

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

        p = s.find('.')
        if p < 0:
                return s
        return s[p+1:]

def fields (sql, reskeys):
        # produce a list of fields that's sorted as much as possible based on
        # the contents of 'sql'

        sql = sql.strip()

        if sql[:6].lower() != 'select':  
                return reskeys
        elif sql[:11].lower() == 'select into':
                sql = sql[11:]
        else:
                sql = sql[6:]

        p = sql.lower().find('from')
        if p < 0:
                return reskeys
        myList = list(map (lambda x: x.strip, sql[:p].split(',')))

        front = []
        for field in myList:                      # try ordering from front
                if field in reskeys:
                        front.append (field)
                        reskeys.remove (field)
                else:
                        alt = alternate(field)
                        if alt in reskeys:
                                front.append (alt)
                                reskeys.remove (alt)
                        else:
                                break           # roadblock from front
        end = []
        myList.reverse()                          # now try ordering from back
        for field in myList:
                if field in reskeys:
                        end.insert (0, field)
                        reskeys.remove (field)
                else:
                        alt = alternate(field)
                        if alt in reskeys:
                                end.insert (0, alt)
                                reskeys.remove (alt)
                        else:
                                break           # roadblock from back

        return front + reskeys + end

def tabjoin (myList):
        return '\t'.join (myList)

class Table:
        def __init__ (self, query, result_set):
                if len(result_set) == 0:
                        self.cols = []
                        self.rows = []
                        return
                self.cols = fields (query, list(result_set[0].keys()))
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
                global TABLE_COUNT

                if (not self.rows) or (len(self.rows) == 0):
                        return ''

                TABLE_COUNT = TABLE_COUNT + 1
                lines = [ '<TABLE id="resultsTable%d" border="1">' % TABLE_COUNT ]

                lines.append('<thead>')

                s = '<TR><TH>Row #</TH>'
                for col in self.cols:
                        s = s + '<TH>%s</TH>' % col
                lines.append (s + '</TR>')

                lines.append('</thead><tbody>')

                ct = 0
                for row in self.rows:
                        s = '<TR>'
                        ct = ct + 1
                        s = s + '<TD>%d</TD>' % ct
                        for col in range (0, len(self.cols)):
                                val_type = type (row[col])
                                if val_type == int:
                                        s = s + '<TD align=right>%d</TD>' % \
                                                row[col]
                                elif val_type == float:
                                        s = s + '<TD align=right>%f</TD>' % \
                                                row[col]
                                elif val_type == type(None):
                                        s = s + '<TD>null</TD>'
                                else:
                                        s = s + '<TD>%s</TD>' % \
                                                cgi.escape(str(row[col]))
                        lines.append (s + '</TR>')
                lines.append ('</tbody></TABLE>')
                return '\n'.join (lines)

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

                lines = [ tabjoin (headers) ] + list(map (tabjoin, datarows))
                return '\n'.join (lines)

        def text (self):
                if (not self.rows) or (len(self.rows) == 0):
                        return ''

                headers = [ 'Row #' ]
                for col in self.cols:
                        headers.append (col)

                datarows = []
                maxlens = list(map (len, headers))
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
                                s = '%s %s' % (s, line[i].ljust(maxlens[i]))
                        lines.append (s)
                return '\n'.join (lines)

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
                return '\n'.join (lines)

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
                return '\n'.join (lines)

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
                        <a href="http://www.informatics.jax.org/usrlocalmgi/live/schemaSpy/mgd/" target="_blank">mgd</a> | 
                        <a href="http://www.informatics.jax.org/usrlocalmgi/live/schemaSpy/fe/" target="_blank">fe</a> | 
                        <a href="http://www.informatics.jax.org/usrlocalmgi/live/schemaSpy/snp/" target="_blank">snp</a> | 
                        <a href="http://www.informatics.jax.org/usrlocalmgi/live/schemaSpy/radar/" target="_blank">radar</a></TD>''',
                '  <TD align=center> <I>Example: select * from mrk_marker ' + \
                        'limit 15</I><BR>',
                '  <TR><TD colspan=3 align=center>',
                '    <TEXTAREA NAME=sql rows=%s cols=%s>%s</TEXTAREA>' % \
                        (config.lookup ('HEIGHT'), config.lookup ('WIDTH'),
                        sql),
                '</TABLE>',
                '</FORM>'
                ]
        return '\n'.join (lines)
        
def jsUpdate(i, total):
        s = '''<script>document.getElementById("status").innerHTML="Working on command %d of %d...";</script>''' % (i, total)
        return s

def jsFinal():
        s = '''<script>document.getElementById("status").innerHTML="Finished commands";</script>'''
        return s

def jsTable(timings):
        total = 0
        myList = []
        myList.append('<B>Timings:</B><br/>Shorter timings have lighter shades; click the query number to go down to its results.<P>')
        for (i, timing) in timings:
                total = total + timing

        myList.append(legend(total))

        for (i, timing) in timings:
                myList.append(bar(i, timing, total))
                myList.append('<br/>')

        myList.append('Link to <a href="%s" target="_blank">current set of results</a> (can copy &amp; paste URL)<br/>' % makeLink())

        s = '''<script>document.getElementById("status").innerHTML='%s';</script>''' % ' '.join(myList)
        return s

def results (parms):
        dbms = 'postgres'

        if dbms == 'postgres':
                dbm = dbManager.postgresManager (parms['server'],
                        parms['database'], config.lookup('POSTGRES_USER'),
                        config.lookup('POSTGRES_PASSWORD') )

        i = 0
        myList = []

        if FORMAT == HTML:
                myList.append ('<HR>')
        else:
                myList.append ('')

        if FORMAT == HTML:
                myList.append ('Results from %s..%s' % (parms['server'], parms['database']))
                myList.append('<hr/>')
                myList.append('<div id="status"></div>')
        else:
                myList.append ('Results from %s..%s' % (parms['server'], parms['database']))

        queries = parms['sql'].split('||')
        if len(queries) == 1 and queries[0] == '':
                queries = []

        timings = []

        print('\n'.join(myList))
        sys.stdout.flush()
        myList = []

        for query in queries:
            i = i + 1 
            if FORMAT == HTML:
                    print(jsUpdate(i, len(queries)))
                    sys.stdout.flush()

            try:
                title = 'Result Set %d' % i
                half = int((78 - len(title)) / 2)

                cmds = [ 'SQL command:' ] + query.strip().split('\n')

                if FORMAT == HTML:
                        myList.append ('<HR><a name="%d">%s</a> (back to <a href="#top">top</a>)<BR>' % (i,title))
                        myList.append ('<PRE>%s</PRE>' % '\n'.join(cmds))
                else:
                        myList.append ('=' * half + title + '=' * (78 - half))
                        myList = myList + cmds
                        myList.append ('')

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
                        myList.append ('<FONT SIZE="-1">%s</FONT> <span id="makeSortable%d" onClick="makeSortable(%d)" class="shownButton">&nbsp;Show Enhanced Table&nbsp;</span><P>' % (stats, i, i))
                        myList.append (tbl.html())

                elif FORMAT == TAB:
                        myList.append (stats)
                        myList.append ('')
                        myList.append (tbl.tab())

                elif FORMAT == TEXT:
                        myList.append (stats)
                        myList.append ('')
                        myList.append (tbl.text())

                print('\n'.join(myList))
                sys.stdout.flush()
                myList = []
            except:
                tb = Traceback (traceback.extract_tb (sys.exc_info()[2]),
                                        sys.exc_info()[0], sys.exc_info()[1])
                if FORMAT == HTML:
                        myList.append (tb.html())
                else:
                        myList.append (tb.text())

                return '\n'.join (myList)

        if (FORMAT == HTML) and (queries):
                print(jsFinal())
                print(jsTable(timings))

        return '\n'.join (myList)

maxWidth = 1000                 # pixels for graph width

def legend(total):
        divs = []
        divs.append('<div style="width:25px; border-right: solid thin black; text-align: right; display: inline-block;">&nbsp;</div>')
        width = ((maxWidth - 5) / 8.0) - 5
        for i in range(1,9):
                t = i * total / 8.0
                divs.append('<div style="width:%dpx; border-bottom: solid thin black; border-right: solid thin black; text-align: right; display: inline-block; padding-right: 5px;">%0.3f sec</div>' % (width, t))
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
        for k in list(fs.keys()):
                parms[k] = fs[k].value

        if parms['format'] == 'html':
                FORMAT = HTML
        elif parms['format'] == 'tab':
                FORMAT = TAB
        elif parms['format'] == 'text':
                FORMAT = TEXT
        return

def makeLink():
        # make a link to the current page, including the SQL command(s)

        url = 'http://%s%s' % (os.environ['HTTP_HOST'], os.environ['REQUEST_URI'])
        if not url.endswith('index.cgi'):
                url = os.path.join(url, 'index.cgi')

        url = '%s?server=%s&database=%s&format=%s&sql=' % (url,
                parms['server'], parms['database'], parms['format'])

        url = url + urllib.parse.quote(parms['sql'])
        return url 

title = 'websql %s' % VERSION
header = '''<HTML><HEAD><TITLE>%s</TITLE></HEAD><BODY><H3><a name="top">%s</a></H3>
<style>
.hiddenButton { display : none; }
.shownButton { display : inline; border: 1px solid black; font-family: Arial; font-size: .85em;
        background-color: lightyellow; color: black; }
</style>
''' % \
        (title, title)
footer = '''
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.10.19/css/jquery.dataTables.min.css" />
        <script src="https://cdn.datatables.net/1.10.19/js/jquery.dataTables.min.js"></script>
        <script>
        var makeSortable = function(id) {
                $('#resultsTable' + id).DataTable( {paging: false} );
                $('#makeSortable' + id).removeClass('shownButton').addClass('hiddenButton');
        };
        </script>
        </BODY></HTML>'''

if __name__ == '__main__':
        servermap = ServerMap.ServerMap (config.lookup ('MAPFILE'))
        pulldowns = Pulldowns.Pulldowns (servermap)

        parms['DBMS1'] = 'postgres'
        if servermap.default_server() != '':
                parms['server'] = servermap.default_server()
        if servermap.default_database() != '':
                parms['database'] = servermap.default_database()

        process_parms()

        errorMsg = None
        if (parms['DBMS1'] == 'postgres') and (not dbManager.LOADED_POSTGRES_DRIVER):
                errorMsg = 'Could not find the psycopg2 module for Postgres'

        if not servermap.valid('postgres', parms['server'], parms['database']):
                errorMsg = 'The given server and database are not currently recognized (%s..%s)' % (parms['server'], parms['database'])

        if errorMsg:
                print('Content-type: text/html\n')
                print(header)
                print('Failed: "%s"' % errorMsg)
                print(footer)
                sys.exit(0)

        if FORMAT == HTML:
                print('Content-type: text/html\n')
                print(header)
                print(pulldowns.code())
                print(form(parms, pulldowns))
                print(results(parms))
                print(footer)

        elif FORMAT == TAB or FORMAT == TEXT:
                print('Content-type: text/plain\n')
                print(results(parms))

        else:
                print('Content-type: text/html\n')
                print(header)
                print('Unrecognized output format: "%s"' % parms['format'])
                print(footer)
