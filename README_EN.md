<p align="center">
  <img src="./icons/VEX Robotics 2C.svg" width="180" alt="VEX Logo" />
</p>
<h1 align="center">VEX-Rankings</h1>
<p align="center">
  <strong>🤖 Automated Elo Rankings for VEX U (VURC) 2026-2027 Override Season</strong>
</p>
<p align="center">
  Serverless · GitHub Actions Auto-Update · Static GitHub Pages Hosting
</p>
<p align="center">
  <strong>English</strong> | <a href="readme.md">中文</a>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" /></a>
  <a href="https://github.com/hlzx-cpu/VEX-rankings/actions"><img src="https://img.shields.io/github/actions/workflow/status/hlzx-cpu/VEX-rankings/deploy.yml?label=Auto%20Update&logo=github" alt="GitHub Actions" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://plotly.com/"><img src="https://img.shields.io/badge/Plotly-Interactive-3F4F75?logo=plotly&logoColor=white" alt="Plotly" /></a>
  <a href="https://hlzx-cpu.github.io/VEX-rankings/rankings/"><img src="https://img.shields.io/badge/Demo-GitHub%20Pages-222?logo=github&logoColor=white" alt="GitHub Pages" /></a>
</p>

---

## 👀 Live Preview

> **🌐 View Online** → [hlzx-cpu.github.io/VEX-rankings/rankings/](https://hlzx-cpu.github.io/VEX-rankings/rankings/)
>
> Data should refresh on a low-frequency schedule such as every 6 hours via GitHub Actions — no setup required.

---

## 🌟 Features

- 📊 **Multi-dimensional bubble chart** — Elo (Y), SoS (X), Driver Skills (color), Programming Skills (bubble size) — all in one view
- 🔍 **Team search & comparison** — Use `/` to search multiple teams (e.g. `SJTU1/SJTU2`), highlighted on chart with detail table
- 🌗 **Dark / Light theme** — One-click toggle in the top-right corner
- 🌐 **Bilingual (EN / 中文)** — Built-in language switcher
- ⚡ **Zero server** — GitHub Pages static hosting, token securely stored in GitHub Secrets

---

## 📐 Algorithms

### 1️⃣ Elo Rating (Y-axis)

Classic chess Elo — no Margin of Victory (MoV), preventing score inflation.

- Initial Elo = **1500**, K-factor = **32**
- Expected win probability & post-match update:

$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}} \qquad R_A' = R_A + K(S_A - E_A)$$

> All matches sorted globally by `started_at`, updated sequentially. $S$ = 1 win / 0.5 draw / 0 loss.

### 2️⃣ Strength of Schedule — SoS (X-axis)

$$SoS_{raw} = \frac{1}{n}\sum_{i=1}^{n}Elo(\text{opponent}_i) \qquad SoS = 0.30 + \frac{SoS_{raw} - \min}{\max - \min} \times 0.50$$

> Opponents recorded per match (duplicates retained), mean of final opponent Elo, then Min-Max normalized to $[0.30, 0.80]$.

### 3️⃣ Skills Scores

| Dimension              | Chart Mapping   | Meaning                              |
| ---------------------- | --------------- | ------------------------------------ |
| **Driver Skills**      | Color intensity | Season-best driver skills score      |
| **Programming Skills** | Bubble size     | Season-best programming skills score |

### 4️⃣ Data Source

