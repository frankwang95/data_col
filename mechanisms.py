import random
import time
import requests
import datetime
import threading
from utils import taggedPrintR



#################### PAUSED BEHAVIOR ####################
def paused(instJobContr):
	time.sleep(1)
	return(1)



#################### JOB BEHAVIORS ####################
### Default scheduler simply assigns jobs to random instances
def defaultJob(job):
	for i in job.unassn():
		instance = job.contr.instances[random.choice(job.contr.instances.keys())]
		i.assignment = instance
		with instance.itemLock:
			instance.items.append(i)
	return(0)


indexJ = {'paused': paused, 'default': defaultJob}



#################### INSTANCE BEHAVIORS ####################
### Default scheduler completes jobs as quickly as possible, working in time blocks of 5 seconds at a time
def defaultInst(inst):
	tEnd = time.time() + 5
	random.shuffle(inst.items)
	while time.time() < tEnd and len(inst.items) > 0:
		x = inst.items.pop(0)

		try: resutltFromAWS = inst.request(x)

		except Exception as e:
			inst.items.append(x)
			inst.addLog(e)
	return(0)


indexI = {'paused': paused, 'default': defaultInst}



#################### CONTROLLER BEHAVIORS ####################
def hourlyCycle(contr):
	try:
		t = datetime.datetime.now()
		if t.minute == 0:
			contr.initialize(n = 5)
			for i in contr.awsI:
				contr.awsI[i].mech = 'yelp'
				contr.awsI[i].flush()
			return(0)
		if t.minute == 20:
			n = len(contr.awsI) - 2
			toClose = random.sample(contr.awsI.keys(), n)
			for i in toClose: contr.awsI[i].open = False
			return(0)
	except Exception as e:
		print e
	time.sleep(10)
	return(0)


indexC = {'paused': paused}
