from math import exp, log, sqrt, pi
import time, datetime
import sys, os
from multiprocessing import Process, Pipe, Manager
import numpy as np
from scipy.stats import norm
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support import expected_conditions as EC

def useFirefox():
	return webdriver.Firefox()

class NadexSearch:

	"""						FUNCTIONS					"""

	def __init__(self):
		self.driver = webdriver.Firefox()
		self.username = "demo-stochastic"
		self.password = "VINY5X"
		self.balance = -1
		self.purchaseInProgress = False
		self.optionList = []
		self.currencyPairs = ['AUD/JPY', 'AUD/USD', 'EUR/GBP', 'EUR/JPY', 'EUR/USD',
							  'GBP/JPY', 'GBP/USD', 'USD/CAD', 'USD/CHF', 'USD/JPY']
		
	
	def signIn(self):
		"""Goes to the Nadex website and signs in to a demo account."""
		
		self.driver.get("http://www.nadex.com/login.html")
		ui.WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "account_id")))

		#~ wait = ui.WebDriverWait(driver, 15) # Times out after 15 seconds.
		
		elem = self.driver.find_element_by_id("account_id")
		elem.send_keys(self.username)
		elem = self.driver.find_element_by_id("password")
		elem.send_keys(self.password)
		elem.send_keys(Keys.RETURN)
		
		print("Waiting for page to load...")
		
		ui.WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "ifrMyPrices")))
		time.sleep(2)
		
		self.balance = self.getBalance()
		
		print("\rPage open.")
		time.sleep(1.2)
		print("\nWelcome. Your starting balance is: \t$" + str('%.2f' % self.balance))
		
		#~ For switching to custom watchlist.
		#~ driver.find_element_by_id("selectWatchlist_currVal").click()
		#~ driver.find_element_by_xpath('//*[@id="selectWatchlist_ddScroll"]/ul/li[16]').click()
		#~ time.sleep(10)

	def getBalance(self):
		"""Returns the account's current balance as a floating point."""

		currentBalance = self.driver.execute_script("return parent.document.getElementById('rsrcBalance').textContent")
		currentBalance = currentBalance.replace('$', '')
		currentBalance = currentBalance.replace(',', '')
		currentBalance = float(currentBalance)
		return currentBalance

	def getOptionNames(self, clean=False):
		"""Return a list of option names from the main Watchlist.
		Useful because the names of options are always changing.
		Clean=True will remove unpriced options."""

		names = self.driver.execute_script(  """adrNames = window.parent.frames['ifrMyPrices'].document.getElementsByClassName('floatLeft tableIcon dealOpen');
										namesText = "";
										for(var i = 0; i < adrNames.length; i++){
											namesText += adrNames[i].textContent + ",";
										}
										return namesText;""")

		nameList = [n for n in names.split(",")]

		del nameList[-1]
		
		if not nameList:
			print("There are no open contracts.")

		elif clean:
			priceList = self.getPrices(False)
			counter = 0
			while counter < len(priceList):
				if (len(priceList[counter]) < 4) or (len(priceList[counter + 1]) < 4):
					del nameList[(counter//2)]
				counter += 2
		
		return nameList

	def getPrices(self, clean=False):
		"""Returns a list of option prices from the main Watchlist.
		Useful for obvious reasons.
		Clean=True will remove unpriced options."""

		prices = self.driver.execute_script( """adrPrices = window.parent.frames['ifrMyPrices'].document.getElementsByClassName('price dealOpen');
										priceText = "";
										for(var j = 0; j < adrPrices.length; j++){
											priceText += adrPrices[j].textContent + ",";
										}
										return priceText;""")

		priceList = [p for p in prices.split(",")]
		
		del priceList[-1]
		
		if not priceList:
			print("There are no open contracts.")

		else:
			for x in range(0,len(priceList)):
				try:
					priceList[x] = float(priceList[x])
				except ValueError:
					continue
					
			if clean:
				counter = 0
				while counter < len(priceList):
					if not isinstance(priceList[counter], float):
						del priceList[counter:counter+2]
					else:
						counter += 2
					
		return priceList
	
	def getExpireTimes(self):
		"""Returns expire time in years.
		Why years? The interest rates are expressed in years, and the units must be consistent."""

		times = self.driver.execute_script(  """adrTimes = window.parent.frames['ifrMyPrices'].document.getElementsByClassName('yui-dt0-col-timeToExpiry yui-dt-col-timeToExpiry yui-dt-sortable');
										timeText = "";
										for(var k = 0; k < adrTimes.length; k++){
											timeText += adrTimes[k].textContent + ",";
										}
										return timeText;""")
		timeList = [t.replace(" ", "") for t in times.split(',')]
		del timeList[0] #Needed to remove title and empty string.
		del timeList[-1]
		
		for x in range(0, len(timeList)):
			if timeList[x] == '-':
				continue

			t = timeList[x]
			if any('h' == c for c in t): #Not all timestamps are given in the same format.
				t = t.replace("h", "")
				t = t.replace("m", "")
				t = time.strptime(t, "%H:%M")
				t = datetime.timedelta(hours=t.tm_hour, minutes=t.tm_min).total_seconds()
			
			elif any('m' == c for c in t):
				t = t.replace("m", "")
				t = t.replace("s", "")
				
				try:
					t = time.strptime(t, "%M:%S")
					t = datetime.timedelta(minutes=t.tm_min, seconds=t.tm_sec).total_seconds()
				except:
					t = "0"+t
					t = time.strptime(t, "%M:%S")
					t = datetime.timedelta(minutes=t.tm_min, seconds=t.tm_sec).total_seconds()
			
			else:
				t = t.replace("s", "")
				t = time.strptime(t, "%S")
				t = datetime.timedelta(seconds=t.tm_sec).total_seconds()
			
			t /= 31536000.0
			timeList[x] = t
		
		return timeList
	
	def getIndicatives(self):
		"""Returns the underlying indicative values."""

		indicatives = self.driver.execute_script("""adrUnd = window.parent.frames['ifrMyPrices'].document.getElementsByClassName('yui-dt0-col-underlyingIndicativePrice yui-dt-col-underlyingIndicativePrice');
											undText = "";
											for(var l = 1; l < adrUnd.length; l++){
												undText += adrUnd[l].textContent + ",";
											}
											return undText;""")
		indicativesList = [float(i) if ('.' in i) else i for i in indicatives.split(',')]
		return indicativesList
	
	def makeOptions(self, childPipes):
		"""Not really sure what this does.
		Makes instances of my option class for each open contract?"""
		
		names = self.getOptionNames(False)
		if not names:
			return None
		expiry = self.getExpireTimes()
		underlying = self.getIndicatives()
		prices = self.getPrices(False)

		for x in range(0, len(names)):
			if not any(names[x].split(" ")[0] == pair for pair in self.currencyPairs):
				continue
			if prices[2*x] == '-' or prices[2*x+1] == '-':
				continue
			self.optionList.append(CurrencyOption(names[x], prices[2*x], prices[2*x + 1], expiry[x], underlying[x], childPipes[x], x))
	
	def scanner(self, spread):
		"""Displays options with specified spread. Useful for making trades manually."""
		
		names = self.getOptionNames(False)
		if not names:
			return
		
		prices = self.getPrices(True)
		if not prices:
			print("There are no priced contracts.")
			return
		
		print("Name", '%44s' % "Sell", "   Buy	     Spread\n")
		n = 0
		p = 0
		frmt = "%*s%*s%*s%*s"

		while n < len(names):
			try:		#try is necessary to prevent errors from '-' prices.
				differential = abs(float(prices[p]) - float(prices[p+1]))
				if differential <= spread:
					print(frmt % (0, names[n], 50-len(names[n]), prices[p], 7, prices[p+1], 9, differential))
			except TypeError:
				pass
			
			n += 1
			p += 2
	
	def priceHistory(self, length, optionConnections, timeConnection, gatheringConnection):
		"""This function has not been tested yet!
		I believe this was supposed to be run in a separate process and simply collect price data.
		Probably not useful for arbitrage."""
		
		global processIDs
		proxyList = processIDs
		proxyList.append(os.getpid())
		processIDs = proxyList

		buyList = []
		sellList = []
		times = []
		
		currentPrices = self.getPrices(False)
		
		for x in range(0, len(currentPrices)//2):
			buyList.append([currentPrices[2*x + 1]])
			sellList.append([currentPrices[2*x]])

		gatheringConnection.send(True)
		counter = 0

		while True:
			start_time = time.time()
			print("Start")

			if len(currentPrices) != length:
				gatheringConnection.send(False)
				print("The amount of open contracts has changed.")
				sys.exit()

			else:
				currentTimes = self.getExpireTimes()
				currentUnderlying = self.getIndicatives()
				currentPrices = self.getPrices(False)
			
				for p in range(0, len(currentPrices)//2):
					buyList[p].append(currentPrices[p*2 + 1])
					sellList[p].append(currentPrices[p*2])
					print(sellList[p], buyList[p], currentTimes[p], currentUnderlying[p])
					optionConnections[p].send((sellList[p], buyList[p], currentTimes[p], currentUnderlying[p]))

				times.append(time.time() - start_time)

				timeConnection.send(times)

				print("End ", counter)
				counter+=1
	
	def startTrading(self, childPipes):
		"""Launches processes for each option."""
		global optionList

		if not optionList:
			self.makeOptions(childPipes)
		
		for option in optionList:
			Process(target=self.analyzeData, args=(option,)).start()
			time.sleep(1)

		print("Analysis has begun.")
	
	def analyzeData(self, option):
		"""This is a place for *very* basic trading algorithms for testing, not for winning.
		Currently does nothing interesting. Make it trade off of the Greeks or something."""
		# Not sure what these comments are for.
		# global processIDs
		# proxyList = processIDs
		# currentProcess = os.getpid()
		# proxyList.append(currentProcess)
		# processIDs = proxyList

		while True:
			if abs(option.buyPrice - option.sellPrice) <= 5:
				if option.strike/option.underlying <= 0.9 and option.delta() <= 0.5:
					option.buy(lotSize=1, short=True)
					sys.exit()
				elif 1 >= option.strike/option.underlying >= 0.995  and option.delta() > 0:
					option.buy(lotSize=1, short=False)
					sys.exit()
				elif  1 >= option.strike/option.underlying >= 0.995  and option.delta() < 0:
					option.buy(lotSize=1, short=True)
					sys.exit()
				elif 1.01 >= option.strike/option.underlying >= 1  and option.delta() < 0:
					option.buy(lotSize=1, short=True)
					sys.exit()



	def placeOrderExample(self):
		"""Places an order with no strategy, just to demonstrate that it works."""
		
		global optionList
		
		if not optionList:
			return "There are no contracts to order."
		
		global currentFrame
		
		for option in optionList:
			start_time = time.time()
			option.buy(lotSize=1, short=False)
			timeTracker[9].append(time.time() - start_time)
			print("Average time: ", np.mean(timeTracker[9]))
	
	def fillWatchlist(self):
		"""Code looks awful, I'll have to overhaul it when it comes time I finally need it.
		Used for creating a custom watchlist, filled with every Forex binary option.
		This is useful because Nadex does not save the entire watchlist, and thus it needs to be updated from time to time."""
		
		global currentFrame
		
		driver.switch_to_default_content()
		driver.switch_to_frame("ifrFinder")
		currentFrame = 'ifrFinder'
		ui.WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ygtvt4")))
		driver.find_element_by_id("ygtvt4").click()
		ui.WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "ygtvt8")))
		
		for number in range(8,17):
			ID = "ygtvt" + str(number)
			driver.find_element_by_id(ID).click()
			
		for number in range(18,87):
			
			ID = "ygtvlabelel" + str(number)
			driver.find_element_by_id(ID).click()
			driver.switch_to_default_content()
			driver.switch_to_frame("ifrDealingRates")
			time.sleep(3)
			
			buttons = driver.find_elements_by_css_selector(".optionsBtn")	
			
			for button in buttons:
				
				button.click()
				driver.switch_to_default_content()
				ui.WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "PORTFOLIO")))
				driver.find_element_by_xpath('//*[@id="PORTFOLIO"]/a').click()
				driver.switch_to_frame("ifrDealingRates")
			
			driver.switch_to_default_content()
			driver.switch_to_frame("ifrFinder")
	
	def JStest(self):
		"""Starts running a JavaScript 'console' for debugging purposes."""
		
		print('Type "exit JS" to quit.')
		command = input('>>>')
		
		while command != 'exit JS':
			try:
				driver.execute_script(command)
				try:
					print(driver.execute_script(command))
				except:
					pass
			except:
				print("Error")
			
			command = input('>>>')
		
	def mainMenu(self):
		"""The main menu of the program where the user can manually tell it what to do.
		Mostly for debuging purposes, since most of these things should be automated eventually."""
		
		global optionConnectionParent, optionConnectionChild, priceGatheringChild, priceGatheringParent
		global motherOfAllUnderlying, currentExpiries
		global optionList
		global price_time_parent, price_time_child

		priceGatheringChild.send(False)

		while True:
			print("\nPress 1 to scan for options.\nPress 2 to fill the watchlist with open Forex binaries.")
			print("Press 3 to demonstrate purchasing.\nPress 4 to print option names.\nPress 5 to print option prices.")
			print("Press 6 to start gathering price data.\nPress 7 to print sell price data.\nPress 8 to print buy price data.")
			print("Press 9 to start trading.\nPress 0 to enter JavaScript console.")
			menu = str(input(""))
			menu = menu.lower()
			
			if menu == "1":
				spread = eval(input("Enter a spread: "))
				start_time = time.time()
				
				self.scanner(spread)

				timeTracker[1].append(time.time() - start_time)
				print("\nTime elapsed: ", timeTracker[1][-1], "seconds.")
				print("Average time: ", np.mean(timeTracker[1]), "seconds.")
				
			elif menu == "2":
				start_time = time.time()
				self.fillWatchlist()
				timeTracker[2].append(time.time() - start_time)
				print("\nTime elapsed: ", timeTracker[2][-1], "seconds.")
				print("Average time: ", np.mean(timeTracker[2]), "seconds.")
				
			elif menu == "3":
				if not priceGatheringParent.recv():
					currentPrices = self.getPrices()
					if currentPrices:

						for x in range(0, len(currentPrices)):
							newParent, newChild = Pipe()
							optionConnectionParent.append(newParent)
							optionConnectionChild.append(newChild)

						priceHistoryProcess = Process(target=self.priceHistory, args=(len(currentPrices), optionConnectionChild, price_time_child, priceGatheringChild))
						priceHistoryProcess.start()

				if not optionList:
					self.makeOptions(optionConnectionChild)
				
				purchasingDemonstration = Process(target=self.placeOrderExample, args=())
				purchasingDemonstration.start()
				purchasingDemonstration.join()
				
			elif menu == "4":
				condition =  eval(input("Remove unpriced options? [0/1]"))
				try:
					start_time = time.time()
					
					print(self.getOptionNames(condition))

					timeTracker[4].append(time.time() - start_time)
					print("\nTime elapsed: ", timeTracker[4][-1], "seconds.")
					print("Average time: ", np.mean(timeTracker[4]), "seconds.")
					
				except:
					print("Invalid input")
				
			elif menu == "5":
				condition =  eval(input("Remove unpriced options? [0/1]"))
				try:
					start_time = time.time()
					
					print(self.getPrices(condition))
					timeTracker[5].append(time.time() - start_time)
					print("\nTime elapsed: ", timeTracker[5][-1], "seconds.")
					print("Average time: ", np.mean(timeTracker[5]), "seconds.")
					
				except:
					print("Invalid input")
			
			elif menu == "6":
				if not priceGatheringParent.recv():
					currentPrices = self.getPrices()
					if currentPrices:
						# optionConnectionParent, optionConnectionChild = [Pipe() for p in currentPrices]
						for x in range(0, len(currentPrices)):
							newParent, newChild = Pipe()
							optionConnectionParent.append(newParent)
							optionConnectionChild.append(newChild)

						priceHistoryProcess = Process(target=self.priceHistory, args=(len(currentPrices), optionConnectionChild, price_time_child, priceGatheringChild))
						priceHistoryProcess.start()
				else:
					print("This process is already running.")
			
			elif menu == "7":
				for pipe in optionConnectionParent:
					print(pipe.recv())
			
			elif menu == "8":
				for pipe in optionConnectionParent:
					print(pipe.recv())
			
			elif menu == "9":
				if not priceGatheringParent.recv():
					currentPrices = self.getPrices()
					if currentPrices:
						# optionConnectionParent, optionConnectionChild = [Pipe() for p in currentPrices]
						for x in range(0, len(currentPrices)):
							newParent, newChild = Pipe()
							optionConnectionParent.append(newParent)
							optionConnectionChild.append(newChild)

						priceHistoryProcess = Process(target=self.priceHistory, args=(len(currentPrices), optionConnectionChild, price_time_child, priceGatheringChild))
						priceHistoryProcess.start()
						while not motherOfAllSellPrices:
							pass

				self.startTrading(optionConnectionChild)
			
			elif menu == "0":
				self.JStest()
				
			elif menu in ["exit", "quit", "stop", "abort", "end"]:
				break
				
			else:
				print("Invalid input.")

