import atexit
from collections import deque
import time
import pickle
import random
import logging

from bs4 import BeautifulSoup
from unidecode import unidecode
import requests

import scraper

# TODO write debug logs like "reloaded page, found x new entries", etc

# TODO make link management its own module
BASE_LINK = "https://www.kleinanzeigen.de"
# c = category, l = location, r = radius (km)
SEARCH_PARAMETERS = "/c192l9354r5"  # Verschenken/Freiburg/5km

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# TODO get by page number, guard against fails
def get_ad_elements(page=1):
    link = BASE_LINK + "/seite:" + str(page) + SEARCH_PARAMETERS
    doc = requests.get(link).text
    soup = BeautifulSoup(doc, features='html.parser')
    return soup.select('.aditem')


keywords = ["küche", "ofen", "herd", "spüle"]
# TODO needs way more work
# External keyword list
# Maybe (optionaly) indicate which keyword hit and where
def keyword_check(ad):
    # check keywords in title AND (short) description
    for k in keywords:
        # ignore case
        # remove accents
        k = unidecode(k.lower())
        if (k in unidecode(ad.title.lower())) or (k in unidecode(ad.short_description.lower())):
            return True
    return False

# TODO make it look nicer
def main():
    # maxlen 30 to avoid an evergrowing list 
    # and avoid repeat notifications
    seen_ids = deque(maxlen=30)
    try:
        # load previous seen IDs if available
        seen_ids += pickle.load(open("seen_ids.p", "rb"))
        logging.info("Loaded seen IDs file from a previous session")
    except FileNotFoundError:
        # start new seen IDs list
        logging.info("File 'seen_ids.p' not found, creating new list..")

    # test if atexit works on exception exits
    atexit.register(pickle.dump, seen_ids, open("seen_ids.p", "wb"))
    while True:
        found = 0
        logging.info("main(): Loop start..")
        for ad_elem in get_ad_elements():
            ad_id = scraper.get_id(ad_elem)
            if ad_id not in seen_ids:
                seen_ids.append(ad_id)
                found += 1                

                print(f"Found and checking ad item ID:{ad_id}..")
                if keyword_check(scraper.AdItem(ad_elem)):
                    print("Found match in:\n" + str(ad))
        logging.info(f"Found {found} new ad items since last check")
        pickle.dump(seen_ids, open("seen_ids.p", "wb"))
        rand_wait = random.randint(2 * 60, 3 * 60) # 2-3 min
        logging.info(f"Waiting for {rand_wait}s (~{rand_wait / 60:.2f}m)")
        time.sleep(rand_wait)


if __name__ == '__main__':
    main()
