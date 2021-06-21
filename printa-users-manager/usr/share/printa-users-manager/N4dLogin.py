# N4DLogin v.2

import os
import xmlrpc.client
import ssl
import sys
import socket

import gettext
_=gettext.gettext
gettext.textdomain('printa')

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

RSRC_PATH="/usr/share/printa-users-manager/rsrc/"

DEBUG=True

def dprint(data):
	
	if DEBUG:
		print("[N4dLogin] %s"%data)

class N4dLogin:
	
	def __init__(self):
		
		self.user=os.environ["USER"]
		self.uid=os.getuid()
		self.server="localhost"
		self.ticket=None
		self.use_cache=True
		self.allow_user_edit=True
		self.force_get_auth=True
		self.banner_path=RSRC_PATH+'/printa_logo.svg'
		self.icon_path=RSRC_PATH+"/printa.svg"
		
		self.valid_groups=[]
		
	#def __init__
	

	def set_valid_groups(self,valid_groups):
		
		self.valid_groups=valid_groups
	
	def set_use_cache(self,status):
		
		self.use_cache=status
		
	#def set_use_cache
	
	def set_allow_user_edit(self,status):
		
		self.allow_user_edit=status
		
	#def set_allow_user_edit
	
	def set_force_get_auth(self,status):
		
		self.force_get_auth=status
		
	#def set_force_get_auth
	
	def set_banner_path(self,path):
		
		self.banner_path=path
		
	#def set_banner_path
	
	def set_icon_path(self,path):
		
		self.icon_path=path
		
	#def set_icon_path
	
	def run(self):

		if self.use_cache:
			#STEP 1 - AUTHLESS
			self.create_ticket()
			#STEP 2 -  HOPE WE CAN READ A TICKET
			self.ticket=self.read_ticket()
			
			if self.ticket==None:
				# STEP 3 - BAD  LUCK. WE NEED AUTHENTICATION
				if force_get_auth:
					self.get_auth()
					
		else:
			if self.force_get_auth:
				self.get_auth()
				
	#def run

	
	def set_server(self,server):
		
		context=ssl._create_unverified_context()	
		self.client=xmlrpc.client.ServerProxy("https://%s:9779"%server,allow_none=True,context=context)
		self.server=server
		self.ip=self.get_own_ip(self.server)
		
	#def set_server

	
	def get_own_ip(self,server):

		ip = None
		
		try:
			s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
			s.connect((server,9779))
			ip,port=s.getsockname()
		except Exception as e:
			print(e)
		
		return ip
		
	#def get_own_ip
	
	def validate_user(self,u,p):
		
		dprint("Validating user...")
		
		ret={}
		ret["status"]=False
		ret["msg"]=""
		
		try:
			ret=self.client.validate_user(u,p)
			status=ret["status"]
			
			
			dprint(ret)
			if status==0:
				groups=ret["return"][1]
				if len(self.valid_groups)>0:
					for g in groups:
						if g in self.valid_groups:
							ret["status"]=True
							
					ret["msg"]="User is not in any of the valid groups to run this application."
				else:
					ret["status"]=True
			else:
				ret["msg"]="User and/or password error"
		except Exception as e:
			print(e)
			ret["msg"]=str(e)
			
		return ret
		
	#def validate_user
	
	
	def create_ticket(self):
	
		try:
			dprint("Asking %s to create a ticket..."%self.server)
			ret=self.client.create_ticket(self.user)
			return True
		except:
			return False
	
	#def create_ticket
	
	
	def read_ticket_from_server(self,u,p):
		try:
			dprint("Reading remote ticket...")
			ret=self.client.get_ticket(u,p)
			if ret["status"]==0:
				t=ret["return"]
				if self.use_cache:
					remote_ticket_path="/run/user/%s/printa/%s.n4d"%(self.uid,self.user)
					f=open(remote_ticket_path,"w")
					f.write(t)
					f.close()
					os.chmod(remote_ticket_path,0o400)
				return t
				
			return False
	
		except Exception as e:
			print(e)
			return False
			
	#def read_ticket_from_server
	
	
	def read_ticket(self):
		
		#lets hope there is an available ticket
		
		dprint("Trying to read local tickets...")
			
		ticket_path="/run/n4d/tickets/%s"%self.user
		remote_ticket_path="/run/user/%s/printa/%s.n4d"%(self.uid,self.user)

		tickets=[]
		if self.ip!="127.0.0.1":
			dprint("Skiping self generated ticket...")
		else:
			tickets.append(ticket_path)
			
		tickets.append(remote_ticket_path)
	
		for ticket in tickets:
			if os.path.exists(ticket):
				f=open(ticket)
				t=f.readline()
				f.close()
				dprint("Ticket found in %s"%ticket)
				if self.validate_user(self.user,t)["status"]==0:
					return t
				else:
					os.remove(ticket)

		return None
		
	#def read_ticket
	
	
	def run_dialog(self,alert_msg=""):
		
		def manual_validate(entry,dialog):
		
			dialog.hide()
		
		#def manual_validate
		
		#alright kde and gtk, i give up, here is your parent
		w=Gtk.Window()
		
		dialog = Gtk.Dialog("Printa",w,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
		(Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
		
		dialog.set_icon_from_file(self.icon_path)
		
		img=Gtk.Image()
		img.set_from_file(self.banner_path)
		img.show()
		dialog.vbox.pack_start(img,False,True,5)

		hbox1=Gtk.Grid()
		hbox1.set_row_spacing(5)
		hbox1.set_column_spacing(15)
		hbox1.set_border_width(5)
		user_entry=Gtk.Entry()
		user_entry.set_text(self.user)
		user_entry.set_sensitive(self.allow_user_edit)
		user_label=Gtk.Label(_("User"))
		user_label.set_alignment(1,0.5)
		password_entry=Gtk.Entry()
		password_entry.set_visibility(False)
		password_entry.connect("activate",manual_validate,dialog)
		password_label=Gtk.Label(_("Password"))
		password_label.set_alignment(1,0.5)
		hbox1.attach(user_label,0,0,1,1)
		hbox1.attach(user_entry,1,0,1,1)
		hbox1.attach(password_label,0,1,1,1)
		hbox1.attach(password_entry,1,1,1,1)

		hbox1.set_halign(Gtk.Align.CENTER)
		dialog.vbox.pack_start(hbox1,False,False,5)
		msg_label=Gtk.Label()
		if alert_msg!="":
			skel_msg="<span foreground='red'>%s</span>"%alert_msg
			msg_label.set_markup(skel_msg)
		dialog.vbox.pack_start(msg_label,True,True,5)
		dialog.vbox.show_all()
		password_entry.grab_focus()
		dialog.present()
		response = dialog.run()
		dialog.hide()
		
		ret={}
		ret["response"]=response
		ret["user"]=user_entry.get_text()
		ret["password"]=password_entry.get_text()
		
		return ret
		
	#def run_dialog
	
	
	def get_auth(self):
		
		#we don't have access to local ticket
		try:
			ret={}
			ret=self.run_dialog()
			validated=False
			
			while not validated and ( ret["response"]==-1 or ret["response"]==-3):
				validation=self.validate_user(ret["user"],ret["password"])
				validated=validation["status"]
				if not validated:
					ret=self.run_dialog(validation["msg"])
			if validated:
				if self.use_cache:
					self.ticket=self.read_ticket_from_server(ret["user"],ret["password"])
				else:
					self.ticket=ret["password"]
				self.user=ret["user"]
			else:
				print("Exiting")
				#sys.exit(0)
				
		except Exception as e:
			print(e)
		
	#def ask_for_ticket
	
	
#class N4dLogin