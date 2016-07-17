import time
import threading
import socket
import os
import boto3
import requests
import subprocess

from fake_useragent import UserAgent
import fabric.api as fab
import fabric

from utils import key, ua, snd, recv, ioLock
import mechanisms as mech
import controllerIO



###################### FAB METHODS AND VARIABLES ######################
fab.env.user = 'ubuntu'
fab.env.key_filename = key + '.pem'
fabric.state.output['running'] = False


def prep():
	with fab.hide('status', 'aborts', 'running', 'warnings', 'stdout', 'stderr', 'user'), fab.settings(warn_only=True):
		fab.put('gethttp.py', '~')



###################### INSTANCE CLASS ######################
class AWSInstance:
	def __init__(self, contr, counter, type = 't2.nano'):
		self.contr = contr
		self.counter = counter
		self.type = 'aws'
		self.mechI = 'paused'
		self.stats = {'date': None, 'hour': None, 'min': None}
		self.items = []

		self.itemLock = threading.Lock()

		# command tags
		self.closeCmd = False
		self.flushCmd = False

		# initialize instance on amazon side
		self.addLog('opening aws instance on amazon servers...')
		self.inst = contr.awsHandle.create_instances(
			ImageId='ami-9abea4fb',
			InstanceType = type,
			MinCount=1, MaxCount=1,
			KeyName='datacol',
			SecurityGroups = ['launch-wizard-9'])[0]
		self.inst.wait_until_running()
		self.inst.create_tags(Tags=[{'Key':'Name', 'Value': 'datcol'}])
		self.pDNS = 'ubuntu@' + self.inst.public_dns_name

		self.addLog('loading dependencies to server...')
		time.sleep(60)
		self.inst.load()
		fab.execute(prep, hosts = [self.pDNS])

		self.addLog('aws instance initialized')	
		
		threading.Thread(target = self.instThread).start()


	### Main instance thread behavior
	def instThread(self):
		while not self.contr.shutdownT:
			time.sleep(1)

			with self.itemLock:
				if self.closeCmd:
					self.close()
					return(0)

				if self.flushCmd:
					self.flush()
					self.flushCmd = False
			
			try: mech.indexI[self.mechI](self)
			except Exception as e:
				self.addLog('mechanism failure: {0}'.format(e))
		return(0)


	### Adds message to the controller log
	def addLog(self, str):
		self.contr.log.append(time.strftime("[%H:%M:%S] ", time.localtime()) + 'INSTANCE@{0}: {1}'.format(self.counter, str))
		return(0)


	def flush(self):
		items = self.items[:]
		for i in items:
			self.items.remove(i)
			i.assignment = None
		self.addLog('instance items flushed')
		return(0)


	def close(self):
		self.addLog('closing instance')
		del self.contr.instances[self.counter]
		self.inst.terminate()
		time.sleep(10) # to make sure job processes are no longer writing to this process
		self.flush()
		self.addLog('instance closed successfully')


	def changeMech(self, newMech):
		self.mechI = newMech
		self.addLog('instance mech changed to: {0}'.format(newMech))
		return(0)


	def request(self, html):
		recieved = subprocess.check_output(['ssh', '-o', 'StrictHostKeyChecking=no',
			'-i', 'datacol.pem', self.pDNS,
			'python gethttp.py', html.replace('&', '\&'), '"{0}"'.format(ua.random)],
			stderr=subprocess.STDOUT,
			stdin=subprocess.PIPE
		)
		return(recieved)



class LocalInstance:
	def __init__(self, contr, counter):
		self.type = 'local'
		self.contr = contr
		self.counter = counter
		self.mechI = 'paused'
		self.stats = {}
		self.items = []

		self.itemLock = threading.Lock()

		# command tags
		self.closeCmd = False
		self.flushCmd = False

		self.addLog('local instance initialized')

		threading.Thread(target = self.instThread).start()


	### Adds message to the controller log
	def addLog(self, str):
		self.contr.log.append(time.strftime("[%H:%M:%S] ", time.localtime()) + 'INSTANCE@{0}: {1}'.format(self.counter, str))
		return(0)

	### Main thread function
	def instThread(self):
		while not self.contr.shutdownT:
			time.sleep(2)

			with self.itemLock:
				if self.closeCmd:
					self.close()
					return(0)
				if self.flushCmd:
					self.flush()
					self.flushCmd = False
	
				try: mech.indexI[self.mechI](self)
				except Exception as e:
					self.addLog('mechanism failure: {0}'.format(e))
		return(0)


	### Flush thread items
	def flush(self):
		items = self.items[:]
		for i in items:
			self.items.remove(i)
			i.assignment = None
		self.addLog('instance items flushed')
		return(0)

	### Close this thread
	def close(self):
		self.addLog('closing instance...')
		del self.contr.instances[self.counter]
		time.sleep(5)
		self.flush()
		self.addLog('instance closed successfully')
		return(0)


	def request(self, link):
		return(requests.get(link).text)


	def changeMech(self, newMech):
		#maybe check for validity
		self.mechI = newMech
		self.addLog('instance mech changed to: {0}'.format(newMech))
		return(0)



###################### ITEM CLASS ######################
class Item:
	def __init__(self, job, data, assgn = None):
		self.done = False
		self.job = job
		self.data = data
		self.assignment = assgn



