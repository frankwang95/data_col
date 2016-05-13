import random
import time
import datetime
import threading
from utils import request, hourodds, taggedPrintR



#################### PAUSED BEHAVIOR ####################
def paused(instJobContr):
	#time.sleep(5)
	return(1)



#################### SECHDULER BEHAVIORS ####################
### Default scheduler simply assigns jobs to random instances
def defaultSch(job):
	while len(job.unassigned) > 0:
		instance = job.contr.awsI[random.choice(job.contr.awsI.keys())]
		job.unassigned[0].assignment = instance
		instance.items.append(job.unassigned[0])
		del job.unassigned[0]
	return(0)


### Gives dictionary for access to scheduler behaviors
indexS = {'paused': paused, 'default': defaultSch}



#################### INSTANCE BEHAVIORS ####################
### Default scheduler completes jobs as quickly as possible
### Works in time blocks of 5 seconds
def defaultInst(inst):
	tEnd = time.time() + 5
	while time.time() < tEnd and len(inst.items) > 0:
		x = inst.items.pop(0)

		try:
			resultFromAWS = request(inst.pDNS, x.data)
			x.done = resultFromAWS
			x.assignment = None
		except Exception as e:
			inst.items.append(x)
	return(0)
	


def yelp(inst):
	today = int(time.strftime('%d'))
	hour = int(time.strftime('%H'))
	minute = int(time.strftime('%M')) - (int(time.strftime('%M')) % 5)

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
			if inst.stats['datepull'] and inst.stats['hourpull'] and inst.stats['minpull'] and (minute > 10 or minute < 10):
				time.sleep(random.randint(0,100))
				try:
					resultFromAWS = request(inst.pDNS, x.data)
					x.done = resultFromAWS
					x.assignment = None
				except Exception as e:
					print e
					inst.items.append(x)
					continue
			else:
				inst.items.append(x)
				continue
		try:
			resultFromAWS = request(inst.pDNS, x.data)
			x.done = resultFromAWS
			x.assignment = None
		except Exception as e:
			inst.items.append(x)
	return(0)


### Gives dictionary for access to instance behaviors
indexI = {'paused': paused, 'default': defaultInst, 'yelp': yelp}



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