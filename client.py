import socket
import ast
import os
import mechanisms as mech
from utils import snd, recv

port_def = 58302
retOpt = ['default']

# mechS - See mechanisms.py
# ret - 'default', 'pathtowrite'
def putget(data, name = 'default', mechS = 'paused', ret = 'default', port = port_def):
	if mechS not in mech.indexS:
		print('mechS argument invalid, putget failed')
		return(1)
	if ret != 'default':
		ret = os.path.abspath(ret)
		if not os.path.exists(ret):
			print('ret argument invalid, putget failed')
			return(1)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('localhost', port))
	string = ' '.join([name] + [mechS] + [ret] + [str(i) for i in data])
	retOut = 0
	snd(s, string)
	if ret == 'default':
		retOut = recv(s)
		retOut = ast.literal_eval(retOut)
	s.close()
	return(retOut)