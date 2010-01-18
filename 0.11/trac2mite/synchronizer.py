from tracsqlhelper import *
from trac.util.datefmt import utc, to_timestamp

class Trac2MiteSynchronizer(object):
	
	def __init__(self, env, mite, user_name):
		self.mite = mite
		self.user_name = user_name
		self.lastError = None
		self.env = env
		
	def synchronize(self, local_rsrcs_by_type):
		"""Missing description...
		"""
		try:
			for rsrc_type in local_rsrcs_by_type.keys():
				remote_rsrcs = self.mite.get_remote_resources(rsrc_type)
				remote_rsrcs_mapped = self.map_remote_resources(rsrc_type, remote_rsrcs)
				self.synchronize_rsrcs(rsrc_type, local_rsrcs_by_type[rsrc_type], remote_rsrcs_mapped)
		except Exception, e:
			self.lastError = e.__str__()
			print "\n***Error in Trac2MitePlugin: << %s >>\n" % self.lastError
			return False
			
		return True
		
	def synchronize_rsrcs(self, rsrc_type, local_rsrcs, remote_rsrcs):
		"""Synchronize resources of rsrc_type by comparing values in local_rsrcs and remote_rsrcs"""
		
		# array to save the 'remote_rsrc_id' for each local record
		local_remote_ids = {}
		local_rsrc_ids = set()
		updated_local_record_ids = set()
		
		for local_rsrc in local_rsrcs:
			local_rsrc_ids.add(local_rsrc["id"])
			local_remote_ids[int(local_rsrc["remote_rsrc_id"])] = local_rsrc["id"]
		
		for rsrc in remote_rsrcs:
			# UPDATE local resource in case
			if rsrc["remote_rsrc_id"] in local_remote_ids:
				db_record_id = local_remote_ids[rsrc["remote_rsrc_id"]]
				updated_local_record_ids.add(db_record_id)
				update_row_from_dict(self.env, "mite_rsrcs", "id", db_record_id, rsrc)
			# CREATE NEW local resource
			else:	
				insert_row_from_dict(self.env, "mite_rsrcs", rsrc)
		
		# check which entries have to get deleted 	
		diff = local_rsrc_ids - updated_local_record_ids
		
		# DELETE local resources
		for local_rsrc_id in diff:
			execute_non_query(self.env, "DELETE FROM mite_rsrcs WHERE id=%s", local_rsrc_id)
		
	def map_remote_resources(self, rsrc_type, remote_rsrcs):
		"""Maps data structure of remote object to data structure used in the database"""
		mapped_rsrcs = []
		
		for rsrc in remote_rsrcs:
			
			name = rsrc["name"]
			if (rsrc_type=="p") and "customer-name" in rsrc:
				name += " (%s)" % rsrc["customer-name"]
			
			values = {	"user": self.user_name, 
						"type": rsrc_type,
						"remote_rsrc_id" : int(rsrc['id']),
						"name" : name}
						
			mapped_rsrcs.append(values)
		return mapped_rsrcs