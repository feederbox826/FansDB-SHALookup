# FansDB Scraper
This is a scraper for [FansDB](https://docs.fansdb.cc)

v24 Instructions:
- add the index address: `https://feederbox826.github.io/FansDB-SHALookup/main/index.yml` as a scraper source
- Install the following python modules with `pip install --user --break-system-packages NAME`
  - `emojis`
  - `requests`
  - `stashapp-tools`
- edit your config.py? 

v23 Instructions:
- Clone this repository or download the zip file from this page
- unpack into a folder inside your scraper folder
- make sure you have python setup and the 3 modules needed
    - `pip install -r requirements.txt` or follow the error messages if something is missing
- copy `config.py.example` to `config.py` and edit accordingly
    - configure the connection to stash (api key only needed if you enabled authentication to access stash, otherwise leave empty)
    - adjust the tags used to identify successful or failed scrapes
