import xmlrpc.client
import ssl
import syslog

def dprint(msg):
	
	syslog.syslog("[PRINTA] %s"%msg)

class N4dManager:

	def __init__(self):
		
		try:
			self.get_service_variables()
		except:
			self.printa_server="localhost"
		
	#def __init__

	def get_service_variables(self):
		
		client=xmlrpc.client.ServerProxy("https://localhost:9779",allow_none=True,context=ssl._create_unverified_context())
		var=client.get_variable("","VariablesManager","PRINTASERVER")
		self.printa_server="localhost"
		
		if var!=None:
			self.printa_server=var
		else:
			self.printa_server="127.0.0.1"
		
	#def get_variables
	

	def add_request(self,ip,user,msg):
		
		client=xmlrpc.client.ServerProxy("https://%s:9779"%self.printa_server,allow_none=True,context=ssl._create_unverified_context())
		ret=client.add_request("","PrintaServer","",ip,user,msg)
		return ret
		
	#def register_request

	
	def get_request_status(self,id):
		
		client=xmlrpc.client.ServerProxy("https://%s:9779"%self.printa_server,allow_none=True,context=ssl._create_unverified_context())
		ret=client.get_request_status("","PrintaServer",id)
		
		return ret
		
	#def check_request_status
	
	
#class N4dManager