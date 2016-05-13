import time
import threading
import socket
import os
import boto3
from fake_useragent import UserAgent
from utils import key, snd, recv, ioLock
import fabric.api as fab
import mechanisms as mech
import controllerIO



###################### FAB METHODS AND VARIABLES ######################
fab.env.user = 'ubuntu'
fab.env.key_filename = key + '.pem'


def prep():
	with fab.hide('output','running','warnings'), fab.settings(warn_only=True):
		fab.put('gethttp.py', '~')



###################### INSTANCE CLASS ######################
'''
class Instance:
	def __init__(self, contr, counter, awsInst):
		self.open = True
		self.contr = contr
		self.counter = counter
		self.inst = awsInst
		self.pDNS = 'ubuntu@' + awsInst.public_dns_name
		self.mechI = 'paused'
		self.stats = {'date': None, 'hour': None, 'min': None}
		self.items = []

		threading.Thread(target = self.instThread).start()


### Main instance thread behavior
	def instThread(self):
		while not self.contr.shutdownT:
			time.sleep(1)

			if not self.open:
				self.close()
				return(0)
			
			try: mech.indexI[self.mechI](self)
			except Exception as e:
				self.addLog(str(e))
				self.addLog('INSTANCE@{0}: mechanism failure, please address and reload mechanisms'.format(self.pDNS))
		return(0)


### Removes all jobs from instance for reassignment
	def flush(self):
		n = len(self.items)

		while n > 0:
			self.returnItem(self.items[0])
			n -= 1
		return(0)


### Prints out instance parameters nicely
	def prettyPrint(self):
		self.addLog(>>>> COUNTER: {0}
		public dns: {1}
		mechanism: {2}
		items in queue: {3}\n.format(self.counter, self.inst.public_dns_name, self.mechI, len(self.items)))

### Closes instance on EC2 servers
### Returns jobs properly for reassignment
### Removes self from main controller list
	def close(self):
		dns = str(self.inst.public_dns_name)
		self.addLog('INSTANCE@{0}: closing instance'.format(dns))
		del self.contr.instances[self.counter]
		self.inst.terminate()
		time.sleep(10) # to make sure job processes are no longer writing to this process
		while self.items != []: self.returnItem(self.items[0])
		self.addLog('INSTANCE@{0}: instance closed successfully'.format(dns))


### Helper function to aid in item removal functions
	def returnItem(self, item):
		item.assignment = None
		item.job.unassigned.append(item)
		self.items.remove(item)
		return(0)
'''


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
		self.unassigned = list(self.items)

		threading.Thread(target = self.jobThread).start()


	### Gives number of remaining items to be done in a job
	def rem(self):
		return(len([i for i in self.items if not i.done]))


	### Adds message to the controller log
	def addLog(self, str):
		self.contr.log.append(time.strftime("[%H:%M:%S] ", time.localtime()) + 'JOB@{0}: {1}'.format(self.name, str))
		return(0)


	### Main job thread behavior
	def jobThread(self):
		while not self.contr.shutdownT:
			time.sleep(5)

			if len(self.contr.instances) > 0 and len(self.unassigned) > 0:
 				try: code = mech.indexS[self.mechS](self)
 				except: self.addLog('mechanism failure, please address and reload mechanisms')
 				if code == 0: self.addLog('JOB@{0}: assigned jobs'.format(self.name))

 			if self.rem() == 0:
 				self.done = True
 				try: self.retProc()
 				except: self.addLog('JOB@{0}: return delivery failed'.format(self.name))
 				self.addLog('JOB@{0}: completed'.format(self.name))
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
			handle.write(i.done)
			handle.close()
		return(0)


