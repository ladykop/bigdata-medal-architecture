import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

SOURCES = {
    "Hespress": {"url": "https://www.hespress.com", "t": "h1.post-title", "b": ".article-content p"},
    "CNN": {"url": "https://edition.cnn.com", "t": "h1.headline__text", "b": ".article__content p"},
    "BBC": {"url": "https://www.bbc.com/news", "t": "main h1", "b": "article p"}
}

def run_scraping():
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for name, config in SOURCES.items():
        try:
            res = requests.get(config['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Extracting titles based on the provided CSS selector, limiting to the top 5
            titles = soup.select(config['t'])[:5]
            for t in titles:
                results.append({
                    "title": t.text.strip(),
                    "source": name,
                    "scraped_at": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error {name}: {e}")
            
    with open("/opt/airflow/scripts/news_raw.json", "w") as f:
        json.dump(results, f)

if __name__ == "__main__":
    run_scraping()