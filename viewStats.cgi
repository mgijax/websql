#!/usr/local/bin/python

# CGI script to use when viewing statistic groups, statistics, and 
# measurements.  User can select various server/database combinations, as
# well as choosing a group or individual statistic to view.

import sys
sys.path.insert (0, '/usr/local/mgi/live/lib/python/')
import db
import CGI
import stats

databases = {
	'shire'		: ('PROD_MGI', 'mgd'),
	'rohan'		: ('DEV_MGI', 'mgd'),
	'firien'	: ('DEV2_MGI', 'mgd'),
	'jsb'		: ('DEV_MGI', 'mgd_lec'),
	'dev1'		: ('DEV1_MGI', 'mgd_wi1'),
	}
defaultDbKey = 'shire'

class StatisticCGI (CGI.CGI):
	def processParms(self):
		# process any parameters from the user and stores them in
		# instance variables

		self.get_parms()

		self.dbKey = defaultDbKey
		self.group = None
		self.statistic = None
		self.groupObj = None
		self.statisticObj = None

		if self.fields.has_key('dbKey'):
			self.dbKey = self.fields['dbKey']
			if not databases.has_key(self.dbKey):
				raise 'ParameterError', \
					'Unknown database selection: %s' \
						% self.fields['dbKey']

		if self.fields.has_key('group'):
			try:
				self.group = int(self.fields['group'])
			except:
				raise 'ParameterError', \
					'Invalid group key: %s' % \
						self.fields['group']

		if self.fields.has_key('statistic'):
			try:
				self.statistic = int(self.fields['statistic'])
			except:
				raise 'ParameterError', \
					'Invalid statistic key: %s' % \
						self.fields['statistic']

		if self.group and self.statistic:
			raise 'ParameterError', \
			'May use either "group" or "statistic", but not both'

		(server, database) = databases[self.dbKey]

		db.set_sqlLogin ('mgd_public', 'mgdpub', server, database)
		db.useOneConnection(1)
		stats.setSqlFunction (db.sql)
		return

	def preloadObjects (self):
		if self.group:
			results = db.sql ('''SELECT name
				FROM MGI_Set
				WHERE _Set_key = %d''' % self.group, 'auto')
			if not results:
				raise 'ParameterError', \
					'Unknown group key: %d' % self.group
			self.groupObj = \
				stats.StatisticGroup (results[0]['name'])

		elif self.statistic:
			self.statisticObj = \
				stats.getStatisticByKey (self.statistic)
		return

	def link (self, name, value, text):
		if self.dbKey != defaultDbKey:
			x = 'viewStats.cgi?dbKey=%s&%s=%d' % \
				(self.dbKey, name, value)
		else:
			x = 'viewStats.cgi?%s=%d' % (name, value)
		return '<A HREF="%s">%s</A>' % (x, text)

	def buildSummaryLines (self):
		summary = []

		if not (self.group or self.statistic):
			summary.append ('All Groups and Statistics<BR>')
			summary.append ('[Click a group or statistic to ' + \
				'restrict display]')
		elif self.group:
			summary.append ('Statistics for Group "%s"' % \
				self.groupObj.getName())
		elif self.statistic:
			summary.append ('Groups containing Statistic "%s"' % \
				self.statisticObj.getName())

		if len(summary) == 1:
			summary.append ('<BR>' + \
			'[<A HREF="viewStats.cgi?dbKey=%s">View All</A>]' % \
			self.dbKey)

		return '\n'.join (summary)

	def buildServerForm (self):
		list = [
			'<FORM NAME="dbForm" ACTION="viewStats.cgi" ' + \
				'METHOD="GET">',
			'<SELECT NAME="dbKey">',
			]

		dbkeys = databases.keys()
		dbkeys.sort()

		for key in dbkeys:
			if key == self.dbKey:
				tag = ' SELECTED'
			else:
				tag = ''

			list.append ('<OPTION VALUE="%s"%s>%s</OPTION>' % \
				(key, tag, key))

		list.append ('</SELECT>')
		list.append ('<INPUT TYPE="submit" NAME="submit" ' + \
			'VALUE="Change">')
		list.append ('</FORM>')

		return '\n'.join (list)

	def buildGroupCell (self):
		if self.statistic:
			groups = self.statisticObj.getGroups()
		else:
			groups = stats.getAllGroups()

		list = []
		for group in groups:
			gObj = stats.StatisticGroup (group)
			list.append(self.link ('group', gObj.getKey(), group))

		if not list:
			list.append ('None')
		return '<BR>\n'.join (list)

	def buildStatisticCell (self):
		list = [ '<TABLE BORDER="0">' ]
		row = '<TR ALIGN="left"><TD>%s</TD><TD ALIGN="right">%s</TD></TR>'
		rowB = '<TR ALIGN="left"><TD><B>%s</B></TD><TD ALIGN="right">%s</TD></TR>'

		if self.statistic:
			s = self.statisticObj
			m = s.getLatestMeasurement()

			if not m:
				mVal = '&nbsp;'
			elif m.hasIntValue():
				mVal = stats.commaDelimit(str(m.getIntValue()))
			else:
				mVal = stats.commaDelimit('%1.3f' % m.getFloatValue())

			list.append (rowB % ('Name', s.getName()))
			list.append (rowB % ('Abbreviation', s.getAbbrev()))
			list.append (rowB % ('Definition', s.getDefinition()))
			list.append (rowB % ('_Statistic_key', s.getKey()))
			list.append (rowB % ('Private?', s.isPrivate()))
			list.append (rowB % ('Int Value?', s.hasIntValue()))
			list.append (rowB % ('Latest Value', mVal))
			list.append ('</TABLE>')
			list.append ('<B>SQL:</B><BR><PRE>%s</PRE>' % \
					s.getSql())
		else:
			if self.group:
				statistics = self.groupObj.getStatistics()
			else:
				statistics = stats.getStatistics()

			if not statistics:
				list.append (row % ('None', '&nbsp;'))
			else:
				for stat in statistics:
					m = stat.getLatestMeasurement()
					if not m:
					    mVal = '&nbsp;'
					elif m.hasIntValue():
					    mVal = stats.commaDelimit(str(m.getIntValue()))
					else:
					    mVal = stats.commaDelimit('%1.3f' % m.getFloatValue())

					list.append (row % (
					    self.link ('statistic',
						stat.getKey(),
						stat.getName()),
						mVal))
			list.append ('</TABLE>')

		return '\n'.join (list)

	def buildMeasurementCell (self):
		if not self.statistic:
			return 'n/a'
		measurements = self.statisticObj.getMeasurements()
		measurements.reverse()
		list = [
			'<TABLE BORDER="0">',
			'<TR><TH>Timestamp</TH><TH>Value</TH></TR>',
			]
		row = '<TR><TD ALIGN="left">%s</TD>' + \
			'<TD ALIGN="right">%s</TD></TR>'
		for m in measurements:
			if m.hasIntValue():
				mVal = str(m.getIntValue())
			else:
				mVal = '%1.3f' % m.getFloatValue()
			list.append (row % (m.getTimestamp(),
				stats.commaDelimit(mVal)))

		list.append ('</TABLE>')
		return '\n'.join (list)

	def buildPage (self):
		if self.statistic:
			groupHead = 'Groups Including This Statistic'
		else:
			groupHead = 'Groups'

		if self.group:
			statHead = 'Statistics in this Group'
		else:
			statHead = 'Statistics'

		list = [
			'<HTML><HEAD><TITLE>Statistic Viewer</TITLE></HEAD>',
			'<BODY>',
			'<TABLE BORDER="1" WIDTH="100%">',
			'<TR><TD COLSPAN="3" ALIGN="center">',
			'<FONT SIZE="+1">Statistic Viewer</FONT><BR>',
			self.buildSummaryLines(),
			self.buildServerForm(),
			'</TD></TR><TR>',
			'<TH>%s</TH><TH>%s</TH>' % (groupHead, statHead),
			'<TH>Measurements</TH></TR><TR VALIGN="top">',
			'<TD WIDTH="25%%">%s</TD>' % self.buildGroupCell(),
			'<TD WIDTH="50%%">%s</TD>' % \
				self.buildStatisticCell(),
			'<TD WIDTH="25%%">%s</TD>' % \
				self.buildMeasurementCell(),
			'</TR>',
			'</TABLE></BODY></HTML>',
			]
		print '\n'.join(list)
		return

	def main (self):
		self.processParms()
		self.preloadObjects()
		self.buildPage()
		return

# instantiates an object of the StatisticCGI class and starts it running, if
# we are executing as a script (rather than being imported as a library)

if __name__ == '__main__':
	StatisticCGI().go()
