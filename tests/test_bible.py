from bs4 import BeautifulSoup
import pytest
from bibleapp.bible import (
    extract_verse_content,
    build_verse_url,
    select_container,
    BibleVerse,
    fetch_url_content,
    get_verse_of_the_day,
)
from unittest.mock import Mock, patch
import requests

################################################
########### extract_verse_content ##############
################################################

# The normal case
normal_dummy_html = """
<div>
    <a href="/bible/111/JHN.3.16.NIV">
        For God so loved the world...
    </a>
    <a href="/bible/111/JHN.3.16.NIV">
        John 3:16 (NIV)
    </a>
</div>
"""

def test_extract_verse_content_normal():
    soup = BeautifulSoup(normal_dummy_html, features='html.parser')
    container = soup.find('div')
    output = extract_verse_content(container)
    assert output == ('For God so loved the world...', 'John 3:16 (NIV)')

    
# Now test failure cases
one_anchor_dummy_html = """
<div>
    <a href="/bible/111/JHN.3.16.NIV">
        For God so loved the world...
    </a>
</div>
"""
one_anchor_expected_message = "Expected two elements, found 1"

empty_dummy_html = """
<div>
</div>
"""
no_anchor_expected_message = "Expected two elements, found 0"

three_anchor_dummy_html = """ 
<div>
    <a href="/bible/111/JHN.3.16.NIV">
        For God so loved the world...
    </a>
    <a href="/bible/111/JHN.3.16.NIV">
        John 3:16 (NIV)
    </a>
    <a>
    New International Version
    </a>
</div>
"""
three_anchor_expected_message = "Expected two elements, found 3"

first_anchor_empty_dummy_html = """
<div>
    <a>
    </a>
    <a href="/bible/111/JHN.3.16.NIV">
        John 3:16 (NIV)
    </a>
</div>
"""

second_anchor_empty_dummy_html = """
<div>
    <a href="/bible/111/JHN.3.16.NIV">
        For God so loved the world...
    </a>
    <a>
    </a>
</div>
"""

empty_anchor_expected_message = "Verse text or reference text is empty."

@pytest.mark.parametrize("test_input,expected_message",[
                             (one_anchor_dummy_html, one_anchor_expected_message),
                             (empty_dummy_html, no_anchor_expected_message),
                             (three_anchor_dummy_html, three_anchor_expected_message),
                             (first_anchor_empty_dummy_html, empty_anchor_expected_message),
                             (second_anchor_empty_dummy_html, empty_anchor_expected_message)],
                         ids=['one-anchor', 'no-anchor', 'three-anchors', 'first-anchor-empty', 'second-anchor-empty'])
def test_extract_verse_content_failures(test_input, expected_message):
    soup = BeautifulSoup(test_input, features='html.parser')
    container = soup.find('div')
    with pytest.raises(ValueError, match=expected_message):
        extract_verse_content(container)
        
        
################################################
########### build_verse_url ####################
################################################

normal_base_url = 'https://www.test.co.uk'

# Also check that it returns the first link given in a html container
normal_choose_first_dummy_html = """
<div>
    <a href="/bible/111/JHN.3.16.NIV">
        For God so loved the world...
    </a>
    <a href="/DO_NOT_RETURN_THIS">
        John 3:16 (NIV)
    </a>
</div>
"""

# Normal case
@pytest.mark.parametrize("test_input,expected_url", [
    (normal_dummy_html, 'https://www.test.co.uk/bible/111/JHN.3.16.NIV'),
    (normal_choose_first_dummy_html, 'https://www.test.co.uk/bible/111/JHN.3.16.NIV'),
    ],
    ids=['standard-case', 'two-diff-url-anchors'])
def test_build_verse_url_valid(test_input, expected_url):
    soup = BeautifulSoup(test_input, features='html.parser')
    normal_relative_anchor = soup.find('div')
    test_url = build_verse_url(normal_base_url, normal_relative_anchor)
    assert test_url == expected_url
    
    
# Failures
empty_url_html = """
<div>
    <a href="">
        For God so loved the world...
    </a>
</div>
"""

@pytest.mark.parametrize("test_input,expected_message", [
    (empty_dummy_html, "No anchor tag found in the container."),
    (first_anchor_empty_dummy_html, "URL is None or empty"),
    (empty_url_html, "URL is None or empty")
],
    ids=['no-anchor', 'missing-ref', 'empty-url'])
