from componentdependencies.interface import IRequireComponents
from trac.core import *
from tracsqlhelper import *
from trac.util.datefmt import utc, to_timestamp

class Trac2MiteUserPrefs(object):
	implements(IRequireComponents)
	
	def __init__(self):
		self.is_authenticated = False
		self.account_name = None
		self.api_key = None
		self.note_pattern = None
		self.bindings = []
		# p = project and s = service
		self.rsrc_types = ["p", "s"]
		self.rsrcs_by_type = {"p" : [], "s" : []}
		self.rsrcs_by_type_and_binded = {"p" : [], "s" : []}
		self.connection_updated_on = None
		
	##################
	### implementation IRequireComponents
	def requires(self):
		"""Missing description...
		"""
		return [Trac2MitePlugin]
		
	############	
	### internal methods
	def init_prefs(self, env, req):
		"""Missing description...
		"""
		# if already initialized don't repeat the following database queries
		if self.account_name:
			return True

		user_prefs = get_all_dict(env,"SELECT * FROM mite_user_prefs WHERE user=%s",req.authname)

		if not user_prefs: return False

		prefs = user_prefs[0]
		
		self.account_name = prefs["account_name"]
		self.api_key = prefs["api_key"]
		self.note_pattern = prefs["note_pattern"]
		self.connection_updated_on = prefs["connection_updated_on"] 
		self.is_authenticated = True if self.connection_updated_on else False
		
		if self.is_authenticated:
			# init mite bindings	
			bindings_db = get_all_dict(env,"SELECT mite_rsrc_id FROM mite_bindings WHERE user=%s",req.authname)
			
			for binding in bindings_db:
				self.bindings.append(binding['mite_rsrc_id'])
			
			# init and order mite resources by type and bindings 
			for rsrc_type in self.rsrc_types:
				sql = "SELECT * FROM mite_rsrcs WHERE user=%s AND type=%s"
				self.rsrcs_by_type[rsrc_type] = get_all_dict(env, sql,req.authname,rsrc_type)
				
				for rsrc in self.rsrcs_by_type[rsrc_type]:
					if rsrc['id'] in self.bindings:
						self.rsrcs_by_type_and_binded[rsrc_type].append(rsrc)
				
		return True