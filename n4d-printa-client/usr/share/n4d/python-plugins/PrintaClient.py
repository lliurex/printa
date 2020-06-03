import os
import threading 
import time
import socket
import pwd

class PrintaClient:
	
	def __init__(self):
		
		if not os.path.exists("/run/printa"):
			os.makedirs("/run/printa")
		
	#def init
		
	def startup(self,options):
		
		objects["VariablesManager"].register_trigger("PRINTAREQUESTS","PrintaClient",self.request_trigger)
		t=threading.Thread(target=self._startup)
		t.daemon=True
		t.start()
		
	#startup
	

	def _startup(self):
		
		tries=1
		for x in range(0,tries):
			
			self.printa_server=objects["VariablesManager"].get_variable("PRINTASERVER")
			if self.printa_server!=None:
				break
			else:
				time.sleep(1)
		
		if self.printa_server==None:
			self.printa_server="127.0.0.1"
		
	#def startup

	
	def _get_own_ip(self):
		
		ip = None
		
		try:
			s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
			s.connect((self.printa_server,9779))
			ip,port=s.getsockname()
		except Exception as e:
			print e
			
		return ip
		
	#def _get_own_ip
	
	def request_trigger(self,value):
		
		if value!=None:
			ip=self._get_own_ip()
			print ip,value.keys()
			if ip in value:
				for user in value[ip]:
					try:
						user_data=pwd.getpwnam(user)
						user_path="/run/user/%s/printa/printa_client"%user_data.pw_uid
						if os.path.exists(user_path):
							print "UPDATING %s TOKEN..."%user
							f=open(user_path,"w")
							f.write(str(time.time()))
							f.close()
					except Exception as e:
						print e
			
		
	#def request_trigger
	
	
	
#class PrintaClient