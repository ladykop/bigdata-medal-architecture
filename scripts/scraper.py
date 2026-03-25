import json
from kafka import KafkaProducer
import requests
from bs4 import BeautifulSoup

# Setup Kafka Producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def scrape_article(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extracting data points
    data = {
        "title": soup.find('h1').text if soup.find('h1') else None,
        "author": "Author Name", # Replace with actual selector
        "date_publication": "2026-03-25", # Replace with actual selector
        "content": soup.find('div', class_='content').text if soup.find('div', class_='content') else None,
        "source": "Hespress", 
        "url": url
    }
    
    # 1. Streaming Ingestion: Send to Kafka immediately 
    producer.send('news_topic', data)
    
    # 2. Batch Ingestion: Return for local Bronze storage
    return data

# Example usage
# scrape_article("https://www.hespress.com/example-article")