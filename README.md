# 🎯 TalentRadar — AI-Powered LinkedIn Candidate Sourcing Agent

> Paste a job description. Get a ranked shortlist of LinkedIn candidates — scored, analyzed, and ready for outreach.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?logo=openai)](https://openai.com)
[![Apify](https://img.shields.io/badge/Apify-LinkedIn%20Data-00B020)](https://apify.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Overview

**TalentRadar** is an agentic AI recruiting tool that automates the hardest part of sourcing: finding qualified candidates before they're on anyone else's radar.

It works by combining **Google X-Ray search** (no LinkedIn API needed), **Apify-powered profile enrichment**, and **GPT-based SRN FitScore evaluation** — all wrapped in a real-time Streamlit dashboard.

**What you get from a single job description:**
- A deduplicated list of matching LinkedIn profiles from across the web
- Full profile data (experience, education, skills) fetched via Apify
- AI-generated fit scores (0–10) with strengths, weaknesses, and hire/no-hire recommendations
- Candidate cards ready for review and CSV export

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    agentic_system_ui.py                         │
│             Streamlit UI · Progress tracking · Export           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────▼────────────┐
          │  elite_sourcing_agent  │   Job parsing · Context detection
          │  + JobDescriptionAnalyzer│  · Orchestration · Ranking
          └───┬───────────┬────────┘
              │           │
    ┌─────────▼──┐   ┌────▼──────────────┐
    │  search_   │   │  linkedin_xray_   │
    │  generator │   │  search.py        │
    │            │   │                   │
    │ X-Ray query│   │ Google CSE API    │
    │ generation │   │ Profile filtering │
    │ (progressive   │ Pagination (100+) │
    │ relaxation)│   └───────────────────┘
    └────────────┘
              │
    ┌─────────▼──────────────────────┐
    │      linkedin_real_data.py     │
    │                                │
    │  PRIMARY: Apify Actor scraping │
    │  FALLBACK: OpenAI inference    │
    │  Batch processing · Rate limit │
    └─────────────┬──────────────────┘
                  │
    ┌─────────────▼──────────────────┐
    │       smart_evaluator.py       │
    │                                │
    │  SmartContextDetector          │
    │  SmartEvaluator (GPT-4)        │
    │  Pydantic output parsing       │
    │  SRN FitScore (0–10)           │
    └────────────────────────────────┘
```

---

## ✨ Features

**Search & Discovery**
- **LinkedIn X-Ray Search** — Constructs optimized `site:linkedin.com/in/` queries without LinkedIn API access
- **Progressive Query Relaxation** — Starts highly targeted, automatically broadens to guarantee results
- **Multi-query Deduplication** — Tracks unique profile URLs across all search rounds
- **Pagination Support** — Fetches up to 100 results via Google CSE's paged API

**Profile Enrichment**
- **Apify-powered scraping** — Fetches real profile data: full experience history, education, skills, connections, and profile pictures
- **OpenAI fallback** — When Apify is unavailable, GPT-3.5 infers a plausible profile to keep the system operational
- **Batch processing** — Processes profiles in small batches with automatic rate limiting between requests
- **Experience calculation** — Parses duration strings (`2 yrs 3 mos`) into total years of experience

**Evaluation & Ranking**
- **Smart Context Detection** — Classifies industry, company type, role type, and seniority from the job description
- **SRN FitScore (0–10)** — 7-dimension GPT-4 evaluation with Pydantic-validated structured output
- **Hire Recommendations** — STRONG HIRE / CONSIDER / WEAK / NO HIRE with rationale
- **Company & University Signals** — Elite employer and top-university bonuses in fallback scoring

**UI & Export**
- **Streamlit Dashboard** — Real-time progress bar, candidate cards with color-coded score badges
- **CSV Export** — Download the full ranked candidate list
- **Query Performance Panel** — Shows per-query result counts and hit rates

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- [Google Custom Search Engine](https://programmablesearchengine.google.com) restricted to `linkedin.com/in/*`
- OpenAI API key (GPT-4 access recommended)
- Apify account with a LinkedIn scraper actor configured

### Installation

```bash
git clone https://github.com/jyotidabass/talent-radar.git
cd talent-radar
pip install -r requirements.txt
```

### Configuration

Create `.streamlit/secrets.toml` in the project root:

```toml
# OpenAI — used for SRN FitScore evaluation and profile fallback inference
OPENAI_API_KEY = "sk-..."

# Google Custom Search — X-Ray LinkedIn search
GOOGLE_API_KEY = "AIza..."
SEARCH_ENGINE_ID = "your-cse-id"

# Apify — LinkedIn profile enrichment (real data)
APIFY_API_KEY = "apify_api_..."
APIFY_ACTOR_ID = "your-actor-id"
```

> **Setting up Google CSE:**
> 1. Go to [programmablesearchengine.google.com](https://programmablesearchengine.google.com)
> 2. Create a new search engine
> 3. Under "Sites to search", add `linkedin.com/in/*`
> 4. Copy the Search Engine ID into `SEARCH_ENGINE_ID`

> **Setting up Apify:**
> 1. Sign up at [apify.com](https://apify.com)
> 2. Find a LinkedIn Profile Scraper actor (e.g., `apify/linkedin-profile-scraper`)
> 3. Copy your API token and the actor ID into secrets

### Run the App

```bash
streamlit run agentic_system_ui.py
```

---

## 🔍 How It Works

### Step-by-step pipeline

```
1. Paste job description
        ↓
2. SmartContextDetector
   → industry, company type, role type, seniority
        ↓
3. SearchQueryGenerator
   → Up to 5 targeted X-Ray queries with title + location + company variations
        ↓
4. LinkedInXRaySearch (Google CSE)
   → Fetch LinkedIn profile snippets, paginate, deduplicate
        ↓
5. WorkingLinkedInIntegration (Apify)
   → Enrich each profile URL with full data (experience, education, skills)
   → Fallback to OpenAI inference if Apify is unavailable
        ↓
6. SmartEvaluator (GPT-4)
   → Score each profile on 7 dimensions → SRN FitScore
   → Generate strengths, weaknesses, hire recommendation
        ↓
7. Rank · Display · Export
```

### SRN FitScore Rubric

| Dimension | What's Evaluated |
|---|---|
| **Education** | Degree level, school prestige, field relevance |
| **Career Trajectory** | Promotions, progression speed, upward movement |
| **Company Relevance** | Employer tier, industry alignment |
| **Tenure & Stability** | Average job duration, unexplained gaps |
| **Core Skills Match** | Technical and functional overlap with JD |
| **Bonus Signals** | Open source, patents, publications, leadership |
| **Red Flags** | Job hopping, irrelevant history, career gaps |

**Hire Thresholds:**

| Score | Recommendation |
|---|---|
| 🟢 `8.5 – 10.0` | **STRONG HIRE** — Exceptional, meets elite standards |
| 🟡 `7.0 – 8.4` | **CONSIDER** — Good candidate, needs further evaluation |
| 🟠 `5.5 – 6.9` | **WEAK** — Below bar, significant concerns |
| 🔴 `< 5.5` | **NO HIRE** — Does not meet minimum requirements |

### Supported Role Types

The context detector and query generator support these role families out of the box:

`Software Engineer` · `DevOps / SRE` · `Data Scientist / ML Engineer` · `Product Manager` · `Designer (UX/UI)` · `Sales / BD` · `Marketing / Growth` · `Finance / Accounting` · `Legal / Compliance` · `Operations / PM` · `HR / Talent` · `Executive / VP / Director`

---

## 📁 File Reference

| File | Description |
|---|---|
| `agentic_system_ui.py` | Streamlit app — job input form, real-time progress, candidate cards, CSV export |
| `elite_sourcing_agent.py` | Core agent — `JobDescriptionAnalyzer`, `EliteSourcingAgent`, search orchestration, ranking |
| `smart_evaluator.py` | `SmartContextDetector` (role/industry classification) + `SmartEvaluator` (GPT-4 SRN FitScore with Pydantic output) |
| `search_generator.py` | `SearchQueryGenerator` — X-Ray query builder with title variations, location mappings, industry company signals, progressive relaxation |
| `linkedin_xray_search.py` | `LinkedInXRaySearch` — Google CSE wrapper, profile snippet extraction, pagination up to 100 results |
| `linkedin_real_data.py` | `WorkingLinkedInIntegration` — Apify actor calls, batch enrichment, OpenAI fallback, experience duration parsing, structured profile summarization |
| `requirements.txt` | Python dependencies |

---

## ⚙️ Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI |
| `openai` | Profile fallback inference (GPT-3.5) |
| `langchain-openai` | SRN FitScore evaluation (GPT-4) |
| `langchain` | LLM prompt/chain orchestration |
| `apify-client` | LinkedIn profile enrichment via Apify actors |
| `requests` | Google CSE API calls |
| `beautifulsoup4` | HTML parsing |
| `pydantic` | Structured LLM output validation |
| `python-dotenv` | Local `.env` support |
| `pandas` | Candidate data handling, CSV export |
| `chromadb` | Vector store (available for future memory/search features) |
| `fastapi` + `uvicorn` | API server (for headless/programmatic use) |

---

## 🛡️ Limitations & Ethical Use

- TalentRadar uses **Google X-Ray search** to find publicly visible LinkedIn snippets — it does not use the LinkedIn API or scrape LinkedIn directly.
- Apify-fetched profile data is sourced from **publicly accessible LinkedIn profiles** only.
- Candidate scores are AI-generated from **limited public data** — always verify candidates and conduct proper interviews before making any hiring decisions.
- **Do not use fit scores as the sole basis for any hiring, rejection, or screening decision.**
- The OpenAI fallback in `linkedin_real_data.py` generates **inferred, synthetic profiles** when Apify fails. These are flagged in the raw data as `"source": "openai_inference"` — do not treat them as verified real candidates.
- Ensure your use complies with LinkedIn's [Terms of Service](https://www.linkedin.com/legal/user-agreement), GDPR, CCPA, and applicable employment discrimination laws.

---

## 🗺️ Roadmap

- [ ] Resume/PDF upload and direct candidate intake
- [ ] Personalized outreach email generation per candidate
- [ ] ATS export — Greenhouse, Lever, Ashby
- [ ] Multi-job batch sourcing mode
- [ ] Feedback loop to improve scoring accuracy over time
- [ ] Streamlit Cloud one-click deploy
- [ ] In-app secrets setup wizard

---

## 📄 License

MIT License — see `LICENSE` for details.