All data is fetched from public [events.vex.com](https://events.vex.com) pages and JSON endpoints, covering Teams, Matches, and Skills data. The current low-frequency update path does not require a personal API token.

---

## 🧮 Customizing Math Models

> After forking or deploying locally, you can freely modify Elo and SoS logic. All core code is in **`data_fetcher.py`**.

### Example 1: Adjusting Elo K-factor

K-factor controls how much a single match impacts Elo. Find it near the top of `data_fetcher.py` (~line 53):

```python
# ── Default ──
K_FACTOR = 32
```

Increase to `40` for greater recent-match impact:

```python
# ── Modified: recent matches matter more ──
K_FACTOR = 40
```

> 📌 **Recommended range**: VEX seasons are short — use **24 ~ 48** (chess newcomers K=40, professionals K=10).

### Example 2: Adjusting SoS Normalization Range

Default maps to `[0.30, 0.80]`. Widen the interval for greater X-axis spacing. Find the normalization logic in `run_once()` (~line 1005):

```python
# ── Default: maps to [0.30, 0.80] ──
if raw_max > raw_min:
    df["strength_of_schedule"] = 0.30 + (df["strength_of_schedule"] - raw_min) / (raw_max - raw_min) * 0.50
```

Change to `[0.10, 0.90]`:

```python
# ── Modified: maps to [0.10, 0.90] for wider X-axis spread ──
if raw_max > raw_min:
    df["strength_of_schedule"] = 0.10 + (df["strength_of_schedule"] - raw_min) / (raw_max - raw_min) * 0.80
```

> 💡 Formula: `lower + ... × (upper − lower)`. After modifying, also update the X-axis `range` in `generate_interactive_html()`.

---

## ☁️ Cloud Serverless Deployment (GitHub Pages)

This project defaults to a fully automated **GitHub Actions + GitHub Pages** architecture — no server needed:

```
events.vex.com ──▶ GitHub Actions (Cron) ──▶ rankings/index.html ──▶ GitHub Pages
```

1. Actions triggers on Cron schedule → runs `data_fetcher.py`
2. Computes Elo / SoS → generates `rankings/index.html`
3. Auto commits & pushes → GitHub Pages serves immediately

> 💡 **Fork and go** — no server, database, or domain required.

### ⏱️ Adjusting Cloud Update Frequency

Configuration file: **`.github/workflows/deploy.yml`** — modify the `cron` expression:

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '*/30 * * * *'    # ← Modify this line
```

Common Cron examples:

```yaml
# 🟢 Recommended: every 6 hours
- cron: '0 */6 * * *'

# 🔵 Every 6 hours (saves Actions quota)
- cron: '0 */6 * * *'

# 🟡 Once daily at midnight (off-season)
- cron: '0 0 * * *'

# 🔴 Every 2 hours (competition-heavy period)
- cron: '0 */2 * * *'
```

> ⚠️ GitHub Actions free tier: private repos **2000 min/month**, public repos unlimited. Each run takes ~10-15 min.

---

## 🖥️ Local Deployment & Auto-Updates

> For users who want to run on a local machine, private server, or Raspberry Pi.

### 📋 Setup

```bash
# 1. Clone the project
git clone https://github.com/hlzx-cpu/VEX-rankings.git
cd VEX-rankings

# 2. Install dependencies (Python 3.8+)
pip install -r requirements.txt

# 3. No token is required for the current public data source
#    Optional: tune the request interval
echo "EVENTS_VEX_REQUEST_INTERVAL=1.0" > .env
```

### ▶️ Running

```bash
# Single fetch + generate HTML (first run ~8-15 min)
python data_fetcher.py

# Built-in loop mode (for example, update every 6 hours)
python data_fetcher.py --loop 21600

# Optional: Dash local dashboard (http://localhost:8050)
python app.py
```

### 🔄 Automating with System Crontab (Linux / macOS)

For more reliable automation than `--loop`, use your OS cron scheduler:

```bash
# Edit crontab
crontab -e
```

Add the following lines in the editor:

```bash
# ── Run every hour on the hour ──
0 * * * * cd /your/absolute/path/VEX-rankings && /usr/bin/python3 data_fetcher.py >> /tmp/vex-rankings.log 2>&1

# ── Run every 12 hours ──
# 0 */12 * * * cd /your/absolute/path/VEX-rankings && /usr/bin/python3 data_fetcher.py >> /tmp/vex-rankings.log 2>&1

# ── Run every 6 hours ──
# 0 */6 * * * cd /your/absolute/path/VEX-rankings && /usr/bin/python3 data_fetcher.py >> /tmp/vex-rankings.log 2>&1
```

> 📌 **Notes**:
> - Replace `/your/absolute/path/` with the actual path (e.g. `/home/pi/VEX-rankings`)
> - Use the full `python3` path (check with `which python3`)
> - Output is redirected to a log file for debugging
> - Make sure `.env` has the token configured

### 🪟 Automating on Windows (Task Scheduler)

Windows users can use Task Scheduler for the same effect:

```powershell
# Create an hourly scheduled task
schtasks /create /tn "VEX-Rankings-Update" /tr "python E:\your\path\VEX-rankings\data_fetcher.py" /sc hourly /st 00:00
```

Or use the GUI: **Start Menu → search "Task Scheduler" → Create Basic Task**, then follow the wizard to set frequency and script path.

---

## 📅 Yearly Season Update

When a new season starts, update these year numbers:

| #   | File              | Location                      | Current Value              | Notes                                               |
| --- | ----------------- | ----------------------------- | -------------------------- | --------------------------------------------------- |
| 1   | `data_fetcher.py` | top-level config              | `SEASON_YEAR = 2026`       | **Most critical**: determines which season to fetch |
| 2   | `data_fetcher.py` | `GAME_NAME` / HTML copy       | `Override`                 | Page title and empty-data message                   |
| 3   | `app.py`          | `dash.Dash(title=...)`        | `VURC 2026-2027 Override 战绩看板` | Dash dashboard title                       |

> 💡 Search for the current season year and update `SEASON_YEAR` / `GAME_NAME`.

---

## 🗂️ Project Structure

```
VEX-rankings/
├── .github/workflows/
│   └── deploy.yml              # GitHub Actions scheduling config
├── icons/
│   └── VEX Robotics 2C.svg     # Project logo
├── rankings/
│   └── index.html              # Auto-generated interactive rankings page
├── data_fetcher.py             # Core engine: data fetching + Elo/SoS + HTML generation
├── app.py                      # Dash local dashboard (optional)
├── dashboard_data.csv          # Intermediate data file
├── requirements.txt            # Python dependencies
├── readme.md                   # 中文文档
└── README_EN.md                # English documentation
```

---

## ❓ FAQ

<details>
<summary><b>Does the API Token need regular renewal?</b></summary>

**Not currently.** This project now uses low-frequency public events.vex.com data access, so GitHub Actions does not need `ROBOTEVENTS_TOKEN`.

</details>

<details>
<summary><b>Why does the first run take 8-15 minutes?</b></summary>

Public endpoints may still rate-limit. Use a low-frequency schedule such as every 6 hours; the script throttles requests and backs off on 429 responses.

</details>

<details>
<summary><b>How do I change chart colors and layout?</b></summary>

Edit `generate_interactive_html()` in `data_fetcher.py`. Adjustable items: color scale (`colorscale`), backgrounds (`paper_bgcolor`/`plot_bgcolor`), fonts, etc.

</details>

---

## 📄 License

[MIT](LICENSE) © VEX-Rankings Contributors
