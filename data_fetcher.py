"""
data_fetcher.py
===============
后台数据抓取引擎 —— VURC 2025-2026 战绩分析看板

职责：
  1. 从 RobotEvents API v2 拉取 Teams / Matches / Skills 数据
  2. 计算每支队伍的 Elo、SoS、Driver Skills、Programming Skills
  3. 将结果写入 dashboard_data.csv（供 app.py 轮询读取）

使用：
  python data_fetcher.py            # 立即抓取一次
  python data_fetcher.py --loop 300 # 每 300 秒循环抓取

依赖：
  pip install requests pandas python-dotenv
"""

import argparse
import logging
import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from dotenv import load_dotenv

# 从当前目录的 .env 文件加载环境变量
load_dotenv(Path(__file__).parent / ".env")

# ─── 配置 ──────────────────────────────────────────────────────────────────────
# Token 从 .env 文件读取，源码中不存储任何密钥
API_TOKEN = os.environ.get("ROBOTEVENTS_TOKEN", "")
if not API_TOKEN:
    raise EnvironmentError(
        "未找到 ROBOTEVENTS_TOKEN。\n"
        "请在项目根目录创建 .env 文件，写入：\n"
        "  ROBOTEVENTS_TOKEN=你的Token"
    )
BASE_URL        = "https://www.robotevents.com/api/v2"
PROGRAM_ID      = 4          # VEX U
OUTPUT_CSV      = Path(__file__).parent / "dashboard_data.csv"
K_FACTOR        = 32
INITIAL_ELO     = 1500
REQUEST_INTERVAL = 2.0       # 每次请求间隔秒数（API 限速约 1 req/s，保守设为 2s）

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── API 工具函数 ───────────────────────────────────────────────────────────────
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
}


class NotFoundError(RuntimeError):
    """HTTP 4xx 错误（资源不存在），不应重试。"""


def _get(endpoint: str, params: dict | None = None) -> dict:
    """GET 请求。
    - 每次成功请求后主动 sleep REQUEST_INTERVAL 秒（主动限速）
    - 4xx (非429): 立即抛出 NotFoundError，不重试
    - 429 Too Many Requests: 退避等待后重试，最多 5 次
    - 5xx / 超时: 最多重试 3 次
    """
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    max_attempts = 8
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=30)
            if r.status_code == 429:
                # 速率限制：退避等待（尊重 Retry-After 响应头）
                retry_after = r.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else max(30, 30 * (attempt + 1))
                log.warning("触发 429 速率限制，等待 %d 秒再重试 (attempt=%d)...", wait, attempt + 1)
                time.sleep(wait)
                continue
            if 400 <= r.status_code < 500:
                raise NotFoundError(f"HTTP {r.status_code}: {url}")
            r.raise_for_status()
            time.sleep(REQUEST_INTERVAL)   # 主动限速，避免触发 429
            return r.json()
        except NotFoundError:
            raise
        except requests.RequestException as exc:
            log.warning("请求失败 (%s) attempt=%d: %s", url, attempt + 1, exc)
            if attempt < max_attempts - 1:
                time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"API 请求多次失败: {url}")


def paginate(endpoint: str, params: dict | None = None) -> list[dict]:
    """自动分页，返回合并后的 data 列表。"""
    params = dict(params or {})
    params.setdefault("per_page", 250)
    results = []
    page = 1
    while True:
        params["page"] = page
        payload = _get(endpoint, params)
        batch = payload.get("data", [])
        results.extend(batch)
        meta = payload.get("meta", {})
        last_page = meta.get("last_page", 1)
        log.debug("  %s page=%d/%d, fetched=%d", endpoint, page, last_page, len(batch))
        if page >= last_page:
            break
        page += 1
    return results


# ─── Season 查找 ────────────────────────────────────────────────────────────────
def get_vurc_season_id(year: int = 2025) -> int:
    """返回 VEX U 指定赛季的 season ID（含 year 年份的赛季）。"""
    seasons = paginate("seasons", {"program[]": PROGRAM_ID})
    for s in seasons:
        if str(year) in s.get("name", ""):
            log.info("找到赛季: %s (id=%s)", s["name"], s["id"])
            return s["id"]
    # 备选：返回最新赛季
    if seasons:
        s = seasons[-1]
        log.warning("未找到 %d 年赛季，使用最新: %s (id=%s)", year, s["name"], s["id"])
        return s["id"]
    raise RuntimeError("未找到任何 VEX U 赛季")


