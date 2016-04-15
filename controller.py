import time
import threading
import socket
import os
import boto3
from fake_useragent import UserAgent
from utils import key, snd, recv, ioLock, taggedPrintR
import fabric.api as fab
import mechanisms as mech



###################### FAB METHODS AND VARIABLES ######################
fab.env.user = 'ubuntu'
fab.env.key_filename = key + '.pem'


def prep():
	with fab.hide('output','running','warnings'), fab.settings(warn_only=True):
		fab.put('gethttp.py', '~')



###################### MAIN DATA CLASSES ######################
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
			time.sleep(5)

			if not self.open:
				self.close()
				return(0)
			
			try: mech.indexI[self.mechI](self)
			except Exception as e:
				taggedPrintR(str(e))
				taggedPrintR('INSTANCE@{0}: mechanism failure, please address and reload mechanisms'.format(self.pDNS))
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
		taggedPrintR('''>>>> COUNTER: {0}
		public dns: {1}
		mechanism: {2}
		items in queue: {3}\n'''.format(self.counter, self.inst.public_dns_name, self.mechI, len(self.items)))


### Closes instance on EC2 servers
### Returns jobs properly for reassignment
### Removes self from main controller list
	def close(self):
		dns = str(self.inst.public_dns_name)
		taggedPrintR('INSTANCE@{0}: closing instance'.format(dns))
		del self.contr.awsI[self.counter]
		self.inst.terminate()
		time.sleep(10) # to make sure job processes are no longer writing to this process
		while self.items != []: self.returnItem(self.items[0])
		taggedPrintR('INSTANCE@{0}: instance closed successfully'.format(dns))


### Helper function to aid in item removal functions
	def returnItem(self, item):
		item.assignment = None
		item.job.unassigned.append(item)
		self.items.remove(item)
		return(0)



class Item:
	def __init__(self, job, data, assgn = None):
		self.done = False
		self.job = job
		self.data = data
		self.assignment = assgn


	def prettyprint(self):
		taggedPrintR('''>>>> ITEM:
		done: {0}
		job: {1}
		data: {2}
		assignment: {3}\n'''.format(self.done, self.job, self.data, self.assignment))



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


### Prints out job parametrs nicely
	def prettyPrint(self):
		taggedPrintR('''>>>> NAME: {0}
		connection: {1}
		remaining requests: {2}
		schedule mechanism: {3}
		return method: {4}
		assignment: {5}\n'''.format(self.name, self.conn, self.rem(), self.mechS, self.ret, self.assignedBool()))


### Main job thread behavior
	def jobThread(self):
		while not self.contr.shutdownT:
			time.sleep(5)

 			if len(self.contr.awsI) > 0 and len(self.unassigned) > 0:
 				try: code = mech.indexS[self.mechS](self)
 				except: taggedPrintR('JOB@{0}: mechanism failure, please address and reload mechanisms'.format(self.name))
 				if code == 0: taggedPrintR('JOB@{0}: assigned jobs'.format(self.name))

 			if self.rem() == 0:
 				self.done = True
 				try: self.retProc()
 				except: taggedPrintR('JOB@{0}: return delivery failed'.format(self.name))
 				taggedPrintR('JOB@{0}: completed'.format(self.name))
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



