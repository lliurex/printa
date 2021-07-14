import copy
import time
import xmlrpc.client
import ssl
import cups
import pwd
import grp
import math
import json
import tempfile
import os
import shutil
import threading
import codecs

import n4d.server.core
import n4d.responses

class PrintaServer:

	
	FREE_PASS=1
	ENOUGH_QUOTA=2
	
	USER_LOCKED=-1
	NOT_ENOUGH_QUOTA=-2
	AUTOREFILL_OPTIONS_ERROR=-5
	NOT_A_VALID_USER_ERROR=-10
	UNKNOWN_PRINTER_ERROR=-15
	NOT_A_VALID_USER_ERROR=-20
	INVALID_FLAG_COMBINATION_ERROR=-30
	REQUEST_NOT_FOUND_ERROR=-40
	GET_PRINTERS_ERROR=-50
	PRINTER_ALREADY_CONTROLLED_ERROR=-60
	PRINTER_NOT_CONTROLLED_ERROR=-70
	UNKNOWN_USER_ERROR=-80
	
	def __init__(self):
		
		self.run_path="/run/printa/"
		self.history_path="/var/lib/printa"
		self.history_file=self.history_path+"/history.json"
		self.saving_history=False
		self.use_default_quota=True
		self.default_user_quota=200
		self.default_printer_quota=6000
		self._check_history_file()
		self.autorefill_thread=threading.Thread()
		self.autorefill_thread_working=False
		self.core=n4d.server.core.Core.get_core()
		
	#def init
	
	def startup(self,options):

		self.requests_variable=self.core.get_variable("PRINTAREQUESTS")["return"]

		if self.requests_variable == None:
			self.requests_variable = {}
			self.core.set_variable("PRINTAREQUESTS",self.requests_variable,{"info":"Printa current requests - Volatile","volatile":True})
		
		self.db=self.core.get_variable("PRINTADB")["return"]
		
		if self.db == None:
			self.db = {}
			self.db["users"]={}
			self.db["printers"]={}
			self.db["autorefill"]={}
			self.db["autorefill"]["enabled"]=False
			self.db["autorefill"]["period"]=0
			self.db["autorefill"]["quota_limit"]=500
			self.db["autorefill"]["last_set"]=None
			self.db["autorefill"]["should_set"]=None
			self.db["autorefill"]["amount"]=0
			self.db["autorefill"]["group_filter"]=[]
			self.core.set_variable("PRINTADB",self.db,{"info":"Printa User and Printer data"})
			
		if self.db["autorefill"]["enabled"]:
			self._start_autorefill_loop()
		
	#def startup
	
	# ##################################### #
	#	PRIVATE FUNCTIONS		#
	# ##################################### #	
	
	def _add_user(self,username):
		
		if not self._is_valid_user(username):
			
			return {"status": False, "msg":"Invalid user"}
		
		if username not in self.db["users"]:
			
			self.db["users"][username]={}
			self.db["users"][username]["quota"]={}
			self.db["users"][username]["quota"]["default"]=self.default_user_quota
			for printer in self.db["printers"]:
				self.db["users"][username]["quota"][printer]=self.default_user_quota
			self.db["users"][username]["last_quota_update"]=time.time()
			self.db["users"][username]["free_pass"]=False
			self.db["users"][username]["locked"]=False
			
			self.save_db_variable()
			
			return {"status": True, "msg":""}
			
		return {"status": False, "msg": "User already exists"}
		
	#def add_user
	
	def _add_printer(self,printer_name):
		
		try:
			if printer_name not in self.db["printers"]:
				
				name=printer_name
				self.db["printers"][name]={}
				self.db["printers"][name]["quota"]=self.default_printer_quota
				self.db["printers"][name]["quota_enabled"]=False
				self.db["printers"][name]["last_quota_update"]=time.time()
				self.db["printers"][name]["free_pass"]=False
				self.db["printers"][name]["locked"]=False
			
				for user in self.db["users"]:
					self.db["users"][user]["quota"][name]=self.default_user_quota
				
				self.save_db_variable()
				
				return {"status":True,"msg":""}
			
			return {"status":False,"msg":"Printer already added"}
			
		except Exception as e:
			return {"status":False,"msg":str(e)}
		
	#def add_printer
	
	def _remove_printer(self,printer_name):
		
		if printer_name in self.db["printers"]:
			self.db["printers"].pop(printer_name)
			
			for user in self.db["users"]:
				if printer_name in self.db["users"][user]["quota"]:
					self.db["users"][user]["quota"].pop(printer_name)
			
			self.save_db_variable()
			
		return True
		
	#def _remove_printer
	
	def _is_valid_user(self,user):
		
		try:
			pwd.getpwnam(user)
			return True
		except:
			return False
		
	#def _is_valid_user
	
	def _get_job_pages(self,job_info):
		
		#BACKEND ARGS
		# 0 printing backend
		# 1 job id
		# 2 user
		# 3 job name
		# 4 number of copies
		# 5 options
		# 6 
		
		copies=int(job_info["args"][4])
		pages=job_info["pages"]
		pages=pages*copies
		
		options={}
		for option in job_info["args"][5].split(" "):
			try:
				key,value=option.split("=")
				options[key]=value
			except Exception as e:
				pass
		
		# KNOWN CASES
		if "number-up" in options:
			nup=1.0
			try:
				nup=float(options["number-up"])
			except:
				pass
			pages=math.ceil(pages/nup)
			pages=int(pages)

		return pages
		
	#def _get_job_pages
	
	def _check_history_file(self):
		
		if not os.path.exists(self.history_path):
			os.makedirs(self.history_path)
		
	#def check history file
	
	def _get_history(self):
		
		if os.path.exists(self.history_file):
			f=open(self.history_file)
			history=json.load(f)
			f.close()
			
			return history
			
		return {}
	
	#def _get_history
	
	def _save_history(self,data):
		
		try:
			
			while(self.saving_history):
				time.sleep(2)
			
			self.saving_history=True
			tmp,filename=tempfile.mkstemp()
			f = codecs.open(filename,'w',"utf-8")
			json.dump(data,f,indent=4,ensure_ascii=False)			
			f.close()
			shutil.copy(filename,self.history_file)
			self.saving_history=False
			
			return True
		except Exception as e:
			print(e)
			self.saving_history=False
			return False
		
	#def _save_history
	
	def _add_job_to_history(self,job):
		
		history=self._get_history()
		
		user=job["user"]
		if user not in history:
			history[user]=[]
		
		history[user].append(job)
		self._save_history(history)
		
	#def _add_job_to_history
	
	
	def _format_time(self,t):
		
		format_str="%H:%M:%S - %Y/%m/%d"
		return time.strftime(format_str,time.localtime(t))
		
	#def _format_time
	
	def _start_autorefill_loop(self):
		
		if not self.autorefill_thread.is_alive():
			if self.db["autorefill"]["enabled"] and self.db["autorefill"]["period"]!=0 and self.db["autorefill"]["should_set"]!=None:
				self.autorefill_thread=threading.Thread(target=self._autorefill_loop)
				self.autorefill_thread.daemon=True
				self.autorefill_thread.start()
		
	#def _start_autorefill_loop
	
	def _kill_autorefill_loop(self):
		
		#DANGER ZONE
		if self.autorefill_thread.is_alive():
			timeout=10
			count=0
			while(self.autorefill_thread_working):
				time.sleep(1)
				count+=1
				if count >=timeout:
					print("[PrintaServer] Autorefill thread kill timed out")
					self.autorefill_thread_working=False
					break
					
			self.autorefill_thread._Thread__stop()
			
			if not self.autorefill_thread.is_alive():
				print("[PrintaServer] Autorefill thread stopped")
		
	#def _kill_autorefill_loop
	
	def _restart_autorefill_loop(self):
		
		self._kill_autorefill_loop()
		self._start_autorefill_loop()
		
		return self.autorefill_thread.is_alive()
		
	#def _restart_autorefill_loop
	
	def _autorefill_loop(self):
		
		print("[PrintaServer] Autorefill thread started")
		while(self.db["autorefill"]["enabled"]):
			current_time=time.time()
			if current_time >= self.db["autorefill"]["should_set"]:
				print("[PrintaServer] Autorefilling quota at %s..."%(self._format_time(self.db["autorefill"]["should_set"])))
				self.autorefill_thread_working=True
				self.db["autorefill"]["last_set"]=self.db["autorefill"]["should_set"]
				self.db["autorefill"]["should_set"]+=self.db["autorefill"]["period"]
				
				if len(self.db["autorefill"]["group_filter"])==0:
					for user in self.db["users"]:
						
						new_amount=self.db["users"][user]["quota"]["default"]+self.db["autorefill"]["amount"]
						if new_amount >= self.db["autorefill"]["quota_limit"]:
							self.db["users"][user]["quota"]["default"]=self.db["autorefill"]["quota_limit"]
						else:
							self.db["users"][user]["quota"]["default"]=new_amount
				
				self.save_db_variable()
				self.autorefill_thread_working=False
				
			else:
				sleep_time=self.db["autorefill"]["should_set"]  - current_time
				print("[PrintaServer] Autorefill is sleeping for %s secs until %s"%(sleep_time,self._format_time(self.db["autorefill"]["should_set"])))
				time.sleep(sleep_time)
		
	#def _autorefill_loop
	
	def _get_notify_ip(self,call_ip,origin_ip):
		
		# call_ip as seen by n4d (printa server)
		# origin_ip as seen by cups backend (client ip using a certain cups server)
		
		if call_ip == origin_ip or origin_ip=="127.0.0.1":
			# printa-server is printing from its own printer
			return call_ip
			
		if call_ip == "127.0.0.1":
			# clients are printing from printa-server printer
			return origin_ip
			
		if origin_ip == "127.0.0.1":
			# client is printing from its own printer
			return call_ip
			
		if origin_ip == objects["VariablesManager"].get_variable("SRV_IP"):
			#printa-server are printing from client1 printer
			return "127.0.0.1"
		
		#client2 is printing from client1 printer
		return origin_ip
			
		
	#def _get_notify_ip
	
	def _get_group_members(self,group):
			
		ret=[]
		try:
			ginfo=grp.getgrnam(group)
			ret=ginfo.gr_mem
		except Exception as e:
			print(e)
				
		return ret
			
	#def get_group_members
	
	# ##################################### #
	# 	AUTO REFILL OPERATIONS		#
	# ##################################### #
	
	def get_autorefill_options(self):
		
		return n4d.responses.build_successful_call_response(self.db["autorefill"])
		#return {"status": True, "msg": self.db["autorefill"]}
		
	#def get_autorefill_options
	
	def set_autorefill_status(self,status):
		
		self.db["autorefill"]["enabled"]=status
		if self.db["autorefill"]["period"]!=0:
			current_time=time.time()
			self.db["autorefill"]["last_set"]=current_time
			self.db["autorefill"]["should_set"]=current_time+self.db["autorefill"]["period"]
		self.save_db_variable()
		
		if not status:
			self._kill_autorefill_loop()
		else:
			self._start_autorefill_loop()
		
		return n4d.responses.build_successful_call_response()
		#return {"status":True,"msg":""}
		
	#def set_autorefill_status
	
	def set_autorefill_options(self,amount,period_in_days,quota_limit,group_filter=[],restart=True):
		
		try:
			self.db["autorefill"]["amount"]=int(amount)
			self.db["autorefill"]["quota_limit"]=int(quota_limit)
			#Easier to work with seconds internally
			self.db["autorefill"]["period"]=int(period_in_days)*24*60*60
			self.db["autorefill"]["last_set"]=time.time()
			if type(group_filter)==list:
				self.db["autorefill"]["group_filter"]=group_filter
			self.db["autorefill"]["should_set"]=self.db["autorefill"]["last_set"]+self.db["autorefill"]["period"]
			self.save_db_variable()
			
			if restart:
				self._restart_autorefill_loop()
		
			return n4d.responses.build_sucessful_call_response()
			#return {"status": True, "msg": ""}
			
		except Exception as e:
			return n4d.responses.build_failed_call_response(PrintaServer.AUTOREFILL_OPTIONS_ERROR,str(e))
			#return {"status": False, "msg":str(e)}
		
	#def set_autorefill_options
	
	# ##################################### #
	#	VARIABLES OPERATIONS		#
	# ##################################### #

	def save_requests_variable(self,variable=None):

		if variable==None:
			variable=copy.deepcopy(self.requests_variable)
		else:
			self.requests_variable=copy.deepcopy(variable)

		#objects["VariablesManager"].set_variable("PRINTAREQUESTS",variable)
		self.core.set_variable("PRINTAREQUESTS",variable)
		
		return n4d.responses.build_successful_call_response()
		#return {"status":True,"msg":""}
		
	#def save_variable

	
	def save_db_variable(self,variable=None):
		
		if variable==None:
			variable=copy.deepcopy(self.db)
		else:
			self.db=copy.deepcopy(variable)
			
		#objects["VariablesManager"].set_variable("PRINTADB",variable)
		self.core.set_variable("PRINTADB",variable)
		
		return n4d.responses.build_successful_call_response()
		#return {"status":True,"msg":""}
	
	#def save_db_variable
	
	# ##################################### #
	#	 USER/PRINTER DB OPERATIONS	#
	# ##################################### #
	
	def get_user_info(self,user):
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")
			#return {"status":False,"msg":"Not a valid user"}
		
		if user not in self.db["users"]:
			self._add_user(user)
			
		
		user_data=copy.deepcopy(self.db["users"][user])
		
		h=self._get_history()
		if user in h:
			user_data["history"]=h[user]
		
		return n4d.responses.build_successful_call_response(user_data)
		#return {"status":True,"msg":user_data}
		
	#def get_user_info
	
	def get_user_quota(self,user,printer="default"):
	
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")
		
		if user not in self.db["users"]:
			self._add_user(user)
			
		if printer!="default" and printer not in self.db["printers"]:
			return n4d.responses.build_failed_call_response(PrintaServer.UNKNOWN_PRINTER_ERROR,"Unknown printer")
		
		return n4d.responses.build_successful_call_response(self.db["users"][user]["quota"][printer])
		#return {"status":True,"msg":self.db["users"][user]["quota"][printer]}
	
	#def get_user_quota
	
	def add_to_user_quota(self,user,add_value,printer="default"):
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")
		
		if user not in self.db["users"]:
			self._add_user(user)
		
		if printer in self.db["users"][user]["quota"]:
		
			self.db["users"][user]["quota"][printer]+=add_value
			
			if self.db["users"][user]["quota"][printer] < 0:
				self.db["users"][user]["quota"][printer]=0
				
			self.save_db_variable()
			return n4d.responses.build_successful_call_response()
			#return {"status":True, "msg":""}
		else:
			return n4d.responses.build_failed_call_response(PrintaServer.UNKNOWN_PRINTER_ERROR,"Unknown printer")
			#return {"status":False,"msg":"Unknown printer"}
		
	#def add_to_user_quota
	
	def set_user_quota(self,user,quota_value,printer="default"):
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")		
		
		if user not in self.db["users"]:
			self._add_user(user)
		
		if printer in self.db["users"][user]["quota"]:
		
			self.db["users"][user]["quota"][printer]=quota_value
			
			if self.db["users"][user]["quota"][printer] < 0:
				self.db["users"][user]["quota"][printer]=0
				
			self.save_db_variable()
			return n4d.responses.build_successful_call_response()
			#return {"status":True, "msg":""}
			
		else:
			return n4d.responses.build_failed_call_response(PrintaServer.UNKNOWN_PRINTER_ERROR,"Unknown printer")
			#return {"status":False, "msg":"Unknown printer"}
			
	#def set_user_quota
	
	def set_user_freepass(self,user,state):
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")	
		
		if user not in self.db["users"]:
			self._add_user(user)
			
		if type(state)!=bool:
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Unknown state: %s"%state)	
			#return {"status":False,"msg":"Unknown state %s"%state}
			
		self.db["users"][user]["free_pass"]=state
		self.save_db_variable()
		
		return n4d.responses.build_successful_call_response()
		#return {"status":True,"msg":""}
		
	#def set_free_pass
	
	def set_user_locked(self,user,state):
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")	
		
		if user not in self.db["users"]:
			self._add_user(user)
			
		if type(state)!=bool:
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Unknown state: %s"%state)	
			
		self.db["users"][user]["locked"]=state
		self.save_db_variable()
		
		return n4d.responses.build_successful_call_response()
		
	#def set_free_pass
	
	def set_user_info(self,user,quota,locked,free_pass):
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")	
		if user not in self.db["users"]:
			self._add_user(user)
			
		
		self.db["users"][user]["quota"]["default"]=quota
		self.db["users"][user]["locked"]=locked
		self.db["users"][user]["free_pass"]=free_pass

		self.save_db_variable()

		return n4d.responses.build_successful_call_response()
		
	#def set_user_info
	
	def add_to_group_quota(self,group,add_value,printer="default"):

		users=self._get_group_members(group)
		ret={}
		
		for user in users:
			tmp=self.add_to_user_quota(user,add_value,printer)
			if tmp["status"]==0:
				uret=tmp["return"]
			else:
				uret=False
			ret[user]=uret
				
		#return {"status":True,"msg":ret}		
		return n4d.responses.build_successful_call_response(ret)
		
	#def add_to_group_quota
	
	
	def set_group_quota(self,group,quota,printer="default"):
		
		users=self._get_group_members(group)
		ret={}
		
		for user in users:
			tmp=self.set_user_quota(user,quota,printer)
			if tmp["status"]==0:
				uret=tmp["return"]
			else:
				uret=False
			ret[user]=uret
				
		#return {"status":True,"msg":ret}
		return n4d.responses.build_successful_call_response(ret)
		
	#def set_group_info
	
	def set_group_freepass(self,group,free_pass):
		
		users=self._get_group_members(group)
		ret={}
		
		for user in users:
			tmp=self.set_user_free_pass(user,free_pass)
			if tmp["status"]==0:
				uret=tmp["return"]
			else:
				uret=False
			ret[user]=uret
				
		return n4d.responses.build_successful_call_response(ret)
		
	#def set_group_free_pass
	
	def set_group_locked(self,group,locked):
		
		users=self._get_group_members(group)
		ret={}
		
		for user in users:
			tmp=self.set_user_locked(user,locked)
			if tmp["status"]==0:
				uret=tmp["return"]
			else:
				uret=False
			ret[user]=uret
				
		return n4d.responses.build_successful_call_response(ret)
		
	#def set_group_free_pass
	
	def set_group_flag(self,group,locked,freepass):
		
		if locked and freepass:
			return n4d.responses.build_failed_call_response(PrintaServer.INVALID_FLAG_COMBINATION_ERROR,"Invalid flag combination")
			#return {"status":False,"msg":"Invalid flag combination"}
		
		users=self._get_group_members(group)
		ret={}
		for user in users:
			tmp=self.set_user_locked(user,locked)
			if tmp["status"]==0:
				ret1=tmp["return"]
			else:
				ret1=False
			tmp=self.set_user_freepass(user,freepass)
			if tmp["status"]==0:
				ret2=tmp["return"]
			else:
				ret2=False
			ret[user]=[]
			ret[user].append(ret1)
			ret[user].append(ret2)
			
		return n4d.responses.build_successful_call_response(ret)
			
		
	#def set_group_flag
	
	def is_job_printable(self,user,job_info):
		
		#USER_LOCKED=-1
		#NOT_ENOUGH_QUOTA=-2
		#FREE_PASS=1
		#ENOUGH_QUOTA=2
		
		pages=self._get_job_pages(job_info)
		
		if not self._is_valid_user(user):
			return n4d.responses.build_failed_call_response(PrintaServer.NOT_A_VALID_USER_ERROR,"Not a valid user")	
		
		if user not in self.db["users"]:
			self._add_user(user)

		if self.db["users"][user]["locked"]:
			return n4d.responses.build_failed_call_response(PrintaServer.USER_LOCKED,"User locked")	
			#return {"status":False,"msg":USER_LOCKED}
		
		if self.db["users"][user]["free_pass"]:
			return n4d.responses.build_successful_call_response(PrintaServer.FREE_PASS,"Free pass")	
			#return {"status":True,"msg":FREE_PASS}
			
		if self.db["users"][user]["quota"]["default"] > pages:
			return n4d.responses.build_successful_call_response(PrintaServer.ENOUGH_QUOTA,"Enough quota")	
			#return {"status":True,"msg":ENOUGH_QUOTA}
		
		return n4d.responses.build_failed_call_response(PrintaServer.NOT_ENOUGH_QUOTA,"Not enough quota")	
		#return {"status": False, "msg": NOT_ENOUGH_QUOTA}
		
	#def is_job_printable
	
	# ##################################### #
	#	REQUESTS OPERATIONS		#
	# ##################################### #	
	
	def add_request(self,printa_backend_ip,client_ip,user,info): 
		
		ret={}
		ret["status"]=False
		ret["msg"]=""
		
		id=info["job_info"]["id"]
		t=info["job_info"]["time"]
		estimated_pages=self._get_job_pages(info["job_info"])
		info["job_info"]["estimated_pages"]=estimated_pages
		context=ssl._create_unverified_context()
		client=xmlrpc.client.ServerProxy("https://%s:9779"%printa_backend_ip,context=context)
		try:

			cret=client.validate_request("","PrintaServer",id,t)["return"]
			if cret:
				
				notify_ip=self._get_notify_ip(printa_backend_ip,client_ip)
				
				if notify_ip not in self.requests_variable:
					self.requests_variable[notify_ip]={}
				if user not in self.requests_variable[notify_ip]:
					self.requests_variable[notify_ip][user]=[]

				self.requests_variable[notify_ip][user].append(info)
				self.save_requests_variable()
				ret["status"]=True
			else:
				ret["msg"]="Unknown request"
			
		except Exception as e:
			print(e)
			ret["status"]=False
			ret["msg"]=str(e)
		
		return n4d.responses.build_successful_call_response(ret)
		#return ret
		
	#def add_request
	
	def get_request_var(self):
		
		return n4d.responses.build_successful_call_response(self.requests_variable)
		#return {"status":True,"msg":self.requests_variable}
		
	#def get_request_var
	
	def commit_request(self,ip,user,id,status):
		
		if ip in self.requests_variable:
			if user in self.requests_variable[ip]:
				for r in self.requests_variable[ip][user]:
					if r["job_info"]["id"]==id:
						r["job_info"]["status"]=status
						
						if status=="completed":
							
							# lets make sure we can complete the job
							ret=self.is_job_printable(user,r["job_info"])
							if ret["status"]==0:
								if not self.db["users"][user]["free_pass"]:
									self.add_to_user_quota(user,r["job_info"]["pages"]*-1)
							else:
								return n4d.responses.build_failed_call_response(ret["status"],ret["msg"])
								#return {"status": False, "msg":ret["msg"]}
						
						self._add_job_to_history(r["job_info"])
						self.save_requests_variable()
						return n4d.responses.build_successful_call_response()
						#return {"status":True,"msg":""}
		
		return n4d.responses.build_failed_call_response(PrintaServer.REQUEST_NOT_FOUND_ERROR,"Request not found")
		#return {"status":False,"msg":"Request not found"}
		
	#def commit_request
	
	def get_request_status(self,id):
		
		for ip in self.requests_variable:
			for user in self.requests_variable[ip]:
				for r in self.requests_variable[ip][user]:
					if r["job_info"]["id"]==id:
						status=r["job_info"]["status"]
						return n4d.responses.build_successful_call_response(status)
						#return {"status":True,"msg":status}
			
		#return {"status":False,"msg":"Request not found"}
		return n4d.responses.build_failed_call_response(PrintaServer.REQUEST_NOT_FOUND_ERROR,"Request not found")
		
	#def get_request_status

	def validate_request(self,id,timestamp):
		
		ret=False
		path=self.run_path+str(id)

		if os.path.exists(path):

			f=open(path)
			ts=f.readline().strip("\n")
			f.close()

			if ts==str(timestamp):
				ret=True
		
		return n4d.responses.build_successful_call_response(ret)
		#return ret
		
	#def validate_request
	
	# ##################################### #
	#	PRINTER QUERIES			#
	# ##################################### #
	
	def get_printers(self):
		
		printers={}
		
		try:
			con=cups.Connection()
			printers=con.getPrinters()
			return n4d.responses.build_successful_call_response(printers)
			#return {"status":True,"msg":printers}
		except Exception as e:
			return n4d.responses.build_failed_call_response(PrintaServer.GET_PRINTERS_ERROR,str(e))
			#return {"status":False,"msg":str(e)}
		
	#def get_printers
	
	def get_controlled_printers(self):
		
		ret=self.get_printers()
		if ret["status"]==0:
			printers={}
			for printer in ret["return"]:
				if "printa:" in ret["return"][printer]["device-uri"]:
					printers[printer]=ret["return"][printer]["device-uri"]
			
			return n4d.responses.build_successful_call_response(printers)
			#return {"status":True,"msg":printers}
		else:
			return n4d.responses.build_failed_call_response(PrintaServer.GET_PRINTERS_ERROR,ret["msg"])
			#return {"status":False, "msg":"Failed to get printers: %s"%ret["msg"]}
		
	#def get_controlled_printers
	
	def get_non_controlled_printers(self):
		
		ret=self.get_printers()
		if ret["status"]==0:
			printers={}
			for printer in ret["return"]:
				if "printa:" not in ret["return"][printer]["device-uri"]:
					printers[printer]=ret["return"][printer]["device-uri"]
			
			return n4d.responses.build_successful_call_response(printers)
			#return {"status":True,"msg":printers}
		else:
			return n4d.responses.build_failed_call_response(PrintaServer.GET_PRINTERS_ERROR,ret["msg"])
			#return {"status":False, "msg":"Failed to get printers: %s"%ret["msg"]}
		
	#def get_non_controlled_printers
	
	def enable_control(self,printer_name):
		
		ret =self.get_controlled_printers()
		if ret["status"]==0:
			controlled_printers=ret["return"]
		else:
			return n4d.responses.build_failed_call_response(PrintaServer.GET_PRINTERS_ERROR,ret["msg"])
			
		if printer_name not in controlled_printers:
			ret = self.get_non_controlled_printers()
			if ret:
				current_devices = ret["msg"]
			else:
				return n4d.responses.build_failed_call_response(PrintaServer.UNKNOWN_PRINTER_ERROR,"Unknown printer")
				
			if printer_name in current_devices:
				
				current_uri=current_devices[printer_name]
				new_uri="printa:"+current_uri
				con=cups.Connection()
				con.setPrinterDevice(printer_name,new_uri)
				self._add_printer(printer_name)
				
				return n4d.responses.build_successful_call_response()
				#return {"status":True,"msg":""}
				
			else:
				return n4d.responses.build_failed_call_response(PrintaServer.UNKNOWN_PRINTER_ERROR,"Unknown printer")
			
		else:
			return n4d.responses.failed_call_response(PrintaServer.PRINTER_ALREADY_CONTROLLED_ERROR,"Printer already controlled")
			#return {"status":False,"msg":"Printer already controlled"}
		
	#def enable_control
	
	def disable_control(self,printer_name):
		
		ret =self.get_controlled_printers()
		if ret["status"]==0:
			controlled_printers=ret["return"]
		else:
			return n4d.responses.build_failed_call_response(PrintaServer.GET_PRINTERS_ERROR,ret["msg"])
			#return {"status":False, "msg": "Failed to get printers" }
			
		if printer_name in controlled_printers:
				
			current_uri=controlled_printers[printer_name]
			new_uri=current_uri.lstrip("printa:")
			con=cups.Connection()
			con.setPrinterDevice(printer_name,new_uri)
			self._remove_printer(printer_name)
			return n4d.responses.build_successful_call_response()
			#return {"status":True,"msg":""}
				
		else:
			return n4d.responses.failed_call_response(PrintaServer.PRINTER_NOT_CONTROLLED_ERROR,"Printer not controlled")
			
			#return {"status":False,"msg":"Printer not controlled. Nothing to do"}
		
	#def disable_control
	
	def validate_ticket(self):
		
		# Harmless call allowed to every authenticated user to check if
		# ticket is valid or not.  N4D itself should handle 
		# authentication and let this call in.  If we don't get here,  
		# printa-client needs to request a fresh new ticket.
		
		return n4d.responses.build_successful_call_response()
		#return {"status":True,"msg":""}
		
	#def 
	
	
	# ######################### #
	# 	USER QUERIES	    #
	# ######################### #
	
	def get_user_history(self,user):
		
		if self._is_valid_user(user):
			h=self._get_history()
			ret=[]
			if user in h:
				ret=h[user]
			
			return n4d.responses.build_successful_call_response(ret)
			#return {"status": True, "msg": ret }
		
		return n4d.responses.build_failed_call_response(PrintaServer.UNKNOWN_USER_ERROR,"Unknown user")
		#return {"status":False,"msg":"Unknown user"}
		
	#def get_user_history
	
	def get_own_history(self,user):
		
		# user arg is protected. Regular users can only get their
		# own print  history
		
		return self.get_user_history(user)
		
	#def get_own_history
	
	def get_user_list(self):
		
		ul=pwd.getpwall()
	
		ret_list=[]
		
		for user in ul:
			if user.pw_uid > 999 and user.pw_name!="nobody":
				u={}
				u["uid"]=user.pw_uid
				u["name"]=user.pw_name
				u["gecos"]=user.pw_gecos
				ret_list.append(u)
		
		return n4d.responses.build_successful_call_response(ret_list)
		#return {"status":True,"msg":ret_list}	
		
	#def get_user_list
	
	def get_group_list(self,filter=None):
		
		gl=grp.getgrall()
		
		tmp={}
		
		for g in gl:
			if len(g.gr_mem)>0:
				tmp[g.gr_gid]={}
				tmp[g.gr_gid]["name"]=g.gr_name
				tmp[g.gr_gid]["members"]=g.gr_mem
	
		
		ret_list=[]
		
		for g in reversed(sorted(tmp)):
			group={}
			group["gid"]=g
			group["name"]=tmp[g]["name"]
			group["members"]=tmp[g]["members"]
			if filter!=None:
				if filter in group["name"]:
					ret_list.append(group)
			else:
				ret_list.append(group)
		
		
		return n4d.responses.build_successful_call_response(ret_list)
		#return {"status":True, "msg":ret_list}
		
	#def get_group_list
		
	
#class PrintaServer