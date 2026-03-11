"""
scraper.py — Step 1
Scrapes the Promtior website and saves content to data/scraped_content.json
Usage: python scraper.py
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
import time

BASE_URL = "https://www.promtior.ai"
OUTPUT_FILE = "data/scraped_content.json"
MAX_PAGES = 30
REQUEST_DELAY = 1.0  # seconds between requests


def is_same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "head"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    return "\n".join(line for line in lines if line)


def scrape_website(base_url: str = BASE_URL, max_pages: int = MAX_PAGES) -> list[dict]:
    visited: set[str] = set()
    queue: list[str] = [base_url]
    results: list[dict] = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    session = requests.Session()
    session.headers.update(headers)

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue

        try:
            print(f"  Scraping: {url}")
            # Retry up to 3 times with backoff
            response = None
            for attempt in range(3):
                try:
                    response = session.get(url, timeout=20)
                    response.raise_for_status()
                    break
                except requests.RequestException as retry_err:
                    if attempt < 2:
                        print(f"  [RETRY {attempt+1}/3] {retry_err}")
                        time.sleep(3 * (attempt + 1))
                    else:
                        raise
            if response is None:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            text = clean_text(soup)

            if text:
                results.append({"url": url, "content": text})

            visited.add(url)

            # Collect internal links
            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                absolute = urljoin(url, href)
                # Remove fragments and query strings to avoid duplicate pages
                parsed = urlparse(absolute)
                clean = parsed._replace(fragment="", query="").geturl()
                if is_same_domain(clean, base_url) and clean not in visited:
                    queue.append(clean)

            time.sleep(REQUEST_DELAY)

        except requests.RequestException as e:
            print(f"  [WARN] Could not fetch {url}: {e}")

    return results


def main():
    os.makedirs("data", exist_ok=True)
    print(f"Starting scrape of {BASE_URL} (max {MAX_PAGES} pages)...")
    data = scrape_website()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nDone. Scraped {len(data)} pages → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
