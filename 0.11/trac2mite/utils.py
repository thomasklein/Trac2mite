from tracsqlhelper import *

# methods to setup listeners in certain ticket time actions of the TracHoursPlugins 
def add_listener_before_process_request(self, req):
	
	path = req.path_info.rstrip('/')
	
	# only add listeners if the current request 
	# goes to hours for  specific ticket e.g. hours/<ticket-id>
	if path.count('/') == 2:
		ticket_id = int(path.split('/')[-1]) # matches a ticket number
	
		for listener in self.change_listeners:
			listener.before_process_request(req, ticket_id)
	
	return self.process_request_old(req)

def add_listener_after_ticket_time_created(self, *args, **kwargs):
	"""called for TracHoursPlugin.add_ticket_hours
	args: 0 = ticket.id, 1 = worker, 2 = seconds_worked
	kwargs: submitter, time_started, comments
	"""
	self.add_ticket_hours_old(*args, **kwargs)
	
	# get last inserted ticket time
	new_ticket_time = get_all_dict(self.env, "SELECT * FROM ticket_time WHERE ticket==%s ORDER BY time_submitted DESC LIMIT 1" % args[0]).pop()
	
	for listener in self.change_listeners:
		listener.after_ticket_time_created(new_ticket_time)

def add_listener_before_ticket_times_edited(self, req, ticket):
	"""Called for TracHoursPlugin.edit_ticket_hours.
	Can't call it afterwards, because TracHoursPlugin.edit_ticket_hours end with a redirection.
	Calls listener for 'before_ticket_times_deleted' with ticket times marked for deletion and 
	listeners for 'before_ticket_times_updated' for the rest
	"""
	for listener in self.change_listeners:
		
		# collect removed hours
		removed_tt_ids = []
		for field, newval in req.args.items():
			if field.startswith("rm_"):
				id = int(field[len("rm_"):])
				removed_tt_ids.append(id)
		
		listener.before_ticket_times_deleted(removed_tt_ids)
		
		# collect updated ticket times
		updated_tt = {}
		for field, newval in req.args.items():
			if field.startswith("hours_"):
				id = int(field[len("hours_"):])
				
			# skip removed ticket times
				if id in removed_tt_ids: continue
				
				try:
					updated_ticket_time = (int(float(newval) * 3600) + 
							 	  	   	   int(float(req.args['minutes_%s' % id]) * 60))
				except ValueError:
					raise ValueError("Please enter a valid number of hours")
					req.redirect(req.href(req.path_info))			
				
				updated_tt[id] = updated_ticket_time
		
		listener.before_ticket_times_updated(updated_tt)
		
	return self.edit_ticket_hours_old(req, ticket)