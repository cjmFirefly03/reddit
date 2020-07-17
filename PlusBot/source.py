from redditwikiclass import RedditWikiClass
from util import format_millis_date, format_date_millis


class Source(RedditWikiClass):

    def __init__(self, tag="", partner="", grlc=0, source="", date=float):
        self.tag = tag
        self.partner = partner
        self.grlc = grlc
        self.source = source
        self.date = date

    def create_from_wiki(self, row, flags={}):
        new_s = Source(row['Tag'].strip(), row['Trader'].strip(), row['GRLC'].strip(), row['Source'].strip(),
                       format_date_millis(row['Date'].strip()))
        return new_s

    def get_id(self):
        return self.partner + str(self.date)

    def __str__(self):
        return self.partner + "|" + self.tag + "|" + self.get_grlc() + "|" + self.source + "|" + format_millis_date(self.date) + "\n"

    def get_grlc(self):
        if self.grlc:
            return str(self.grlc)
        return "---"
