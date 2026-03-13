# 🎯 TalentRadar — AI-Powered LinkedIn Candidate Sourcing Agent

> Automatically discover, score, and rank top LinkedIn candidates from any job description using Google X-Ray search and LLM-powered evaluation.

---

## 📌 Overview

TalentRadar is an agentic recruiting tool that takes a job description and returns a ranked shortlist of LinkedIn candidates — complete with AI-generated fit scores, strengths/weaknesses, and hiring recommendations.

It combines:
- **Google Custom Search (X-Ray)** to surface LinkedIn profiles without LinkedIn API access
- **OpenAI GPT** to analyze candidates against the job description using the SRN FitScore methodology
- **Streamlit** for an interactive, real-time UI

---

## 🏗️ Architecture

```
agentic_system_ui.py        ← Streamlit frontend & orchestration
elite_sourcing_agent.py     ← Core agent: job analysis, search, ranking
smart_evaluator.py          ← LLM-powered candidate scoring (SRN FitScore)
search_generator.py         ← LinkedIn X-Ray query generation with progressive relaxation
linkedin_xray_search.py     ← Google CSE integration & LinkedIn profile filtering
linkedin_real_data.py       ← Apify-based LinkedIn profile enrichment
```

---

## ✨ Features

- **Automatic Job Parsing** — Extracts role family, seniority, industry, skills, and location from raw job descriptions
- **LinkedIn X-Ray Search** — Generates optimized Google queries targeting `linkedin.com/in/` profiles
- **SRN FitScore (0–10)** — Multi-dimensional AI scoring across education, career trajectory, company relevance, tenure, and core skills
- **Progressive Query Relaxation** — Starts specific, broadens automatically to guarantee results
- **Streamlit Dashboard** — Real-time progress tracking, candidate cards, and CSV export
- **Deduplication** — Tracks unique profile URLs across all search queries

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js (optional, for document generation)
- A Google Custom Search Engine (CSE) configured to search LinkedIn
- OpenAI API key

### Installation

```bash
git clone https://github.com/your-org/talent-radar.git
cd talent-radar
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root, **or** configure secrets via Streamlit's `secrets.toml`:

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "sk-..."
GOOGLE_API_KEY = "AIza..."
SEARCH_ENGINE_ID = "your-cse-id"
```

> **Setting up Google CSE:** Go to [programmablesearchengine.google.com](https://programmablesearchengine.google.com), create a new engine, and restrict it to `linkedin.com/in/*`.

### Running the App

```bash
streamlit run agentic_system_ui.py
```

---

## 🔍 How It Works

1. **Paste a job description** into the UI
2. The agent detects context — industry, company type, role type, seniority
3. Up to 5 targeted LinkedIn X-Ray queries are generated
4. Google Custom Search returns matching LinkedIn profile snippets
5. Each profile is evaluated by GPT using the SRN FitScore rubric
6. Candidates are ranked and displayed with scores, strengths, and recommendations

### SRN FitScore Rubric

| Dimension | Weight |
|---|---|
| Education | Pedigree, degree relevance |
| Career Trajectory | Growth, promotions, progression |
| Company Relevance | Tier of past employers |
| Tenure & Stability | Average job duration |
| Core Skills Match | Technical/functional skill overlap |
| Bonus Signals | Patents, open source, publications |
| Red Flags | Short stints, gaps, irrelevant history |

**Score Thresholds:**
- 🟢 `8.5+` — Strong Hire
- 🟡 `7.0–8.4` — Consider
- 🟠 `5.5–6.9` — Weak
- 🔴 `< 5.5` — No Hire

---

## 📁 File Reference

| File | Purpose |
|---|---|
| `agentic_system_ui.py` | Streamlit UI — search form, progress bar, candidate cards |
| `elite_sourcing_agent.py` | Main agent class, job analyzer, search orchestration |
| `smart_evaluator.py` | GPT-based candidate evaluation with Pydantic output parsing |
| `search_generator.py` | X-Ray query builder with title/location variation mappings |
| `linkedin_xray_search.py` | Google CSE wrapper and LinkedIn profile filter |
| `linkedin_real_data.py` | Apify integration for enriched LinkedIn data |
| `requirements.txt` | Python dependencies |

---

## ⚙️ Dependencies

| Package | Use |
|---|---|
| `streamlit` | Web UI |
| `openai` / `langchain-openai` | LLM evaluation |
| `requests` | Google CSE API calls |
| `apify-client` | LinkedIn profile enrichment |
| `pydantic` | Structured LLM output parsing |
| `python-dotenv` | Environment variable management |
| `pandas` | Candidate data handling & CSV export |

---

## 🛡️ Limitations & Ethical Use

- This tool uses **Google X-Ray search** (not the LinkedIn API) to surface publicly visible profile snippets. Full profile data is not scraped.
- Candidate scores are based on **limited snippet data** — always verify candidates directly before outreach.
- Use in compliance with LinkedIn's Terms of Service and applicable data privacy laws (GDPR, CCPA).
- Do not use scores as the sole basis for hiring decisions.

---

## 🗺️ Roadmap

- [ ] Resume parsing and direct upload
- [ ] Outreach email generation per candidate
- [ ] ATS (Greenhouse / Lever) export integration
- [ ] Multi-job batch sourcing
- [ ] Feedback loop to improve scoring over time

---

## 📄 License

MIT License — see `LICENSE` for details.
