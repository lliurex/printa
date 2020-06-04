#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck','3.0')
from gi.repository import Gtk,GObject,Gio,Wnck,GdkX11

import threading 
import time
import os
import pwd
import socket
import xmlrpc.client
import ssl
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
import N4dLogin
import sys
import psutil

DEBUG=True
RSRC_PATH="/usr/share/printa-client/rsrc/"

def dprint(data):
	
	if DEBUG:
		print("[PrintaClient] %s"%data)


class PrintaClient:
	
	def __init__(self):
		
		self.window_ref=None
		self.processed_ids=[]
		self.uid=os.geteuid()
		self.user=pwd.getpwuid(self.uid).pw_name
		self.dpath="/run/user/%s/printa"%os.getuid()
		self.token_path=self.dpath+"/printa_client"
		self.gui_token=self.dpath+"/printa_client_gui_token"
		
		if not os.path.exists(self.dpath):
			os.makedirs(self.dpath)
			
		self.create_gui_token()
		self.create_path_file()
		dprint(self.token_path)
		
		self.remote_server=self.get_printa_config_variable()
		self.ip=self.get_own_ip(self.remote_server)
		self.n4d_login=N4dLogin.N4dLogin(self.remote_server)

		self.init_gio_watcher()
		
		GObject.threads_init()
		self.start_gui()
		
	#def init
	
	# ######################
	
	# N4D FUNCTIONS 
	# ######################

	def commit_job(self,status):
		
		if self.n4d_login.ticket!=None:
		
			self.job["status"]=status
			context=ssl._create_unverified_context()
			c=xmlrpc.client.ServerProxy("https://%s:9779"%self.remote_server,allow_none=True,context=context)
			u=(self.n4d_login.user,self.n4d_login.ticket)
			ret=c.commit_request(u,"PrintaServer",self.ip,self.job["user"],self.job["id"],self.job["status"])
			dprint(ret)
		
	#def commit_job

	def is_job_printable(self):
	
		USER_LOCKED=-1
		NOT_ENOUGH_QUOTA=-2
		FREE_PASS=1
		ENOUGH_QUOTA=2
	
		context=ssl._create_unverified_context()
		c=xmlrpc.client.ServerProxy("https://%s:9779"%self.remote_server,allow_none=True,context=context)
		u=(self.n4d_login.user,self.n4d_login.ticket)
		ret=c.is_job_printable(u,"PrintaServer","",self.job)
		dprint("IS_JOB_PRINTABLE:")
		dprint(ret)
		can_print=ret["status"]
		reason=""
		if not can_print:
			if ret["msg"]==USER_LOCKED:
				reason="User is locked"
			elif ret["msg"]==NOT_ENOUGH_QUOTA:
				reason="Not enough quota"
			else:
				reason=ret["msg"]
		
		return [can_print,reason]
		
	#def is_job

	def get_user_quota(self):
		
		context=ssl._create_unverified_context()
		c=xmlrpc.client.ServerProxy("https://%s:9779"%self.remote_server,allow_none=True,context=context)
		u=(self.n4d_login.user,self.n4d_login.ticket)
		ret=c.get_user_quota(u,"PrintaServer","")
		dprint("USER QUOTA:")
		dprint(ret)
		if ret["status"]:
			return ret["msg"]
		else:
			return -1
		
	#def get_user_quota

	def get_requests_variable(self):
		
		context=ssl._create_unverified_context()
		c=xmlrpc.client.ServerProxy("https://%s:9779"%self.remote_server,allow_none=True,context=context)
		ret=c.get_request_var("","PrintaServer")
		
		return ret
		
	#def get_requests_variable
	
	def get_printa_config_variable(self):
	
		context=ssl._create_unverified_context()
		c=xmlrpc.client.ServerProxy("https://localhost:9779",allow_none=True,context=context)
		v=c.get_variable("","VariablesManager","PRINTASERVER")
		if v!=None:
			return v
		return "127.0.0.1"
		
	#def get_printa_config_variable
	
	def validate_ticket(self):
		
		if self.n4d_login.ticket!=None:

			context=ssl._create_unverified_context()
			c=xmlrpc.client.ServerProxy("https://%s:9779"%self.remote_server,allow_none=True,context=context)
			u=(self.n4d_login.user,self.n4d_login.ticket)
			ret=c.validate_ticket(u,"PrintaServer")
			
			if type(ret)==dict:
				if ret["status"]:
					return True
				
		# not a valid ticket. Requesting a new one and forcing user and password dialog
		self.n4d_login=N4dLogin.N4dLogin(self.remote_server,True)
		
	#def validate_ticket
	
	# ######################## #


	#  TOKEN WATCHING FUNCTIONS
	# ##########################
	
	def init_gio_watcher(self):
		
		gio_file=Gio.File.new_for_path(self.token_path)
		self.monitor=gio_file.monitor_file(Gio.FileMonitorFlags.NONE,None)
		self.monitor.connect("changed",self.file_changed)
	
	#def init_gio_watcher
	
	
	def file_changed(self,monitor,file,other_file,event):

		if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
			self.process_msg_variable()
		
	#def file_changed
	
	def process_msg_variable(self):
		
		dprint("Got PRINTAREQUESTS variable change...")
		
		ret=self.get_requests_variable()

		if ret["status"]:
			v=ret["msg"]
		
		msgs=[]
		
		show_window=False
	
		if self.ip in v:
			if self.user in v[self.ip]:
				for request in v[self.ip][self.user]:
					if request["job_info"]["time"]>=self.last_check and request["job_info"]["status"]=="waiting" and request["job_info"]["id"] not in self.processed_ids:
						dprint(request)
						self.validate_ticket()
						
						self.msg_label.set_text("")
						self.job_name.set_text(request["job_info"]["job_name"])
						self.printer.set_text(request["job_info"]["printer_name"])
						if "estimated_pages" in request["job_info"]:
							self.pages.set_text(str(request["job_info"]["estimated_pages"]))
						else:
							self.pages.set_text(str(request["job_info"]["pages"]))
						if self.n4d_login.ticket!=None:
							user_quota=str(self.get_user_quota())
						else:
							user_quota="???"
						self.quota_label.set_text(user_quota)
						self.job=request["job_info"]
						show_window=True
						self.processed_ids.append(self.job["id"])
		
		if show_window:
			dprint("Requesting window...")
			
			if self.n4d_login.ticket!=None:
			
				ret=self.is_job_printable()
				dprint(ret)
				can_print,reason=ret
				self.print_button.set_sensitive(can_print)
			
				if not can_print:
					skel_msg="<span foreground='red'>Job can't be printed: %s</span>"%reason
					self.msg_label.set_markup(skel_msg)
				
			else:
				skel_msg="<span foreground='red'>Authentication error. Job can't be printed</span>"
				self.msg_label.set_markup(skel_msg)
				self.print_button.set_sensitive(False)
				
			self.w.show_all()
			self.w.present()
			
	#def process_msg_variable
	
	# ############################

	# BASIC FUNCTIONS
	# ###################
	
	def create_gui_token(self):
		#self.gui_token
		
		try:
			if os.path.exists(self.gui_token):
				f=open(self.gui_token)
				pid=int(f.readline())
				f.close()
				
				if psutil.pid_exists(pid):
					p=psutil.Process(pid)
					cmdline=p.cmdline()
					if len(cmdline)==2 and cmdline[1]=="/usr/bin/printa-client":
						print("[!] Another instance of printa-client is already running.")
						sys.exit(1)
		except Exception as e:
			raise e
			sys.exit(1)
				
		f=open(self.gui_token,"w")
		f.write(str(os.getpid()))
		f.close()
					
					
	
	
	def get_own_ip(self,remote_server):

		ip = None
		
		try:
			s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
			s.connect((remote_server,9779))
			ip,port=s.getsockname()
		except Exception as e:
			print(e)
		
		dprint("IP: %s"%ip)
		return ip
		
	#def get_own_ip
	
	def create_path_file(self):
		
		dprint("Generating timestamp token...")
		self.last_check=time.time()
		f=open(self.token_path,"w")
		f.write(str(self.last_check))
		f.close()
		
	#def create_path_file
	
	def start_gui(self):
		
		dprint("Initializing gui...")
		
		builder=Gtk.Builder()
		builder.add_from_file(RSRC_PATH+"printa-client.ui")
		
		self.print_button=builder.get_object("print_button")
		self.cancel_button=builder.get_object("cancel_button")
		self.w=builder.get_object("window2")
		self.job_name=builder.get_object("label20")
		self.printer=builder.get_object("label21")
		self.pages=builder.get_object("label22")
		self.quota_label=builder.get_object("label26")
		self.print_button=builder.get_object("button4")
		self.cancel_button=builder.get_object("button3")
		self.msg_label=builder.get_object("label24")

		self.connect_signals()
		
		Gtk.main()
		
	#def start_gui
	
	def connect_signals(self):
		
		self.print_button.connect("clicked",self.print_clicked)
		self.cancel_button.connect("clicked",self.cancel_clicked)
		self.w.connect("delete_event",self.hide_window)
		self.w.connect("map-event",self.map_event)		
		
	#def connect_signals

	
	# ######################
	
	# SIGNAL FUNCTIONS
	# ######################
	
	def hide_window(self,widget,event=None):
		
		dprint("Hiding window...")
		self.w.hide()
		return True
		
	#def hide_window
	
	def map_event(self,widget,event):
		
		dprint("Window is shown. Requesting focus...")
		
		xid=self.w.get_window().get_xid()
		tstamp=GdkX11.x11_get_server_time(self.w.get_window())
		
		if self.window_ref==None:
		
			screen=Wnck.Screen.get_default()
			screen.force_update()
			
			for w in screen.get_windows():
				if w.get_xid()==xid:
					self.window_ref=w
					w.activate(tstamp)
					break
		
		if self.window_ref !=None:
			self.window_ref.activate(tstamp)
			
		self.w.present()
		
	#def map_event
	
	def print_clicked(self,widget):
		
		dprint("Accepting job...")
		
		# let's make sure we are still able to print
		ret=self.is_job_printable()
		dprint(ret)
		can_print,reason=ret
		if can_print:
			self.commit_job("completed")
			self.w.hide()
		else:
			skel_msg="<span foreground='red'>Job can't be printed: %s</span>"%reason
			self.msg_label.set_markup(skel_msg)
			widget.set_sensitive(False)
			
	#def print clicked
	
	def cancel_clicked(self,widget):
		
		dprint("Cancelling...")
		self.commit_job("cancelled")
		self.w.hide()
		
	#def cancel clicked
	
	
#class PrintaClient

if __name__=="__main__":
	pc=PrintaClient()
	