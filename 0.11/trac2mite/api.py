from trac.core import *

# new interface to define ExtensionPoints in TracHoursPlugin
class ITracHoursPluginListener(Interface):
	
	def after_ticket_time_created(ticket_time):
		"""Called when a ticket time is created."""

	def before_ticket_times_updated(ticket_times):
		"""Called when ticket times are modified"""
	
	def before_ticket_times_deleted(self,ticket_times_ids):
		"""Called before ticket times get's deleted """	
		
	def before_process_request(req, ticket_id):
		"""Called when a TracHoursPlugin page is requested"""