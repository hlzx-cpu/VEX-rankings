"""
app.py
======
VURC 2026-2027 Override 实时战绩分析 Web 看板（Dash 前端）

架构：
  - 使用 dcc.Interval 每 30 秒从 dashboard_data.csv 读取数据
  - 使用 plotly.graph_objects 渲染气泡散点图
  - 右上角"队伍对比面板"可输入队伍编号进行多队对比

使用方式（在终端 / PowerShell 中执行）：
  ┌──────────────────────────────────────────────────┐
  │  第一步：安装依赖（仅首次）                      │
  │    pip install -r requirements.txt               │
  │                                                  │
  │  第二步：抓取数据（生成 dashboard_data.csv）      │
  │    python data_fetcher.py                        │
  │    # 首次运行约需 8-15 分钟（受 API 限速影响）    │
    │    # 循环模式：python data_fetcher.py --loop 21600 │
  │                                                  │
  │  第三步：启动看板                                │
  │    python app.py                                 │
  │    # 浏览器访问 http://localhost:8050             │
  └──────────────────────────────────────────────────┘

环境变量：
  在项目根目录创建 .env 文件，写入：
    当前公共数据源不需要 ROBOTEVENTS_TOKEN
"""

import threading
import webbrowser
from pathlib import Path

import dash
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, dash_table, callback_context

# ─── 路径配置 ────────────────────────────────────────────────────────────────────
DATA_CSV = Path(__file__).parent / "dashboard_data.csv"

# ─── 初始化 Dash ─────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="VURC 2026-2027 Override 战绩看板")
server = app.server

# ─── 布局 ────────────────────────────────────────────────────────────────────────
app.layout = html.Div(
    style={
        "fontFamily": "'Segoe UI', Arial, sans-serif",
        "backgroundColor": "#f5f7fa",
        "minHeight": "100vh",
        "padding": "16px",
    },
    children=[
        # ── 页面标题栏
        html.Div(
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "marginBottom": "12px",
            },
            children=[
                html.H2(
                    "VURC 2026-2027 Override 实时战绩看板",
                    style={"margin": 0, "color": "#1a1a2e", "fontSize": "22px"},
                ),
                html.Div(
                    id="last-update-label",
                    style={"color": "#888", "fontSize": "13px"},
                ),
            ],
        ),
        # ── 状态提示
        html.Div(id="status-bar", style={"marginBottom": "8px", "color": "#c0392b", "fontSize": "13px"}),

        # ── 主内容区（图表 + 对比面板）
        html.Div(
            style={"display": "flex", "gap": "16px", "alignItems": "flex-start"},
            children=[
                # ── 左侧：主图表
                html.Div(
                    style={"flex": "1", "minWidth": 0},
                    children=[
                        dcc.Graph(
                            id="bubble-chart",
                            config={"responsive": True, "displayModeBar": True},
                            style={"borderRadius": "8px", "overflow": "hidden"},
                        ),
                    ],
                ),
                # ── 右侧：队伍对比面板
                html.Div(
                    style={
                        "width": "320px",
                        "flexShrink": 0,
                        "backgroundColor": "white",
                        "borderRadius": "8px",
                        "padding": "16px",
                        "boxShadow": "0 1px 4px rgba(0,0,0,0.08)",
                    },
                    children=[
                        html.H4("🔍 队伍对比", style={"margin": "0 0 8px 0", "color": "#1a1a2e", "fontSize": "15px"}),
                        html.P("输入队伍编号（如 SJTU1），选择后自动高亮",
                               style={"color": "#888", "fontSize": "12px", "margin": "0 0 10px 0"}),
                        dcc.Dropdown(
                            id="compare-teams",
                            multi=True,
                            placeholder="输入队伍编号...",
                            style={"marginBottom": "12px", "fontSize": "13px"},
                        ),
                        # 对比结果表格
                        html.Div(id="compare-table"),
                    ],
                ),
            ],
        ),

        # ── 每 30 秒触发一次刷新（避免 callback 超时）
        dcc.Interval(id="interval", interval=30_000, n_intervals=0),
        # ── 隐藏存储：缓存 CSV 数据供多个回调使用
        dcc.Store(id="cached-data"),
    ],
)