### Checks to see if all jobs are properly assigned to an instance
	def assignedBool(self):
		return self.unassigned == []



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
		self.shutdown()


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
			self.addLog('CONTROLLER: new job recieved:')
			x.prettyPrint()
		except:
			self.addLog('CONTROLLER: bad input or recv failure, closing connection')


	########## Command-line Input ##########
	def runCommand(self, inp):
		inp = inp.split()
		if len(inp) == 0: return(0)
		if inp[0] == 'shutdown':
			check = raw_input('>>> are you sure you want to shutdown?\n>>> ')
			if check == 'y':
				self.shutdown()
			return(0)
		if inp[0] == 'reload':
			reload(mech)
			self.addLog('>>>>>> mechanism library reloaded')
			return(0)
		if inp[0] == 'controller':
			if inp[1] not in mech.indexC:
				self.addLog('>>>>>> error: mechanism {0} does not exist'.format(inp[1]))
				return(1)
			self.mech = inp[1]
			self.addLog('>>>>>> mechanism for controller changed to {0}'.format(inp[1]))
			return(0)
		if inp[0] == 'instance':
			if len(inp) == 1:
				if len(self.instances) == 0:
					self.addLog('>>>>>> no instances open')
					return(0)
				for i in self.instances: self.instances[i].prettyPrint()
				self.addLog('>>>>>> TOTAL: ' + str(len(self.instances)))
				return(0)
			if inp[1] == 'stats':
				n = int(inp[2])
				if n not in self.instances:
					self.addLog('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				self.addLog('>>>>>> stats for instance {0}: {1}'.format(n, self.instances[n].stats))
				return(0)
			if inp[1] == 'flush':
				n = int(inp[2])
				if n not in self.instances:
					self.addLog('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				self.addLog('>>>>>> flushing items for instance {0}'.format(n))
				self.instances[n].flush()
				return(0)
			if inp[1] == 'initialize':
				self.initialize(int(inp[2]))
				return(0)
			if inp[1] == 'close': 
				if len(inp) < 3: self.addLog('>>>>>> error, enter instance key(s) to close')
				nL = [int(i) for i in inp[2:]]
				for i in nL:
					if i not in self.instances:
						self.addLog('>>>>>> warning: index {0} out of range'.format(i))
					self.instances[i].open = False
				return(0)
			if inp[1] == 'mech':
				n = int(inp[2])
				if n not in self.instances:
					self.addLog('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				if inp[3] not in mech.indexI:
					self.addLog('>>>>>> error: mechanism {0} does not exist'.format(inp[3]))
					return(1)
				self.instances[n].mechI = inp[3]
				self.addLog('>>>>>> mechanism for instance {0} changed to {1}'.format(n, inp[3]))
				return(0)
		if inp[0] == 'job':
			if len(inp) == 1:
				if len(self.jobs) == 0:
					self.addLog('>>>>>> no jobs open')
					return(0)
				for i in self.jobs: self.jobs[i].prettyPrint()
				self.addLog('>>>>>> TOTAL: ' + str(len(self.jobs)))
				return(0)
			if inp[1] == 'mech':
				nm = inp[2]
				if n not in self.jobs:
					self.addLog('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				if inp[3] not in mech.indexS:
					self.addLog('>>>>>> error: mechanism {0} does not exist'.format(inp[3]))
					return(1)
				self.jobs[nm].mechS = inp[3]
				self.addLog('>>>>>> mechanism for job {0} changed to {1}'.format(nm, inp[3]))
				return(0)
			if inp[1] == 'testing':
				nm = inp[2]
				for i in self.jobs[nm].items:
					i.prettyprint()
		if inp[0] == 'port':
			self.addLog('>>>>>> ' + str(self.port))
			return(0)
		self.addLog('>>>>>> command invalid')

	########## Shutdown
	def shutdown(self):
		self.addLog('CONTROLLER: shutting down NOW')
		self.shutdownT = True

		x = list(self.instances.keys())
		for i in x: self.instances[i].close()

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(('localhost', self.port))
		s.close()		
		return(0)


	########## Reload
	def relMech(self):
		try:
			reload(mech)
			self.addLog('mechanism library reloaded')
		except Exception as e:
			self.addLog('mechanism reload failure with exception: {0}'.format(e))


	########## AWS Management
	def initialize(self, n = 1, type = 't2.nano'):
		self.addLog('CONTROLLER: initializing instances...')
		imgL = self.awsHandle.create_instances(
			ImageId='ami-9abea4fb',
			InstanceType = type,
			MinCount=n, MaxCount=n,
			KeyName='datacol',
			SecurityGroups = ['launch-wizard-9'])
		for i in imgL: i.wait_until_running()
		time.sleep(20)
		for rec in imgL: rec.create_tags(Tags=[{'Key':'Name', 'Value': 'datcol'}])
		self.addLog('CONTROLLER: DONE - new instances initialized')
		
		# Send get file to all nodes
		self.addLog('CONTROLLER: putting dependencies to new instances...')
		time.sleep(60)
		for i in imgL:
			i.load()
			fab.execute(prep, hosts = ['ubuntu@' + i.public_dns_name])
		for i in imgL:
			x = Instance(self, self.instanceCounter, i)
			self.instances[self.instanceCounter] = x
			self.addLog('CONTROLLER: new instance created')
			x.prettyPrint()
			self.instanceCounter += 1

		self.addLog('CONTROLLER: DONE - instances ready')
		return(0)

Controller()