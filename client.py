import socket
import ast
import os
import mechanisms
from utils import snd, recv



# mechS - See mechanisms.py
# ret - 'default', 'pathtowrite'
def putget(data, port, ip = 'localhost', name = 'default', mech = 'paused', tags = []):
	if mech not in mechanisms.indexJ:
		print('mechS argument invalid, putget failed')
		return(1)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((ip, port))
	string = ' '.join([name, mech, str(tags).replace(' ', '')] + [str(i) for i in data])
	retOut = 0
	snd(s, string)
	retOut = recv(s)
	retOut = ast.literal_eval(retOut)
	for i in retOut:
		i[2] = i[2].decode('utf-8')
	s.close()
	return(retOut)
