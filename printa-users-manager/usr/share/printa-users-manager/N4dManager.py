import xmlrpc.client
import ssl
import syslog

import N4dLogin

DEBUG=True
SYSLOG=True

RSRC_PATH="/usr/share/printa-users-manager/rsrc/"

def dprint(data):
	if DEBUG:
		print("[N4dManager] %s"%data)
	if SYSLOG:
		syslog.syslog("[N4dManager] %s"%data)

class N4dManager:
	
	def __init__(self):
	
		self.printa_server=self.get_printa_server()
		context=ssl._create_unverified_context()	
		self.client=xmlrpc.client.ServerProxy("https://%s:9779"%self.printa_server,allow_none=True,context=context)
		
		self.login=N4dLogin.N4dLogin()
		self.login.set_server(self.printa_server)
		self.login.set_allow_user_edit(True)
		self.login.set_force_get_auth(True)
		self.login.set_use_cache(False)
		self.login.set_banner_path(RSRC_PATH+"printa-manager-banner.svg")
		self.login.set_icon_path(RSRC_PATH+"printa.svg")
		self.login.set_valid_groups(["admins","sudo"])
	
	#def init

	def get_printa_server(self):
		
		client=xmlrpc.client.ServerProxy("https://localhost:9779",allow_none=True,context=ssl._create_unverified_context())
		printa_server=client.get_variable("","VariablesManager","PRINTASERVER")
		
		if printa_server==None:
			printa_server="127.0.0.1"
		
		return printa_server
		
	#def get_variables


	def set_auth(self,user,password):
	
		self.auth=[user,password]
		
		return True
		
	#def set_auth

	def get_user_list(self):
		
		try:
			ret=self.client.get_user_list("","PrintaServer")
			if ret["status"]:
				#dprint("get_user_list success")
				return ret["msg"]
			else:
				dprint("[!] get_user_list failed")
				return []
				
		except Exception as e:
			dprint(e)
			return []

	#def get_user_list
	
	def get_group_list(self):
		
		try:
			ret=self.client.get_group_list("","PrintaServer")
			if ret["status"]:
				#dprint("get_group_list success")
				return ret["msg"]
			else:
				dprint("[!] get_group_list failed")
				return []
		except Exception as e:
			dprint(e)
			return []
		
	#def get_group_list
	
	def get_user_info(self,user):
		
		try:
			ret=self.client.get_user_info(self.auth,"PrintaServer",user)
			if ret["status"]:
				#dprint("get_user_info success %s"%user)
				return ret["msg"]
			else:
				dprint("[!] get_user_info failed")
				return Noine
		except Exception as e:
			dprint(e)
			return None
		
	#def get_user_info
	
	def set_user_info(self,user,quota,locked,freepass):
		
		try:
			ret=self.client.set_user_info(self.auth,"PrintaServer",user,quota,locked,freepass)
			
			if ret["status"]:
				#dprint("set_user_info success")
				return True
			else:
				dprint("[!] set_user_info failed")
				return False
		except Exception as e:
			dprint(e)
			return False
		
	#def set_user_info
	
	def set_group_quota(self,group,quota,printer="default"):
		
		try:
			ret=self.client.set_group_quota(self.auth,"PrintaServer",group,quota,printer)
			
			if ret["status"]:
				#dprint("set_group_quota success")
				return True
			else:
				dprint("[!] set_group_quota failed")
				return False
		except Exception as e:
			dprint(e)
			return False
		
	#def set_group_quota
	
	def add_to_group_quota(self,group,add_value,printer="default"):
		
		try:
			ret=self.client.add_to_group_quota(self.auth,"PrintaServer",group,add_value,printer)
			if ret["status"]:
				#dprint("add_to_group_quota success")
				return True
			else:
				dprint("[!] add_to_group_quota failed")
				return False
		except Exception as e:
			dprint(e)
			return False
		
	#def set_group_quota
	
	def set_group_locked(self,group,locked):
		
		try:
			ret=self.client.set_group_locked(self.auth,"PrintaServer",group,locked)
			
			if ret["status"]:
				#dprint("set_group_locked success")
				return True
			else:
				dprint("[!] set_group_locked failed")
				return False
		except Exception as e:
			dprint(e)
			return False
			
	#def set_group_quota
	
	def set_group_freepass(self,group,freepass):
		
		try:
			ret=self.client.set_group_freepass(self.auth,"PrintaServer",group,freepass)
			
			if ret["status"]:
				#dprint("set_group_freepass success")
				return True
			else:
				dprint("[!] set_group_freepass failed")
				return False
		except Exception as e:
			dprint(e)
			return False
		
	#def set_group_quota
	
	def set_group_flag(self,group,locked,freepass):
	
		try:
			ret=self.client.set_group_flag(self.auth,"PrintaServer",group,locked,freepass)
		
			if ret["status"]:
				#dprint("set_group_flag success")
				return True
			else:
				dprint("[!] set_group_flag failed")
				return False
		except Exception as e:
			dprint(e)
			return False
		
	#def set_group_flag
	
	def get_autorefill_options(self):
		
		try:
			ret=self.client.get_autorefill_options("","PrintaServer")
			
			if ret["status"]:
				#dprint("get_autorefill_options success")
				#Fix period from seconds to days
				ret["msg"]["period"]=ret["msg"]["period"]/(24*60*60)
				return ret["msg"]
			else:
				dprint("get_autorefill_options failed: %e"%ret["msg"])
				return None
		except Exception as e:
			dprint(e)
			return None		
		
	#def get_autorefill_options
	
	def set_autorefill_options(self,amount,period,quota_limit):
		
		try:
			ret=self.client.set_autorefill_options(self.auth,"PrintaServer",amount,period,quota_limit)
			
			if ret["status"]:
				#dprint("set_autorefill_options success")
				return True
			else:
				dprint("set_autorefill_options failed: %s"%ret["msg"])
				return False
		except Exception as e:
			dprint(e)
			return False
		
	#def set_autorefill_options
	
	def set_autorefill_status(self,status):
		
		try:
			ret=self.client.set_autorefill_status(self.auth,"PrintaServer",status)
			
			if ret["status"]:
				#dprint("set_autorefill_status success")
				return True
			else:
				dprint("set_autorefill_status failed: %s"%ret["msg"])
				return False	
		except Exception as e:
			dprint(e)
			return False
			
	#def set_autorefill_status
