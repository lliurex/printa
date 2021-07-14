import os
import xmlrpc.client
import ssl
import sys
import socket


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

DEBUG=True
ICON_PATH="/usr/share/printa-client/rsrc/printa.svg"

def dprint(data):
	
	if DEBUG:
		print("[N4dLogin] %s"%data)

class N4dLogin:
	
	def __init__(self,server="server",force_get_auth=False):
		
		self.user=os.environ["USER"]
		self.uid=os.getuid()
		self.server=server
		self.set_server(self.server)
		self.ticket=None
		
		self.ip=self.get_own_ip(self.server)
		
		#STEP 1 - AUTHLESS
		self.create_ticket()
		#STEP 2 -  HOPE WE CAN READ A TICKET
		self.ticket=self.read_ticket()
		
		if self.ticket==None:
			# STEP 3 - BAD  LUCK. WE NEED AUTHENTICATION
			if force_get_auth:
				self.get_auth()
		
	#def __init__

	
	def set_server(self,server):
		
		context=ssl._create_unverified_context()	
		self.client=xmlrpc.client.ServerProxy("https://%s:9779"%server,allow_none=True,context=context)
		
	#def set_server

	
	def get_own_ip(self,server):

		ip = None
		
		try:
			s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
			s.connect((server,9779))
			ip,port=s.getsockname()
		except Exception as e:
			dprint(str(e))
		
		return ip
		
	#def get_own_ip
	
	def validate_user(self,u,p):
		
		dprint("Validating user...")
		try:
			ret=self.client.validate_user(u,p)
			#dprint(status)
			if ret["status"]==0:
				return True
			return False
		except:
			return False
			
	#def validate_user
	
	def validate_ticket(self,u,t):
		
		dprint("Validating ticket...")
		try:
			ret=self.client.validate_ticket((u,t),"PrintaServer")
			if ret["status"]==0:
				return True
			return False
		except:
			return False
		
	#def validate_ticket
	
	
	def create_ticket(self):
	
		try:
			dprint("Asking %s to create a ticket..."%self.server)
			ret=self.create_ticket(self.user)
			if ret["status"]==0:
				return True
			return False
			
		except:
			return False
	
	#def create_ticket
	
	
	def read_ticket_from_server(self,u,p):
		try:
			dprint("Reading remote ticket...")
			ret=self.client.get_ticket(u,p)
			if ret["status"]==0:
				t=ret["return"]
				remote_ticket_path="/run/user/%s/printa/%s.n4d"%(self.uid,self.user)
				f=open(remote_ticket_path,"w")
				f.write(t)
				f.close()
				os.chmod(remote_ticket_path,0o400)
				return t
			return False
	
		except Exception as e:
			dprint(str(e))
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
				if self.validate_ticket(self.user,t):
					return t
				else:
					os.remove(t)
					
		return None
		
	#def read_ticket
	
	
	def run_dialog(self,alert_msg=""):
		
		def manual_validate(entry,dialog):
		
			dialog.hide()
		
		#def manual_validate
		
		w=Gtk.Window()
		
		dialog = Gtk.Dialog("Printa",w,Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
		(Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
		
		img=Gtk.Image()
		img.set_from_file(ICON_PATH)
		img.show()
		dialog.vbox.pack_start(img,False,True,5)

		hbox1=Gtk.Table(2,2)
		hbox1.set_row_spacings(5)
		hbox1.set_col_spacings(5)
		hbox1.set_border_width(5)
		user_entry=Gtk.Entry()
		user_entry.set_text(self.user)
		user_entry.set_sensitive(False)
		user_label=Gtk.Label("User")
		user_label.set_alignment(0,0)
		password_entry=Gtk.Entry()
		password_entry.set_visibility(False)
		password_entry.connect("activate",manual_validate,dialog)
		password_label=Gtk.Label("Password")
		password_label.set_alignment(0,0)
		hbox1.attach(user_label,0,1,0,1)
		hbox1.attach(user_entry,1,2,0,1)
		hbox1.attach(password_label,0,1,1,2)
		hbox1.attach(password_entry,1,2,1,2)
		dialog.vbox.pack_start(hbox1,False,True,5)
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
				validated=self.validate_user(ret["user"],ret["password"])
				if not validated:
					ret=self.run_dialog("User and/or password error")
			
			if validated:
				self.ticket=self.read_ticket_from_server(ret["user"],ret["password"])
			else:
				dprint("Exiting")
				
		except Exception as e:
			print(e)
		
	#def ask_for_ticket
	
	
#class N4dLogin