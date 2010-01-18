"""
Trac2MitePlugin:
Connects your Trac account with your mite.account. Track your time easily on issues within Trac (requires 'TracHoursPlugin') and get them automatically send to mite.

See: http://trac-hacks.org/wiki/Trac2Mite
"""

from componentdependencies.interface import IRequireComponents
from datetime import datetime
import re
from ticketsidebarprovider.interface import ITicketSidebarProvider
from ticketsidebarprovider.ticketsidebar import TicketSidebarProvider
import time
from trac.core import *
from tracsqlhelper import *
from trac.util.translation import _
from trac.util.datefmt import utc, to_timestamp
from trac.web.chrome import ITemplateProvider, add_script, add_warning, add_notice, add_link

# local imports
from api import ITracHoursPluginListener
from mite import Mite
from setup import SetupTrac2Mite
from userprefs import Trac2MiteUserPrefs
from utils import *

# other plugins
from trachours.hours import TracHoursPlugin
from trachours.web_ui import TracHoursSidebarProvider

class Trac2MitePlugin(Component):
	implements(ITemplateProvider,
			   ITracHoursPluginListener,
			   IRequireComponents,
			   ITicketSidebarProvider)
	
	def __init__(self):
		self.prefs = None
		self.mite = None
		self.current_req = None
	
	### implementation IRequireComponents
	def requires(self):
		"""Missing description...
		"""
		return [TracHoursPlugin,
				SetupTrac2Mite]

	### implementation ITemplateProvider
	def get_templates_dirs(self):
		"""Missing description...
		"""
		# add ExtensionPoints to TracHoursPlugin, but only ONCE
		new_listeners = getattr(TracHoursPlugin, "change_listeners", None)
		
		if not new_listeners:
			
			# bypass methods for handling "ticket times requests" to custom methods 
			
			### add change listeners
			TracHoursPlugin.change_listeners = ExtensionPoint(ITracHoursPluginListener)
			
			### before EVERY request to the TracHours component
			TracHoursPlugin.process_request_old = TracHoursPlugin.process_request
			TracHoursPlugin.process_request = add_listener_before_process_request
			
			### before adding a new ticket time	
			TracHoursPlugin.add_ticket_hours_old = TracHoursPlugin.add_ticket_hours
			TracHoursPlugin.add_ticket_hours = add_listener_after_ticket_time_created
			
			### before editing ticket times
			TracHoursPlugin.edit_ticket_hours_old = TracHoursPlugin.edit_ticket_hours
			TracHoursPlugin.edit_ticket_hours = add_listener_before_ticket_times_edited
			
		from pkg_resources import resource_filename
		return [resource_filename(__name__, 'templates')]
		
	def get_htdocs_dirs(self):
		from pkg_resources import resource_filename
		return [('t2m', resource_filename(__name__, 'htdocs'))]

	##################	
	### implementation ITracHoursPluginListener
	
	def before_process_request(self, req, ticket_id):
		"""Called when a TracHoursPlugin page is requested
		This handler gets called BEFORE each of the following listeners.
		Therefore it is attempted to init the mite communication object (mite).
		"""
		
		self.current_req = req # save the request object to use it in other listeners
		self.init_mite_components()
		self.init_hours_mite_values(ticket_id)
			
	def after_ticket_time_created(self,ticket_time):
		"""Called when a ticket time is created."""
		if not self.mite: return 
		
		values = self.get_posted_mite_values(ticket_time)
		ticket_datetime = datetime.fromtimestamp(ticket_time["time_started"]).__str__()
		
		# replace placeholders set in the user preferences by their current values 
		processed_comment = self.replace_placeholders_in_comment(values['comments'], ticket_time)
		
		mite_time_entry_id = self.mite.insert_time_entry(ticket_datetime, values['minutes'], values['project_id'], values['service_id'], processed_comment)
		
		db_values = {
			"mite_time_entry_id": mite_time_entry_id,
			"mite_time_entry_updated_on": to_timestamp(datetime.now(utc)),
			"mite_service_id" : values['service_id'],
			"mite_project_id" : values['project_id']}
		
		# Update ticket time with new mite specific values
		update_row_from_dict(self.env, "ticket_time", "id", ticket_time.get("id"), db_values)
		
	def before_ticket_times_updated(self, ticket_times):
		"""Updates all ticket times in mite saved in the dictionary ticket_times
		"""
		# Return, if the connection to mite was yet not established by the user
		# OR there were no ticket times to consider 
		if not self.mite or not len(ticket_times): return 
		
		for tt_id, tt_in_seconds in ticket_times.iteritems():
			
			ticket_time = get_all_dict(self.env,"SELECT * FROM ticket_time WHERE id=%s",tt_id).pop()
			
			# get posted values
			values = self.get_posted_mite_values(ticket_time, tt_id)
			
			# if the ticket time was already sendt to mite once
			if ticket_time["mite_time_entry_id"]:
				
				status = self.mite.update_time_entry(ticket_time["mite_time_entry_id"],values['minutes'], values['project_id'], values['service_id'])
				
				if not status:
					# in case the remote time entry is deleted but still linked to the local time entry
					if self.mite.lastError=="HTTP Error 404: Not Found":
						
						nullifier = {"mite_time_entry_id" : '',
									 "mite_time_entry_updated_on" : '',
									 "mite_service_id" : '',
									 "mite_project_id" : ''}
						
						# Nullify mite values in ticket time record
						update_row_from_dict(self.env, "ticket_time", "id", tt_id, nullifier)
						
						print "Removed mite values from ticket time record (ID: %s)." % tt_id
					else:
						print "ERROR in Trac2Mite: Could not update time entry '%s' and synchronize mite account data! Reason: %s" % (ticket_time["mite_time_entry_id"], self.mite.lastError)
				
				# update database row
				else:
					db_values = {
						"mite_time_entry_updated_on": to_timestamp(datetime.now(utc)),
						"mite_project_id" : values['project_id'],
						"mite_service_id" : values['service_id']}

					# Update ticket time with new mite specific values
					update_row_from_dict(self.env, "ticket_time", "id", tt_id, db_values)
				
			# if it is an existing ticket time, which was not linked to mite before...
			else:
				ticket_datetime = datetime.fromtimestamp(ticket_time["time_started"]).__str__()
				
				# ...and the user selected a mite service or project
				# send the entry to mite and update the local time entry
				if values['project_id'] or values['service_id']:
					
					processed_comment = self.replace_placeholders_in_comment(ticket_time['comments'], ticket_time)
					
					# send to mite
					mite_time_entry_id = self.mite.insert_time_entry(ticket_datetime, values['minutes'], values['project_id'], values['service_id'], processed_comment)
				
					db_values = {
						"mite_time_entry_id": mite_time_entry_id,
						"mite_time_entry_updated_on": to_timestamp(datetime.now(utc)),
						"mite_project_id" : values['project_id'],
						"mite_service_id" : values['service_id']}
				
					# Update ticket time with new mite specific values
					update_row_from_dict(self.env, "ticket_time", "id", tt_id, db_values)
		
	def before_ticket_times_deleted(self,ticket_times_ids):
		"""Called before ticket times get's deleted"""	
		if not self.mite: return 
		
		for tt_id in ticket_times_ids:
			
			ticket_time = get_all_dict(self.env,"SELECT * FROM ticket_time WHERE id=%s",tt_id).pop()
			
			if ticket_time["mite_time_entry_id"]:
				status = self.mite.delete_time_entry(ticket_time["mite_time_entry_id"])
				if not status:
					print "ERROR in Trac2Mite: Could delete time entry '%s' from your account data! Reason: %s" % (ticket_time["mite_time_entry_id"], self.mite.lastError)
			
	##################
	### methods for ITicketSidebarProvider
	
	def enabled(self, req, ticket):
		"""Missing description...
		"""
		if ticket.id and req.authname and 'TICKET_ADD_HOURS' in req.perm:
			return True
		return False

	def content(self, req, ticket):
		"""Missing description...
		"""
		self.current_req = req # save the request object to use it in other listeners
		self.init_mite_components()
			
	##################		
	### local functions
	
	def init_mite_components(self):
		"""Missing description...
		"""
		self.prefs = Trac2MiteUserPrefs()
		self.mite = None
		
		if self.prefs.init_prefs(self.env, self.current_req):
			self.mite = Mite(self.prefs.account_name, self.prefs.api_key, self.prefs.is_authenticated)
		
			# add javascript file which dynamically adds mite input fields
			add_script(self.current_req, 't2m/js/mite.js')
		
			# MEGA HACK HERE! ANOTHER WAY NEEDED!
			# add user resources as fake link elements <link ...> for the header
			# to fetch 'em via javascript later on
			# can't use add_script_data because not yet available in the current stable version (0.11) of Trac
			for rsrc_type in self.prefs.rsrc_types:
				for rsrc in self.prefs.rsrcs_by_type_and_binded[rsrc_type]:
					add_link(self.current_req,
							 rsrc['remote_rsrc_id'],
							 "",
							 rsrc['name'],
							 mimetype='trac2miteRsrc',
							 classname=rsrc_type)
							
	
	def init_hours_mite_values(self, ticket_id):
		"""Missing description...
		"""
		sql = "SELECT id, mite_project_id, mite_service_id, mite_time_entry_id FROM ticket_time WHERE ticket=%s AND mite_time_entry_id != ''"
		mite_ticket_time_values = get_all_dict(self.env, sql,ticket_id)
		
		# Same nasty HACK as in init_mite_components()
		for values in mite_ticket_time_values:
			
			add_link(self.current_req,
				 	str(values['id']) + "_" + str(values['mite_project_id']),
				 	"",
					values['id'],
				 	mimetype='trac2miteValue',
					classname='p')
						
			add_link(self.current_req,
					str(values['id']) + "_" + str(values['mite_service_id']),
					"",
					values['id'],# id of the ticket time
					mimetype='trac2miteValue',
					classname='s')
			
	def get_posted_mite_values(self, ticket_time, record_suffix=''):
		"""Returns a dictionary with all mite related stuff for a ticket time entry"""	
		
		record_suffix_f = ''
		
		if record_suffix != '':
			record_suffix_f = '_' + str(record_suffix)
		
		# repeat steps as in TracHoursPlugin "hours.py -> edit_ticket_hours" because the event handler gets called 
		# before anything with the ticket happens
		hours = self.current_req.args['hours' + record_suffix_f].strip() or 0
		minutes = self.current_req.args['minutes' + record_suffix_f].strip() or 0
		try:
			seconds_worked = int(float(hours) * 3600 + float(minutes) * 60)
		except ValueError:
			raise ValueError("Please enter a valid number of hours")
			self.current_req.redirect(self.current_req.href(self.current_req.path_info))
		
		values = {
			"project_id": self.current_req.args.get('mite_p_id%s' % record_suffix,''),
			"service_id": self.current_req.args.get('mite_s_id%s' % record_suffix,''),
			"minutes"	: (seconds_worked / 60),
			"comments"	: ticket_time.get('comments','')}
		return values
		
		
	def replace_placeholders_in_comment(self, comment, ticket_time):
		"""Replaces all placeholders set in the user preferences 
		note_pattern - 'Additional infos for a time entry note'
		by their current values and append or place in the actual comment"""	
		
		if self.prefs.note_pattern == '':
			return
		
		ticket = get_all_dict(self.env,"SELECT * FROM ticket WHERE id=%s",ticket_time['ticket']).pop()
		
		new_comment = self.prefs.note_pattern
		new_comment = new_comment.replace("{ticket_id}", str(ticket['id']))
		new_comment = new_comment.replace("{ticket_summary}", ticket['summary'])
		new_comment = new_comment.replace("{ticket_status}", ticket['status'])
		new_comment = new_comment.replace("{ticket_type}", ticket['type'])
		new_comment = new_comment.replace("{milestone}", ticket['milestone'])
		new_comment = new_comment.replace("{component}", ticket['component'])
		new_comment = new_comment.replace("{reporter}", ticket['reporter'])
		new_comment = new_comment.replace("{owner}", ticket['owner'])
		
		if new_comment.find("{comment}") != -1:
			new_comment = new_comment.replace("{comment}", comment)
		else:
			new_comment += " " + comment
		
		return new_comment