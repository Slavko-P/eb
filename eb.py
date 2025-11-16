# TODO USE POSTGRES DATABASE ON RENDER.COM TO STORE SEEN IDs

import atexit
from collections import deque
import time
import pickle
import random
import logging
import asyncio
import os

from bs4 import BeautifulSoup
from unidecode import unidecode
import requests
import apprise

import scraper


# TODO log timestamps
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ad option to replace ü with ue and so on
keywords = ["ofen", "herd", "miele", "bosch", "siemens", "solar", "gpu", "grafikkarte", "pc", "playstation", "ps", "xbox", "wii", "nintendo"]
# TODO needs way more work
# External keyword list with auto update with reloading program
# Maybe (optionaly) indicate which keyword hit and where
# Make a more accurate detector (like having the words stand alone)
# i.e. notify me for "herd" but not "Herden"
def keyword_check(ad):
    # check keywords in title AND (short) description
    for k in keywords:
        # ignore case
        # remove accents
        k = unidecode(k.lower())
        if (k in unidecode(ad.title.lower())):
            return True
    return False

# TODO make it look nicer
def main():
    apobj = apprise.Apprise()
    # Linux desktop
    apobj.add("dbus://")
    apobj.add("ntfy://eb_scraper")
    # my Telegram
    apobj.add(os.environ.get("TGRAM", None))
    # DOESNT WORK BUT SAYS THE NOTIF IS SENT, FIND OUT WHY
    # notify(title="super duper secret message", body="Hi")
    # a page worth (25) + 5 in case some ads gets removed then put back
    # TEST IF OrderedDict/Dict is better for this use case
    seen_ids = deque(maxlen=50)
    try:
        # load previous seen IDs if available
        with open("seen_ids.p", "rb") as f:
            seen_ids += pickle.load(f)
        logging.info("Loaded seen IDs file from a previous session.")
    except FileNotFoundError:
        # start new seen IDs list
        logging.info("File 'seen_ids.p' not found, a new file will be created.")

    # test if atexit works on exception exits
    # atexit.register(pickle.dump, seen_ids, open("seen_ids.p", "wb"))
    while True:
        found = 0
        logging.info("Checking for new ad listings..")
        for ad_elem in scraper.get_ad_elements():
            ad_id = scraper.get_id(ad_elem)
            if ad_id not in seen_ids:
                seen_ids.append(ad_id)
                found += 1                
                ad = scraper.AdItem(ad_elem)
                logging.info(f"New item: '{ad.title}' ({ad.id})")
                if keyword_check(ad):
                    logging.info(f"Found match in: {ad_id}.")
                    # apobj.notify(title="FOUND MATCH", body=f"Found: '{ad.title}' ({ad.id})\n{ad.link}")
                    apobj.notify(title=f"{ad.title} ({ad.id})", body=f"{ad.link}")
        logging.info(f"Found {found} new ad item(s) since last check.")
        # in case of unexpected exit afterwards
        with open("seen_ids.p", "wb") as f:
            pickle.dump(seen_ids, f)

        rand_wait = random.randint(2 * 60, 4 * 60) # 2-4 min
        logging.info(f"Waiting for {rand_wait}s (~{rand_wait / 60:.2f}m).")
        time.sleep(rand_wait)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(" User exited the program via keyboard interrupt")
