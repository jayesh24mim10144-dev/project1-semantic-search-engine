import requests
from bs4 import BeautifulSoup
import redis
from sentence_transformers import SentenceTransformer
import json
from urllib.parse import urljoin
import time
from pymongo import MongoClient

# Load embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Redis connection
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# MongoDB connection
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["search_engine"]
pages_collection = db["pages"]

def get_page_content(url):
    """Fetch and parse a webpage."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MiniSearchBot/0.1; +https://example.com/bot)"
        }
        response = requests.get(url, timeout=10, headers=headers)
        if response.status_code == 200 and "text/html" in response.headers.get("Content-Type", ""):
            return response.text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
    return None

def extract_about(soup):
    """Extract description or about content."""
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        return desc["content"]

    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        return og_desc["content"]

    p = soup.find("p")
    if p:
        return p.get_text().strip()

    return ""

def process_page(url, html):
    """Extract useful data from page and store it."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title else ""
    about = extract_about(soup)
    vector = model.encode(about).tolist() if about else []

    # Collect outgoing links
    outgoing_links = []
    for link in soup.find_all("a", href=True):
        new_url = urljoin(url, link["href"]).split("#")[0]
        if new_url.startswith("http"):
            outgoing_links.append(new_url)
            # Add to Redis queue if not already visited
            if not r.sismember("visited_urls", new_url):
                r.lpush("to_crawl", new_url)

            # Register backlink
            r.hset(f"backlinks:{new_url}", url, 1)

    # Collect backlinks for this page
    backlinks = list(r.hkeys(f"backlinks:{url}"))

    # Store in MongoDB
    page_data = {
        "url": url,
        "title": title,
        "about": about,
        "vector": vector,
        "outgoing_links": outgoing_links,
        "backlinks": backlinks,
        "timestamp": time.time(),
    }
    pages_collection.update_one({"url": url}, {"$set": page_data}, upsert=True)
    print(f"Successfully Stored: {url}")

def crawler_loop():
    """Run indefinitely until terminated."""
    while True:
        url = r.lpop("to_crawl")
        if not url:
            print("No URLs left, waiting...")
            time.sleep(5)
            continue

        if r.sismember("visited_urls", url):
            continue

        html = get_page_content(url)
        if not html:
            continue

        process_page(url, html)
        r.sadd("visited_urls", url)
        time.sleep(1)  # polite delay

if __name__ == "__main__":
    # Seed URLs if Redis queue is empty
    if r.llen("to_crawl") == 0:
        seeds = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://wikileaks.org/",
            "https://annas-archive.org/search?q=",
            "https://archive.org",
            "https://archive.org/details/audio_music",
            "https://archive.org/details/internetarchivebooks",
            "https://archive.org/details/youtubecrawl",
            "https://stackoverflow.com/questions",
            "https://www.quora.com/What-is-artificial-intelligence-15",
        ]
        for seed in seeds:
            r.rpush("to_crawl", seed)

    crawler_loop()