# ─── 数据抓取 ────────────────────────────────────────────────────────────────────
def fetch_teams(season_id: int) -> list[str]:
    """返回本赛季所有注册队伍的编号列表（number）。"""
    log.info("抓取 Teams (season=%d)...", season_id)
    rows = paginate("teams", {"program[]": PROGRAM_ID, "season[]": season_id})
    numbers = [r["number"] for r in rows if r.get("number")]
    log.info("共 %d 支队伍", len(numbers))
    return numbers


def _parse_match(m: dict, eid: int) -> dict | None:
    """将 API 返回的 match 对象解析为标准记录，失败返回 None。"""
    alliances = m.get("alliances", [])
    if len(alliances) < 2:
        return None
    red  = next((a for a in alliances if a.get("color") == "red"),  alliances[0])
    blue = next((a for a in alliances if a.get("color") == "blue"), alliances[1])
    red_teams  = [t["team"].get("number") or t["team"].get("name", "")
                  for t in red.get("teams",  []) if t.get("team")]
    blue_teams = [t["team"].get("number") or t["team"].get("name", "")
                  for t in blue.get("teams", []) if t.get("team")]
    if not red_teams or not blue_teams:
        return None
    return {
        "event_id":   eid,
        "match_id":   m.get("id"),
        "started_at": m.get("started"),
        "red_teams":  red_teams,
        "blue_teams": blue_teams,
        "red_score":  red.get("score",  0) or 0,
        "blue_score": blue.get("score", 0) or 0,
    }


def fetch_matches(season_id: int, events: list[dict]) -> pd.DataFrame:
    """
    直接使用 event 对象中内嵌的 divisions 字段获取 division id，
    再通过 /events/{eid}/divisions/{did}/matches 获取比赛数据。
    返回按 started_at 全局排序的 DataFrame。
    """
    log.info("抓取 Matches，共 %d 个赛事...", len(events))
    records = []
    skipped = 0
    has_data = 0

    for ev in events:
        eid = ev["id"]
        ev_records: list[dict] = []

        # 直接使用 event 对象中内嵌的 divisions 列表
        divisions = ev.get("divisions", [])
        if not divisions:
            log.debug("Event %d 无 divisions 信息，跳过", eid)
            skipped += 1
            continue

        for div in divisions:
            did = div["id"] if isinstance(div, dict) else div
            try:
                matches = paginate(f"events/{eid}/divisions/{did}/matches")
            except NotFoundError:
                continue
            except RuntimeError:
                log.warning("跳过 event %d / division %d (服务器错误)", eid, did)
                continue
            for m in matches:
                rec = _parse_match(m, eid)
                if rec:
                    ev_records.append(rec)

        if ev_records:
            has_data += 1
            log.debug("Event %d: %d 场比赛", eid, len(ev_records))
        else:
            skipped += 1

        records.extend(ev_records)

    log.info("有数据赛事: %d / %d，跳过: %d", has_data, len(events), skipped)

    df = pd.DataFrame(records)
    if df.empty:
        log.warning("未抓取到任何 Match 数据")
        return df

    df["started_at"] = pd.to_datetime(df["started_at"], utc=True, errors="coerce")
    df = df.sort_values("started_at").reset_index(drop=True)
    log.info("共 %d 场比赛（全局排序完成）", len(df))
    return df



def fetch_skills(events: list[dict]) -> pd.DataFrame:
    """
    返回每支队伍本赛季最高 driver / programming 分数。
    列：team_name, driver_skills, programming_skills

    复用已获取的 events 列表，逐个抓取 /events/{id}/skills。
    """
    log.info("抓取 Skills，共 %d 个赛事...", len(events))

    best: dict[str, dict] = {}
    _404_count = 0
    for ev in events:
        eid = ev["id"]
        try:
            rows = paginate(f"events/{eid}/skills")
        except NotFoundError:
            _404_count += 1
            continue
        except RuntimeError:
            log.warning("跳过 event %d 的 Skills (服务器错误)", eid)
            continue

        for r in rows:
            team = r.get("team", {}).get("number", "") or r.get("team", {}).get("name", "")
            if not team:
                continue
            stype = r.get("type", "")   # "driver" | "programming"
            score = r.get("score", 0) or 0
            if team not in best:
                best[team] = {"driver_skills": 0, "programming_skills": 0}
            if stype == "driver":
                best[team]["driver_skills"] = max(best[team]["driver_skills"], score)
            elif stype == "programming":
                best[team]["programming_skills"] = max(best[team]["programming_skills"], score)

    if _404_count:
        log.info("共 %d 个赛事无 Skills 数据，已跳过", _404_count)


    df = pd.DataFrame(
        [{"team_name": k, **v} for k, v in best.items()]
    )
    log.info("共 %d 支队伍有技能赛数据", len(df))
    return df


