import requests
import subprocess
import fabric.api as fab
import fabric
import threading
import time

import mechanisms
from utils import aws_key, csil_pass, ua



################ FAB FUNCTIONS FOR AWS ################
fab.env.user = 'ubuntu'
fab.env.key_filename = key
fabric.state.output['running'] = False


def prep():
	with fab.hide('status', 'aborts', 'running', 'warnings', 'stdout', 'stderr', 'user'), fab.settings(warn_only=True):
		fab.put('gethttp.py', '~')



################ GENERAL INSTANCE FUNCTIONS ################
def addLog(inst, str):
	inst.contr.log.append(time.strftime("[%H:%M:%S] ", time.localtime()) + 'INSTANCE@{0}: {1}'.format(inst.counter, str))
	return(0)


def flush(inst):
	items = inst.items[:]
	for i in items:
		inst.items.remove(i)
		i.assignment = None
	addLog(inst, 'instance items flushed')
	return(0)


def changeMech(inst, mech):
	inst.mech = mech
	addLog(inst, 'instance mech changed to: {0}'.format(mech))
	return(0)



################ INSTANCE CLASSES ################
class CsilInstance:
	def __init__(self, address, contr, counter):
		self.address = address
		self.contr = contr
		self.counter = counter
		self.type = 'csil'
		self.mech = 'paused'
		self.items = []

		self.itemLock = threading.Lock()

		self.closeCmd = False
		self.flushCmd = False

		addLog(self, 'CSIL instance initialized')
		threading.Thread(target = self.instThread).start()


	def instThread(self):
		while not self.contr.shutdownT:
			time.sleep(1)

			with self.itemLock:
				if self.closeCmd:
					self.close()
					return(0)

				if self.flushCmd:
					flush(self)
					self.flushCmd = False
			
			try: mechanisms.indexI[self.mech](self)
			except Exception as e:
				addLog(self, 'mechanism failure: {0}'.format(e))
		return(0)


	def close(self):
		addLog(self, 'closing instance')
		del self.contr.instances[self.counter]
		time.sleep(10) # to make sure job processes are no longer writing to this process
		flush(self)
		addLog(self, 'instance closed successfully')


	def request(self, item):
		sshstr = 'fkwang@' + self.address + '.cs.uchicago.edu'
		recieved = subprocess.check_output(['sshpass', '-p', csil_pass, 'ssh', sshstr,
			'-o', 'StrictHostKeyChecking=no',
			'python gethttp.py', item.html.replace('&', '\&'), '""'.format(ua)],
			stderr=subprocess.STDOUT,
			stdin=subprocess.PIPE
		)
		item.data = recieved.decode('utf-8')
		item.time = time.time()
		item.assignment = None
		item.done = True
		return(0)



class AWSInstance:
	def __init__(self, contr, counter, type='t2.nano'):
		self.contr = contr
		self.counter = counter
		self.type = 'aws'
		self.mech = 'paused'
		self.stats = {'date': None, 'hour': None, 'min': None}
		self.items = []

		self.itemLock = threading.Lock()

		self.closeCmd = False
		self.flushCmd = False

		# initialize instance on amazon side
		addLog(self, 'opening aws instance on amazon servers...')
		self.inst = contr.awsHandle.create_instances(
			ImageId='ami-9abea4fb',
			InstanceType = type,
			MinCount=1, MaxCount=1,
			KeyName='datacol',
			SecurityGroups = ['launch-wizard-9'])[0]
		self.inst.wait_until_running()
		self.inst.create_tags(Tags=[{'Key':'Name', 'Value': 'datcol'}])
		self.pDNS = 'ubuntu@' + self.inst.public_dns_name

		addLog(self, 'loading dependencies to server...')
		time.sleep(60)
		self.inst.load()
		fab.execute(prep, hosts = [self.pDNS])

		addLog(self, 'aws instance initialized')	
		threading.Thread(target = self.instThread).start()


	def instThread(self):
		while not self.contr.shutdownT:
			time.sleep(1)

			with self.itemLock:
				if self.closeCmd:
					self.close()
					return(0)

				if self.flushCmd:
					flush(self)
					self.flushCmd = False
			
			try: mechanisms.indexI[self.mech](self)
			except Exception as e:
				addLog(self, 'mechanism failure: {0}'.format(e))
		return(0)


	def close(self):
		addLog(self, 'closing instance')
		del self.contr.instances[self.counter]
		self.inst.terminate()
		time.sleep(10) # to make sure job processes are no longer writing to this process
		flush(self)
		addLog(self, 'instance closed successfully')


	def request(self, item):
		recieved = subprocess.check_output(['ssh', '-o', 'StrictHostKeyChecking=no',
			'-i', key, self.pDNS,
			'python gethttp.py', item.html.replace('&', '\&'), '""'.format(ua)],
			stderr=subprocess.STDOUT,
			stdin=subprocess.PIPE
		)
		item.data = recieved.decode('utf-8')
		item.time = time.time()
		item.assignment = None
		item.done = True
		return(0)



class LocalInstance:
	def __init__(self, contr, counter):
		self.type = 'local'
		self.contr = contr
		self.counter = counter
		self.mech = 'paused'
		self.stats = {}
		self.items = []

		self.itemLock = threading.Lock()

		# command tags
		self.closeCmd = False
		self.flushCmd = False

		addLog(self, 'local instance initialized')

		threading.Thread(target = self.instThread).start()


	### Main thread function
	def instThread(self):
		while not self.contr.shutdownT:
			time.sleep(2)

			with self.itemLock:
				if self.closeCmd:
					self.close()
					return(0)
				if self.flushCmd:
					flush(self)
					self.flushCmd = False
	
				try: mechanisms.indexI[self.mech](self)
				except Exception as e:
					addLog(self, 'mechanism failure: {0}'.format(e))
		return(0)


	### Close this thread
	def close(self):
		addLog(self, 'closing instance...')
		del self.contr.instances[self.counter]
		time.sleep(5)
		self.flush()
		addLog(self, 'instance closed successfully')
		return(0)


	def request(self, item):
		recieved = requests.get(item.html).text
		item.data = recieved
		item.time = time.time()
		item.assignment = None
		item.done = True
		return(0)

