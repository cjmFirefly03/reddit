import ConfigParser
import decimal
import os
import pickle
import re
import praw
from copy import deepcopy
from flair import Flair
from source import Source
from trader import Trader
from util import replace_markdown, create_table_markdown, format_millis_date, parse_markdown, initVariables, get_post, get_sub, get_records_page

try:
    # for Python 2.x
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIO
from datetime import datetime, timedelta
import itertools
import ConfigParser

# Set globals
config = ConfigParser.ConfigParser()
locations = [os.path.join(os.path.dirname(__file__), 'config.ini'), 'config.ini']
config.read(locations)
botUsername = config.get('DEFAULT', 'USERNAME')
clientSecret = config.get('DEFAULT', 'CLIENT_SECRET')
clientId = config.get('DEFAULT', 'CLIENT_ID')
botPassword = config.get('DEFAULT', 'PASSWORD')
postId = config.get('DEFAULT', 'POST_ID')

# Original Thread
# post_id = '7rxv0z'
# Jan-Feb 2018
# post_id = '7tr7ud'
# Mar 2018
# post_id = '81cu0t'

# post_ids
post_ids = ['81cu0t', '7tr7ud']

comment_verification_re = '(verify|verified|verifies|verifying|confirmed|confirming|confirm|confirms)'
flair_re = '((?P<trades>\d+) Verified)( \| (?P<garlic>\d+\.\d+) GRLC)*'

grlc_pre_re = '(Garlics|Garlic|Garlicoin|GRLC|G)'
grlc_amount_re = '[\.0-9]+\S*'
grlc_scrap_type_re = '(\\\?\[|\{)(?P<type>(S|B))(\\\?\]|\}).*'
grlc_scrap_type_user = '[^\r\n]*'
# username GRLC Number
grlc_scrap_1_re = '[^\r\n0-9]*(' + grlc_pre_re + '[ \t]*(?P<garlic>\d*\.?\d*[KM]*))'
# username Number GRLC
grlc_scrap_2_re = '[^\r\n0-9]*(?P<garlic>\d*\.?\d*[KM]*)[\t ]*' + grlc_pre_re
# GRLC Number username
grlc_scrap_3_re = grlc_pre_re + '[ \t]*(?P<garlic>\d*\.?\d*[KM]*)[^\r\n0-9]*'
# Number GRLC username
grlc_scrap_4_re = '(?P<garlic>\d*\.?\d*[KM]*)[\t ]*' + grlc_pre_re + '[^\r\n0-9]*'

grlc_scraps = [grlc_scrap_1_re, grlc_scrap_2_re]

REPLY_TEMPLATE = "Verification Acknowledged. +1 /u/{0}, +1 /u/{1}. This transaction has been recorded in the " \
                 "[/r/GarlicMarket records](https://www.reddit.com/r/GarlicMarket/wiki/records)"
COMMENT_LINK_TEMPLATE = "[{2}:{3}](https://www.reddit.com/comments/{0}//{1}#{5} \"{4}\") "
DUPLICATE_TEMPLATE = '**Alert**\r\n\r\n' \
                     'Another trade has already been recorded within 24 hours of this trade between ' \
                     '/u/{0} and /u/{1}: {2} ' \
                     'If you feel this is an error, please contact /u/I_regularly_lurk'


