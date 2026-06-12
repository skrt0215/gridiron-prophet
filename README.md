# 🏈 Gridiron Prophet

**Find the edge before kickoff.** Gridiron Prophet analyzes four seasons of NFL
data, factors in live injuries, and predicts every game's spread — then compares
it to the Vegas line to flag where the value is.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1)
![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B)

> For educational and entertainment use only — not betting advice. Bet responsibly.

---

## What it does

- **Weekly picks** — every matchup gets a predicted spread, win probability,
  and confidence level. Games with a **3+ point edge** over Vegas get flagged.
- **Injury intelligence** — see how each team's injuries actually move the line,
  weighted by position and playing time.
- **Head-to-head** — pit any two teams against each other for an instant breakdown.
- **Honest accuracy tracking** — predictions are logged *before* games and graded
  after, so the accuracy numbers are real, not cherry-picked.
- **Rosters & reports** — browse active rosters and weekly injury reports in one place.

All of it lives in a clean, interactive dashboard.

## How it works

Gridiron Prophet trains two machine-learning models on 2022–2025 results — one for
win probability, one for the point spread — using only the information available
*before* each game. It then layers in an injury-impact score and checks the result
against live DraftKings lines to find mispriced games. Every Tuesday it pulls fresh
results, retrains, and grades its last set of picks.

## Quick start

```bash
git clone <your-repo-url>
cd gridiron-prophet
python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Set up the database, then create config/.env with your DB creds + a password
mysql -u <user> -p <db_name> < src/database/schema

# Launch
streamlit run streamlit_app.py
```

Open the dashboard, enter your access password, and you're in.

### Configuration (`config/.env`)
| Variable | Purpose |
|----------|---------|
| `DB_HOST` `DB_PORT` `DB_USER` `DB_PASSWORD` `DB_NAME` | MySQL connection |
| `GRIDIRON_ACCESS_PASSWORD` | Dashboard login (**required**) |
| `ODDS_API_KEY` | Live DraftKings lines (optional) |
| `DB_SSL` | Set `true` for a hosted database (optional) |

## Tech stack

Python · scikit-learn · pandas · MySQL · Streamlit · Plotly — data from ESPN and
The Odds API.

## Roadmap
- [x] Win + spread models with weekly retraining
- [x] Injury-impact analysis and live edge detection
- [x] Self-grading accuracy & ROI tracking
- [ ] Player-level analytics
- [ ] Weather in the prediction pipeline

## License
See [LICENSE](LICENSE).