###################### JOB CLASS ######################
class Job:
	def __init__(self, contr, conn, name, mechS, ret, data):
		self.done = False
		self.contr = contr
		self.conn = conn
		self.name = name
		self.mechS = mechS
		self.ret = ret
		self.items = [Item(self, i) for i in data]

		threading.Thread(target = self.jobThread).start()


	### Gives number of remaining items to be done in a job
	def rem(self):
		return([i for i in self.items if not i.done])


	## Gives number of unassigned items
	def unassn(self):
		return([i for i in self.items if i.assignment == None and i.done == False])


	### Adds message to the controller log
	def addLog(self, str):
		self.contr.log.append(time.strftime("[%H:%M:%S] ", time.localtime()) + 'JOB@{0}: {1}'.format(self.name, str))
		return(0)


	### Main job thread behavior
	def jobThread(self):
		while not self.contr.shutdownT:
			time.sleep(5)

			if len(self.contr.instances) > 0 and len(self.unassn()) > 0:
 				try:
 					code = mech.indexS[self.mechS](self)
					if code == 0: self.addLog('assigned jobs'.format(self.name))
 				except Exception as e: self.addLog('mechanism failure: {0}'.format(e))

 			if len(self.rem()) == 0:
 				self.done = True
 				try: self.retProc()
 				except Exception as e:
 					self.addLog('return delivery failed with Exception: {0}'.format(e))
 				self.addLog('completed'.format(self.name))
 				del self.contr.jobs[self.name]
 				return(0)
		return(0)


	### Function that performs task of returning completed jobs to specified targets
	def retProc(self):
		if self.ret == 'default':
			returnPackage = str([(i.data, i.done) for i in self.items])
			snd(self.conn, returnPackage)
			self.conn.close()
			return(0)

		for i in self.items:
			handle = open(self.ret + '/' + i.data.replace('/', '`'), 'w')
			handle.write(i.done.encode('utf8'))
			handle.close()
		return(0)



###################### CONTROLLER CLASS ######################
class Controller:
	def __init__ (self):
		self.shutdownT = False
		self.jobs = {}
		self.instances = {}
		self.mech = 'paused'
		self.instanceCounter = 0
		self.jobCounter = 0
		self.log = []

		self.awsHandle = boto3.resource('ec2')
		
		self.addLog('launching instance controler')

		## opens input IO
		self.addLog('launching IO')
		self.ioSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ioSocket.settimeout(None)
		self.ioSocket.bind(('', 0))
		self.port = self.ioSocket.getsockname()[1]
		self.ioSocket.listen(100)
		self.addLog('port at {0} listening for connections...'.format(self.port))
		threading.Thread(target = self.ioIn).start()

		## begins main thread process
		threading.Thread(target = self.mainControllerThread).start()

		controllerIO.controllerIO(self)


	### Main thread process
	def mainControllerThread(self):
		while not self.shutdownT:
			time.sleep(1)
			try: mech.indexC[self.mech](self)
			except: self.addLog('mechanism failure, please address and reload mechanisms')
		return(0)


	def addLog(self, str):
		self.log.append(time.strftime("[%H:%M:%S] ", time.localtime()) + 'SCHEDULER: ' + str)
		return(0)


	########## Receiving Jobs ##########
	def ioIn(self):
		while not self.shutdownT:
			(conn, addr) = self.ioSocket.accept()
			self.addLog('CONTROLLER: connection made with: ' + str(addr))
			conn.settimeout(None)
			threading.Thread(target = self.ioInSub, args = (conn,)).start()
		return(0)


	def ioInSub(self, conn):
		recievedIn = recv(conn)
		if recievedIn == 1: return(1)
		recievedIn = recievedIn.split()
		name = recievedIn[0]
		if name == 'default':
			name = str(self.jobCounter)
			self.jobCounter += 1
		mechS = recievedIn[1]
		ret = recievedIn[2]
		data = recievedIn[3:]
		try:
			x = Job(self, conn, name, mechS, ret, data)
			self.jobs[name] = x
			self.addLog('CONTROLLER: new job recieved: {0}'.format(x.name))
		except Exception as e:
			self.addLog('CONTROLLER: bad input or recv failure, closing connection: {0}'.format(e))
		return(0)


	########## Shutdown ##########
	def shutdown(self):
		self.addLog('shutting down NOW')
		self.shutdownT = True

		x = list(self.instances.keys())
		for i in x: self.instances[i].closeCmd = True

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(('localhost', self.port))
		s.close()		
		return(0)


	########## Reload ##########
	def relMech(self):
		try:
			reload(mech)
			self.addLog('mechanism library reloaded')
		except Exception as e:
			self.addLog('mechanism reload failure with exception: {0}'.format(e))
		return(0)


	########## Initialize Instances ##########
	def initialize(self, type):
		self.addLog('attempting to initialize {0} instance...'.format(type))
		if type == 'local':
			self.instances[self.instanceCounter] = LocalInstance(self, self.instanceCounter)
			self.instanceCounter += 1
			return(0)

		elif type == 'aws':
			threading.Thread(target = self.awsInitHelper, args = (self.instanceCounter,)).start()
			self.instanceCounter += 1
			return(0)

		return(1)
		

	def awsInitHelper(self, counter):
		self.instances[counter] = AWSInstance(self, counter)
		return(0)



Controller()