class Bot:

    def __init__(self, author_points, needs_updating=None):
        self.banned_users = get_banned_users()
        print(get_sub().display_name)
        # store new flair for user

        # get cache of authors and links awarded
        self.markdown = get_records_page().content_md
        print('Creating author points')
        self.author_points = author_points
        print('Finished creating author points')
        self.fieldnames = []
        self.keyValue = list()

        if needs_updating:
            self.new_user_flairs = {}
            self.needs_updating_trader_wiki = needs_updating
            for author in needs_updating:
                try:
                    user = self.author_points[author]
                    current_flair = next(get_sub().flair(author))
                    flair = self.create_get_flair(author, current_flair.get('flair_text'), current_flair.get('flair_css_class'))
                    flair.set_flair(user.record, user.grlc)
                    self.new_user_flairs[author] = flair
                except:
                    print('could not get flair for ' + author)
                    continue
        else:
            self.needs_updating_trader_wiki = set()
            self.new_user_flairs = {}
        self.verify_comments = []

    def create_get_wiki(self, username=None):
        if username in self.author_points:
            trader = self.author_points[username]
        else:
            trader = Trader(username)
        return trader

    def create_get_flair(self, username=None, flair_text="", flair_css=""):
        if username in self.new_user_flairs:
            flair = self.new_user_flairs[username]
        else:
            flair = Flair(username, flair_text, flair_css)
        return flair

    def in_key_values(self, parent, child):
        parent_author = parent.author.name
        child_author = child.author.name
        if [parent_author, child_author] in self.keyValue or [child_author, parent_author] in self.keyValue:
            return True
        return False

    def process_comment(self, parent, child, reply):
        parent_author = parent.author.name
        child_author = child.author.name
        previous_trade = is_trade_within_24_hours(self.author_points, parent_author, child_author, child.created_utc)
        if previous_trade:
            trade_source = previous_trade.source
            if parent.id not in trade_source:
                dup_reply = DUPLICATE_TEMPLATE.format(parent_author, child_author, trade_source)
                self.verify_comments.append({'comment': parent, 'reply': dup_reply})
        else:
            transaction = scrape_grlc(child_author, parent.body)

            if parent.edited and transaction:
                transaction['grlc'] = None

            # add comment
            self.verify_comments.append({'comment': parent, 'reply': reply})
            # update wiki entry
            self.process_wiki_comment(parent_author, child_author, parent.id, transaction, child.created_utc)

            # update flair
            self.process_flair_comment(parent_author, parent.author_flair_text, parent.author_flair_css_class,
                                       child_author, child.author_flair_text, child.author_flair_css_class)

    def process_wiki_comment(self, parent_author, child_author, comment_id, transaction=None, date=None):
        parent_wiki = self.create_get_wiki(parent_author)
        child_wiki = self.create_get_wiki(child_author)

        try:
            if transaction and 'type' in transaction:
                t_type = transaction['type']
                t_grlc = format_number(transaction['grlc'])
                if t_type.lower() == 's':
                    c_type = 'B'
                    c_grlc = t_grlc
                    p_grlc = "-"
                elif t_type.lower() == 'b':
                    c_type = 'S'
                    c_grlc = "-"
                    p_grlc = t_grlc
            else:
                c_type = "N/A"
                t_type = "N/A"
                c_grlc = "N/A"
                p_grlc = "N/A"

            parent_comment = COMMENT_LINK_TEMPLATE.format(get_post().id, comment_id, c_type, child_author, p_grlc, date)
            child_comment = COMMENT_LINK_TEMPLATE.format(get_post().id, comment_id, t_type, parent_author, c_grlc, date)
        except:
            pass
        self.process_wiki(parent_wiki, 1, c_type, child_author, p_grlc, parent_comment, date)
        self.process_wiki(child_wiki, 1, t_type, parent_author, c_grlc, child_comment, date)

    def process_wiki(self, trader, amount, tag, partner, grlc, comment=None, date=None):
        source = Source(tag, partner, grlc, comment, date)
        if source.get_id() not in trader.trade_partners:
            trader.trade_partners[source.get_id()] = source
            trader.add_record(amount)
            if grlc != '-' and grlc != 'N/A':
                trader.add_grlc(grlc)
            self.needs_updating_trader_wiki.add(trader.get_id())

        self.author_points[trader.get_id()] = trader

    def process_flair_comment(self, parent_author, parent_flair_text, parent_css_class,
                              child_author, child_flair_text, child_css_class):
        author_flair = self.create_get_flair(parent_author, parent_flair_text, parent_css_class)
        author_wiki = self.create_get_wiki(parent_author)
        child_flair = self.create_get_flair(child_author, child_flair_text, child_css_class)
        child_wiki = self.create_get_wiki(child_author)

        author_flair.set_flair(author_wiki.record, author_wiki.grlc)
        child_flair.set_flair(child_wiki.record, child_wiki.grlc)
        self.new_user_flairs[parent_author] = author_flair
        self.new_user_flairs[child_author] = child_flair

    def get_comments(self, comment_forest):
        comments = {}
        for comment in comment_forest:
            if self.is_comment_valid(comment) and (comment.author.name not in self.banned_users):
                author = str(comment.author.name).lower()
                if comments.get(author) is None:
                    comments[author] = [comment]
                else:
                    comments[author].append(comment)
        return comments

    def update_flair_reddit(self):
        batch_size = 100
        update_flairs = list(map((lambda x: x[1].get_dict()), self.new_user_flairs.items()))
        for chunk in chunked(update_flairs, batch_size):
            try:
                print(get_sub().flair.update(chunk))
            except:
                print('could not update flair IO Error')
                pass
        print('Finished updating flair')

    def update_wiki_reddit(self, reason):
        updated_text = self.update_wiki_record_summary(self.markdown)
        updated_text = self.update_wiki_totals(updated_text)

        get_records_page().edit(content=str(updated_text), reason=reason)
        print(reason)

    def update_wiki_record_summary(self, markdown):
        return replace_markdown(create_table_markdown(self.author_points, ['Username', 'Record', 'GRLC', 'Source', 'Notes']), markdown)

    def update_wiki_totals(self, markdown):
        unique_traders = 0
        grlc = 0
        trades = 0
        for author in self.author_points:
            a = self.author_points[author]
            unique_traders += 1
            trades += int(a.record)
            grlc += float(a.grlc)

        # we give credit to both traders so we must divide by 2 to find out how many trades have happened
        trades = trades / 2
        text = re.sub('GRLC recorded[\*]+:\d*\.?\d*', 'GRLC recorded***:' + str(grlc), markdown)

        print(str(grlc))
        text = re.sub('Trades[\*]+:\d*\.?\d*', 'Trades**:' + str(trades), text)

        print(str(trades))
        text = re.sub('Unique Traders[\*]+:\d*\.?\d*', 'Unique Traders**:' + str(unique_traders), text)

        print(str(unique_traders))
        return text

    def scan_comments(self, comments, add_comment=False, detect_dups=True):
        commentCounter = 0
        for comment in comments:
            commentCounter += 1
            if comment.is_root and self.is_comment_valid(comment) and (comment.author.name not in self.banned_users):
                matches = re.findall('((?<=/u/)|(?<=u/))([A-Za-z0-9_\-]*)', comment.body, re.UNICODE)
                commentCounter += matches.__len__()
                for group in matches:
                    for match in group:
                        if match:
                            feedbackuser = match.lower()
                            if feedbackuser != str(comment.author).lower():
                                comment.replies.replace_more()
                                child_comments = self.get_comments(comment.replies)
                                reply = REPLY_TEMPLATE.format(comment.author.name, feedbackuser)

                                # Check if bot has already recorded the transaction
                                trade_not_recorded = True
                                if detect_dups and botUsername.lower() in child_comments:
                                    for child_comment in child_comments[botUsername.lower()]:
                                        if is_string_equals_i(child_comment.body, reply) or '**Alert**' in child_comment.body:
                                            trade_not_recorded = False
                                            break

                                # Record transaction, no dupes
                                if trade_not_recorded and feedbackuser in child_comments:
                                    for child_comment in child_comments[feedbackuser]:
                                        confirmed = re.search(comment_verification_re, child_comment.body, re.IGNORECASE)
                                        if confirmed:  # and not self.in_key_values(comment, child_comment):
                                            self.process_comment(comment, child_comment, reply)
                                            break

        print("scanned " + str(commentCounter))

        if add_comment:
            print("replying to thread")
            for vc in self.verify_comments:
                vc['comment'].reply(vc['reply'])

    def is_comment_valid(self, comment):
        return not comment.banned_by and not comment.removed and comment.author

    def sync_flair_with_records(self, force_update=False):
        flair_update_necessary = False
        for author in self.author_points:
            trader = self.author_points[author]
            wiki_record = int(trader.record)
            wiki_grlc = float(trader.grlc)
            try:
                current_flair = next(get_sub().flair(author))
            except:
                print('could not get flair for ' + author)
                continue
            flair_text = current_flair.get('flair_text')
            flair_css = current_flair.get('flair_css_class')
            flair_amounts = get_amounts_from_flair(flair_text)
            flair_record = flair_amounts['trades']
            flair_grlc = flair_amounts['garlic']
            if flair_record:
                flair_record = int(flair_record)
            if flair_grlc:
                flair_grlc = float(flair_grlc)
            if not force_update and (wiki_record == flair_record and wiki_grlc == flair_grlc):
                continue
            else:
                flr = self.create_get_flair(author, flair_text, flair_css)
                flr.set_flair(wiki_record, wiki_grlc)
                self.new_user_flairs[author] = flr
                flair_update_necessary = True
                continue

        if flair_update_necessary:
            print("Syncing flairs with wiki " + get_records_page().name + " Last Updated: " + str(datetime.utcnow()))
            self.update_flair_reddit()

    def sync_trader_pages_with_records(self, update=set(), force_update=False):
        USER_TEMPLATE = '###{0}\r\n\r\n' \
                        '####Records\r\n{1}\r\n\r\n' \
                        '####Garlicoin\r\nSent {2} to other users\r\n\r\n' \
                        '####Sources\r\n\r\n' \
                        '{3}' \
                        '\r\n\r\n' \
                        '####Notes' \
                        '{4}'
        update_count = 0
        print('Beginning sync with author wikis')
        for author in self.author_points:
            if force_update or author in self.needs_updating_trader_wiki or author in update:
                trader = self.author_points[author]
                fieldnames = ['Trader', 'Tag', 'GRLC', 'Source', 'Date']
                user_template = USER_TEMPLATE.format(trader.username, trader.record, trader.grlc,
                                                     create_table_markdown(trader.trade_partners, ['Trader', 'Tag', 'GRLC', 'Source', 'Date']),
                                                     trader.notes)
                reason = 'Processed ' + trader.username + ' with ' + str(trader.record) + ' grlc: ' + str(trader.grlc)
                trader.get_wiki().edit(user_template, reason=reason)
                update_count += 1

            if update_count % 100 == 0 and update_count > 0:
                print('Synced ' + str(update_count) + ' wiki records')
        print('Finished syncing author wikis, updated ' + str(update_count) + '/' + str(len(self.author_points)) + ' records ')