class CurrencyOption:
	twoPi = 2*pi

	def __init__(self, name, buy, sell, expireTime, indicative, pipe, index):
		global riskFreeRates, exchangeRates
		self.name = name
		self.buyPrice = buy
		self.sellPrice = sell
		self.expiry = expireTime
		if isinstance(indicative, float):
			self.underlying = indicative
			doExp = True
		else:
			self.underlying = exchangeRates[name.split(" ")[0]]
			doExp = False
		Process(target=self.updateFields, args=(pipe, index, doExp)).start()
		self.strike = float(name.split(" ")[-2].replace(">", ""))
		self.countries = [c for c in name.split(" ")[0].split("/")]
		self.conversionFactor = 1/self.underlying
		self.r_domestic = riskFreeRates[self.countries[0]]
		self.r_foreign = riskFreeRates[self.countries[1]]
		self.d1 = 0
		self.volatility = self.calculateVolatility(0.05)
		self.d2 = self.d1 - self.volatility*sqrt(self.expiry)

	def updateFields(self, pipe, index, doExpiry):
		"""Updates the buy, sell, expire time, and underlying value for the option."""
		
		while doExpiry:
			self.sellPrice = pipe.recv()[0][-1]
			self.buyPrice = pipe.recv()[1][-1]
			self.expiry = pipe.recv()[2]
			self.underlying = pipe.recv()[3]
		
		while not doExpiry:
			self.buyPrice = motherOfAllBuyPrices[index][-1]
			self.sellPrice = motherOfAllSellPrices[index][-1]
			self.underlying = motherOfAllUnderlying[index]

	def convertUnits(self):
		"""Returns the correct conversion factor, aka exchange rate, for the given currencies.
		This seems useless. <- I wrote that year ago, why?
		Probably because it's not used anywhere.
		No, it's because all it really does is return a reciprocal of a value."""

		return 1.0/self.underlying

	def buy(self, lotSize=1, short=False):
		"""Buys the option."""
		
		global ticketsOpen, purchaseInProgress

		while purchaseInProgress:
			pass
		purchaseInProgress = True
		try:
			driver.find_element_by_link_text(self.name).click()
			ticketsOpen += 1
			myTicket = ticketsOpen
		except:
			return "Link_text not found."

		#This is here to prevent the code from executing before the order form has even opened.
		loaded = False
		while not loaded:
			try:
				float(driver.execute_script("return window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('dmaPriceCurrent').textContent"))
				loaded = True
			except:
				pass

		#This chunk actually places the order.
		#The above chunk of code doesn't slow the execution enough.
		#Unfortunately I cannot come up with a better way of further slowing it down enough other than time.sleep().
		time.sleep(0.45)
		try:
			driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('directionChange').click()") #Once for buy, twice for sell.
			driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('size').value = "+str(lotSize))
			if short:
				driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('directionChange').click()")
				driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('level').value = "+str(self.sellPrice))
			else:
				driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('level').value = "+str(self.buyPrice))
			driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('btnSubmit').click()")
			loaded = False
		except:
			print("Error filling buyslip.")

		while not loaded:
			try:
				driver.execute_script("window.parent.frames['ifrBetslip-"+str(myTicket)+"'].document.getElementById('betslipBtnClose').click()")
				loaded = True
			except:
				pass
		
		ticketsOpen -= 1
		purchaseInProgress = False

	
	def calculateVolatility(self, precision):
		"""Calculates volatility using the bisection method on the Garman-Kohlhagen model.
		This function is also responsible for calculating d1 and d2.
		Unit problems have mostly been ironed out, but there may be some left."""
		
		low = 0.01
		high = 300.0
		
		while True:
			self.volatility = (high + low)/2.0
			
			self.d1 = (log(self.underlying/self.strike) + (self.r_domestic - self.r_foreign + 0.5*self.volatility*self.volatility)*self.expiry)/(self.volatility*sqrt(self.expiry))
			value = exp(-self.r_domestic*self.expiry)*norm.cdf(self.d1, 0, 1)*self.buyPrice*self.conversionFactor
			
			if (abs(self.buyPrice - value) <= precision)  or (high <= 0.1) or (low >= 299.9):
				break
			elif value < self.buyPrice:
				low = self.volatility
			elif value > self.buyPrice:
				high = self.volatility
		
		self.d2 = self.d1 - self.volatility*sqrt(self.expiry)		
		return self.volatility
	
