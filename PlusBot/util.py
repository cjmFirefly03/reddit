import re
import csv
import praw
from pytz import timezone
from datetime import datetime
try:
    # for Python 2.x
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIO
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

r = praw.Reddit(user_agent="verification_script",
                username=botUsername,
                password=botPassword,
                client_id=clientId,
                client_secret=clientSecret
                )

regex = re.compile('(?!(?:\r\r|\n\n|\r\n\r\n)).*\n---\|---(.*(\n|\r\n|\r))*(\r\n\r\n|\n\n|\r\r)')

records_page = None
post = None
sub = None


def initVariables(pid, wiki_page_name):
    set_post(pid)
    set_sub()
    set_sub_wiki(wiki_page_name)


def set_post(pid):
    global post
    if post and post.id == pid:
        return post
    post = r.submission(id=pid)
    print(post)
    return post


def set_sub_wiki(wikiPageName):
    global records_page
    if records_page and records_page.name == wikiPageName:
        return records_page
    sub = get_sub()
    records_page = sub.wiki[wikiPageName]
    return records_page


def set_sub():
    global post, sub
    if post:
        sub = r.subreddit(post.subreddit.display_name)


def get_post():
    global post
    return post


def get_sub():
    global sub
    return sub


def get_records_page():
    global records_page
    return records_page


# markdown functions
def find_markdown_links(test_string):
    pattern = '(\[(?P<label>[^\[\]]+)\]\((?P<link>[^\)#"]+)(#(?P<hash>[^\)"]+))*("(?P<title>[^\)"]+)")*\))'
    return re.finditer(pattern, test_string)


# courtesy of twitch.tv/bamnet
def parse_markdown(markdown, object, flags=None):
    global fieldnames
    # match markdown table
    mdtable = regex.search(markdown)
    rows = {}
    if mdtable:
        table = mdtable.group(0)
        table = table.replace(' | ', '|').lstrip().rstrip()
        f = StringIO(table)
        reader = csv.DictReader(f, delimiter='|')
        fieldnames = reader.fieldnames
        for row in reader:
            not_table = row[reader.fieldnames[0]].strip()
            if not_table != '---':
                temp = object.create_from_wiki(row, flags=flags)
                rows[temp.get_id()] = temp
        return rows
    print("ripppp")
    return rows


def create_table_markdown(dictionary={}, fields=[]):
    global fieldnames
    newline = "\n"
    md = "|".join(str(x) for x in fields)
    md += newline
    md += "|".join('---' for x in fields)
    md += newline
    for entry in sorted(dictionary.iterkeys(), key=lambda s: s.lower()):
        e = str(dictionary[entry])
        md += e
    md += newline  # add 2nd newline
    md += newline  # add 3rd newline
    md += newline  # add 4th newline
    md += newline  # add 5th newline
    return md


def replace_markdown(replacement_md, md):
    replaced_md = regex.sub(replacement_md, md)
    f = open('wiki_text.txt', 'w')
    f.write(replaced_md)
    f.close()
    return replaced_md


def format_millis_date(timestamp):
    date = datetime.utcfromtimestamp(timestamp)
    return date.strftime("%m/%d/%y %H:%M:%S")


def format_date_millis(date):
    tz = timezone('UTC')
    date = datetime.strptime(date, "%m/%d/%y %H:%M:%S")
    dt_with_tz = tz.localize(date, is_dst=None)
    ts = (dt_with_tz - datetime(1970, 1, 1, tzinfo=tz)).total_seconds()
    return ts
