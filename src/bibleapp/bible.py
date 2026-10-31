# Simple script for scraping the verse of the day from Bible.com
import requests
from bs4 import BeautifulSoup
from bs4 import element
import urllib
from dataclasses import dataclass


def fetch_url_content(url: str) -> BeautifulSoup:
    """Uses a get request to fetch the content of an HTML page."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}")

    soup = BeautifulSoup(response.content, 'html.parser')
    return soup


def select_container(soup: BeautifulSoup, css_selector: str="div.mbs-4.mbe-6.rounded-8.border-l-large.border-contrast.px-2.py-2.ps-4") -> element.Tag:
    """Selects the container object with the verse of the day content"""
    container = soup.select_one(css_selector)
    if container is None:
        raise ValueError(f"CSS selector of {css_selector} not found.")
    return container


def extract_verse_content(container_tag: element.Tag) -> tuple[str, str]:
    """Returns a tuple of the verse text and reference from the link tags in the verse container"""
    text_list = [x.get_text(strip=True) for x in container_tag.find_all('a')]
    
    if len(text_list) != 2:
        raise ValueError(f"Expected two elements, found {len(text_list)}")
    
    if any (not text for text in text_list):
        raise ValueError("Verse text or reference text is empty.")
  
    verse, reference = text_list
    return verse, reference


def build_verse_url(base_url: str, container_tag: element.Tag) -> str:
    """Returns the absolute URL of the VOTD reference."""
    anchor = container_tag.find('a')
    if anchor is None:
        raise ValueError("No anchor tag found in the container.")
    
    verse_relative_url = anchor.get('href')
    if not verse_relative_url:
        raise ValueError("URL is None or empty")
    
    return urllib.parse.urljoin(base_url, verse_relative_url)  


@dataclass
class BibleVerse:
    text: str
    reference: str
    url: str   

    
def get_verse_of_the_day() -> BibleVerse:
    
    # Construct the URL
    base_url = 'https://www.bible.com/'
    lang = 'en-GB/'
    base_url_lang = urllib.parse.urljoin(base_url, lang)
    votd_landing_page_lang = urllib.parse.urljoin(base_url_lang, 'verse-of-the-day')
    
    # Fetch HTML and locate container
    page_content = fetch_url_content(votd_landing_page_lang)
    verse_container = select_container(page_content)
    
    # Get verse text, reference, link
    text, reference = extract_verse_content(verse_container)
    url = build_verse_url(base_url_lang, verse_container)
    
    # Assign to a BibleVerse object
    return BibleVerse(text, reference, url)


if __name__ == "__main__":
    votd = get_verse_of_the_day()
    print(f"The Bible.com verse of the day is:\n{votd.text}")
    print(f"\n{votd.reference}")
    print(f"\nAvailable from: {votd.url}")