# ─── 回调 1：定时读取 CSV，缓存到 dcc.Store ──────────────────────────────────────
@app.callback(
    Output("cached-data",       "data"),
    Output("last-update-label", "children"),
    Output("status-bar",        "children"),
    Output("compare-teams",     "options"),
    Input("interval",           "n_intervals"),
)
def load_data(_n: int):
    import datetime
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    status  = ""

    if not DATA_CSV.exists():
        status = f"⚠️  未找到 {DATA_CSV.name}，请先运行 data_fetcher.py 生成数据。"
        df = _mock_df()
    else:
        try:
            df = pd.read_csv(DATA_CSV)
        except Exception as exc:
            status = f"⚠️  读取数据失败: {exc}"
            df = _mock_df()

    required = {"team_name", "strength_of_schedule", "elo", "driver_skills", "programming_skills"}
    if not required.issubset(df.columns):
        status = "⚠️  CSV 列结构不完整，请检查 data_fetcher.py 输出。"
        df = _mock_df()

    # 构建 Dropdown 选项
    options = [{"label": t, "value": t} for t in sorted(df["team_name"].tolist())]

    return df.to_dict("records"), f"最近更新: {now_str}", status, options


# ─── 回调 2：绘图（数据变化或选中队伍变化时触发）────────────────────────────────
@app.callback(
    Output("bubble-chart", "figure"),
    Input("cached-data",   "data"),
    Input("compare-teams", "value"),
)
def render_chart(records, selected_teams):
    if not records:
        return go.Figure()

    df = pd.DataFrame(records)
    selected = set(selected_teams or [])

    has_skills = df[df["programming_skills"] > 0].copy()
    no_skills  = df[df["programming_skills"] == 0].copy()

    fig = go.Figure()

    # ── 1) 有 skills 的队伍：半径 ∝ √(programming_skills)
    if not has_skills.empty:
        bubble_size = np.sqrt(has_skills["programming_skills"].values) * 2

        # 高亮选中队伍：加粗边框
        if selected:
            border_width = [3.0 if t in selected else 0.5
                           for t in has_skills["team_name"]]
            border_color = ["#FF0000" if t in selected else "rgba(0,0,0,0.25)"
                           for t in has_skills["team_name"]]
        else:
            border_width = 0.5
            border_color = "rgba(0,0,0,0.25)"

        fig.add_trace(go.Scatter(
            x=has_skills["strength_of_schedule"],
            y=has_skills["elo"],
            mode="markers+text",
            text=has_skills["team_name"],
            textposition="top center",
            textfont=dict(size=9, color="#333333"),
            marker=dict(
                size=bubble_size,
                color=has_skills["driver_skills"],
                colorscale="Plasma",
                colorbar=dict(
                    title=dict(text="driver_skills", side="top"),
                    tickvals=[0, 20, 40, 60, 80, 100, 120, 140],
                    x=1.01, xanchor="left", yanchor="middle", y=0.5,
                    len=0.75, thickness=16,
                ),
                line=dict(width=border_width, color=border_color),
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

    # ── 2) 无 skills 的队伍：灰色小点 + 名称黑色
    if not no_skills.empty:
        if selected:
            border_width_ns = [3.0 if t in selected else 0.5
                               for t in no_skills["team_name"]]
            border_color_ns = ["#FF0000" if t in selected else "rgba(0,0,0,0.1)"
                               for t in no_skills["team_name"]]
        else:
            border_width_ns = 0.5
            border_color_ns = "rgba(0,0,0,0.1)"

        fig.add_trace(go.Scatter(
            x=no_skills["strength_of_schedule"],
            y=no_skills["elo"],
            mode="markers+text",
            text=no_skills["team_name"],
            textposition="top center",
            textfont=dict(size=9, color="#333333"),
            marker=dict(
                size=3,
                color="#BBBBBB",
                symbol="circle",
                line=dict(width=border_width_ns, color=border_color_ns),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "SoS: %{x:.4f}<br>"
                "Elo: %{y:.1f}<br>"
                "Skills: N/A"
                "<extra></extra>"
            ),
            name="无 Skills 数据",
            showlegend=False,
        ))

    # ── X 轴
    fig.update_xaxes(
        title_text="strength_of_schedule",
        range=[0.28, 0.82],
        dtick=0.05,
        showgrid=True, gridcolor="white", gridwidth=1,
        zeroline=False, showline=False,
        tickformat=".2f",
    )

    # ── Y 轴（动态范围）
    elo_min = df["elo"].min()
    elo_max = df["elo"].max()
    elo_pad = max((elo_max - elo_min) * 0.05, 10)
    fig.update_yaxes(
        title_text="elo",
        range=[elo_min - elo_pad, elo_max + elo_pad],
        dtick=50,
        showgrid=True, gridcolor="white", gridwidth=1,
        zeroline=False, showline=False,
    )

    # ── 全局布局
    fig.update_layout(
        title=dict(
            text=(
                "Elo vs Strength of Schedule, Skills Scores "
                "(Driver = Color, Programming = Size) ---VURC--- 2026-2027"
            ),
            x=0, xanchor="left", font=dict(size=13),
        ),
        paper_bgcolor="white",
        plot_bgcolor="#e8edf4",
        height=800,
        margin=dict(l=60, r=130, t=55, b=55),
        font=dict(family="'Segoe UI', Arial, sans-serif"),
        showlegend=False,
    )

    return fig


# ─── 回调 3：对比表格 ─────────────────────────────────────────────────────────────
@app.callback(
    Output("compare-table", "children"),
    Input("cached-data",    "data"),
    Input("compare-teams",  "value"),
)
def render_compare_table(records, selected_teams):
    if not records or not selected_teams:
        return html.P("请在上方选择要对比的队伍", style={"color": "#aaa", "fontSize": "12px", "textAlign": "center"})

    df = pd.DataFrame(records)
    sel = df[df["team_name"].isin(selected_teams)].copy()

    if sel.empty:
        return html.P("未找到选中的队伍", style={"color": "#c0392b", "fontSize": "12px"})

    # 按 Elo 降序排列
    sel = sel.sort_values("elo", ascending=False)

    # 计算排名
    df_sorted = df.sort_values("elo", ascending=False).reset_index(drop=True)
    df_sorted["rank"] = df_sorted.index + 1
    rank_map = dict(zip(df_sorted["team_name"], df_sorted["rank"]))

    rows = []
    for _, r in sel.iterrows():
        rows.append(html.Tr([
            html.Td(r["team_name"], style={"fontWeight": "bold", "color": "#1a1a2e"}),
            html.Td(f"#{rank_map.get(r['team_name'], '?')}", style={"color": "#888"}),
            html.Td(f"{r['elo']:.0f}"),
            html.Td(f"{r['strength_of_schedule']:.3f}"),
            html.Td(str(int(r["driver_skills"]))),
            html.Td(str(int(r["programming_skills"]))),
        ]))

    cell_style = {"padding": "4px 6px", "fontSize": "12px", "borderBottom": "1px solid #eee"}
    header_style = {**cell_style, "fontWeight": "bold", "color": "#555", "borderBottom": "2px solid #ccc"}

    table = html.Table(
        style={"width": "100%", "borderCollapse": "collapse", "marginTop": "4px"},
        children=[
            html.Thead(html.Tr([
                html.Th("队伍", style=header_style),
                html.Th("排名", style=header_style),
                html.Th("Elo", style=header_style),
                html.Th("SoS", style=header_style),
                html.Th("Driver", style=header_style),
                html.Th("Prog", style=header_style),
            ])),
            html.Tbody(rows),
        ],
    )

    # 添加样式到所有 td
    for row in rows:
        for td in row.children:
            td.style = cell_style

    return table


# ─── 示例数据（CSV 缺失时占位显示）────────────────────────────────────────────────
def _mock_df() -> pd.DataFrame:
    return pd.DataFrame({
        "team_name":            ["UCF", "SZTU1", "BAD", "UPSP1", "CPSLO",
                                 "BLRS2", "OBR", "TMAT1", "VCAT", "IEST1"],
        "strength_of_schedule": [0.435, 0.315,  0.595,  0.455,  0.470,
                                  0.510, 0.345,  0.570,  0.415,  0.325],
        "elo":                  [1750,  1555,    1680,   1720,   1660,
                                  1665,  1635,   1660,   1620,   1595],
        "driver_skills":        [112,   100,     88,     105,    72,
                                  82,    60,      90,    68,     55],
        "programming_skills":   [105,   85,      60,     95,     70,
                                  75,    40,      65,    50,     35],
    })


# ─── 入口 ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  VURC 2026-2027 Override 实时战绩看板")
    print("  访问: http://localhost:8050")
    print("  图表每 30 秒自动刷新 dashboard_data.csv")
    print("=" * 55)
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8050")).start()
    app.run(debug=False, host="0.0.0.0", port=8050)
