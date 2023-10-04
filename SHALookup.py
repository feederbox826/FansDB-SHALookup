import json
import sys
import os
import hashlib
from datetime import datetime
from html import unescape
import re
from pathlib import Path

from config import stashconfig
VERSION = "0.0.2-relpath"

try:
    import requests
except ModuleNotFoundError:
    log.error("You need to install the requests module. (https://docs.python-requests.org/en/latest/user/install/)")
    log.error("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install requests")
    sys.exit()
try:
    from lxml import html
except ModuleNotFoundError:
    log.error("You need to install the lxml module. (https://lxml.de/installation.html#installation)")
    log.error("If you have pip (normally installed with python), run this command in a terminal (cmd): pip install lxml")
    sys.exit()
try:
    import stashapi.log as log
    from stashapi.stashapp import StashInterface
except ModuleNotFoundError:
    log.error("You need to install the stashapp-tools (stashapi) python module. (cmd): pip install stashapp-tools", file=sys.stderr)
    sys.exit()

# calculate sha256
def compute_sha256(file_name):
    hash_sha256 = hashlib.sha256()
    with open(file_name, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def sha_file(scene):
    try:
        return compute_sha256(scene['files'][0]['path'])
    except FileNotFoundError:
        try:
            log.debug(scene['files'][0]['path'])
            # try looking in relative path
            # move up two directories from /scrapers/SHALookup
            newpath = os.path.join(Path.cwd().parent.parent, scene['files'][0]['path'])
            return compute_sha256(newpath)
        except FileNotFoundError:
            log.error("File not found. Check if the file exists and is accessible.")
            sys.exit(1)

# get post
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0'
}

def getPostByHash(hash):
    res = requests.get('https://coomer.party/search_hash?hash=' + hash, headers=headers)
    if not res.status_code == 200:
        log.error(f"Request to '{url}' failed with status code {res.status}")
        return None
    tree = html.fromstring(res.text)
    article = tree.xpath('//article[1]/a')
    if (len(article) == 0):
        log.error("No post found for hash " + hash)
        return None
    link = article[0].get('href')
    return splitLookup(link, hash)

def splitLookup(path, hash):
    if (path.startswith('/fansly/')):
        return parseFansly(path, hash)
    else:
        return parseOnlyFans(path, hash)

def searchPerformers(scene):
    pattern = re.compile(r"@([\w\-\.]+)")
    content = unescape(scene['content'])
    # if title is truncated, remove trailing dots and skip searching title
    if scene['title'].endswith('..') and scene['title'].removesuffix('..') in content:
        searchtext = content
    else:
        # if title is unique, search title and content
        searchtext = scene['title'] + " " + content
    usernames = re.findall(pattern,unescape(searchtext))
    return usernames

def parseAPI(path):
    sceneres = requests.get('https://coomer.party/api' + path)
    if not sceneres.status_code == 200:
        log.error(f"Request to '{url}' failed with status code {sceneres.status}")
        sys.exit(1)
    scene = sceneres.json()[0]
    date = datetime.strptime(scene['published'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d')
    result = {}
    result['Title'] = scene['title'] if scene['title'] else date
    result['Details'] = unescape(scene['content'])
    result['Date'] = date
    result['Studio'] = {}
    result['Performers'] = []
    # parse usernames
    usernames = searchPerformers(scene)
    log.debug(usernames)
    for name in list(set(usernames)):
        name = name.strip('.') # remove trailing full stop
        result['Performers'].append({'Name': getnamefromalias(name)})
    # add studio in specific function
    return result, scene

# alias search
def getnamefromalias(alias):
    perfs = stash.find_performers( f={"aliases":{"value": alias, "modifier":"EQUALS"}}, filter={"page":1, "per_page": 5}, fragment= "name" )
    log.debug(perfs)
    if len(perfs):
        return perfs[0]['name']
    return alias

# if fansly
def parseFansly(path, hash):
    # fetch scene
    result, scene = parseAPI(path)
    # look up performer username
    performerres = requests.get(f"https://coomer.party/api/lookup/cache/{scene['user']}?service=fansly")
    if not performerres.status_code == 200:
        log.error(f"Request to '{url}' failed with status code {performerres.status}")
        sys.exit(1)
    username = performerres.json()['name']
    # craft fansly URL
    result['URL'] = f"https://fansly.com/post/{scene['id']}"
    # add studio and performer
    result['Studio']['Name'] = f"{username} (Fansly)"
    result['Performers'].append({ 'Name': getnamefromalias(username) })
    # Add trailer if hash matches preview
    for attachment in scene['attachments']:
        if 'preview' in attachment['name'] and hash in attachment['path']:
            result['Tags'] = [{}]
            result['Tags'][0]['Name'] = 'Trailer'
            break
    return result

# if onlyfans
def parseOnlyFans(path, hash):
    # fetch scene
    result, scene = parseAPI(path)
    log.debug(scene)
    username = scene['user']
    # craft OnlyFans URL
    result['URL'] = f"https://onlyfans.com/{scene['id']}/{username}"
    # add studio and performer
    result['Studio']['Name'] = f"{username} (OnlyFans)"
    result['Performers'].append({ 'Name': getnamefromalias(username) })
    return result

stash = StashInterface(stashconfig)
FRAGMENT = json.loads(sys.stdin.read())
SCENE_ID = FRAGMENT.get('id')
scene = stash.find_scene(SCENE_ID)
hash = sha_file(scene)
log.debug(hash)
#hash = "62502c1614d81da354a2cf1aa4a3ce60525c7cff4db648c8bbaaf686ba94fd52"
result = getPostByHash(hash)
print(json.dumps(result))
sys.exit(0)

# by Scruffy, feederbox826
# Last Updated