# Helper methods
def set_entry(username=None, obj=None, dictionary=dict):
    dictionary[username] = obj


def is_string_equals_i(string, compare_string):
    return string.lower() == compare_string.lower()


def chunked(it, size):
    it = iter(it)
    while True:
        p = tuple(itertools.islice(it, size))
        if not p:
            break
        yield p


def get_amounts_from_flair(flair_text):
    if flair_text:
        search_flair = re.search(flair_re, flair_text)
        if search_flair:
            flair_amounts = re.search(flair_re, flair_text).groupdict()
            if 'garlic' not in flair_amounts:
                flair_amounts['garlic'] = 0
            if 'trades' not in flair_amounts:
                flair_amounts['trades'] = 0
            return flair_amounts
    return {'trades': 0, 'garlic': 0}


def get_banned_users():
    banned_users = []
    fetching_banned = True
    bus = get_sub().banned(limit=1000)
    for ban in bus:
         banned_users.append(ban.name)
    return banned_users


def scrape_grlc(child_author, comment_body):
    regex = grlc_scrap_type_re + child_author + grlc_scrap_type_user
    scrap = re.search(regex, comment_body, re.IGNORECASE)
    if scrap:
        trans_type = scrap.group('type')
        if trans_type:
            for i in range(0, grlc_scraps.__len__()):
                if i < 2:
                    pattern = child_author + grlc_scraps[i]
                else:
                    pattern = grlc_scraps[i] + child_author

                garlic = re.search(pattern, comment_body, re.IGNORECASE)
                if garlic:
                    grlc_str = garlic.group('garlic').lower()
                    try:
                        number = float(re.sub('[KM]+$', '', grlc_str, 10, re.IGNORECASE))
                        non_digits = re.findall('[\d\.]+([KM]+)', grlc_str, re.IGNORECASE)
                        unit_amount = None
                        for unit in non_digits:
                            if is_string_equals_i(unit, 'k'):
                                unit_amount = 10 ** 3
                                break
                            elif is_string_equals_i(unit, 'm'):
                                unit_amount = 10 ** 6
                                break
                        if unit_amount:
                            return {'type': trans_type, 'grlc': number * unit_amount}
                        return {'type': trans_type, 'grlc': number}
                    except ValueError:
                        print(grlc_str + ' ' + child_author + ' comment_body: ' + comment_body)
                        pass
    return None


