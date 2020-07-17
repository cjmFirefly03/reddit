import re

flair_re = '((?P<trades>\d+) Verified)( \| (?P<garlic>\d+\.\d+) GRLC)*'

FLAIR_TRADE_TEMPLATE = "{0} Verified"
FLAIR_GRLC_TEMPLATE = "{0} Verified | {1} GRLC"


class Flair(object):
    def __init__(self, username="", flair_text="", flair_css=""):
        self.username = username
        if flair_text:
            self.flairtext = flair_text
        else:
            self.flairtext = FLAIR_TRADE_TEMPLATE.format('0')
        if flair_css:
            self.cssclass = flair_css
        else:
            self.cssclass = ""

    def set_flair(self, trade=0, grlc=None):
        if 'Scammer' in self.flairtext or 'scammer' in self.cssclass:
            return
        try:
            grlc_temp = FLAIR_GRLC_TEMPLATE.format(str(trade), str(grlc))
            trade_temp = FLAIR_TRADE_TEMPLATE.format(str(trade))
            match = re.match(flair_re, self.flairtext)
            if (match and not match.group('trades') and not match.group('garlic')) or not match:
                if grlc and float(grlc) > 0:
                    self.flairtext = grlc_temp + ' | ' + self.flairtext
                else:
                    self.flairtext = trade_temp + ' | ' + self.flairtext
            else:
                if grlc and float(grlc) > 0:
                    self.flairtext = grlc_temp + re.sub(flair_re, '', self.flairtext)
                else:
                    self.flairtext = trade_temp + re.sub(flair_re, '', self.flairtext)

            self.cssclass = self.get_trade_css_class(trade)
        except:
            print(self.username + self.flairtext + str(trade) + str(grlc))
            pass

    def get_trade_css_class(self, trades):
        if 'scammer' in self.cssclass:
            return 'scammer'

        flair_class = "trade-t0"
        if trades >= 5:
            flair_class = "trade-t1"
        if trades >= 10:
            flair_class = "trade-t2"
        if trades >= 25:
            flair_class = "trade-t3"
        if trades >= 50:
            flair_class = "trade-t4"
        if trades >= 100:
            flair_class = "trade-t5"
        if trades >= 250:
            flair_class = "trade-t6"

        return flair_class

    def get_dict(self):
        return {'user': self.username, 'flair_text': self.flairtext, 'flair_css_class': self.cssclass}

    def __str__(self):
        return self.username + "," + self.flairtext + "," + self.cssclass + "\r\n"
