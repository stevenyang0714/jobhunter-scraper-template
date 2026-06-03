"""
JobHunter — Daily Job Tracker
==============================
Usage:
  python main.py                    # Daily run (last 1 day)
  python main.py --days 7           # Search past 7 days (use for first run)
  python main.py --dry-run          # Preview email without sending
  python main.py --no-dedup         # Ignore seen-jobs cache
"""
import sys
import os
import json
import argparse
import smtplib
import hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, date
from pathlib import Path
from itertools import product as iproduct

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    CANDIDATE_NAME,
    ALERT_EMAIL,
    GMAIL_SENDER,
    GMAIL_APP_PASS,
    GEOGRAPHIES,
    ROLE_KEYWORDS,
    SEEN_JOBS_DB,
    MAX_JOBS_PER_EMAIL,
)
from scrapers.linkedin_scraper import scrape_linkedin
from scoring_engine import filter_and_score
from templates.email_template import build_email_html


def load_seen(path: str) -> set:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        return set(json.loads(p.read_text())) if p.exists() else set()
    except Exception:
        return set()


def save_seen(path: str, seen: set) -> None:
    Path(path).write_text(json.dumps(list(seen), indent=2))


def fingerprint(job) -> str:
    raw = f"{job.title.lower().strip()}_{job.company.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def send_email(html: str, subject: str, recipient: str) -> None:
    sender   = os.environ.get("GMAIL_SENDER", GMAIL_SENDER)
    password = os.environ.get("GMAIL_APP_PASS", GMAIL_APP_PASS)

    if not sender or not password:
        raise ValueError(
            "Gmail credentials missing. "
            "Set GMAIL_SENDER and GMAIL_APP_PASS as GitHub Secrets."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


def write_jobs_json(jobs: list, path: str = "jobs.json") -> None:
    """Write jobs.json for GitHub Pages — read by the JobHunter dashboard."""
    data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total": len(jobs),
        "jobs": [
            {
                "id":           j.id,
                "title":        j.title,
                "company":      j.company,
                "location":     j.location,
                "industry":     j.industry_tag or "Other",
                "source":       j.source,
                "match_score":  round(j.match_score, 1),
                "url":          j.url,
                "description":  j.description[:300],
                "posted_date":  j.posted_date,
            }
            for j in jobs
        ],
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"  ✓ jobs.json written ({len(jobs)} jobs)")


def run(days_ago: int = 1, dry_run: bool = False, no_dedup: bool = False) -> None:
    today = date.today().strftime("%B %d, %Y")
    divider = "=" * 56

    print(f"\n{divider}")
    print(f"  JobHunter — {today}")
    print(f"  Candidate: {CANDIDATE_NAME}")
    print(f"  Alert → {ALERT_EMAIL}")
    print(f"{divider}\n")

    # Load seen-jobs cache
    seen = load_seen(SEEN_JOBS_DB) if not no_dedup else set()

    # Scrape all keyword × geography combinations
    combos = list(iproduct(ROLE_KEYWORDS, GEOGRAPHIES))
    print(f"▶  Scraping {len(combos)} keyword × geography combinations...\n")

    all_jobs = []
    for i, (kw, geo) in enumerate(combos, 1):
        print(f"  [{i:02d}/{len(combos)}] {kw:<35} / {geo}")
        try:
            results = scrape_linkedin(kw, geo, days_ago)
            all_jobs.extend(results)
        except Exception as e:
            print(f"  ⚠  Scrape error: {e}")

    # Deduplicate
    seen_this_run: set = set()
    unique_jobs = []
    for job in all_jobs:
        fp = fingerprint(job)
        if fp in seen_this_run:
            continue
        if not no_dedup and fp in seen:
            continue
        seen_this_run.add(fp)
        unique_jobs.append(job)

    print(f"\n▶  Raw: {len(all_jobs)} | Unique new: {len(unique_jobs)}", end=" | ")

    # Score and filter
    scored = filter_and_score(unique_jobs)
    print(f"Matched (≥threshold): {len(scored)}")

    if not scored:
        print("\n  No qualifying jobs found. No email sent.")
        write_jobs_json([], "jobs.json")
        return

    # Cap at MAX_JOBS_PER_EMAIL (hard cap 30)
    capped = min(MAX_JOBS_PER_EMAIL, 30)
    top_jobs = scored[:capped]

    # Write jobs.json for dashboard
    write_jobs_json(top_jobs, "jobs.json")

    # Build email
    html    = build_email_html(top_jobs, CANDIDATE_NAME, ALERT_EMAIL, today, capped)
    subject = f"[JobHunter] {len(top_jobs)} new roles — {today}"

    if dry_run:
        Path("data/preview.html").parent.mkdir(exist_ok=True)
        Path("data/preview.html").write_text(html)
        print(f"\n  DRY RUN — email saved to data/preview.html (not sent)")
    else:
        print(f"\n▶  Sending digest to {ALERT_EMAIL}...")
        send_email(html, subject, ALERT_EMAIL)
        print(f"  ✓ Email sent — {len(top_jobs)} jobs")

        # Update seen-jobs cache
        for job in top_jobs:
            seen.add(fingerprint(job))
        save_seen(SEEN_JOBS_DB, seen)

    print(f"\n{divider}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobHunter Daily Scraper")
    parser.add_argument("--days",     type=int,  default=1,     help="Search past N days")
    parser.add_argument("--dry-run",  action="store_true",      help="Preview without sending email")
    parser.add_argument("--no-dedup", action="store_true",      help="Ignore seen-jobs cache")
    args = parser.parse_args()

    run(
        days_ago = args.days,
        dry_run  = args.dry_run,
        no_dedup = args.no_dedup,
    )
