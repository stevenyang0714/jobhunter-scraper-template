"""
scrapers/linkedin_scraper.py
==============================
LinkedIn public job listing scraper.
Uses the LinkedIn guest jobs API — no login required.
"""
import time
import random
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Job:
    id:           str
    title:        str
    company:      str
    location:     str
    description:  str
    url:          str
    source:       str
    posted_date:  str
    industry_tag: Optional[str] = None
    match_score:  float = 0.0


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# LinkedIn geography codes for major APAC / Middle East cities
GEO_CODES = {
    "Singapore":    "102454443",
    "Hong Kong":    "103291313",
    "Taiwan":       "104187078",
    "China":        "102890883",
    "Dubai":        "106204383",
    "Abu Dhabi":    "101041765",
    "Saudi Arabia": "103621737",
    "Japan":        "101355337",
    "South Korea":  "105149562",
    "Malaysia":     "103685314",
    "Thailand":     "103013785",
    "Global/Remote":"",
}


def scrape_linkedin(keyword: str, geo: str, days_ago: int = 1) -> list:
    """
    Scrape LinkedIn public job listings for a keyword × geography combination.

    Returns a list of Job objects.
    """
    geo_id   = GEO_CODES.get(geo, "")
    time_filter = f"r{days_ago * 86400}"   # LinkedIn uses seconds

    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": keyword,
        "location": geo,
        "geoId":    geo_id,
        "f_TPR":    time_filter,
        "f_E":      "4,5",           # Experience levels: Mid-Senior, Director
        "start":    "0",
    }

    query_string = "&".join(
        f"{k}={requests.utils.quote(str(v))}"
        for k, v in params.items()
        if v  # skip empty values
    )
    url = f"{base_url}?{query_string}"

    jobs: list = []

    try:
        # Polite delay to avoid rate limiting
        time.sleep(random.uniform(1.5, 3.5))

        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 429:
            print(f"  ⚠  LinkedIn rate limit hit — skipping {keyword}/{geo}")
            return jobs
        if response.status_code != 200:
            return jobs

        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("div", class_="base-card")[:15]  # max 15 per query

        for card in cards:
            try:
                title_el   = card.find("h3", class_="base-search-card__title")
                company_el = card.find("h4", class_="base-search-card__subtitle")
                location_el= card.find("span", class_="job-search-card__location")
                link_el    = card.find("a", class_="base-card__full-link")
                time_el    = card.find("time")

                if not title_el or not link_el:
                    continue

                job_url  = link_el.get("href", "").split("?")[0]
                job_id   = f"li_{job_url.rstrip('/').split('/')[-1]}"
                title    = title_el.get_text(strip=True)
                company  = company_el.get_text(strip=True) if company_el else "Unknown"
                location = location_el.get_text(strip=True) if location_el else geo
                posted   = time_el.get("datetime", str(datetime.today().date())) if time_el else str(datetime.today().date())

                jobs.append(Job(
                    id          = job_id,
                    title       = title,
                    company     = company,
                    location    = location,
                    description = f"{title} at {company} — {keyword} role in {geo}",
                    url         = job_url,
                    source      = "LinkedIn",
                    posted_date = posted,
                ))

            except Exception:
                continue

    except requests.exceptions.Timeout:
        print(f"  ⚠  Timeout for {keyword}/{geo}")
    except Exception as e:
        print(f"  ⚠  Error scraping {keyword}/{geo}: {e}")

    return jobs
