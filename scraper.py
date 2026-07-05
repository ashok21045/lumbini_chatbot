"""
scraper.py
----------
Step 1: Scrape https://lict.edu.np/ and save the raw scraped data to data/raw_data.json

Strategy (in order of preference):
  1. Try the WordPress REST API (lict.edu.np/wp-json/wp/v2/pages & /posts) - fastest & cleanest.
  2. Crawl known/likely pages with requests + BeautifulSoup.
  3. If a page returns very little content (i.e. it needed JS to render), re-fetch it with Selenium.

Run:
    python scraper.py

Output:
    data/raw_data.json
"""

import json
import time
import re
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://lict.edu.np"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "raw_data.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Pages we already know exist on the site (from the nav menu).
# The crawler will ALSO auto-discover any other internal links from the homepage.
SEED_PATHS = [
    "/",
    "/about-us/",
    "/courses/",
    "/bsc-csit/",
    "/bca/",
    "/bim/",
    "/bhm/",
    "/our-team/",
    "/bod/",
    "/teaching-faculty/",
    "/visiting-faculty/",
    "/non-teaching-faculty/",
    "/syllabus/",
    "/bca-course/",
    "/bim-course/",
    "/gallery/",
    "/info-notice/",
    "/events/",
    "/ndtss/",
    "/qaa/",
    "/contact-us/",
]


def try_wp_api():
    """Try pulling structured content straight from the WordPress REST API."""
    results = []
    for endpoint in ("pages", "posts"):
        url = f"{BASE_URL}/wp-json/wp/v2/{endpoint}?per_page=100"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                items = resp.json()
                for item in items:
                    title = BeautifulSoup(
                        item.get("title", {}).get("rendered", ""), "html.parser"
                    ).get_text(strip=True)
                    content_html = item.get("content", {}).get("excerpt", "") or item.get(
                        "content", {}
                    ).get("rendered", "")
                    content_text = BeautifulSoup(content_html, "html.parser").get_text(
                        separator="\n", strip=True
                    )
                    link = item.get("link", "")
                    if content_text:
                        results.append(
                            {
                                "url": link,
                                "type": endpoint,
                                "title": title,
                                "raw_text": content_text,
                            }
                        )
                print(f"[WP-API] Pulled {len(items)} items from /{endpoint}")
        except Exception as e:
            print(f"[WP-API] {endpoint} failed: {e}")
    return results


def clean_text(soup: BeautifulSoup) -> str:
    """Remove nav/header/footer/script/style noise and return clean visible text."""
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form", "svg"]):
        tag.decompose()

    # Try to grab the main content region if the theme exposes one,
    # otherwise fall back to <body>.
    main = (
        soup.find("main")
        or soup.find(attrs={"id": "content"})
        or soup.find(attrs={"class": re.compile("content|entry-content|site-content", re.I)})
        or soup.body
        or soup
    )
    text = main.get_text(separator="\n", strip=True)
    # Collapse excess blank lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


def discover_links(html: str, base_url: str) -> set:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.netloc == urlparse(BASE_URL).netloc:
            # strip fragments/query for de-duplication
            clean = parsed._replace(query="", fragment="").geturl()
            links.add(clean)
    return links


def fetch_with_requests(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"[requests] Failed {url}: {e}")
    return None


def fetch_with_selenium(url: str):
    """Fallback for JS-rendered pages. Requires: pip install selenium webdriver-manager"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        driver.get(url)
        time.sleep(2)  # let JS render
        html = driver.page_source
        driver.quit()
        return html
    except Exception as e:
        print(f"[selenium] Failed {url}: {e}")
        return None


def scrape_page(url: str):
    html = fetch_with_requests(url)
    used_selenium = False

    # If the page came back suspiciously short, it was probably JS-rendered -> retry with Selenium
    if html:
        quick_text = BeautifulSoup(html, "html.parser").get_text(strip=True)
        if len(quick_text) < 200:
            selenium_html = fetch_with_selenium(url)
            if selenium_html:
                html = selenium_html
                used_selenium = True
    else:
        html = fetch_with_selenium(url)
        used_selenium = True

    if not html:
        return None, set()

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url
    text = clean_text(BeautifulSoup(html, "html.parser"))
    links = discover_links(html, url)

    return {
        "url": url,
        "type": "page",
        "title": title,
        "raw_text": text,
        "fetched_with": "selenium" if used_selenium else "requests",
    }, links


def crawl():
    visited = set()
    to_visit = set(urljoin(BASE_URL, p) for p in SEED_PATHS)
    results = []

    while to_visit:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)
        print(f"Scraping: {url}")
        page_data, new_links = scrape_page(url)
        if page_data and len(page_data["raw_text"]) > 30:
            results.append(page_data)
        # Only auto-expand crawl from the homepage/menu pages to avoid runaway crawling
        if len(visited) <= len(SEED_PATHS):
            for link in new_links:
                if link not in visited and len(visited) + len(to_visit) < 60:
                    to_visit.add(link)
        time.sleep(0.5)  # be polite

    return results


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    all_data = []

    print("== Step 1a: Trying WordPress REST API ==")
    api_data = try_wp_api()
    all_data.extend(api_data)

    print("\n== Step 1b: Crawling pages with requests/BeautifulSoup (Selenium fallback) ==")
    crawled_data = crawl()
    all_data.extend(crawled_data)

    # De-duplicate by URL
    seen = set()
    deduped = []
    for item in all_data:
        if item["url"] not in seen:
            seen.add(item["url"])
            deduped.append(item)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(deduped)} pages/posts to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
