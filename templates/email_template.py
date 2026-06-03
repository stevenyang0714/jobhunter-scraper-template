"""
templates/email_template.py
=============================
Builds the HTML email digest sent to the candidate.
"""
from collections import Counter, defaultdict

# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────
_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f5f5; color: #1a1a1a; margin: 0; padding: 0; }}
  .wrap {{ max-width: 640px; margin: 0 auto; padding: 20px; }}

  /* Header */
  .header {{ background: #0D0D0B; border-bottom: 3px solid #3DBA6E;
             padding: 22px 26px; color: #fff; }}
  .header-logo {{ font-size: 13px; letter-spacing: 3px; color: #3DBA6E;
                  font-weight: 700; margin-bottom: 6px; }}
  .header-sub {{ font-size: 12px; color: #aaa; }}

  /* Stats row */
  .stats {{ display: flex; gap: 10px; margin: 16px 0; }}
  .stat {{ background: #fff; border: 2px solid #e0e0e0; border-left: 3px solid #3DBA6E;
           padding: 12px 16px; flex: 1; text-align: center; }}
  .stat-n {{ font-size: 22px; font-weight: 700; color: #3DBA6E; }}
  .stat-l {{ font-size: 10px; color: #888; margin-top: 3px; text-transform: uppercase;
             letter-spacing: 1px; }}

  /* Section label */
  .section {{ font-size: 10px; font-weight: 700; color: #888; letter-spacing: 3px;
              text-transform: uppercase; margin: 20px 0 10px; border-bottom: 1px solid #e0e0e0;
              padding-bottom: 6px; }}

  /* Job card */
  .job {{ background: #fff; border: 1px solid #e0e0e0; border-left: 4px solid #3DBA6E;
          padding: 14px 16px; margin-bottom: 10px; }}
  .job-title {{ font-size: 14px; font-weight: 700; color: #0071E3; text-decoration: none;
                display: block; margin-bottom: 4px; }}
  .job-co {{ font-size: 12px; color: #555; margin-bottom: 8px; }}
  .badges {{ margin-bottom: 10px; }}
  .badge {{ font-size: 10px; padding: 3px 8px; border: 1px solid; display: inline-block;
            margin-right: 5px; margin-bottom: 3px; font-weight: 600; }}
  .badge-ind {{ background: #ebf5ef; color: #2a8a4e; border-color: #2a8a4e; }}
  .badge-geo {{ background: #eaf3ff; color: #0071E3; border-color: #0071E3; }}
  .badge-high {{ background: #ebf5ef; color: #2a8a4e; border-color: #2a8a4e; }}
  .badge-med  {{ background: #fef9e7; color: #9a6800; border-color: #c89000; }}
  .badge-low  {{ background: #f5f5f5; color: #888; border-color: #ccc; }}
  .job-desc {{ font-size: 12px; color: #666; line-height: 1.55; margin-bottom: 12px; }}
  .apply-btn {{ display: inline-block; background: #3DBA6E; color: #000; font-size: 11px;
                font-weight: 700; padding: 8px 16px; text-decoration: none;
                letter-spacing: 1px; }}

  /* Disclaimer */
  .disclaimer {{ background: #f9f9f9; border: 1px solid #e0e0e0; padding: 12px 14px;
                 font-size: 11px; color: #888; margin: 20px 0; line-height: 1.6; }}

  /* Footer */
  .footer {{ text-align: center; padding: 20px 0; color: #aaa; font-size: 11px; }}
  .footer a {{ color: #3DBA6E; text-decoration: none; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <div class="header-logo">▶ JOBHUNTER DAILY DIGEST</div>
    <div class="header-sub">{name} · {date} · {total} matching roles</div>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total</div></div>
    <div class="stat"><div class="stat-n">{high}</div><div class="stat-l">Strong ≥80%</div></div>
    <div class="stat"><div class="stat-n">{top_geo}</div><div class="stat-l">Top Region</div></div>
    <div class="stat"><div class="stat-n">{top_ind}</div><div class="stat-l">Top Industry</div></div>
  </div>

  {sections}

  <div class="disclaimer">
    ⚠ Match scores are keyword-based estimates (industry × geography × role × company).
    They reflect search query overlap — not a guarantee of fit.
    Always review the full job description before applying.
  </div>

  <div class="footer">
    Sent to {email} by <a href="https://inseadjobhunter.netlify.app">JobHunter</a> ·
    Supported by <a href="https://linkedin.com/in/sy8888">Steven Yang · INSEAD MBA '26</a>
  </div>
</div>
</body>
</html>"""

_JOB_CARD = """
<div class="job">
  <a href="{url}" class="job-title">{title}</a>
  <div class="job-co">{company} · <span style="color:#888">{source}</span></div>
  <div class="badges">
    <span class="badge badge-ind">{industry}</span>
    <span class="badge badge-geo">{location}</span>
    <span class="badge {score_cls}">{score}% {score_label}</span>
  </div>
  <div class="job-desc">{desc}</div>
  <a href="{url}" class="apply-btn">VIEW & APPLY →</a>
</div>"""

_INDUSTRY_ORDER = [
    "Healthcare", "Medical Device", "Pharmaceutical", "Biotechnology",
    "Technology", "Financial Services", "Consulting", "Venture Capital", "Other",
]


def build_email_html(
    jobs: list,
    candidate_name: str,
    alert_email: str,
    date_str: str,
    max_jobs: int = 20,
) -> str:
    """Build the full HTML email digest."""
    jobs = jobs[:max_jobs]
    total = len(jobs)

    high_count = sum(1 for j in jobs if j.match_score >= 80)
    geo_counter = Counter(j.location.split(",")[0].strip() for j in jobs)
    ind_counter = Counter(j.industry_tag or "Other" for j in jobs)

    top_geo = geo_counter.most_common(1)[0][0] if geo_counter else "—"
    top_ind = ind_counter.most_common(1)[0][0] if ind_counter else "—"

    # Group by industry
    groups: dict = defaultdict(list)
    for job in jobs:
        groups[job.industry_tag or "Other"].append(job)

    sections = ""
    for ind in _INDUSTRY_ORDER:
        if ind not in groups:
            continue
        sections += f'<div class="section">{ind}</div>'
        for job in sorted(groups[ind], key=lambda j: j.match_score, reverse=True):
            score = int(job.match_score)
            score_cls   = "badge-high" if score >= 80 else ("badge-med" if score >= 60 else "badge-low")
            score_label = "STRONG" if score >= 80 else ("MODERATE" if score >= 60 else "LOW")
            sections += _JOB_CARD.format(
                url         = job.url or "#",
                title       = job.title,
                company     = job.company,
                source      = job.source,
                industry    = job.industry_tag or "Other",
                location    = job.location,
                score_cls   = score_cls,
                score       = score,
                score_label = score_label,
                desc        = (job.description or "")[:250],
            )

    return _BASE.format(
        name     = candidate_name,
        date     = date_str,
        total    = total,
        high     = high_count,
        top_geo  = top_geo,
        top_ind  = top_ind,
        email    = alert_email,
        sections = sections,
    )
