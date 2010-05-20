#!/usr/local/bin/python

# views permissions encoded in database as users (in MGI_User), roles (in
# VOC_Term), and tasks (in VOC_Term).  allows one to select a user, role, or
# task to see details of it.

# optional parameters:
#	server : string server name (default PROD1_MGI)
#	database : string database name (default mgd)
#	user : string username
#	task : string task name
#	role : string role name

import sys
sys.path.insert (0, '/usr/local/mgi/live/lib/python/')
import db
import CGI

class PermissionCGI (CGI.CGI):
	def processParms(self):
		# processes any parameters from the user and stores them in
		# five instance variables

		self.get_parms()		# fills in self.fields

		self.server = 'PROD1_MGI'
		self.database = 'mgd'
		self.user = None
		self.task = None
		self.role = None

		if self.fields.has_key('server'):
			self.server = self.fields['server']

		if self.fields.has_key('database'):
			self.database = self.fields['database']

		parmCount = 0

		if self.fields.has_key('user'):
			self.user = self.fields['user']
			parmCount = parmCount + 1

		if self.fields.has_key('task'):
			self.task = self.fields['task']
			parmCount = parmCount + 1

		if self.fields.has_key('role'):
			self.role = self.fields['role']
			parmCount = parmCount + 1

		# ensure that our parameters only have integer values, to
		# protect against SQL injection attacks; (since this is
		# hitting the production db, let's be extra careful)

		for param in [ 'user', 'task', 'role' ]:
			if self.fields.has_key(param):
				try:
					p = int(self.fields[param])
				except:
					raise 'ParameterError', \
					'Value of "%s" must be an integer' % \
						param

		# should not happen, but we'll check anyway...

		if parmCount > 1:
			raise 'ParameterError', 'Too many parameters; ' + \
				'specify only one of user, task, and role'
		return

	def setupConnection(self):
		# initializes the database connection;
		# assumes processParms() has been called first

		db.set_sqlLogin ('mgd_public', 'mgdpub', self.server,
			self.database)
		db.useOneConnection(1)

		return

	def getUser (self):
		# retrieves the username corresponding to self.user;
		# assumes setupConnection() was called first;
		# returns a string

		results = db.sql ('''SELECT login
			FROM MGI_User
			WHERE _User_key = %s''' % self.user, 'auto')
		if results:
			return results[0]['login']
		return 'None'

	def getTerm (self, key):
		# retrieves the vocab term corresponding to key;
		# assumes setupConnection() was called first;
		# returns a string

		results = db.sql ('''SELECT term
			FROM VOC_Term
			WHERE _Term_key = %s''' % key, 'auto')
		if results:
			return results[0]['term']
		return 'None'

	def buildSummaryLines(self):
		# builds the summary lines that go at the top of the display,
		# describing what is displayed below;
		# assumes setupConnection() has been called;
		# returns a string

		summary = ''

		if self.user:
			summary = 'Roles and Tasks for User "%s"' % \
				self.getUser()
		elif self.role:
			summary = 'Tasks and Users for Role "%s"' % \
				self.getTerm (self.role)
		elif self.task:
			summary = 'Users and Roles for Task "%s"' % \
				self.getTerm (self.task)
		
		if summary:
			return summary + \
				'<BR>[<A HREF="permViewer.cgi">View All</A>]'
		else:
			return 'All Users, Roles, and Tasks<BR>' + \
			'[Click a user, role, or task to restrict display]'

	def buildSQL (self, selectClauses, fromClauses, whereClauses,
			orderClauses):
		# build a SQL statement, including a WHERE and an ORDER BY
		# clause if needed (and not, if not needed);
		# returns a string

		cmd = '''SELECT %s
			FROM %s''' % (', '.join (selectClauses),
				', '.join (fromClauses))
		if whereClauses:
			cmd = '''%s
				WHERE %s''' % (cmd,
					' AND '.join (whereClauses))
		if orderClauses:
			cmd = '''%s
				ORDER BY %s''' % (cmd,
					', '.join (orderClauses))
		return cmd

	def buildUserCell (self):
		# builds the values to be included in the table cell showing
		# the users, restricted as needed by input parameters;
		# assumes setupConnection() has been called;
		# returns a string

		fromClauses = ['MGI_User mu']
		whereClauses = []

		if self.user:
			whereClauses.append ('mu._User_key = %s' % self.user)
		elif self.role:
			fromClauses.append ('MGI_UserRole ur')
			whereClauses.append ('mu._User_key = ur._User_key')
			whereClauses.append ('ur._Role_key = %s' % self.role)
		elif self.task:
			fromClauses.append ('MGI_UserRole ur')
			fromClauses.append ('MGI_RoleTask rt')
			whereClauses.append ('mu._User_key = ur._User_key')
			whereClauses.append ('ur._Role_key = rt._Role_key')
			whereClauses.append ('rt._Task_key = %s' % self.task)

		cmd = self.buildSQL (['mu.login, mu._User_key'],
			fromClauses, whereClauses, [ 'mu.login' ])

		results = db.sql (cmd, 'auto')
		list = []
		for row in results:
			list.append (
				'<A HREF="permViewer.cgi?user=%d">%s</A>' % \
				(row['_User_key'], row['login']) )
		if not list:
			return 'None'
		return '<BR>'.join (list)

	def buildRoleCell (self):
		# builds the values to be included in the table cell showing
		# the roles, restricted as needed by input parameters;
		# assumes setupConnection() has been called;
		# returns a string

		fromClauses = ['VOC_Vocab vv', 'VOC_Term vt']
		whereClauses = [
			'vv._Vocab_key = vt._Vocab_key',
			'vv.name = "User Role"',
			]

		if self.user:
			fromClauses.append ('MGI_UserRole ur')
			whereClauses.append ('ur._Role_key = vt._Term_key')
			whereClauses.append ('ur._User_key = %s' % self.user)
		elif self.role:
			whereClauses.append ('vt._Term_key = %s' % self.role)
		elif self.task:
			fromClauses.append ('MGI_RoleTask rt')
			whereClauses.append ('vt._Term_key = rt._Role_key')
			whereClauses.append ('rt._Task_key = %s' % self.task)

		cmd = self.buildSQL (['vt.term, vt._Term_key'],
			fromClauses, whereClauses, [ 'vt.term' ])

		results = db.sql (cmd, 'auto')
		list = []
		for row in results:
			list.append (
				'<A HREF="permViewer.cgi?role=%d">%s</A>' % \
				(row['_Term_key'], row['term']) )
		return '<BR>'.join (list)

	def buildTaskCell (self):
		# builds the values to be included in the table cell showing
		# the tasks, restricted as needed by input parameters;
		# assumes setupConnection() has been called;
		# returns a string

		fromClauses = ['VOC_Vocab vv', 'VOC_Term vt']
		whereClauses = [
			'vv._Vocab_key = vt._Vocab_key',
			'vv.name = "User Task"',
			]

		if self.user:
			fromClauses.append ('MGI_UserRole ur')
			fromClauses.append ('MGI_RoleTask rt')
			whereClauses.append ('rt._Task_key = vt._Term_key')
			whereClauses.append ('ur._Role_key = rt._Role_key')
			whereClauses.append ('ur._User_key = %s' % self.user)
		elif self.role:
			fromClauses.append ('MGI_RoleTask rt')
			whereClauses.append ('rt._Task_key = vt._Term_key')
			whereClauses.append ('rt._Role_key = %s' % self.role)
		elif self.task:
			whereClauses.append ('vt._Term_key = %s' % self.task)

		cmd = self.buildSQL (['vt.term, vt._Term_key'],
			fromClauses, whereClauses, [ 'vt.term' ])

		results = db.sql (cmd, 'auto')
		list = []
		for row in results:
			list.append (
				'<A HREF="permViewer.cgi?task=%d">%s</A>' % \
				(row['_Term_key'], row['term']) )
		if not list:
			return 'None'
		return '<BR>'.join (list)

	def buildPage (self):
		# builds the page of output with a centered summary section
		# at the top, and with three columns below for users, roles,
		# and tasks, with those columns restricted as needed by input
		# parameters;
		# assumes setupConnection() has been called;
		# returns a string

		list = [
			'<HTML><HEAD><TITLE>Permission Viewer</TITLE></HEAD>',
			'<BODY>',
			'<TABLE BORDER="1" WIDTH="100%">'
			'<TR><TD COLSPAN="3" ALIGN="center">',
			'<FONT SIZE="+1">Permission Viewer</FONT><BR>',
			self.buildSummaryLines(),
			'</TD></TR><TR>',
			'<TH>Users</TH><TH>Roles</TH><TH>Tasks</TH></TR><TR>',
			'<TD VALIGN="top" WIDTH="20%%">%s</TD>' % self.buildUserCell(),
			'<TD VALIGN="top" WIDTH="40%%">%s</TD>' % self.buildRoleCell(),
			'<TD VALIGN="top" WIDTH="40%%">%s</TD>' % self.buildTaskCell(),
			'</TR>',
			'</TABLE></BODY></HTML>',
			]
		print '\n'.join (list)
		return

	def main (self):
		# the main program of the script; orchestrates everything from
		# processing parameters through retrieving data and building
		# the page of output

		self.processParms()
		self.setupConnection()
		self.buildPage()
		return

# instantiates an object of the PermissionCGI class and starts it running, if
# we are executing as a script (rather than being imported as a library)

if __name__ == '__main__':
	PermissionCGI().go()