#	"""	 GREEKS	     """
# Note that many of these functions have a*a in them, since it is slightly faster than a**2.

	def printGreeks(self):
		"""Simply calculates all of the major Greeks and prints them out.
		Used for debugging purposes."""
		
		print("d1 =\t\t\t", self.d1)
		print("d2 =\t\t\t", self.d2)
		print("Volatility =\t", self.volatility)
		print("Delta (call) =\t", self.delta(short=False))
		print("Delta (put) =\t", self.delta(short=True))
		print("Leverage (call) =\t", self.leverage(short=False))
		print("Leverage (put) =\t", self.leverage(short=True))
		print("Theta (call)=\t", self.theta(short=False))
		print("Theta (put)=\t", self.theta(short=True))
		print("Vega =\t\t\t", self.vega())
		print("Rho (call)=\t\t", self.rho(short=True))
		print("Rho (put)=\t\t", self.rho(short=False))
		print("Gamma =\t\t\t", self.gamma())
		print("Vanna =\t\t\t", self.vanna())
		print("Vomma =\t\t\t", self.vomma())
		print("Speed =\t\t\t", self.speed())
		print("Zomma =\t\t\t", self.zomma())
		print("Ultima =\t\t", self.ultima())

	def delta(self, short=False):
		"""Derivative of the value with respect to the underlying."""
		
		if short:
			return -exp(-self.r_foreign * self.expiry) * norm.cdf(-self.d1)
		else:
			return exp(-self.r_foreign * self.expiry) * norm.cdf(self.d1)
	
	def leverage(self, short=False):
		"""Delta * underlying/price."""
		
		if short:
			return -exp(-self.r_foreign * self.expiry) * norm.cdf(-self.d1) * (self.underlying/self.strike)
		else:
			return exp(-self.r_foreign * self.expiry) * norm.cdf(self.d1) * (self.underlying/self.strike)
	
	def theta(self, short=False):
		"""Minus one times the derivative of value with respect to time."""
		
		if short:
			return (-exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2) * self.underlying * self.volatility/(2*sqrt(twoPi*self.expiry)))-(self.r_foreign*exp(-self.r_foreign*self.expiry)*norm.cdf(-self.d1))+(self.r_domestic*exp(self.r_domestic*self.expiry)*self.strike*norm.cdf(-self.d2))
		else:
			return (-exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2) * self.underlying * self.volatility/(2*sqrt(twoPi*self.expiry)))+(self.r_foreign*exp(-self.r_foreign*self.expiry)*norm.cdf(self.d1))-(self.r_domestic*exp(self.r_domestic*self.expiry)*self.strike*norm.cdf(self.d2))
	
	def vega(self):
		"""Derivative of value with respect to volatility."""
		
		return exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2)*self.underlying*sqrt(self.expiry/(twoPi))
	
	def rho(self, short=False):
		"""Derivative of value with respect to the interest rate."""
		
		if short:
			return -self.expiry * exp(-self.r_domestic*self.expiry) * self.strike * norm.cdf(-self.d2)
		else:
			return self.expiry * exp(-self.r_domestic*self.expiry) * self.strike * norm.cdf(self.d2)
	
	def gamma(self):
		"""Derivative of delta with respect to underlying.
		Second Derivative of with value respect to underlying."""
		
		return exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2)/(self.underlying * self.volatility * sqrt(twoPi*self.expiry))
	
	def vanna(self):
		"""Derivative of delta with respect to volatility.
		Derivative of vega with respect to underlying.
		Second Derivative of value with respect once to underlying and volatility."""
		
		return -exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2) * self.d2 /(self.volatility * sqrt(twoPi))
	
	def vomma(self):
		"""Derivative of vega with respect to volatility.
		Second Derivative of value with respect to volatility."""
		
		return self.underlying * exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2) * sqrt(self.expiry) * self.d1 * self.d2 / self.volatility
	
	def speed(self):
		"""Derivative of gamma with respect to underlying.
		Third Derivative of value with respect to underlying."""
		
		return -((exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2)/(self.underlying * self.volatility * sqrt(twoPi*self.expiry)))/self.underlying) * (1 + self.d1/(self.volatility*sqrt(self.expiry)))
	
	def zomma(self):
		"""Derivative of gamma with respect to volatility.
		Third Derivative of value with respect twice to underlying and once to volatility."""
		
		return (exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2)/(self.underlying * self.volatility * sqrt(twoPi*self.expiry))) * ((self.d1*self.d2 -1)/self.volatility)
	
	def ultima(self):
		"""Derivative of vomma with respect to volatility.
		Third Derivative of value with respect to volatility."""
		
		return ((-exp(-self.r_foreign * self.expiry - (self.d1*self.d1)/2)*self.underlying*sqrt(self.expiry/twoPi))/(self.volatility*self.volatility)) * (self.d1*self.d2*(1-self.d1*self.d2) + self.d1*self.d1 + self.d2*self.d2)



