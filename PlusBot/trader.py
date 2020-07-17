from redditwikiclass import RedditWikiClass
from source import Source
import re
from util import find_markdown_links, parse_markdown, get_sub, get_records_page


class Trader(RedditWikiClass):

    def __init__(self, username="", record=0, grlc=0, source=None, notes="", flags=None):
        sub = get_sub()
        self.username = username
        self.record = record
        self.grlc = grlc
        if source and sub.display_name in source:
            self.source = source
        else:
            self.source = '[' + username + ' Record](https://www.reddit.com/r/' + sub.display_name + '/wiki/' + self.get_wiki_id() + ')'
        self.notes = notes
        if not flags or 'generate_partners' in flags and flags['generate_partners'] == "True":
            try:
                if 'wiki' in source:
                    self.trade_partners = self.get_trade_partners_wiki()
                else:
                    self.trade_partners = self.get_trade_partners_links(self.source)
            except:
                self.trade_partners = {}
                pass
        else:
            self.trade_partners = {}

    def create_username(self, text):
        links = find_markdown_links(text)
        if links:
            for link in links:
                return link.group('label')
        usertag = re.search('((?<=/u/)|(?<=u/))([A-Za-z0-9_\-]*)', text)
        if usertag:
            return usertag.group(0)
        return text

    def get_trade_partners_wiki(self):
        profile_md = self.get_wiki().content_md
        return parse_markdown(profile_md, Source())

    def get_wiki(self):
        return get_sub().wiki[self.get_wiki_id()]

    def get_wiki_id(self):
        return get_records_page().name + '/' + self.username

    def get_trade_partners_links(self, source):
        links = find_markdown_links(source)
        partners = {}
        user = self.username
        if links:
            for link in links:
                trader_pair = link.group('label')
                traders = trader_pair.split(':')
                if traders[0] == user or traders[0] == 'B' or traders[0] == 'S':
                    partner = traders[1]
                else:
                    partner = traders[0]
                grlc = link.group('title')
                tag = self.get_tag(trader_pair, grlc)
                date = float(link.group('hash'))
                partners[partner] = Source(tag, partner, grlc, link.group(0), date)

        return partners

    def get_tag(self, pair, grlc):
        partners = pair.split(':')
        if self.username in pair:
            try:
                amount = float(grlc)
                if amount > 0:
                    if partners[0] == self.username:
                        return '[S]'
                    elif partners[1] == self.username:
                        return '[B]'
                else:
                    if partners[0] == self.username:
                        return '[B]'
                    elif partners[1] == self.username:
                        return '[S]'
                return 'N/A'
            except:
                return 'N/A'
        else:
            return partners[0]

    def add_record(self, trade=None):
        self.record = int(self.record) + int(trade)

    def add_grlc(self, amount=None):
        self.grlc = float(self.grlc) + float(amount)

    def create_from_wiki(self, row):
        username = ''
        record = '0'
        grlc = '0'
        source = ''
        notes = ''
        if row['Username']:
            username = row['Username'].strip()
        if row['Record']:
            record = row['Record'].strip()
        if row['GRLC']:
            grlc = row['GRLC'].strip()
        if row['Source']:
            source = row['Source'].strip()
        if row['Notes']:
            notes = row['Notes'].strip()
        new_t = Trader(username, record, grlc, source, notes, flags)
        return new_t

    def get_id(self):
        return self.username

    def __str__(self):
        return self.username + "|" + str(self.record) + "|" + str(self.grlc) + "|" + self.source + "|" + self.notes + "\n"