# ─── Elo + SoS 计算 ─────────────────────────────────────────────────────────────
def compute_elo_sos(matches_df: pd.DataFrame, all_teams: list[str]) -> pd.DataFrame:
    """
    返回包含 [team_name, elo, strength_of_schedule] 的 DataFrame。
    """
    elo: dict[str, float] = defaultdict(lambda: float(INITIAL_ELO))
    opponents: dict[str, list[str]] = defaultdict(list)

    # 初始化所有已知队伍
    for t in all_teams:
        _ = elo[t]   # 触发 defaultdict 初始化

    def update(winner_teams: list[str], loser_teams: list[str], draw: bool):
        for a in winner_teams:
            for b in loser_teams:
                ea = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400))
                eb = 1 - ea
                sa = 0.5 if draw else 1.0
                sb = 0.5 if draw else 0.0
                elo[a] += K_FACTOR * (sa - ea)
                elo[b] += K_FACTOR * (sb - eb)
                opponents[a].append(b)
                opponents[b].append(a)

    for _, row in matches_df.iterrows():
        red   = row["red_teams"]
        blue  = row["blue_teams"]
        rs    = row["red_score"]
        bs    = row["blue_score"]
        if not red or not blue:
            continue
        if rs > bs:
            update(red, blue, draw=False)
        elif bs > rs:
            update(blue, red, draw=False)
        else:
            update(red, blue, draw=True)

    # 计算 SoS
    sos: dict[str, float] = {}
    for team, opps in opponents.items():
        if opps:
            sos[team] = sum(elo[o] for o in opps) / len(opps)
        else:
            sos[team] = float(INITIAL_ELO)

    records = [
        {"team_name": t, "elo": round(elo[t], 2), "strength_of_schedule": round(sos.get(t, INITIAL_ELO), 4)}
        for t in elo
    ]
    return pd.DataFrame(records)


# ─── 静态 HTML 输出 ─────────────────────────────────────────────────────────────
RANKINGS_DIR = Path(__file__).parent / "rankings"


