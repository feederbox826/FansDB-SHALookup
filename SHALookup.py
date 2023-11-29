import json
import sys
import os
import hashlib
from datetime import datetime
from html import unescape
import re
from pathlib import Path
from unicodedata import normalize
from confusables import remove

from config import stashconfig, success_tag, failure_tag
VERSION = "1.2.8"
MAX_TITLE_LENGTH = 64

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

# define stash globally
stash = StashInterface(stashconfig)

def getPostByHash(hash):
    shares = requests.get('https://coomer.su/api/v1/search_hash/' + hash, headers=headers, timeout=10)
    data = shares.json()
    if (shares.status_code == 404 or len(data) == 0):
        log.debug("No results found")
        return None
    # construct url to fetch from API
    post = data['posts'][0]
    path = f'https://coomer.su/api/v1/{post["service"]}/user/{post["user"]}/post/{post["id"]}'
    # fetch post
    postres = requests.get(path, headers=headers)
    if postres.status_code == 404:
        log.error("Post not found")
        sys.exit(1)
    elif not postres.status_code == 200:
        log.error(f"Request failed with status code {postres.status}")
        sys.exit(1)
    scene = postres.json()
    return splitLookup(scene, hash)

def splitLookup(scene, hash):
    if (scene['service'] == "fansly"):
        return parseFansly(scene, hash)
    else:
        return parseOnlyFans(scene, hash)

def searchPerformers(scene):
    pattern = re.compile(r"(?:^|\s)@([\w\-\.]+)")
    content = unescape(scene['content'])
    # if title is truncated, remove trailing dots and skip searching title
    if scene['title'].endswith('..') and scene['title'].removesuffix('..') in content:
        searchtext = content
    else:
        # if title is unique, search title and content
        searchtext = scene['title'] + " " + content
    usernames = re.findall(pattern,unescape(searchtext))
    return usernames

# from dolphinfix
def truncate_title(title, max_length):
    # Check if the title is already under max length
    if len(title) <= max_length:
        return title
    # Find the last space character before max length
    last_space_index = title.rfind(" ",0, max_length)
    # truncate at last_space_index if valid, else max_length
    title_end = last_space_index if last_space_index != -1 else max_length
    return title[:title_end]

def normalize_title(title):
    normalized = normalize("NFKD", title)
    unconfused = remove(normalized)
    return unconfused.strip()

# from dolphinfix
def format_title(description, username, date):
    firstline = description.split("\n")[0].strip().replace("<br />", "")
    formatted_title = truncate_title(
        normalize_title(firstline), MAX_TITLE_LENGTH
    )
    if not len(description): # no description, return username and date
        return username + " - " + date
    elif len(formatted_title) <= 5: # title too short, add date
        return formatted_title + " - " + date
    elif not bool(re.search("[A-Za-z0-9]", formatted_title)): # textless, truncate and add date
        # decrease MAX_TITLE_LENGTH further to account for " - YYYY-MM-DD"
        return truncate_title(formatted_title, MAX_TITLE_LENGTH - 13) + " - " + date
    else:
        return formatted_title

def parseAPI(scene, hash):
    date = datetime.strptime(scene['published'], '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d')
    result = {}
    scene['content'] = unescape(scene['content']).replace("<br />", "\n")
    # title parsing
    result['Details'] = scene['content']
    result['Date'] = date
    result['Studio'] = {}
    result['Performers'] = []
    result['Tags'] = []
    # parse usernames
    usernames = searchPerformers(scene)
    log.debug(usernames)
    for name in list(set(usernames)):
        name = name.strip('.') # remove trailing full stop
        result['Performers'].append({'Name': getnamefromalias(name)})
    # figure out multi-part scene
    # create array with file and attachments
    if (scene['file']):
        files = [scene['file']] + scene['attachments']
    else:
        files = scene['attachments']
    # only include videos
    files = [file for file in files if file['path'].endswith(".m4v") or file['path'].endswith(".mp4")]
    for i, file in enumerate(files):
        if hash in file['path']:
            scene['part'] = i + 1
    scene['total'] = len(files)
    # add studio in specific function
    return result, scene