class Controller:
	def __init__ (self):
		self.shutdownT = False
		self.ioLock = threading.Lock()
		self.stats = {}
		self.jobs = {}
		self.awsI = {}
		self.mech = 'paused'
		self.awsCounter = 0
		self.jobCounter = 0
		self.awsHandle = boto3.resource('ec2')

		taggedPrintR('CONTROLLER: launching instance controler')

		## opens command input
		taggedPrintR('CONTROLLER: launching input handler')
		threading.Thread(target = self.commandHandler).start()

		## opens input IO
		taggedPrintR('CONTROLLER: launching IO')
		self.ioSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ioSocket.settimeout(None)
		self.ioSocket.bind(('', 0))
		self.port = self.ioSocket.getsockname()[1]
		self.ioSocket.listen(100)
		taggedPrintR('CONTROLLER: port at {0} listening for connections...'.format(self.port))
		threading.Thread(target = self.ioIn).start()

		threading.Thread(target = self.mainControllerThread).start()

	def mainControllerThread(self):
		while not self.shutdownT:
			time.sleep(5)
			try: mech.indexC[self.mech](self)
			except: taggedPrintR('CONTROLLER: mechanism failure, please address and reload mechanisms')
		self.shutdown()

	########## IO
	def taggedPrintR(self, str):
		with self.ioLock: taggedPrintdefR(time.strftime("[%H:%M:%S] ", time.localtime()) + str)
		return(0)

	def ioIn(self):
		while not self.shutdownT:
			(conn, addr) = self.ioSocket.accept()
			taggedPrintR('CONTROLLER: connection made with: ' + str(addr))
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
			taggedPrintR('CONTROLLER: new job recieved:')
			x.prettyPrint()
		except:
			taggedPrintR('CONTROLLER: bad input or recv failure, closing connection')

	########## Handler
	def commandHandler(self):
		while not self.shutdownT:
			raw_input('')
			with ioLock: inp = raw_input(">>> ")
			try: self.runCommand(inp)
			except:
				taggedPrintR('>>>>>> command invalid')
		return(0)

	def runCommand(self, inp):
		inp = inp.split()
		if len(inp) == 0: return(0)
		if inp[0] == 'shutdown': ###CHECKED###
			with self.ioLock: check = raw_input('>>> are you sure you want to shutdown?\n>>> ')
			if check == 'y':
				self.shutdownT = True
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect(('localhost', self.port))
				s.close()
			return(0)
		if inp[0] == 'reload':
			reload(mech)
			taggedPrintR('>>>>>> mechanism library reloaded')
			return(0)
		if inp[0] == 'controller':
			if inp[1] not in mech.indexC:
				taggedPrintR('>>>>>> error: mechanism {0} does not exist'.format(inp[1]))
				return(1)
			self.mech = inp[1]
			taggedPrintR('>>>>>> mechanism for controller changed to {0}'.format(inp[1]))
			return(0)
		if inp[0] == 'instance': ###CHECKED###
			if len(inp) == 1:
				if len(self.awsI) == 0:
					taggedPrintR('>>>>>> no instances open')
					return(0)
				for i in self.awsI: self.awsI[i].prettyPrint()
				taggedPrintR('>>>>>> TOTAL: ' + str(len(self.awsI)))
				return(0)
			if inp[1] == 'stats':
				n = int(inp[2])
				if n not in self.awsI:
					taggedPrintR('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				taggedPrintR('>>>>>> stats for instance {0}: {1}'.format(n, self.awsI[n].stats))
				return(0)
			if inp[1] == 'flush':
				n = int(inp[2])
				if n not in self.awsI:
					taggedPrintR('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				taggedPrintR('>>>>>> flushing items for instance {0}'.format(n))
				self.awsI[n].flush()
				return(0)
			if inp[1] == 'initialize':
				self.initialize(int(inp[2]))
				return(0)
			if inp[1] == 'close': 
				if len(inp) < 3: taggedPrintR('>>>>>> error, enter instance key(s) to close')
				nL = [int(i) for i in inp[2:]]
				for i in nL:
					if i not in self.awsI:
						taggedPrintR('>>>>>> warning: index {0} out of range'.format(i))
					self.awsI[i].open = False
				return(0)
			if inp[1] == 'mech':
				n = int(inp[2])
				if n not in self.awsI:
					taggedPrintR('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				if inp[3] not in mech.indexI:
					taggedPrintR('>>>>>> error: mechanism {0} does not exist'.format(inp[3]))
					return(1)
				self.awsI[n].mechI = inp[3]
				taggedPrintR('>>>>>> mechanism for instance {0} changed to {1}'.format(n, inp[3]))
				return(0)
		if inp[0] == 'job':
			if len(inp) == 1:
				if len(self.jobs) == 0:
					taggedPrintR('>>>>>> no jobs open')
					return(0)
				for i in self.jobs: self.jobs[i].prettyPrint()
				taggedPrintR('>>>>>> TOTAL: ' + str(len(self.jobs)))
				return(0)
			if inp[1] == 'mech':
				nm = inp[2]
				if n not in self.jobs:
					taggedPrintR('>>>>>> error: index {0} out of range'.format(n))
					return(1)
				if inp[3] not in mech.indexS:
					taggedPrintR('>>>>>> error: mechanism {0} does not exist'.format(inp[3]))
					return(1)
				self.jobs[nm].mechS = inp[3]
				taggedPrintR('>>>>>> mechanism for job {0} changed to {1}'.format(nm, inp[3]))
				return(0)
			if inp[1] == 'testing':
				nm = inp[2]
				for i in self.jobs[nm].items:
					i.prettyprint()
		if inp[0] == 'port': ###CHECKED###
			taggedPrintR('>>>>>> ' + str(self.port))
			return(0)
		taggedPrintR('>>>>>> command invalid')

	########## Shutdown
	def shutdown(self):
		taggedPrintR('CONTROLLER: shutting down NOW')
		x = list(self.awsI.keys())
		for i in x: self.awsI[i].close()
		return(0)

	########## AWS Management
	def initialize(self, n = 1, type = 't2.nano'):
		taggedPrintR('CONTROLLER: initializing instances...')
		imgL = self.awsHandle.create_instances(
			ImageId='ami-9abea4fb',
			InstanceType = type,
			MinCount=n, MaxCount=n,
			KeyName='datacol',
			SecurityGroups = ['launch-wizard-9'])
		for i in imgL: i.wait_until_running()
		time.sleep(20)
		for rec in imgL: rec.create_tags(Tags=[{'Key':'Name', 'Value': 'datcol'}])
		taggedPrintR('CONTROLLER: DONE - new instances initialized')
		
		# Send get file to all nodes
		taggedPrintR('CONTROLLER: putting dependencies to new instances...')
		time.sleep(60)
		for i in imgL:
			i.load()
			fab.execute(prep, hosts = ['ubuntu@' + i.public_dns_name])
		for i in imgL:
			x = Instance(self, self.awsCounter, i)
			self.awsI[self.awsCounter] = x
			taggedPrintR('CONTROLLER: new instance created')
			x.prettyPrint()
			self.awsCounter += 1

		taggedPrintR('CONTROLLER: DONE - instances ready')
		return(0)

Controller()