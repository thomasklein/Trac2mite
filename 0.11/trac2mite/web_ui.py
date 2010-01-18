"""
web handlers for Trac2Mite
"""
from componentdependencies.interface import IRequireComponents
from datetime import datetime
from trac.core import *
from trac.prefs import IPreferencePanelProvider
from tracsqlhelper import *
from trac.util.datefmt import utc, to_timestamp
from trac.util.translation import _
from trac.web.chrome import ITemplateProvider, add_stylesheet, add_script, add_warning, add_notice

# local imports
from mite import Mite
from synchronizer import Trac2MiteSynchronizer
from trac2mite import Trac2MitePlugin
from userprefs import Trac2MiteUserPrefs

class Track2MitePreferencePanelProvider(Component):
	implements(IPreferencePanelProvider,IRequireComponents)

	_form_fields = ['mite_account_name', 'mite_api_key']
	
	def __init__(self):
		self.prefs = None
		self.mite = None
	
	##################
	### implementation IRequireComponents
	def requires(self):
		"""Missing description...
		"""
		return [Trac2MitePlugin]
	
	##################
	### implementation IPreferencePanelProvider

	def get_preference_panels(self, req):
		"""Return a list of available preference panels.

        The items returned by this function must be tuple of the form
        `(panel, label)`.
        """
		if req.authname and req.authname != 'anonymous':
			yield ('mite', _('mite'))

	def render_preference_panel(self, req, panel):
		"""Process a request for a preference panel.

        This function should return a tuple of the form `(template, data)`,
        where `template` is the name of the template to use and `data` is the
        data to be passed to the template.
        """
		add_stylesheet(req, 't2m/css/mite.css')
		add_script(req, 't2m/js/mite.js')
		
		# if the form with the user prefernces was sendt 
		if req.method == 'POST':
			
			status = True
			note = ''
			
			# value was set dynamically in mite.js => initMiteComponentsPreferences()
			button_pressed = req.args.get("mite_button_pressed",'')
			
			if button_pressed == 'disconnect_account_data':
				status = self.disconnect_mite_account(req)
				note = "You got successfully disconnected from your mite.account!"
			elif button_pressed == 'check_account_data':
				
				if self.prefs.account_name != None:
					note = "You successfully synchronized with your mite.account!"
				else:
					note = "You got successfully connected to your mite.account!"
				
				status = self.check_and_save_account_data(req)
			
			elif button_pressed == 'save_preferences':
				status = self.save_preferences(req)
				note = 'Your preferences got successfully updated!'
			
			if status == True:
				add_notice(req,note)
			else:
				add_warning(req,status)
		
		self.prefs = Trac2MiteUserPrefs()
		self.prefs.init_prefs(self.env, req)
		
		connection_status_css_class = "mite_connection_inactive"
		connection_status_text = "Inactive"
		mite_user_resources_f = None
		
	# set new values for above vars 
	# if the user is already connected to a mite account
		if self.prefs.is_authenticated:
			connection_status_css_class = "mite_connection_active"
			connection_status_text = "Connection active (Updated at %s)" % datetime.fromtimestamp(self.prefs.connection_updated_on).__str__()
			mite_user_resources_f = self.getMiteResources_f()
		
	# return template name and vars to use
		return 'prefs_panel_mite.html', {
			'user_settings': {'mite_account_name': self.prefs.account_name,
							  'mite_api_key': self.prefs.api_key,
							  'is_authenticated' : self.prefs.is_authenticated,
							  'note_pattern' : self.prefs.note_pattern},
			'connection_status_css_class': connection_status_css_class,
			'connection_status_text': connection_status_text,
			'mite_user_resources_f': mite_user_resources_f
			}
			
	
	def check_and_save_account_data(self, req):
		"""Tries to connect to mite with the given credentials
		and synchronizes all user resources with Trac
		"""
		values = {	"account_name":req.args.get('mite_account_name'),
					"api_key":req.args.get('mite_api_key')}

		if not (values["account_name"] and values["api_key"]):
			return "Given credentials were incomplete. Please recheck them."

		if not self.init_mite(values["account_name"],values["api_key"]):
			return "Could not connect to your mite account. Please recheck your credentials."

		# calculate current timestamp based on the current datetime
		values["connection_updated_on"] = to_timestamp(datetime.now(utc))

		# UPDATE old user preferences if there were any
		if (self.prefs.account_name):
			update_row_from_dict(self.env, "mite_user_prefs", "user", req.authname, values)
		# INSERT a new row for this users preferences
		else:
			values["user"] = req.authname
			insert_row_from_dict(self.env, "mite_user_prefs", values)
		
		synch = Trac2MiteSynchronizer(self.env, self.mite, req.authname)
		
		if not synch.synchronize(self.prefs.rsrcs_by_type):
			return "ERROR in Trac2Mite: Could not synchronize with your account data! Reason: %s" % synch.lastError
		
		# ONLY on the initial connection....
		if (self.prefs.account_name):
			return True
			
		# set ALL of the users mite resources as default BINDINGS 
		self.prefs = Trac2MiteUserPrefs()
		self.prefs.init_prefs(self.env, req)
	
		for rsrc_type in self.prefs.rsrc_types:
			for rsrc in self.prefs.rsrcs_by_type[rsrc_type]:

				values_prefs = {"user":req.authname,
								"mite_rsrc_id": rsrc['id'],
								"component_id": 0}
				insert_row_from_dict(self.env, "mite_bindings", values_prefs)
		
		return True
		
		
	def disconnect_mite_account(self, req):
		"""Missing description...
		"""
		execute_non_query(self.env, "DELETE FROM mite_user_prefs WHERE user=\"%s\"" % req.authname)
		execute_non_query(self.env, "DELETE FROM mite_rsrcs WHERE user=\"%s\"" % req.authname)
		execute_non_query(self.env, "DELETE FROM mite_bindings WHERE user=\"%s\"" % req.authname)
		
		sql = "SELECT * FROM ticket_time WHERE worker=%s"
		user_ticket_times = get_all_dict(self.env, sql,req.authname)
		
		nullifier = {"mite_time_entry_id" : '',
					 "mite_time_entry_updated_on" : '',
					 "mite_service_id" : '',
					 "mite_project_id" : ''}
		
		for ticket_time in user_ticket_times:
			update_row_from_dict(self.env, "ticket_time", "id", ticket_time["id"], nullifier)
		
		return True
		
	def init_mite(self, account_name=None, api_key=None, authenticated=False):
		"""Missing description...
		"""
		# init or re-init mite object if credentials are given
		if (account_name and api_key):
			mite = Mite(account_name,api_key, authenticated)
		# if object already existed	
		elif self.mite != None:
			return True	
		# use users preferences in case there are any  
		elif (self.prefs.account_name):
			mite = Mite(self.prefs.account_name,self.prefs.api_key)
		else:
			print "\n***ERROR in Trac2Mite: No credentials provided to init mite the first time!\n"
			return False

		if not mite.authenticated:
			print "\n***ERROR in Trac2Mite: Authentication failed!\nReason: << "+mite.lastError+" >>\n"
			return False

		self.mite = mite	
		return True
	
	
	def save_preferences(self, req):
		"""Saves user preference values for mite
		"""
		values_prefs = {"note_pattern":req.args.get('preferences_note_pattern')}
		update_row_from_dict(self.env, "mite_user_prefs", "user", req.authname, values_prefs)
		
		self.save_bindings(req)
		
		return True
	
	
	def save_bindings(self, req):
		"""Saves all selected resources entries as bindings in the database
		"""
		bindings_int = [] # contains each value of bindings converted to int 
		
		# get all selected bindings and save those in the database
		for rsrc_type in self.prefs.rsrc_types:
			
			bindings = req.args.get('mite_bindings_' + rsrc_type + '[]','')
			
			if (bindings != '') and  (not isinstance(bindings, list)):
				bindings = [bindings]
			
			# loop through all selected bindings and check 'em for existence  
			for binding in bindings:
				
				bindings_int.append(int(binding))
				
				# check if the binding already exists
				# in this case nothing has to be done
				if int(binding) in self.prefs.bindings:
					continue
				
				# otherwise save a new binding
				values_prefs = {"user":req.authname,
								"mite_rsrc_id": binding,
								"component_id": 0}
				
				insert_row_from_dict(self.env, "mite_bindings", values_prefs)
		
		# DELETE old bindings	
		diff = set(self.prefs.bindings) - set(bindings_int)	
		for old_binding in diff:
			execute_non_query(self.env, "DELETE FROM mite_bindings WHERE mite_rsrc_id=%s", old_binding)
			
		return True
		
		
	def getMiteResources_f(self):
		"""Missing description...
		"""
		rsrcs_f = {}
		
		for rsrc_type in self.prefs.rsrc_types:
			
			rsrcs_f[rsrc_type] = "<select size='" + str(len(self.prefs.rsrcs_by_type[rsrc_type])) + "' name='mite_bindings_" + rsrc_type + "[]' multiple='multiple'>\n"
			
			for rsrc in self.prefs.rsrcs_by_type[rsrc_type]:
				selected = ''
				if rsrc['id'] in self.prefs.bindings:
					selected = 'SELECTED '
				rsrcs_f[rsrc_type] += "<option " + selected + "value='" + str(rsrc['id']) + "'>" + rsrc['name'] + "</option>\n"
			
			rsrcs_f[rsrc_type] += "</select>\n"
			
		return rsrcs_f
	