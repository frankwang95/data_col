import curses
import curses.textpad
import time



###################### UTIL FUNCTIONS ######################
def padTabs(str):
	str = ' ' + str
	while len(str) < 20:
		str += ' '
	return(str)


def progBar(perc, l):
	str = '|'
	n = int(perc * (l - 2))
	while len(str) < (l - 1):
		if n > 0:
			str = str + '#'
			n -= 1
		else: str = str + ' '
	str = str + '|'
	return(str)



###################### MAIN CLASSES ######################
class ioState:
	def __init__(self, contr):
		self.winTabs = ['Log', 'Instances', 'Jobs']
		self.currTab = 0
		self.logScrollState = 0
		self.jobScrollState = 0
		self.instScrollState = 0



class controllerIO:
	def __init__(self, contr):
		self.contr = contr
		self.shutdownT = False
		self.shutdownTimer = 5

		self.stdscr = curses.initscr()
		self.stdscr.keypad(1)
		self.stdscr.nodelay(1)
		curses.noecho()
		curses.cbreak()

		# SET COLORS
		# unselected tab
		curses.start_color()
		try:
			curses.init_color(20, 400, 400, 400)
			curses.init_pair(1, curses.COLOR_BLACK, 20)
		except:
			curses.init_pair(1,curses.COLOR_WHITE, curses.COLOR_BLACK)
		# selected tab
		curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)

		# SET PARAMETERS
		self.winTabs = ['Log', 'Instances', 'Jobs']
		self.currTab = 0
		self.logScrollState = 0
		self.jobScrollState = 0
		self.instScrollState = 0

		# SET WIN DIM
		# windows should be at least 360 wide x 240 tall??
		self.winH = self.stdscr.getmaxyx()[0]
		self.winW = self.stdscr.getmaxyx()[1]

		# INITIALIZE SUB WIN
		# tabs
		self.tabWin = curses.newwin(1, self.winW, 0, 0)
		
		# main win
		self.mainWin = curses.newwin(self.winH - 2, self.winW, 1, 0)
		
		# command win
		self.inWin = curses.newwin(1, self.winW, self.winH - 1, 0)
		self.inTextBox = curses.textpad.Textbox(self.inWin)
		self.inWin.nodelay(1)

		self.stdscr.refresh()

		while not self.shutdownT or self.shutdownTimer > 0:
			self.mainWin.erase()

			if self.shutdownT:
				self.shutdownTimer -= 1

			self.mainWin.erase()

			c = self.stdscr.getch()
			if c == ord(':'):
				cmd = self.inTextBox.edit()
				try:
					if self.runCmd(cmd.strip()) == 1:
						self.contr.addLog('>> command invalid: {0}'.format(cmd))
				except Exception as e:
					self.contr.addLog('>> command encountered exception: {0}'.format(e))
				self.inWin.erase()

			if c == curses.KEY_RIGHT:
				self.currTab = (self.currTab + 1) % len(self.winTabs)
			if c == curses.KEY_LEFT:
				self.currTab = (self.currTab - 1) % len(self.winTabs)

			self.dispTabs()
			if self.currTab == 0: self.dispLog()
			elif self.currTab == 1: self.dispInst()
			elif self.currTab == 2: self.dispJobs()

			self.tabWin.refresh()
			self.mainWin.refresh()
			self.inWin.refresh()
			time.sleep(0.2)
		curses.endwin()


	def dispLog(self):
		logItems = [i[:self.winW] for i in self.contr.log[-(self.winH - 2):]]
		for i in range(len(logItems)):
			try: self.mainWin.addstr(i, 0, logItems[i])
			except Exception as e:
				h = open('errorlog.txt', 'w')
				str = '''ERROR: {0}
PRINTED MESSAGE: {1}
VERT INDEX: {2}
HORZ INDEX: {3}
WINDOW VERT SIZE: {4}
WINDOW HORZ SIZE: {5}
'''.format(e, logItems[i], len(logItems[i]), self.winH, self.winH)
				h.write(str)
				h.close()
		return(0)


	def dispInst(self):
		inst = self.contr.instances.copy()
		yn = 0
		xn = 0
		for i in inst:
			self.dispSingleInst(inst[i], yn * 5, xn * 61)
			xn += 1
			if xn * 61 + 61 > self.winW:
				yn += 1
				xn = 0
		return(0)


	def dispSingleInst(self, inst, y, x):
		self.mainWin.addstr(y, x, 'counter: ', curses.A_BOLD)
		self.mainWin.addstr(y, x + 9, str(inst.counter))
		self.mainWin.addstr(y + 1, x, 'type: ' + inst.type)
		self.mainWin.addstr(y + 2, x, 'mech: ' + inst.mech)
		self.mainWin.addstr(y + 3, x, 'items pending: ' + str(len(inst.items)))
		return(0)


	def dispJobs(self):
		jobs = self.contr.jobs.copy()
		yn = 0
		xn = 0
		for i in jobs:
			self.dispSingleJob(jobs[i], yn * 6, xn * 61)
			xn += 1
			if xn * 61 + 61 > self.winW:
				yn += 1
				xn = 0
		return(0)


	def dispSingleJob(self, job, y, x):
		name = job.name[:54]
		prog = 1 - float(len(job.rem()))/len(job.items)

		self.mainWin.addstr(y, x, 'name: ', curses.A_BOLD)
		self.mainWin.addstr(y, x + 6, name)
		self.mainWin.addstr(y + 1, x, 'mech: ' + job.mech)
		self.mainWin.addstr(y + 2, x, 'tags: ' + ', '.join(job.tags))
		self.mainWin.addstr(y + 3, x, 'progress: ' + '{0}/{1}'.format(len(job.items) - len(job.rem()), len(job.items)))
		self.mainWin.addstr(y + 4, x, progBar(prog, 60))
		return(0)


	def dispTabs(self):
		for i in range(len(self.winTabs)):
			if i == self.currTab: self.tabWin.addstr(0, i * 20, padTabs(self.winTabs[i]), curses.color_pair(2))
			else: self.tabWin.addstr(0, i * 20, padTabs(self.winTabs[i]), curses.color_pair(1))
		return(0)


	def runCmd(self, cmd):
		cmdspl = cmd.split()
		if cmdspl[0] == 'shutdown':
			self.currTab = 0 # changes to log window
			self.shutdownT = True
			self.contr.shutdown()
			return(0)

		if cmdspl[0] == 'reload':
			self.contr.relMech()
			return(0)

		if cmdspl[0] == 'instance':
			if cmdspl[1] == 'initialize':
				return(self.contr.initialize(cmdspl[2]))
			if cmdspl[1] == 'close':
				self.contr.instances[int(cmdspl[2])].closeCmd = True
				return(0)
			if cmdspl[1] == 'flush':
				self.contr.instances[int(cmdspl[2])].flushCmd = True
				return(0)
			if cmdspl[1] =='mech':
				self.contr.instances[int(cmdspl[2])].changeMech(cmdspl[3])
				return(0)

		if cmdspl[0] == 'job':
			if cmdspl[1] == 'mech':
				self.contr.jobs[cmdspl[2]].changeMech(cmdspl[3])
				return(0)

		if cmdspl[0] == 'controller':
			if cmdspl[1] == 'mech':
				self.contr.changeMech(cmdspl[2])
				return(0)

		return(1)