def format_number(num):
    try:
        dec = decimal.Decimal(str(num))
    except:
        return 'N/A'
    tup = dec.as_tuple()
    delta = len(tup.digits) + tup.exponent
    digits = ''.join(str(d) for d in tup.digits)
    if delta <= 0:
        zeros = abs(tup.exponent) - len(tup.digits)
        val = '0.' + ('0'*zeros) + digits
    else:
        val = digits[:delta] + ('0'*tup.exponent) + '.' + digits[delta:]
    val = val.rstrip('0')
    if val[-1] == '.':
        val = val[:-1]
    if tup.sign:
        return '-' + val
    return val


def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb+') as f:
        pickle.dump(obj, f, 0)


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)


def is_trade_within_24_hours(author_points, parent_author, compare_partner, test_time):
    if parent_author in author_points:
        partners = author_points[parent_author].trade_partners
        filtered_dict = {k: v for k, v in partners.iteritems() if compare_partner in k}
        for partner in filtered_dict:
            original_time = datetime.utcfromtimestamp(partners[partner].date)
            compare_time = datetime.utcfromtimestamp(test_time)
            if (original_time - timedelta(hours=24)) <= compare_time <= (original_time + timedelta(hours=24)):
                return partners[partner]
    return False


def remove_duplicates_24_hours(author_points):
    update = set()
    for author in author_points:
        trade_partners = author_points[author].trade_partners
        unique_partners = {}
        fixed_partners = {}
        for partner in sorted(trade_partners.iterkeys(), key=lambda s: s.lower()):
            p = trade_partners[partner]
            if p.partner not in unique_partners:
                unique_partners[p.partner] = p.date
                fixed_partners[p.get_id()] = p
            else:
                test_p = unique_partners[p.partner]
                original_time = datetime.utcfromtimestamp(test_p)
                compare_time = datetime.utcfromtimestamp(p.date)
                update.add(author)
                if (original_time - timedelta(hours=24)) <= compare_time <= (original_time + timedelta(hours=24)):
                    print(author + ': Removed ' + p.partner + ' with date ' + format_millis_date(p.date) + ' entry exists. date: ' +
                          format_millis_date(test_p))
                    continue
                else:
                    fixed_partners[p.get_id()] = p
                    unique_partners[p.partner] = p.date

        new_grlc = 0
        for p in fixed_partners:
            t_grlc = format_number(fixed_partners[p].grlc)
            if t_grlc != 'N/A':
                new_grlc += float(t_grlc)
        author_points[author].trade_partners = fixed_partners
        author_points[author].record = len(fixed_partners)
        author_points[author].grlc = new_grlc
    return {'author_points': author_points, 'update': update}


