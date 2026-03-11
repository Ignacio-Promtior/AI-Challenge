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
STORAGE_DIR = os.environ.get("STORAGE_DIR", ".")  # Railway: /app/storage, local: .
OUTPUT_FILE = os.path.join(STORAGE_DIR, "data", "scraped_content.json")
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
            "Mozilla/5.0 (compatible; PromtiorRAGBot/1.0; "
            "+https://github.com/AI-Challenge)"
        )
    }

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue

        try:
            print(f"  Scraping: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

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
    os.makedirs(os.path.join(STORAGE_DIR, "data"), exist_ok=True)
    print(f"Starting scrape of {BASE_URL} (max {MAX_PAGES} pages)...")
    data = scrape_website()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nDone. Scraped {len(data)} pages → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
