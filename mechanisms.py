import random
import time
import requests
import datetime
import threading
from utils import taggedPrintR



csil_mach = ['linux', 'machoke', 'machamp', 'bellsprout', 'weepinbell', 'victreebel', 'tentacool', 'tentacruel', 'geodude', 'graveler', 'golem', 'ponyta', 'rapidash', 'slowpoke', 'slowbro', 'magnemite', 'magneton', 'farfetchd', 'doduo', 'seel', 'dewgong', 'grimer', 'muk', 'shellder', 'cloyster', 'gastly', 'haunter', 'gengar', 'onix', 'drowzee', 'hypno', 'krabby', 'kingler', 'voltorb', 'electrode', 'exeggutor', 'cubone', 'marowak', 'hitmonchan', 'lickitung', 'koffing']
ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'
#ua2 = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36'



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


def yelp(inst):
	if random.randint(1, 1000) == 1000 and len(inst.items) > 0:
		x = inst.items.pop(0)
		try: resutltFromAWS = inst.request(x)
		except Exception as e:
			inst.items.append(x)
			inst.addLog(e)
	time.sleep(5)
	return(0)


indexI = {'paused': paused, 'default': defaultInst, 'yelp': yelp}



#################### CONTROLLER BEHAVIORS ####################
def initializeCsil(contr):
	for m in csil_mach:
		init_call = 'csil-' + m
		contr.initialize(init_call)
	for i in contr.instances: contr.instances[i].changeMech('yelp')
	contr.changeMech('paused')
	return(0)



indexC = {'paused': paused, 'start-csil': initializeCsil}
