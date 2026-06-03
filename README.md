# JobHunter Scraper

**Automated daily job tracker for INSEAD MBA candidates.**

This is a template repo. Set it up once — matching jobs arrive in your inbox every morning at 08:00 SGT.

---

## ⚡ Quick Setup (5 minutes)

### Step 1 — Use this template
Click **"Use this template"** → **"Create a new repository"** → set to **Private** → Create.

### Step 2 — Replace settings.py
Go to [inseadjobhunter.netlify.app](https://inseadjobhunter.netlify.app), complete the Setup Wizard, and download your personalized `settings.py`.

In your new repo: click `config/settings.py` → pencil icon (Edit) → select all → paste your downloaded settings → **Commit changes**.

### Step 3 — Get your Gmail App Password
1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification**
3. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Type a name (e.g. `job-tracker`) → press Enter
5. **Copy the 16-character password immediately** — it only shows once

### Step 4 — Add GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `GMAIL_SENDER` | yourname@gmail.com |
| `GMAIL_APP_PASS` | (16-char App Password, no spaces) |

### Step 5 — Enable GitHub Pages (for jobs.json)
**Settings → Pages → Source: Deploy from a branch → main / root → Save**

Your jobs feed will be at:
```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/jobs.json
```

Copy this URL and paste it into **JobHunter → Preferences → jobs.json URL**.

### Step 6 — Run your first scrape
**Actions → Daily Job Tracker → Run workflow → days: 7 → Run workflow**

Wait ~10 minutes. Check your alert email. If you receive the digest — **setup is complete!** 🎉

After this, the scraper runs automatically every day at **08:00 SGT**.

---

## 🔄 Updating your preferences

1. Go to [inseadjobhunter.netlify.app](https://inseadjobhunter.netlify.app) → Preferences → make changes → Download settings.py
2. In your repo: click `config/settings.py` → Edit → paste new content → Commit
3. Changes take effect on the next scraper run (or run manually via Actions)

---

## 📁 Repo structure

```
job-tracker/
├── main.py                          # Entry point
├── scoring_engine.py                # Match scoring logic
├── config/
│   ├── __init__.py
│   └── settings.py                  # ← YOUR PERSONALIZED SETTINGS
├── scrapers/
│   ├── __init__.py
│   └── linkedin_scraper.py          # LinkedIn job scraper
├── templates/
│   ├── __init__.py
│   └── email_template.py            # Email digest builder
├── .github/
│   └── workflows/
│       └── daily_job_tracker.yml    # GitHub Actions (daily cron)
└── data/
    └── seen_jobs.json               # Auto-generated, tracks seen jobs
```

---

## 💡 Tips

- First run: use `days: 7` to catch jobs from the past week
- Dry run: set `dry_run: true` to preview without sending email
- The scraper commits `jobs.json` to your repo after each run — this is what the dashboard reads

---

Supported by [Steven Yang · INSEAD MBA '26](https://www.linkedin.com/in/sy8888)