def run(author_points=None, comments=None, **kwargs):
    if kwargs:
        add_comment = kwargs['ac']
        force_flair = kwargs['ff']
        force_wiki = kwargs['fw']
        detect_dups = kwargs['dd']
    else:
        add_comment = True
        force_flair = False
        force_wiki = False
        detect_dups = True

    print("Comment: " + str(add_comment) + " ForceFlair: " + str(force_flair) + " ForceWiki: " + str(force_wiki) + ' DetectDups: ' + str(detect_dups))
    copy_records = deepcopy(author_points)
    save_obj(copy_records, "original_records")
    save_obj(copy_records, "original_records_" + datetime.utcnow().strftime("%m_%d_%y"))
    fixed_authors = remove_duplicates_24_hours(author_points)
    fixed_points = fixed_authors['author_points']
    needs_update = fixed_authors['update']
    deep = deepcopy(fixed_points)
    bot = Bot(deep)
    bot.scan_comments(comments, add_comment=add_comment, detect_dups=detect_dups)

    bot.update_wiki_reddit("Updated trade records for /r/" + get_sub().display_name + " Last Updated: " + str(datetime.utcnow()))

    if force_flair:
        bot.sync_flair_with_records(force_update=True)
    else:
        bot.update_flair_reddit()
    bot.sync_trader_pages_with_records(update=needs_update, force_update=force_wiki)

    save_obj(bot.author_points, "current_records")


def sync_flair():
    bot = Bot(get_author_points())
    bot.sync_flair_with_records(True)


def get_author_points(pkl_name="current_records"):
    author_points = load_obj(pkl_name)
    if author_points:
        return author_points
    print('Generating author points')
    return parse_markdown(get_records_page().content_md, Trader())


def get_comments():
    print('Fetching comments')
    post = get_post()
    post.comment_sort = 'new'
    post.comments.replace_more(limit=None)
    print('Finished fetching ' + post.id + ' comments')
    return post.comments


def process_post(post_id, wiki_name, **kwargs):
    initVariables(post_id, wiki_name)
    comments = get_comments()
    if kwargs and kwargs['pf'] is not None:
        points = get_author_points(pkl_name=kwargs['pf'])
    else:
        points = get_author_points()
    print("Processing " + post_id + " thread")
    run(points, comments, **kwargs)


if __name__ == "__main__":
    r = praw.Reddit(user_agent="verification_script",
                    username=botUsername,
                    password=botPassword,
                    client_id=clientId,
                    client_secret=clientSecret
                    )
    anotherone = r.submission('89az64')
    records_page = r.subreddit(anotherone.subreddit.display_name).wiki['records']
