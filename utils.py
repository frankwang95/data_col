import socket
import time
import subprocess
import threading



#################### GETTING REQUESTS ####################
aws_key = './keys/datacol.pem'
csil_pass = None
ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9'




#################### NETWORKING FUNCTIONS ####################
def snd(s, msg):
	msgL = [msg[(4096 * i) : 4096 * (i + 1)] for i in range(0, len(msg)/4096 + 1)]
	n = len(msgL)
	s.sendall(str(n))
	s.recv(2)
	for i in msgL:
		s.sendall(i)
		s.recv(2)
	return(0)


def recv(s, err = 5):
	while err > 0:
		try:
			msg = ""
			n = s.recv(8)
			n = int(n)
			s.sendall("0")
			while n > 0:
				piece = s.recv(4096)
				s.sendall("0")
				msg = msg + piece
				n -= 1
			return (msg)
		except: err -= 1
	s.close()
	return(1)



#################### TERMINAL IO FUNCTIONS ####################
ioLock = threading.Lock()

def taggedPrintR(str):
	with ioLock: print(time.strftime("[%H:%M:%S] ", time.localtime()) + str)
	return(0)

