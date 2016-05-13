import curses
import curses.textpad
import time
import threading



def padTabs(str):
	str = ' ' + str
	while len(str) < 20:
		str += ' '
	return(str)



class jobState:
	def __init__(self, contrIO):
		self.contrIO = contrIO



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
		curses.start_color()
		curses.init_color(20, 400, 400, 400);
		# unselected tab
		curses.init_pair(1, curses.COLOR_BLACK, 20)
		# selected tab
		curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)

		# SET PARAMETERS
		self.winTabs = ['Log', 'Instances', 'Jobs']
		self.currTab = 0

		# SET WIN DIM
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
			if self.shutdownT:
				self.shutdownTimer -= 1

			self.mainWin.erase()

			c = self.stdscr.getch()
			if c == ord(':'):
				cmd = self.inTextBox.edit()
				self.runCmd(cmd.strip())
				self.inWin.erase()
			if c == curses.KEY_RIGHT:
				self.currTab = (self.currTab + 1) % len(self.winTabs)
			if c == curses.KEY_LEFT:
				self.currTab = (self.currTab - 1) % len(self.winTabs)

			self.dispTabs()
			self.dispLog()

			self.tabWin.refresh()
			self.mainWin.refresh()
			self.inWin.refresh()
			time.sleep(0.5)


	def dispLog(self):
		logItems = [i[:self.winW] for i in self.contr.log[-(self.winH - 1):]]
		for i in range(len(logItems)):
			self.mainWin.addstr(i, 0, logItems[i])
		return(0)


	def dispInstances(self):
		return(0)


	def dispJobs(self):
		return(0)


	def dispTabs(self):
		#self.tabWin.addstr(0, 0, padTabs('test'), curses.color_pair(2))
		for i in range(len(self.winTabs)):
			if i == self.currTab:
				self.tabWin.addstr(0, i * 20, padTabs(self.winTabs[i]), curses.color_pair(2))
			else:
				self.tabWin.addstr(0, i * 20, padTabs(self.winTabs[i]), curses.color_pair(1))
		return(0)





	def runCmd(self, cmd):
		if cmd == 'shutdown':
			self.shutdownT = True
			self.contr.shutdown()
			return(0)
		if cmd == 'reload': self.contr.relMech()
		return(0)