def generate_interactive_html(df: pd.DataFrame) -> None:
    """
    根据 DataFrame 生成一个带原生 JS 交互的单文件 HTML（暗黑主题）。
    输出到 rankings/index.html，可直接部署到 GitHub Pages。
    """
    RANKINGS_DIR.mkdir(exist_ok=True)

    has_skills = df[df["programming_skills"] > 0].copy()
    no_skills  = df[df["programming_skills"] == 0].copy()

    fig = go.Figure()

    # ── 1) 有 skills 的队伍
    if not has_skills.empty:
        bubble_size = np.sqrt(has_skills["programming_skills"].values) * 2
        fig.add_trace(go.Scatter(
            x=has_skills["strength_of_schedule"],
            y=has_skills["elo"],
            mode="markers+text",
            text=has_skills["team_name"],
            textposition="top center",
            textfont=dict(size=9, color="#c9d1d9"),
            marker=dict(
                size=bubble_size,
                color=has_skills["driver_skills"],
                colorscale="Plasma",
                colorbar=dict(
                    title=dict(text="driver_skills", side="top", font=dict(color="#c9d1d9")),
                    tickvals=[0, 20, 40, 60, 80, 100, 120, 140],
                    tickfont=dict(color="#8b949e"),
                    x=1.01, xanchor="left", yanchor="middle", y=0.5,
                    len=0.75, thickness=16,
                ),
                line=dict(width=0.5, color="rgba(255,255,255,0.25)"),
                opacity=0.82,
                showscale=True,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "SoS: %{x:.4f}<br>"
                "Elo: %{y:.1f}<br>"
                "Driver: %{customdata[0]}<br>"
                "Programming: %{customdata[1]}"
                "<extra></extra>"
            ),
            customdata=has_skills[["driver_skills", "programming_skills"]].values,
            name="有 Skills 数据",
        ))

    # ── 2) 无 skills 的队伍
    if not no_skills.empty:
        fig.add_trace(go.Scatter(
            x=no_skills["strength_of_schedule"],
            y=no_skills["elo"],
            mode="markers+text",
            text=no_skills["team_name"],
            textposition="top center",
            textfont=dict(size=9, color="#8b949e"),
            marker=dict(
                size=3,
                color="#484f58",
                symbol="circle",
                opacity=0.7,
                line=dict(width=0.5, color="rgba(255,255,255,0.1)"),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "SoS: %{x:.4f}<br>"
                "Elo: %{y:.1f}<br>"
                "Skills: 无数据"
                "<extra></extra>"
            ),
            name="无 Skills 数据",
            showlegend=False,
        ))

    # ── 坐标轴
    fig.update_xaxes(
        title_text="strength_of_schedule",
        range=[0.28, 0.82], dtick=0.05,
        showgrid=True, gridcolor="#21262d", gridwidth=1,
        zeroline=False, showline=False,
        tickformat=".2f",
        tickfont=dict(color="#8b949e"),
        title_font=dict(color="#c9d1d9"),
    )
    elo_min = df["elo"].min()
    elo_max = df["elo"].max()
    elo_pad = max((elo_max - elo_min) * 0.05, 10)
    fig.update_yaxes(
        title_text="elo",
        range=[elo_min - elo_pad, elo_max + elo_pad], dtick=50,
        showgrid=True, gridcolor="#21262d", gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(color="#8b949e"),
        title_font=dict(color="#c9d1d9"),
    )

    # ── 全局布局（暗黑主题）
    fig.update_layout(
        title=dict(
            text=(
                "Elo vs Strength of Schedule, Skills Scores "
                "(Driver = Color, Programming = Size) ---VURC--- 2025-2026"
            ),
            x=0, xanchor="left", font=dict(size=13, color="#e6edf3"),
        ),
        paper_bgcolor="#0d1117",
        plot_bgcolor="#161b22",
        height=800,
        margin=dict(l=60, r=130, t=55, b=55),
        font=dict(family="'Segoe UI', Arial, sans-serif", color="#c9d1d9"),
        showlegend=False,
    )

    # ── 将队伍数据导出为 JSON，供 JS 端检索（不依赖 Plotly 内部数据结构）
    team_lookup = {}
    for _, row in df.iterrows():
        team_lookup[row["team_name"].upper()] = {
            "team": row["team_name"],
            "elo": round(float(row["elo"]), 1),
            "sos": round(float(row["strength_of_schedule"]), 4),
            "driver": int(row["driver_skills"]),
            "prog": int(row["programming_skills"]),
        }
    import json
    team_json = json.dumps(team_lookup, ensure_ascii=False)

    # ── 导出 HTML 片段
    plot_html = fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        div_id="vurc-plot",
    )

    # ── 构建完整 HTML 页面
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VURC 2025-2026 Rankings</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0d1117;
      color: #c9d1d9;
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
    }}
    .toolbar {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 24px;
      background: #161b22;
      border-bottom: 1px solid #30363d;
      flex-wrap: wrap;
    }}
    .toolbar h1 {{
      font-size: 18px;
      font-weight: 600;
      color: #e6edf3;
      margin-right: auto;
      white-space: nowrap;
    }}
    .toolbar input[type="text"] {{
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #c9d1d9;
      padding: 6px 12px;
      font-size: 14px;
      width: 220px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .toolbar input[type="text"]:focus {{
      border-color: #58a6ff;
    }}
    .toolbar input[type="text"]::placeholder {{
      color: #484f58;
    }}
    .btn {{
      padding: 6px 16px;
      font-size: 13px;
      font-weight: 500;
      border: 1px solid #30363d;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
    }}
    .btn-primary {{
      background: #238636;
      color: #ffffff;
      border-color: #238636;
    }}
    .btn-primary:hover {{ background: #2ea043; }}
    .btn-secondary {{
      background: #21262d;
      color: #c9d1d9;
    }}
    .btn-secondary:hover {{ background: #30363d; }}
    #chart-container {{
      padding: 8px 16px;
    }}
    /* ── 搜索结果信息表格 ── */
    #info-panel {{
      padding: 0 24px 12px 24px;
    }}
    #info-panel:empty {{ display: none; }}
    #info-panel table {{
      border-collapse: collapse;
      width: auto;
      min-width: 520px;
      margin-top: 8px;
      font-size: 13px;
    }}
    #info-panel th {{
      background: #21262d;
      color: #e6edf3;
      padding: 6px 14px;
      text-align: left;
      border-bottom: 2px solid #30363d;
      font-weight: 600;
      white-space: nowrap;
    }}
    #info-panel td {{
      padding: 5px 14px;
      border-bottom: 1px solid #21262d;
      color: #c9d1d9;
      white-space: nowrap;
    }}
    #info-panel tr:hover td {{
      background: #1c2128;
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <h1>VURC 2025-2026 Rankings</h1>
    <input type="text" id="team-input" placeholder="e.g.  SJTU1/SJTU2" />
    <button class="btn btn-primary" id="btn-search">🔍 Highlight</button>
    <button class="btn btn-secondary" id="btn-clear">✕ Clear</button>
  </div>
  <div id="info-panel"></div>
  <div id="chart-container">
    {plot_html}
  </div>

  <script>
  var TEAM_DATA = {team_json};
  (function() {{
    var graphDiv  = document.getElementById('vurc-plot');
    var input     = document.getElementById('team-input');
    var btnSearch = document.getElementById('btn-search');
    var btnClear  = document.getElementById('btn-clear');
    var infoPanel = document.getElementById('info-panel');

    /* ── 解析输入：按 / 分割为多个关键词 ── */
    function parseQueries(raw) {{
      return raw.split('/').map(function(s) {{ return s.trim().toUpperCase(); }})
                .filter(function(s) {{ return s.length > 0; }});
    }}

    /* ── 判断某个队名是否匹配任一关键词 ── */
    function isMatch(name, queries) {{
      for (var q = 0; q < queries.length; q++) {{
        if (name.indexOf(queries[q]) !== -1) return true;
      }}
      return false;
    }}

    /* ── 搜索 & 高亮 ── */
    function highlightTeam() {{
      var queries = parseQueries(input.value);
      if (!queries.length || !graphDiv || !graphDiv.data) return;

      var matchedNames = {{}};  // 去重记录

      var nTraces = graphDiv.data.length;
      for (var ti = 0; ti < nTraces; ti++) {{
        var trace = graphDiv.data[ti];
        var texts = trace.text || [];
        var n     = texts.length;
        var widths    = new Array(n);
        var colors    = new Array(n);
        var opacities = new Array(n);

        for (var i = 0; i < n; i++) {{
          var tname = (texts[i] || '').toUpperCase();
          if (isMatch(tname, queries)) {{
            widths[i]    = 4;
            colors[i]    = '#FF3333';
            opacities[i] = 1.0;
            matchedNames[tname] = true;
          }} else {{
            widths[i]    = 0.5;
            colors[i]    = 'rgba(255,255,255,0.15)';
            opacities[i] = 0.35;
          }}
        }}

        Plotly.restyle(graphDiv, {{
          'marker.line.width': [widths],
          'marker.line.color': [colors],
          'marker.opacity':    [opacities]
        }}, [ti]);
      }}

      // 从预嵌入的 TEAM_DATA 查找信息
      var matchedRows = [];
      var keys = Object.keys(matchedNames);
      for (var k = 0; k < keys.length; k++) {{
        var info = TEAM_DATA[keys[k]];
        if (info) matchedRows.push(info);
      }}
      renderInfoTable(matchedRows);
    }}

    /* ── 渲染搜索结果表格 ── */
    function renderInfoTable(rows) {{
      if (!rows.length) {{
        infoPanel.innerHTML = '';
        return;
      }}
      rows.sort(function(a, b) {{ return (b.elo || 0) - (a.elo || 0); }});
      var html = '<table><thead><tr>'
        + '<th>Team</th><th>Elo</th><th>SoS</th><th>Driver Skills</th><th>Prog Skills</th>'
        + '</tr></thead><tbody>';
      for (var i = 0; i < rows.length; i++) {{
        var r = rows[i];
        html += '<tr>'
          + '<td style="font-weight:600;color:#58a6ff">' + r.team + '</td>'
          + '<td>' + r.elo.toFixed(1) + '</td>'
          + '<td>' + r.sos.toFixed(4) + '</td>'
          + '<td>' + r.driver + '</td>'
          + '<td>' + r.prog + '</td>'
          + '</tr>';
      }}
      html += '</tbody></table>';
      infoPanel.innerHTML = html;
    }}

    /* ── 清除高亮 & 表格 ── */
    function clearHighlight() {{
      if (!graphDiv || !graphDiv.data) return;
      var nTraces = graphDiv.data.length;
      for (var ti = 0; ti < nTraces; ti++) {{
        var trace = graphDiv.data[ti];
        var n = (trace.text || []).length;
        var widths    = new Array(n);
        var colors    = new Array(n);
        var opacities = new Array(n);
        for (var i = 0; i < n; i++) {{
          widths[i]    = 0.5;
          colors[i]    = ti === 0 ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.1)';
          opacities[i] = ti === 0 ? 0.82 : 0.7;
        }}
        Plotly.restyle(graphDiv, {{
          'marker.line.width': [widths],
          'marker.line.color': [colors],
          'marker.opacity':    [opacities]
        }}, [ti]);
      }}
      input.value = '';
      infoPanel.innerHTML = '';
    }}

    btnSearch.addEventListener('click', highlightTeam);
    btnClear.addEventListener('click', clearHighlight);
    input.addEventListener('keydown', function(e) {{
      if (e.key === 'Enter') highlightTeam();
    }});
  }})();
  </script>