def test_build_verse_url_invalid(test_input,expected_message):
    soup = BeautifulSoup(test_input, features='html.parser')
    relative_anchor = soup.find('div')
    with pytest.raises(ValueError, match=expected_message):
        build_verse_url(normal_base_url, relative_anchor)
        
        
################################################
########### select_container ###################
################################################

normal_container_html = """
<div class="verse-container">For God so loved the world...</div>
<div class="other-container">This text should not be returned.</div>
"""

two_container_html = """
<div class="verse-container">First text</div>
<div class="verse-container">Second text</div>
"""

@pytest.mark.parametrize("test_input,expected_message", [
    (normal_container_html, "For God so loved the world..."),
    (two_container_html, "First text"),
], ids=["Normal case","Two containers"])
def test_success_select_container(test_input, expected_message):
    soup = BeautifulSoup(test_input, 'html.parser')
    css_selector = 'div.verse-container'
    result = select_container(soup, css_selector=css_selector)
    assert result.get_text(strip=True) == expected_message
    
no_container = """<div class="other-container">This text should not be returned.</div>"""

def test_no_container():
    soup = BeautifulSoup(no_container, 'html.parser')
    with pytest.raises(ValueError):
            select_container(soup, 'div.verse-container')
            
            
            

################################################
########### fetch_url_content ##################
################################################

test_url = "https://www.test.co.uk/verse-of-the-day"

@pytest.fixture
def mock_response():
    """Creates a successful mock HTTP response."""
    response = Mock()
    response.content = b"<html><body><p>Test verse</p></body></html>"
    response.raise_for_status.return_value = None
    return response


def test_fetch_url_content_success(mock_response):
    with patch("bibleapp.bible.requests.get", return_value=mock_response) as mock_get:
        result = fetch_url_content(test_url)

    assert isinstance(result, BeautifulSoup)
    assert result.find("p").get_text() == "Test verse"
    mock_get.assert_called_once_with(test_url, timeout=10)


@pytest.mark.parametrize("exception", [
    requests.exceptions.HTTPError("404 Not Found"),
    requests.exceptions.Timeout("Request timed out"),
    requests.exceptions.ConnectionError("Connection failed"),
], ids=["http-error", "timeout", "connection-error"])
def test_fetch_url_content_request_failures(exception):
    with patch("bibleapp.bible.requests.get", side_effect=exception):
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            fetch_url_content(test_url)


def test_fetch_url_content_http_status_failure():
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "500 Internal Server Error"
    )

    with patch("bibleapp.bible.requests.get", return_value=response):
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            fetch_url_content(test_url)



################################################
########### get_verse_of_the_day ###############
################################################

def test_get_verse_of_the_day_success():
    dummy_soup = BeautifulSoup(
        "<html><body><div>Test</div></body></html>",
        "html.parser"
    )
    dummy_container = dummy_soup.find("div")

    expected_verse = "For God so loved the world..."
    expected_reference = "John 3:16 (NIV)"
    expected_url = "https://www.bible.com/en-GB/bible/111/JHN.3.16.NIV"

    with (
        patch("bibleapp.bible.fetch_url_content", return_value=dummy_soup) as mock_fetch,
        patch("bibleapp.bible.select_container", return_value=dummy_container) as mock_select,
        patch("bibleapp.bible.extract_verse_content",
              return_value=(expected_verse, expected_reference)) as mock_extract,
        patch("bibleapp.bible.build_verse_url", return_value=expected_url) as mock_url,
    ):
        result = get_verse_of_the_day()

    assert isinstance(result, BibleVerse)
    assert result == BibleVerse(
        text=expected_verse,
        reference=expected_reference,
        url=expected_url,
    )

    mock_fetch.assert_called_once_with(
        "https://www.bible.com/en-GB/verse-of-the-day"
    )
    mock_select.assert_called_once_with(dummy_soup)
    mock_extract.assert_called_once_with(dummy_container)
    mock_url.assert_called_once_with(
        "https://www.bible.com/en-GB/",
        dummy_container,
    )


def test_get_verse_of_the_day_fetch_failure():
    with patch(
        "bibleapp.bible.fetch_url_content",
        side_effect=RuntimeError("Website unavailable"),
    ):
        with pytest.raises(RuntimeError, match="Website unavailable"):
            get_verse_of_the_day()