"""						GLOBAL VARIABLES			"""
iFrames = ['default', 'ifrMyPrices', 'ifrFinder', 'ifrDealingRates', 'ifrBetslip-0']
currentFrame = iFrames[0]
manager = Manager()
motherOfAllBuyPrices = manager.list()
motherOfAllContractNames = manager.list()
motherOfAllSellPrices = manager.list()
motherOfAllUnderlying = manager.list()
currentExpiries = manager.list()
nadex = NadexSearch()
processIDs = manager.list()
queueList = []
riskFreeRates = {'AUD' : 0.0371, 'CAD' : 0.0225, 'CHF' : 0.0075, 'EUR': 0.0256, #This is incorrect. I don't know how to find the risk-free rate for the EU as a whole. I'm making the approximation that it's equal to the UK's.
				 'GBP' : 0.0256, 'JPY' : 0.0057, 'USD' : 0.0252}
ticketsOpen = -1
timeTracker = [[] for i in range(1,11)]

"""						PIPES						"""

optionConnectionParent = []
optionConnectionChild = []     #Later these are turned into arrays of pipes!
priceGatheringParent, priceGatheringChild = Pipe()
price_time_parent, price_time_child = Pipe()

"""						MAIN						"""

nadex.signIn()

nadex.mainMenu()
		
print("\nFinished.")

"""
                            THINGS TO CLEAN UP:
-Remove all globals and make them attributes of the class.
-Make all exceptions specify a type of exeption.
-Optimize the math in the options class.
-Look for an remove redundant/useless code.
-Conform to PEP 8 :(
-Push to git
"""

"""
							KNOWN BUGS:

# priceHistory() is broken: doesn't return times or underlying; prices stop being appended to the list after a short while.

							TO DO:

# Remove global variables and place them inside the class.

# Create a "process manager" class to control the processes.

# 

# Arbitrage!

# A function is needed to monitor working orders.

# A function is needed to monitor open positions.

"""
