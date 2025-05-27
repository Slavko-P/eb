from datetime import date, datetime, timedelta
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

# TODO make link management its own module
BASE_LINK = "https://www.kleinanzeigen.de"
# c = category, l = location, r = radius (km)
SEARCH_PARAMETERS = "/c192l9354r5"  # Verschenken/Freiburg/5km

# TODO type hints with mypy for static checking
# proper term instead of "link" might be "url"

# TODO get by page number, guard against fails
def get_ad_elements(page=1):
    link = BASE_LINK + "/seite:" + str(page) + SEARCH_PARAMETERS
    doc = requests.get(link).text
    soup = BeautifulSoup(doc, features='html.parser')
    return soup.select('.aditem')


def get_id(elem) -> str:
    id = elem.get("data-adid")
    if not id:
        # No ID found
        logger.error("No ID found")
        return None
    return id

class AdItem:
    def __get_id__(self, elem) -> str:
        id = elem.get("data-adid")
        if not id:
            # No ID found
            logger.error("AdItem: No ID found")
            return None
        return id

    def __get_title__(self, elem) -> str:
        elem_title = elem.select_one(".ellipsis")
        if not elem_title:
            # No title element found
            logger.error("AdItem: No title found")
            return None
        return elem_title.text

    def __get_pathname__(self, elem) -> str:
        pathname = elem.get("data-href")
        if not pathname:
            # No pathname found
            logger.error("AdItem: No pathname found")
            return None
        return pathname

    # Returns link to thumbnail image
    # Could be rewritten to return the full image,
    # without reloading the page (if needed)
    def __get_image_link__(self, elem) -> str:
        img_elem = elem.select_one("img")
        if not img_elem:
            # no image element found
            logger.info(f"AdItem: ID:{self.id} has no thumbnail")
            return None
        return img_elem.get("src")

    # Only works with up to date listings,
    # due to relative wording ("Heute", "Gestern")
    def __get_date__(self, elem):
        date_elem = elem.select_one(".aditem-main--top--right")
        if not date_elem:
            # No date element found
            logger.warning(f"AdItem: ID:{self.id} No date found")
            return None
        date_str = date_elem.text.strip()
        
        # Sponsored ads (Top-Anzeige) no date
        if not date_str:
            # No date string in date element
            logger.info(f"AdItem: ID:{self.id} No date found (sponsored ad)")
            return None

        # "Heute, HH:MM" and "Gestern, HH:MM" format
        try:
            day = date.today()
            time = datetime.strptime(date_str[-5:], "%H:%M").time()
            if date_str.startswith("G"): # Gestern
                # Get yesterday's date
                day -= timedelta(days=1)
            return datetime.combine(day, time)
        except ValueError:
            pass  # Fallback to other format

        # "DD.MM.YYYY" format
        try:
            # The website provides no time (HH:MM) information for this format
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            # Unknown date string format
            logger.warning(f"AdItem: ID:{self.id} Unknown date string format")
            return None

    # TODO Make string manipulation easier to read?
    def __get_area__(self, elem) -> str:
        area_elem = elem.select_one(".aditem-main--top--left")
        if not area_elem:
            # No area element found
            logger.warning(f"AdItem: ID:{self.id} No area found")
            return None
        # Removes extraneous spaces in cases of using radius
        raw_area = area_elem.text
        area = " ".join(raw_area.split())
        # Take out the proximity to city center
        # maybe make a trim() function that trims off the end after a specific
        # char
        return area.split("(", 1)[0]

    def __get_short_description__(self, elem) -> str:
        desc_elem = elem.select_one(".aditem-main--middle--description")
        if not desc_elem:
            # Short description not found
            logger.warning(f"AdItem: ID:{self.id} No short description found")
            return None
        return desc_elem.text.strip()

    def __init__(self, elem):
        self.id = self.__get_id__(elem)
        self.title = self.__get_title__(elem)
        self.pathname = self.__get_pathname__(elem)
        if not self.id or not self.title or not self.pathname:
            # This is not a valid .aditem element
            raise ValueError("Invalid aditem element")

        # Scraped from the main search page
        self.image_link = self.__get_image_link__(elem)
        self.area = self.__get_area__(elem)
        self.date = self.__get_date__(elem)
        self.short_description = self.__get_short_description__(elem)
        # Only set when requested by the user
        self.__full_description__ = None
        # views
        # product details (art, zustand, farbe, etc..)
        # maybe seller info

    @property
    def link(self) -> str:
        # saves a bit of space, I guess
        return BASE_LINK + self.pathname

    # TODO fix it up, and add more optional requestable data
    # be more data/space efficient by storing the new soup then parse the data
    # this is just a naive approach
    @property
    def full_description(self) -> str:
        if self.__full_description__:
            return self.__full_description__
        ad_page = requests.get(self.link).text
        soup = BeautifulSoup(ad_page, features="html.parser")
        self.__full_description__ = soup.select_one(
            "#viewad-description-text").get_text(separator="\n").strip()
        return self.__full_description__

    def __str__(self) -> str:
        return (f"ID: {self.id}\n"
                f"Title: {self.title}\n"
                f"Link: {self.link}\n"
                f"Image: {self.image_link}\n"
                f"Area: {self.area}\n"
                f"Date: {self.date}\n"
                f"Short description: {self.short_description}\n"
                )
