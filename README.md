# FansDB Scraper
This is a scraper for [FansDB](https://docs.fansdb.xyz/)

To use:
- Clone this repository or download the zip file from this page
- unpack into a folder inside your scraper folder
- make sure you have python setup and the 3 modules needed
    - `pip install -r requirements` or follow the error messages if something is missing
- edit `config.py` or replace it with `config.py.example`
    - configure the connection to stash (api key only needed if you enabled authentication to access stash, otherwise leave empty)
    - adjust the tags used to identify successfull or failed scrapes
