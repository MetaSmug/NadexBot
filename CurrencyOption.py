from math import exp, log, sqrt, pi
from scipy.stats import norm
from multiprocessing import Process


class CurrencyOption:
    TWOPI = 2*pi
    riskFreeRates = {'AUD': 0.0371, 'CAD': 0.0225, 'CHF': 0.0075, 'EUR': 0.0256,
                     'GBP': 0.0256, 'JPY': 0.0057, 'USD': 0.0252}

    def __init__(self, name, buy, sell, exchangeRate, expireTime, indicative, pipe, buyHistory, sellHistory, underlyingHistory):

        self.name = name
        self.buyPrice = buy
        self.sellPrice = sell

        self.buyHistory = buyHistory
        self.sellHistory = sellHistory
        self.underlyingHistory = underlyingHistory

        self.expiry = expireTime
        self.doExpiry = None
        if isinstance(indicative, float):
            self.underlying = indicative
            self.doExpiry = True
        else:
            self.underlying = exchangeRate
            self.doExpiry = False
        self.updateProcess = Process(target=self.updateFields, args=(pipe))
        self.updateProcess.start()

        self.strike = float(name.split(" ")[-2].replace(">", ""))
        self.countries = [c for c in name.split(" ")[0].split("/")]
        self.conversionFactor = 1/self.underlying
        self.r_domestic = self.riskFreeRates[self.countries[0]]
        self.r_foreign = self.riskFreeRates[self.countries[1]]

        self.d1 = 0  # Will be set to correct value from function call below.
        self.d2 = 0
        self.d1Squared = 0
        self.d1d2 = 0
        self.d2Squared = 0
        self.volatility = self.calculateVolatility(0.05)

    def updateFields(self, pipe):
        """Updates the buy, sell, expire time, and underlying value for the option."""

        while self.doExpiry:
            self.sellPrice = pipe.recv()[0][-1]
            self.buyPrice = pipe.recv()[1][-1]
            self.expiry = pipe.recv()[2]
            self.underlying = pipe.recv()[3]

        while not self.doExpiry:
            self.buyPrice = self.buyHistory[-1]
            self.sellPrice = self.sellHistory[-1]
            self.underlying = self.underlyingHistory

    def convertUnits(self):
        """Returns the correct conversion factor, aka exchange rate, for the given currencies."""

        return 1.0/self.underlying

    def calculateVolatility(self, precision):
        """Calculates volatility using the bisection method on the Garman-Kohlhagen model.
        This function is also responsible for calculating d1 and d2.
        Unit problems have mostly been ironed out, but there may be some left."""

        low = 0.01
        high = 300.0

        while True:
            self.volatility = (high + low)/2.0

            self.d1 = ((log(self.underlying/self.strike) + (self.r_domestic - self.r_foreign + 0.5*self.volatility*self.volatility)*self.expiry) / (self.volatility*sqrt(self.expiry)))

            value = exp(-self.r_domestic*self.expiry)*norm.cdf(self.d1, 0, 1)*self.buyPrice*self.conversionFactor

            if (abs(self.buyPrice - value) <= precision) or (high <= 0.1) or (low >= 299.9):
                break
            elif value < self.buyPrice:
                low = self.volatility
            elif value > self.buyPrice:
                high = self.volatility

        self.d2 = self.d1 - self.volatility*sqrt(self.expiry)
        self.d1Squared = self.d1*self.d1
        self.d1d2 = self.d1*self.d2
        self.d2Squared = self.d2*self.d2

        return self.volatility

#   """  GREEKS      """

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
            return (-exp(-self.r_foreign * self.expiry - (self.d1Squared)/2) * self.underlying * self.volatility/(2*sqrt(self.TWOPI*self.expiry)))-(self.r_foreign*exp(-self.r_foreign*self.expiry)*norm.cdf(-self.d1))+(self.r_domestic*exp(self.r_domestic*self.expiry)*self.strike*norm.cdf(-self.d2))
        else:
            return (-exp(-self.r_foreign * self.expiry - (self.d1Squared)/2) * self.underlying * self.volatility/(2*sqrt(self.TWOPI*self.expiry)))+(self.r_foreign*exp(-self.r_foreign*self.expiry)*norm.cdf(self.d1))-(self.r_domestic*exp(self.r_domestic*self.expiry)*self.strike*norm.cdf(self.d2))

    def vega(self):
        """Derivative of value with respect to volatility."""

        return exp(-self.r_foreign * self.expiry - (self.d1Squared)/2)*self.underlying*sqrt(self.expiry/(self.TWOPI))

    def rho(self, short=False):
        """Derivative of value with respect to the interest rate."""

        if short:
            return -self.expiry * exp(-self.r_domestic*self.expiry) * self.strike * norm.cdf(-self.d2)
        else:
            return self.expiry * exp(-self.r_domestic*self.expiry) * self.strike * norm.cdf(self.d2)

    def gamma(self):
        """Derivative of delta with respect to underlying.
        Second Derivative of with value respect to underlying."""

        return exp(-self.r_foreign * self.expiry - (self.d1Squared)/2)/(self.underlying * self.volatility * sqrt(self.TWOPI*self.expiry))

    def vanna(self):
        """Derivative of delta with respect to volatility.
        Derivative of vega with respect to underlying.
        Second Derivative of value with respect once to underlying and volatility."""

        return -exp(-self.r_foreign * self.expiry - (self.d1Squared)/2) * self.d2 /(self.volatility * sqrt(self.TWOPI))

    def vomma(self):
        """Derivative of vega with respect to volatility.
        Second Derivative of value with respect to volatility."""

        return self.underlying * exp(-self.r_foreign * self.expiry - (self.d1Squared)/2) * sqrt(self.expiry) * self.d1d2 / self.volatility

    def speed(self):
        """Derivative of gamma with respect to underlying.
        Third Derivative of value with respect to underlying."""

        return -((exp(-self.r_foreign * self.expiry - (self.d1Squared)/2)/(self.underlying * self.volatility * sqrt(self.TWOPI*self.expiry)))/self.underlying) * (1 + self.d1/(self.volatility*sqrt(self.expiry)))

    def zomma(self):
        """Derivative of gamma with respect to volatility.
        Third Derivative of value with respect twice to underlying and once to volatility."""

        return (exp(-self.r_foreign * self.expiry - (self.d1Squared)/2)/(self.underlying * self.volatility * sqrt(self.TWOPI*self.expiry))) * ((self.d1d2 -1)/self.volatility)

    def ultima(self):
        """Derivative of vomma with respect to volatility.
        Third Derivative of value with respect to volatility."""

        return ((-exp(-self.r_foreign*self.expiry - self.d1Squared/2)*self.underlying*sqrt(self.expiry/self.TWOPI))/(self.volatility*self.volatility)) * (self.d1d2*(1 - self.d1d2) + self.d1Squared + self.d2Squared)
