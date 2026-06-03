"""
scoring_engine.py
==================
Keyword-based match scoring engine.

Scores each job on four dimensions:
  Industry   (30%) — does the job / company match target industries?
  Geography  (25%) — does the location match target geographies?
  Role       (30%) — does the title match role keywords?
  Company    (15%) — is it a target company?

Score = weighted sum, scaled 0–100.
Jobs below MATCH_THRESHOLD are filtered out.

NOTE: Scores are keyword-based estimates only.
They reflect search relevance, not a guarantee of fit.
"""

from config.settings import (
    INDUSTRIES,
    GEOGRAPHIES,
    ROLE_KEYWORDS,
    TARGET_COMPANIES,
    WEIGHT_INDUSTRY,
    WEIGHT_GEOGRAPHY,
    WEIGHT_ROLE,
    WEIGHT_COMPANY,
    MATCH_THRESHOLD,
)


# ── KEYWORD MAPS ──────────────────────────────────────────────────────────────
# Maps industry name → associated keywords to search in job text
INDUSTRY_KEYWORDS: dict = {
    "Healthcare":         ["health", "hospital", "clinic", "medical", "patient", "digital health", "mhealth"],
    "Medical Device":     ["medtech", "medical device", "diagnostics", "imaging", "surgical", "medtronic", "abbott", "bd ", "becton"],
    "Pharmaceutical":     ["pharma", "pharmaceutical", "drug", "clinical", "roche", "novartis", "astrazeneca", "pfizer", "merck", "gsk", "lilly", "sanofi"],
    "Biotechnology":      ["biotech", "genomics", "life science", "biopharma", "cell therapy", "gene"],
    "Technology":         ["software", "saas", "cloud", "ai", "data", "platform", "tech", "digital", "enterprise", "product"],
    "Financial Services": ["bank", "financial", "fintech", "insurance", "investment", "asset management", "wealth", "capital"],
    "Consulting":         ["consulting", "advisory", "strategy", "mckinsey", "bain", "bcg", "deloitte", "kpmg", "ey", "pwc", "accenture"],
    "Venture Capital":    ["venture", "vc", "investment", "startup", "seed", "series", "private equity", "pe "],
}

# Maps geography name → associated keywords in job location / description
GEO_KEYWORDS: dict = {
    "Singapore":    ["singapore", "sg", "apac", "southeast asia", "sea"],
    "Hong Kong":    ["hong kong", "hk", "greater china"],
    "Taiwan":       ["taiwan", "taipei", "tw"],
    "China":        ["china", "beijing", "shanghai", "shenzhen", "guangzhou", "cn"],
    "Dubai":        ["dubai", "uae", "united arab emirates", "middle east", "mena"],
    "Saudi Arabia": ["saudi", "riyadh", "ksa", "jeddah", "middle east"],
    "Japan":        ["japan", "tokyo", "osaka", "jp"],
    "Global/Remote":["remote", "global", "worldwide", "anywhere"],
}

SENIORITY_BOOST_KEYWORDS = [
    "senior manager", "director", "associate director",
    "head of", "vp ", "vice president", "lead", "principal",
    "associate", "consultant", "manager",
]


def _norm(text: str) -> str:
    return (text or "").lower()


def _kw_score(text: str, keywords: list) -> float:
    """Fraction of keywords found in text, capped at 1.0."""
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw.lower() in _norm(text))
    return min(hits / max(len(keywords) * 0.3, 1), 1.0)


def score_job(job) -> None:
    """Score a job in-place by setting job.match_score and job.industry_tag."""
    combined = f"{job.title} {job.company} {job.description}"

    # Industry score — best matching industry wins, with small rank bonus
    s_ind = max(
        (
            _kw_score(combined, INDUSTRY_KEYWORDS.get(ind, []))
            * (1 + (len(INDUSTRIES) - i) * 0.05)
            for i, ind in enumerate(INDUSTRIES)
        ),
        default=0.0,
    )

    # Geography score — best matching geography wins
    s_geo = max(
        (
            _kw_score(f"{job.location} {job.description}", GEO_KEYWORDS.get(g, []))
            * (1 + (len(GEOGRAPHIES) - i) * 0.05)
            for i, g in enumerate(GEOGRAPHIES)
        ),
        default=0.0,
    )

    # Role score — any keyword match counts
    s_role = max(
        (_kw_score(combined, [kw]) for kw in ROLE_KEYWORDS),
        default=0.0,
    )

    # Company score — exact company name match
    s_comp = 1.0 if any(
        t.lower() in _norm(job.company) for t in TARGET_COMPANIES
    ) else 0.0

    # Weighted total
    raw = (
        min(s_ind,  1.0) * WEIGHT_INDUSTRY  +
        min(s_geo,  1.0) * WEIGHT_GEOGRAPHY +
        min(s_role, 1.0) * WEIGHT_ROLE      +
        s_comp            * WEIGHT_COMPANY
    )

    # Seniority boost (max 10%)
    if any(kw in _norm(job.title) for kw in SENIORITY_BOOST_KEYWORDS):
        raw = min(raw * 1.10, 1.0)

    job.match_score = round(raw * 100, 1)

    # Tag the most relevant industry
    for ind in INDUSTRIES:
        kws = INDUSTRY_KEYWORDS.get(ind, [])
        if any(kw.lower() in _norm(combined) for kw in kws):
            job.industry_tag = ind
            break


def filter_and_score(jobs: list) -> list:
    """Score all jobs, filter by threshold, return sorted descending."""
    for job in jobs:
        score_job(job)
    return sorted(
        [j for j in jobs if j.match_score >= MATCH_THRESHOLD],
        key=lambda j: j.match_score,
        reverse=True,
    )
