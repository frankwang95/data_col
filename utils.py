import socket
import time
import subprocess
import threading



#################### GETTING REQUESTS ####################
key = 'datacol'
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



#################### MECHANISM UTILITIES ####################
def hourodds(h):
	odds = [40, 40, 30, 30, 40, 40,
	#		 0,  1,  2,  3,  4,  5,
		50, 70, 90, 70, 50, 50,
	#	 6,  7,  8,  9, 10, 11,
		70, 90, 70, 50, 70, 80,
	#	12, 13, 14, 15, 16, 17
		95, 80, 70, 50, 50, 50]
	#	18, 19, 20, 21, 22, 23
	return(odds[h])


