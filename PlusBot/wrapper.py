import sys
import bot
import os
import argparse

def strtobool(x):
    if x.lower() in ("yes", "y", "true", "t", "1"):
        return True
    elif x.lower() in ("no", "false", "n", "f", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected')

parser = argparse.ArgumentParser(description='Run Reddit Verification Bot')
parser.add_argument('-p', '--post-id', nargs='*', default=[], help='Reddit post id', required=True)
parser.add_argument('-rw', '--records-wiki', help='Name of Subreddit Wiki Record Page', required=True)
parser.add_argument('-pf', '--pickle-file', default=None, help='Name of pickle file that is used as db')
parser.add_argument('-ac', '--add-comment', nargs='?', type=strtobool, default=True,
                    help='If true, bot will reply to thread. (default: True)')
parser.add_argument('-ff', '--force-flair-update', nargs='?', type=strtobool, default=False,
                    help='If true, bot will update all flair. If false, bot only updates modified ones. (default: false)')
parser.add_argument('-fw', '--force-wiki-update', nargs='?', type=strtobool, default=False,
                    help='If true, bot will update all record pages - WARNING: this could take a while. '
                         'If false, bot only updates modified ones. (default: false)')
parser.add_argument('-dd', '--detect-dups', nargs='?', type=strtobool, default=True,
                    help='If true, bot will skip previously processed replies')
args = vars(parser.parse_args())

if args['post_id'] and args['records_wiki']:
    print(args)
    wikiName = args['records_wiki']
    addComment = args['add_comment']
    forceFlairUpdate = args['force_flair_update']
    forceWikiUpdate = args['force_wiki_update']
    detectDups = args['detect_dups']
    pickleFile = args['pickle_file']
    print(pickleFile)
    for pid in args['post_id']:
        bot.process_post(pid, wikiName, ac=addComment, ff=forceFlairUpdate, fw=forceWikiUpdate, dd=detectDups, pf=pickleFile)

