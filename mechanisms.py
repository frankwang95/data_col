import random
import time
import requests
import datetime
import threading
from utils import hourodds, taggedPrintR



#################### PAUSED BEHAVIOR ####################
def paused(instJobContr):
	time.sleep(1)
	return(1)



#################### SECHDULER BEHAVIORS ####################
### Default scheduler simply assigns jobs to random instances
def defaultSch(job):
	for i in job.unassn():
		instance = job.contr.instances[random.choice(job.contr.instances.keys())]
		i.assignment = instance
		with instance.itemLock:
			instance.items.append(i)
	return(0)


### Gives dictionary for access to scheduler behaviors
indexS = {'paused': paused, 'default': defaultSch}



#################### INSTANCE BEHAVIORS ####################
### Default scheduler completes jobs as quickly as possible
### Works in time blocks of 5 seconds
def defaultInst(inst):
#	time.sleep(random.randint(0,20) / 5)
	tEnd = time.time() + 5
	random.shuffle(inst.items)
	while time.time() < tEnd and len(inst.items) > 0:
		x = inst.items.pop(0)

		try:
			resutltFromAWS = inst.request(x.data)
			x.done = resutltFromAWS
			x.assignment = None

		except Exception as e:
			inst.items.append(x)
			inst.addLog(e)
	return(0)


def test(inst):
	time.sleep(0.5)
	inst.addLog('testing testing testing testing testing testing testing testing testing testing testing testing testing testing testing')
	return(0)
	


def yelp(inst):
	today = int(time.strftime('%d'))
	hour = int(time.strftime('%H'))
	minute = int(time.strftime('%M')) - (int(time.strftime('%M')) % 5)

	inst.stats['datepull'] = True

	if inst.stats['date'] != today:
		inst.stats['date'] = today
		inst.stats['datepull'] = True
		if random.randint(1,10) == 1: inst.stats['datepull'] = False

	if inst.stats['hour'] != hour:
		inst.stats['hour'] = hour
		inst.stats['hourpull'] = False
		if random.randint(1,100) < hourodds(hour): inst.stats['hourpull'] = True

	if inst.stats['min'] != minute:
		inst.stats['min'] = minute
		inst.stats['minpull'] = False
		if random.randint(1,100) < 70: inst.stats['minpull'] = True

	random.shuffle(inst.items)
	tEnd = time.time() + 20
	while time.time() < tEnd and len(inst.items) > 0:
		x = inst.items.pop(0)
		if x.job.name[:4] == 'yelp':
			if inst.stats['datepull'] and inst.stats['hourpull'] and inst.stats['minpull']:
				time.sleep(random.randint(0,10))
				try:
					resultFromAWS = inst.request(x.data)
					x.done = resultFromAWS
					x.assignment = None
				except Exception as e:
					inst.items.append(x)
					inst.addLog(str(e))
					continue
			else:
				inst.items.append(x)
				continue
		try:
			resultFromAWS = inst.request(x.data)
			x.done = resultFromAWS
			x.assignment = None
		except Exception as e:
			inst.items.append(x)
			inst.addLog(str(e))

	time.sleep(1)
	return(0)


def cleanup(inst):
	for i in inst.contr.jobs:
		for j in inst.contr.jobs[i].items:
			if j.done == False:
				j.assignment = None
	inst.mechI = 'paused'
	sleep(5)


### Gives dictionary for access to instance behaviors
indexI = {'paused': paused, 'default': defaultInst, 'yelp': yelp, 'cleanup': cleanup, 'test': test}



#################### CONTROLLER BEHAVIORS ####################
def defaultContr(contr):
	time.sleep(5)
	return(0)


def hourlyCycle(contr):
	try:
		t = datetime.datetime.now()
		if t.minute == 0:
			contr.initialize(n = 5)
			for i in contr.awsI:
				contr.awsI[i].mechI = 'yelp'
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


indexC = {'paused': paused, 'default': defaultContr, 'hourly': hourlyCycle}