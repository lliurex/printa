import xmlrpc.client
import ssl
import syslog
import socket
import ipaddress

def dprint(msg):
	
	syslog.syslog("[PRINTA] %s"%msg)

class N4dManager:

	def __init__(self):
		
		try:
			self.get_service_variables()
		except:
			self.printa_server="localhost"
		
	#def __init__
	
	def is_valid_ip(self,ip):
		
		try:
			ipaddress.ip_address(ip)
			return True
		except:
			return False
		
	#def is_valid_ip
	
	def get_ip_from_host(self,hostname):
		
		try:
			return socket.gethostbyname(hostname)
		except:
			return hostname
		
	#def get_ip_from_host

	def get_service_variables(self):
		
		client=xmlrpc.client.ServerProxy("https://localhost:9779",allow_none=True,context=ssl._create_unverified_context())
		ret=client.get_variable("PRINTASERVER")
		self.printa_server="localhost"
		
		if ret["status"]==0 and ret["return"]!=None:
			self.printa_server=ret["return"]
			if not self.is_valid_ip(self.printa_server):
				#we might be able to get server ip. Less prone to failure
				# if not, we'll use previously returned value
				self.printa_server=self.get_ip_from_host(self.printa_server)
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