</body>
</html>
"""

    out_path = RANKINGS_DIR / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    log.info("✓ 生成交互式 HTML: %s", out_path)


# ─── 主函数 ──────────────────────────────────────────────────────────────────────
def run_once() -> None:
    """执行一次完整的数据拉取、计算、输出流程。"""
    log.info("═══ 开始数据更新 ═══")

    season_id = get_vurc_season_id(2025)
    teams     = fetch_teams(season_id)

    # 获取一次 events 列表，两个函数共用，避免重复请求
    log.info("抓取 Events (season=%d)...", season_id)
    events = paginate("events", {"program[]": PROGRAM_ID, "season[]": season_id})
    log.info("共 %d 个赛事", len(events))

    # ── 冷却期：Teams/Events 大批量请求后，等待 API 配额恢复 ───────
    cooldown = 30
    log.info("大批量请求完成，冷却 %d 秒，等待 API 配额恢复...", cooldown)
    time.sleep(cooldown)

    matches   = fetch_matches(season_id, events)

    # ── 冷却期：Matches 大批量请求后，等待 API 配额恢复 ────────
    cooldown2 = 30
    log.info("Matches 抓取完成，冷却 %d 秒...", cooldown2)
    time.sleep(cooldown2)

    skills    = fetch_skills(events)

    if matches.empty:
        log.error("无比赛数据，本次跳过写入。")
        return

    elo_sos = compute_elo_sos(matches, teams)

    # 合并 skills
    df = elo_sos.merge(skills, on="team_name", how="left")
    df["driver_skills"]      = df["driver_skills"].fillna(0).astype(int)
    df["programming_skills"] = df["programming_skills"].fillna(0).astype(int)

    # 过滤掉没有参加过任何比赛（SoS = 初始值 且 Elo = 初始值）的队伍
    df = df[~((df["elo"] == INITIAL_ELO) & (df["strength_of_schedule"] == INITIAL_ELO))]

    # 将 SoS 归一化到 ~ [0.3, 0.8]（按百分位线性映射）
    if len(df) > 1:
        raw_min = df["strength_of_schedule"].min()
        raw_max = df["strength_of_schedule"].max()
        if raw_max > raw_min:
            df["strength_of_schedule"] = 0.30 + (df["strength_of_schedule"] - raw_min) / (raw_max - raw_min) * 0.50
            df["strength_of_schedule"] = df["strength_of_schedule"].round(4)

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    log.info("✓ 写入 %s (%d 支队伍)", OUTPUT_CSV, len(df))

    # 生成静态交互式 HTML（用于 GitHub Pages 部署）
    generate_interactive_html(df)

    log.info("═══ 数据更新完成 ═══")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VURC 数据抓取引擎")
    parser.add_argument("--loop", type=int, default=0,
                        help="循环间隔秒数，0 表示只运行一次")
    args = parser.parse_args()

    if args.loop > 0:
        log.info("循环模式：每 %d 秒更新一次", args.loop)
        while True:
            try:
                run_once()
            except Exception as exc:
                log.error("本轮更新失败: %s", exc)
            time.sleep(args.loop)
    else:
        run_once()
