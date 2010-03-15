import urllib2
from xml.etree import ElementTree
import inspect

class RequestX(urllib2.Request):
	"""Extends Request-Object of urllib2 module with the possibility to 
	use other HTTP methods than POST and GET (e.g. PUT, DELETE...) for http requests. 
	
	"""
	def __init__(self, method, *args, **kwargs):
		self._method = method
		urllib2.Request.__init__(self, *args, **kwargs)

	def get_method(self):
		return self._method


class Mite(object):
	
	def __init__(self, account_name, api_key, authenticated = True):
		
		self.authenticated = authenticated
		self.account = "https://" + account_name + ".mite.yo.lk/"
		self.headers = {"X-MiteApiKey":api_key, "Content-Type":"text/xml"}
		self.lastError = ''
		
		if not self.authenticated:
			self.authenticated = self.authenticate()
	
	def authenticate(self):
		return True if (self.do_request("users.xml") != None) else False
	
	def insert_time_entry(self, date, minutes, project_id=None, service_id=None, note=''):
		"""
		returns new id of the time entry
		"""
		
		note = ''
		
		data = """
		<time-entry>
		   <date-at>%s</date-at>
		   <minutes>%s</minutes>
		   <project-id>%s</project-id>
		   <service-id>%s</service-id>
		   <note>%s</note>
		</time-entry>""" % (date, minutes, project_id or '', service_id or '', note.encode('utf-8'))
		
		response = self.do_request("time_entries.xml","POST",data)

		if not response:
			print "\nError in Trac2mite when trying to add a new time entry: '%s'" % self.lastError
			return None
		
		print "\nNew mite time entry (ID: %s) created!\n" % response.find("id").text
		return response.find("id").text
		

	def update_time_entry(self, time_entry_id, minutes=None, project_id=None, service_id=None, note=''):
		"""
		returns, on success, the id of the updated time entry in mite
		"""
		data = "<time-entry>"
		
		if (minutes):
			data += "<minutes>%s</minutes>" % minutes
		if (project_id != None):
			data += "<project-id>%s</project-id>" % project_id
		if (service_id != None):
			data += "<service-id>%s</service-id>" % service_id
		if (note):
			data += "<note>%s</note>" % note
		
		data += "</time-entry>"
		
		# can only contain True or False, since there's no response from the mite.api
		# for a PUT request
		status = self.do_request("time_entries/" + str(time_entry_id) + ".xml","PUT",data)
		
		if not status:
			return False
		
		print "\nmite time entry (ID: %s) was updated!\n" % time_entry_id
		return True
	
	def delete_time_entry(self, time_entry_id):
		"""returns boolean, if the deletion was successful
		"""
		status = self.do_request("time_entries/" + str(time_entry_id) + ".xml","DELETE")
		if not status:
			return False
		print "\nmite time entry (ID: %s) was succesfully deleted!\n" % time_entry_id
		return True
	
	def get_remote_resources(self, rsrc_type, updated_since=None):
		"""Returns remote resources as array of dictionaries.
		If the param updated_since is set, only the resources updated after this date
		will be returned."""
		
		rsrces = {	"p": "projects.xml",
					"s": "services.xml",
					"t": "time_entries.xml",
					"u": "users.xml"}
		
		rsrc_url = rsrces.get(rsrc_type, None)
		
		if not rsrc_url: 
			raise Exception("""Ressource type '%s' not found. Please use one of the 
							following types: %s""" % (rsrc_type, str(rsrces)))
		
		xml_response = self.do_request(rsrc_url)
		
		rsrces_tag = {	"p": "project",
						"s": "service",
						"t": "time_entry",
						"u": "user"}
		
		return self.xml_to_array_of_dics(xml_response, rsrces_tag.get(rsrc_type))
		
	def xml_to_array_of_dics(self, xml, rsrc_tag):
		"""Packs mite resources in xml object (ElementTree) into an array of dictionaries.
		Param rsrc_tag is the name of a single resource root tag (e.g. "project")
		"""
		dic = []
		for it in xml.getiterator(rsrc_tag):
			p_props = it.getchildren()
			dic_props = {}

			for prop in p_props:
				dic_props[prop.tag] = prop.text

			dic.append(dic_props)

		return dic	
		
	def do_request(self, mite_rsrc, method='GET', data=''):
		"""Executes request to the mite.api.
		Returns response as xml object (ElementTree). 
		Occuring errors are saved in self.lastError.
		"""
		url = self.account + mite_rsrc
		req = RequestX(method, url, data, self.headers)
	
		response = None
		try:
			api_response = urllib2.urlopen(req)
			response_status = api_response.info().dict['status']
			
			# special case, because no xml is returned
			if ((method=="PUT" or method=="DELETE") and response_status=="200 OK"):
				return True
			# create xml object for mite.api response
			else:
				response = ElementTree.fromstring(api_response.read())
		except (urllib2.HTTPError,urllib2.URLError, Exception), e:
			self.lastError = e.__str__()
		return response