[中文](readme.md) | English

# VURC 2025-2026 Season Live Rankings

> **View Online** → [hlzx-cpu.github.io/VEX-rankings/rankings/](https://hlzx-cpu.github.io/VEX-rankings/rankings/)

Automated live performance analytics for the VEX U (VURC) 2025-2026 season. Data is refreshed every 30 minutes via GitHub Actions — no local server required.

---

## 📊 Features

- **Multi-dimensional bubble chart**: Elo (Y), Strength of Schedule (X), Driver Skills (color), Programming Skills (bubble size)
- **Team search & compare**: Use `/` to search multiple teams (e.g. `SJTU1/SJTU2`), highlighted on the chart with a detail table
- **Dark / Light theme**: Toggle with one click in the top-right corner
- **Fully static**: Hosted on GitHub Pages, no backend server, API token securely stored in GitHub Secrets

---

## 📐 Algorithms

### 1. Elo Rating (Y-axis)

Classic chess Elo — no Margin of Victory, preventing score inflation.

- Initial Elo = **1500**, K-factor = **32**
- Expected win probability:

$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$

- Post-match update (S = 1 win / 0.5 draw / 0 loss):

$$R_A' = R_A + K(S_A - E_A)$$

- All matches sorted globally by `started_at`, updated sequentially

### 2. Strength of Schedule — SoS (X-axis)

Measures average opponent strength:

1. **Collect opponents**: Record all opponents per match (duplicates kept)
2. **Mean Elo**:

$$SoS_{raw} = \frac{1}{n}\sum_{i=1}^{n}Elo(opponent_i)$$

3. **Normalize**: Min-Max to $[0.30,\;0.80]$

$$SoS = 0.30 + \frac{SoS_{raw} - \min}{\max - \min} \times 0.50$$

### 3. Skills Scores

- **Driver Skills** (color): Season-best driver skills score
- **Programming Skills** (bubble size): Season-best programming skills score

### 4. Data Source

All data fetched from the [RobotEvents API v2](https://www.robotevents.com/api/v2) — Teams, Matches, and Skills endpoints.

---

## 🛠️ Local Deployment (Optional)

For custom modifications or faster update intervals, run locally.

### Requirements

- Python 3.8+
- Install dependencies: `pip install -r requirements.txt`

### Configure Token

1. Apply for a token at [RobotEvents API](https://www.robotevents.com/api/v2)
2. Create a `.env` file in the project root:

```
ROBOTEVENTS_TOKEN=your_token_here
```

### Run

```bash
# Fetch data + generate HTML (first run ~8-15 min)
python data_fetcher.py

# Loop mode (update every 600 seconds)
python data_fetcher.py --loop 600

# Optional: Dash local dashboard (http://localhost:8050)
python app.py
```

### Customization

| What                           | Where                                                     |
| ------------------------------ | --------------------------------------------------------- |
| Faster update interval         | `cron` in `.github/workflows/deploy.yml`, or `--loop` arg |
| Adjust K-factor                | `K_FACTOR` in `data_fetcher.py`                           |
| Change SoS normalization range | Mapping coefficients in `run_once()`                      |
| Modify chart colors/layout     | `generate_interactive_html()` in `data_fetcher.py`        |
| Add new season                 | Year parameter in `get_vurc_season_id()`                  |

---

## � Yearly Season Update Guide

When a new season starts, update the year numbers in the following locations. The project will then automatically fetch the new season's data.

### Files to Update

| #   | File              | Location                                                          | Current Value                 | Notes                                                                                                   |
| --- | ----------------- | ----------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| 1   | `data_fetcher.py` | `run_once()` (~L966)                                              | `get_vurc_season_id(2025)`    | **Most critical**: determines which season to fetch. Change to the new season's start year, e.g. `2026` |
| 2   | `data_fetcher.py` | `<title>` & `<h1>` in `generate_interactive_html()` (~L479, L633) | `VURC 2025-2026`              | Page title and heading text                                                                             |
| 3   | `data_fetcher.py` | Two `chartTitle` entries (~L668, L684)                            | `---VURC--- 2025-2026`        | Chart title (English & Chinese)                                                                         |
| 4   | `app.py`          | `dash.Dash(title=...)` (L45)                                      | `VURC 2025-2026 战绩看板`     | Dash local dashboard browser tab title                                                                  |
| 5   | `app.py`          | Page H2 heading (L67)                                             | `VURC 2025-2026 实时战绩看板` | Dash local dashboard page title                                                                         |
| 6   | `app.py`          | Chart title (L289)                                                | `---VURC--- 2025-2026`        | Dash local dashboard chart title                                                                        |

> **Quick method**: Use your editor's global search-and-replace to change `2025-2026` → new season (e.g. `2026-2027`).  
> Also change the `2025` parameter in `get_vurc_season_id(2025)` to `2026`.

### Web (GitHub Actions auto-deployment)

Just edit the source files and push to GitHub — Actions will automatically regenerate `rankings/index.html`:

1. **Edit `data_fetcher.py`**: Change the year parameter in `run_once()`
2. **Update title text** (optional but recommended): global replace `2025-2026` → new season
3. Push the code; GitHub Actions will generate the new season's rankings within 30 minutes

### Local

1. Make the same year changes in the files listed above
2. Re-run `python data_fetcher.py` to fetch new season data
3. Optionally run `python app.py` for the local dashboard

### Does the API Token need regular renewal?

- **RobotEvents API Tokens do not expire** — once issued, they work indefinitely; no yearly renewal needed
- Token storage locations:
  - **GitHub Actions**: Repository Settings → Secrets → `ROBOTEVENTS_TOKEN`
  - **Local**: `.env` file in the project root (`ROBOTEVENTS_TOKEN=...`)
- If the token stops working (e.g. account change or revocation), apply for a new one at [RobotEvents API](https://www.robotevents.com/api/v2)

---

## �📄 License

MIT
