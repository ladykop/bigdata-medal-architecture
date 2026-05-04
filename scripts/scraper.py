import json
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

# Realistic browser headers — reduces bot-detection blocks
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/121.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


# ---------------------------------------------------------------------------
# RSS-based scraping (BBC, CNN, Al Jazeera, Reuters)
# ---------------------------------------------------------------------------

def scrape_rss_feed(rss_url, source, max_items=5):
    """
    Parse an RSS/Atom feed and return a list of article dicts.
    Much more reliable than HTML scraping for international outlets.
    """
    articles = []
    try:
        resp = requests.get(rss_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        # Use resp.content to let ET/BS handle encoding detection
        root = ET.fromstring(resp.content)

        # Handle both RSS <item> and Atom <entry> formats
        items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
        items = items[:max_items]

        for item in items:
            # Title
            title = (
                item.findtext('title')
                or item.findtext('{http://www.w3.org/2005/Atom}title')
                or ''
            ).strip()

            # Link
            link = (
                item.findtext('link')
                or (item.find('{http://www.w3.org/2005/Atom}link') or {}).get('href', '')
                or ''
            ).strip()

            # Content / description
            raw_content = (
                item.findtext('description')
                or item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded')
                or item.findtext('{http://www.w3.org/2005/Atom}summary')
                or item.findtext('{http://www.w3.org/2005/Atom}content')
                or ''
            )
            content = BeautifulSoup(raw_content, 'html.parser').get_text().strip()

            # Publication date
            pub_date = (
                item.findtext('pubDate')
                or item.findtext('{http://purl.org/dc/elements/1.1/}date')
                or item.findtext('{http://www.w3.org/2005/Atom}published')
                or ''
            )
            # Normalise date to YYYY-MM-DD
            date_str = pub_date[:10] if pub_date else None

            if title:
                articles.append({
                    'title': f"{source} RSS", # Source/Category as Title
                    'author': None,
                    'date_publication': date_str,
                    'content': title, # Headline as Content
                    'source': source,
                    'url': link,
                })

    except Exception as e:
        print(f"[WARNING] RSS failed for {source} ({rss_url}): {e}")

    return articles


# ---------------------------------------------------------------------------
# HTML-based scraping (Moroccan sources)
# ---------------------------------------------------------------------------

def scrape_homepage(url, source):
    """
    Scrape a news homepage and return one article dict representing the page.
    Tries multiple CSS selectors to extract a meaningful title and body.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        # Use resp.content instead of resp.text to allow BeautifulSoup 
        # to detect the correct encoding (e.g., UTF-8 for Arabic)
        soup = BeautifulSoup(resp.content, 'html.parser')

        # Remove nav, footer, scripts, styles so get_text() is cleaner
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        # Try progressively broader title selectors
        title = None
        for sel in ['h1', 'h2', '.article-title', '.post-title', '.entry-title', 'title']:
            el = soup.find(sel)
            if el and el.get_text(strip=True):
                title = el.get_text(strip=True)
                break
        title = title or url  # fall back to URL so record is never dropped

        # Try progressively broader content selectors
        content = None
        for sel in ['article', 'main', '.post-content', '.article-body', '.entry-content', 'body']:
            el = soup.find(sel)
            if el:
                text = el.get_text(separator=' ', strip=True)[:4000]
                if len(text) > 100:
                    content = text
                    break
        content = content or soup.get_text(separator=' ', strip=True)[:4000]

        return {
            'title': "Home", # Placeholder category
            'author': None,
            'date_publication': None,
            'content': title, # Headline as Content
            'source': source,
            'url': url,
        }

    except Exception as e:
        print(f"[WARNING] Failed to scrape {source} ({url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Main entry point: scrape ALL sources
# ---------------------------------------------------------------------------

def scrape_hespress(url):
    """
    Specialized scraper for Hespress to extract headlines from the '24 hours' widget.
    """
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Broader selector for the widget
        container = soup.select_one('ul.h24, ul.ss-container, .h24-b ul')
        
        if container:
            for li in container.find_all('li'):
                a = li.find('a')
                if a:
                    headline = a.get('title') or (a.find('h3').get_text(strip=True) if a.find('h3') else None)
                    link = a.get('href')
                    if not headline or not link: continue
                    if link.startswith('/'): link = "https://www.hespress.com" + link
                        
                    articles.append({
                        'title': "Hespress 24h", # Category as Title
                        'author': None,
                        'date_publication': None,
                        'content': headline, # Headline as Content
                        'source': 'Hespress',
                        'url': link,
                    })
        
        if not articles:
            fallback = scrape_homepage(url, 'Hespress')
            if fallback: 
                fallback['content'] = fallback['title']
                fallback['title'] = "Home"
                articles.append(fallback)
    except Exception as e:
        print(f"[WARNING] Hespress scrape failed: {e}")
    return articles


def scrape_akhbarona(url):
    """
    Refined scraper for Akhbarona with deduplication.
    """
    articles = []
    seen_urls = set() # To prevent duplicates
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Target ONLY top-level newspaper sections to avoid nested row duplication
        for section in soup.find_all('div', class_=re.compile(r'newspaper-\d')):
            # Find the category heading for THIS specific section
            category = "General"
            heading = section.find('div', class_='heading')
            if heading and heading.find('span'):
                category = heading.find('span').get_text(strip=True)

            # Find all news items in this category section
            # 1. Main boxes
            for box in section.find_all('div', class_='main-box'):
                a_tag = box.find('div', class_='main-box-text').find('a') if box.find('div', class_='main-box-text') else None
                if a_tag:
                    headline = a_tag.get_text(strip=True)
                    link = a_tag.get('href')
                    if link.startswith('/'): link = "https://www.akhbarona.com" + link
                    
                    if link not in seen_urls:
                        seen_urls.add(link)
                        articles.append({
                            'title': category,
                            'author': None,
                            'date_publication': None,
                            'content': headline,
                            'source': 'Akhbarona',
                            'url': link
                        })

            # 2. Side/List items
            for p in section.find_all('p', class_='pe-2'):
                a_tag = p.find('a')
                if a_tag:
                    headline = a_tag.get_text(strip=True)
                    link = a_tag.get('href')
                    if link.startswith('/'): link = "https://www.akhbarona.com" + link
                    
                    if link not in seen_urls:
                        seen_urls.add(link)
                        articles.append({
                            'title': category,
                            'author': None,
                            'date_publication': None,
                            'content': headline,
                            'source': 'Akhbarona',
                            'url': link
                        })
                
    except Exception as e:
        print(f"[WARNING] Akhbarona specific scrape failed: {e}")
    return articles


def scrape_barlamane(url):
    """
    Specialized scraper for Barlamane targeting common Moroccan news portal structures.
    """
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Barlamane usually uses entry-title for headlines
        for entry in soup.find_all(['h3', 'h2'], class_='entry-title'):
            a_tag = entry.find('a')
            if a_tag:
                headline = a_tag.get_text(strip=True)
                articles.append({
                    'title': "News", # Placeholder category
                    'author': None,
                    'date_publication': None,
                    'content': headline, # Headline as Content
                    'source': 'Barlamane',
                    'url': a_tag.get('href')
                })
    except Exception as e:
        print(f"[WARNING] Barlamane specific scrape failed: {e}")
    return articles


def scrape_all_sources():
    """
    Scrape all configured news sources.
    """
    results = []

    # 1. International sources via RSS
    rss_sources = [
        ("http://feeds.bbci.co.uk/news/rss.xml",          "BBC"),
        ("http://rss.cnn.com/rss/edition.rss",             "CNN"),
        ("https://www.aljazeera.com/xml/rss/all.xml",      "Al Jazeera"),
        ("https://feeds.reuters.com/reuters/topNews",       "Reuters"),
    ]

    for rss_url, source in rss_sources:
        articles = scrape_rss_feed(rss_url, source, max_items=5)
        print(f"[RSS]  {source:12s}: {len(articles)} articles")
        results.extend(articles)

    # 2. Moroccan sources (Specialized Scrapers)
    # Hespress
    hespress_articles = scrape_hespress("https://hespress.com/")
    print(f"[Web]  Hespress    : {len(hespress_articles)} articles")
    results.extend(hespress_articles)

    # Akhbarona
    akhbarona_articles = scrape_akhbarona("https://www.akhbarona.com/")
    print(f"[Web]  Akhbarona   : {len(akhbarona_articles)} articles")
    results.extend(akhbarona_articles)

    # Barlamane
    barlamane_articles = scrape_barlamane("https://barlamane.com/")
    print(f"[Web]  Barlamane   : {len(barlamane_articles)} articles")
    results.extend(barlamane_articles)

    return results


# ---------------------------------------------------------------------------
# Compatibility alias used by the Airflow DAG
# ---------------------------------------------------------------------------

def bdarch_scrape_article(url, source="Unknown"):
    """Single-URL alias kept for backward compatibility."""
    return scrape_homepage(url, source)