# alias search
def getnamefromalias(alias):
    perfs = stash.find_performers( f={"aliases":{"value": alias, "modifier":"EQUALS"}}, filter={"page":1, "per_page": 5}, fragment= "name" )
    log.debug(perfs)
    if len(perfs):
        return perfs[0]['name']
    return alias

def getFanslyUsername(id):
    res = requests.get(f"https://coomer.su/fansly/user/{id}", headers=headers)
    if not res.status_code == 200:
        log.error(f"Request failed with status code {res.status}")
        sys.exit(1)
    tree = html.fromstring(res.text)
    userbox = tree.xpath('//*[@id="user-header__info-top"]/a/span[2]')
    if (len(userbox) == 0):
        log.error("No user found for id " + id)
        return None
    return userbox[0].text

# if fansly
def parseFansly(scene, hash):
    # fetch scene
    result, scene = parseAPI(scene, hash)
    # look up performer username
    username = getFanslyUsername(scene['user'])
    result['Title'] = format_title(result['Details'], username, result['Date'])
    # add part on afterwards
    if scene['total'] > 1:
        result['Title'] += f" {scene['part']}/{scene['total']}"
    # craft fansly URL
    result['URL'] = f"https://fansly.com/post/{scene['id']}"
    # add studio and performer
    result['Studio']['Name'] = f"{username} (Fansly)"
    result['Performers'].append({ 'Name': getnamefromalias(username) })
    # Add trailer if hash matches preview
    for attachment in scene['attachments']:
        if 'preview' in attachment['name'] and hash in attachment['path']:
            result['Tags'].append({ "Name": 'Trailer' })
            break
    return result

# if onlyfans
def parseOnlyFans(scene, hash):
    # fetch scene
    result, scene = parseAPI(scene, hash)
    username = scene['user']
    result['Title'] = format_title(result['Details'], username, result['Date'])
    # add part on afterwards
    if scene['total'] > 1:
        result['Title'] += f" {scene['part']}/{scene['total']}"
    # craft OnlyFans URL
    result['URL'] = f"https://onlyfans.com/{scene['id']}/{username}"
    # add studio and performer
    result['Studio']['Name'] = f"{username} (OnlyFans)"
    result['Performers'].append({ 'Name': getnamefromalias(username) })
    return result

def scrape():
    FRAGMENT = json.loads(sys.stdin.read())
    SCENE_ID = FRAGMENT.get('id')
    nomatch_id = stash.find_tag(failure_tag, create=True).get('id')
    success_id = stash.find_tag(success_tag, create=True).get('id')
    scene = stash.find_scene(SCENE_ID)
    if not scene:
        log.error("Scene not found - check your config.py file")
        sys.exit(1)
    # log.debug(scene)
    alltags = [tag["id"] for tag in scene["tags"]]
    if nomatch_id in alltags or success_id in alltags:
        log.debug("Already searched, skipping")
        return None
    hash = sha_file(scene)
    log.debug(hash)
    result = getPostByHash(hash)
    # if no result, add "SHA: No Match tag"
    if (result == None):
        stash.update_scenes({
            'ids': [SCENE_ID],
            'tag_ids': {
                'mode': 'ADD',
                'ids': [nomatch_id]
            }
        })
        return None
    # if result, add tag
    result['Tags'].append({ 'Name': success_tag })
    return result

def main():
    try:
        result = scrape()
        print(json.dumps(result))
        log.exit("Plugin exited normally.")
    except Exception as e:
        log.error(e)
        log.exit("Plugin exited with an exception.")

if __name__ == '__main__':
    main()

# by Scruffy, feederbox826
# Last Updated 2023-11-02