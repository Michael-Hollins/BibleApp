# Simple script to retrieve the verse of the day from BibleGateway
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import unquote


def fetch_bible_version_IDs() -> pd.DataFrame:
    """
    Fetches the language, version, and version ID of all available Bibles on BibleGateway.
    """
    base_url = 'https://www.biblegateway.com/usage/linking/versionslist/'
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch {base_url}: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    soup_rows = soup.find_all('tr')
    
    table = []
    current_language = None
    
    for row in soup_rows:
        cells = row.find_all(['td', 'th'])
        if not cells or cells[0].text.strip() == "Language":
            continue
        
        if cells[0].has_attr("rowspan") or len(cells) == 3:
            current_language = cells[0].text.strip()
            version = cells[1].text.strip()
            id_ = cells[2].text.strip()
        else:
            version = cells[0].text.strip()
            id_ = cells[1].text.strip()
            
        table.append({
            "language": current_language,
            "version": version,
            "id": id_
        })
    return pd.DataFrame(table)


def date_today() -> str:
    """Returns today's date in the format %m/%d"""
    return datetime.now().strftime('%m/%d')


def fetch_votd_link(date_today, version_id: str=None):
    """Fetches today's verse of the day link from Bible Gateway"""
    base_url = 'https://www.biblegateway.com/usage/votd/votdlist/'
    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch {base_url}: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    votd_link = None
    for row in soup.find_all('tr'):
        day_cell = row.find('td', class_='day')
        if day_cell and day_cell.text == date_today:
            link = row.find('a')
            if link:
                votd_link = link['href']
                
    if votd_link is None:
        raise ValueError(f'No verse found for {date_today}.')
                
    # Edit the version if desired
    if version_id:
        votd_link = re.sub(r'version=\d+', f'version={version_id}', votd_link)

    return votd_link


def fetch_bible_version_name_from_id(votd_link, version_id: str=None) -> str:
    """Returns the string of the Bible version associated with numeric ID"""
    all_bible_IDs = fetch_bible_version_IDs()
    
    if not version_id:
        version_id = re.search(r'version=(\d+)', votd_link).group(1)
    
    if type(version_id) == int:
        version_id = str(version_id)
    
    if version_id not in all_bible_IDs['id'].values:
        raise ValueError("Invalid ID. Try calling fetch_bible_version_IDs() to check.")
    else:
        return all_bible_IDs.loc[all_bible_IDs['id'] == version_id, 'version'].values[0]
    

def get_passage_text(biblegateway_link):
    """ 
    Parses the BibleGateway link to retrieve just the passage text.
    """
    try:
        response = requests.get(biblegateway_link, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch {biblegateway_link}: {e}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    passage_div = soup.find('div', class_='passage-text')
    if not passage_div:
        raise ValueError("Could not find passage-text div.")

    first_p = passage_div.find('p')
    if not first_p:
        raise ValueError("Could not find a paragraph in the passage.")
    
    verse_text = []
    for sup in first_p.find_all('sup'):
        sup.decompose()
    verse_text = first_p.get_text(strip=True, separator=' ')
    cleaned_text = re.sub(r'\([A-Z]\)', ' ', verse_text) # Remove footnote markers
    return cleaned_text   


def build_votd_display_text(votd_link, version_id: str=None):
    """ Combines the Bible passage, reference and version together into a string """
    passage_text = get_passage_text(votd_link)
    passage_reference = unquote(re.search(r'search=([^&]+)$', votd_link).group(1))
    bible_version = fetch_bible_version_name_from_id(votd_link=votd_link, version_id=version_id)
    return f'"{passage_text}"\n{passage_reference} ({bible_version})'
    

if __name__ == '__main__':
    VERSION_ID=47 #ESV
    target_date = date_today()
    votd_link = fetch_votd_link(date_today=target_date, version_id=VERSION_ID)
    votd_display = build_votd_display_text(votd_link, VERSION_ID)
    print(votd_display)
