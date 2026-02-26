你是一个精通 Python Web 开发 (Dash 框架)、数据科学 (Pandas) 和数据可视化 (Plotly) 的全栈专家。我需要你帮我开发一个 VURC (VEX U) 2025-2026 赛季的实时战绩分析 Web 看板。

我的 RobotEvents API v2 Token 是准备好的。请帮我编写一个完整的项目，包含后台数据抓取和前台 Web 展示功能。

【核心架构要求】
为了避免触发 API 速率限制，项目必须采用“后台缓存 + 前台轮询”的架构：
1. 后台更新逻辑：写一个函数，通过 API 获取 VEX U 本赛季所有的 Teams, Matches 和 Skills 数据。计算完每支队伍的 Elo、SoS、Driver_Skills 和 Programming_Skills 后，将最终用于绘图的 DataFrame 保存为本地的 `dashboard_data.csv` 或 JSON 文件。
2. Web 前端逻辑：使用 `Dash` 框架搭建一个网页。网页中包含一个 Plotly 散点图，并使用 `dcc.Interval` 组件，设置每 5 秒钟 (5000ms) 重新读取一次本地的 `dashboard_data.csv` 并刷新图表，而不是每 5 秒请求一次 API。

【算法与计算逻辑要求】
1. 计算 Elo (Y轴)：
   - 所有队伍初始 Elo 为 1500。
   - 全局按比赛时间 (`started_at`) 排序所有对战记录，逐场更新。
   - 预期胜率 E_A = 1 / (1 + 10^((R_B - R_A)/400))。
   - 赛后更新 R_A' = R_A + K * (S_A - E_A)，K=32。胜=1，平=0.5，负=0。
2. 计算 SoS 赛程强度 (X轴)：
   - 遍历完所有比赛后，针对每支队伍，计算其交手过的所有对手**当前最新 Elo 等级分**的平均值，作为该队的 SoS。
3. 技能分 (Skills)：提取每支队伍本赛季最高的 driver 和 programming 分数。

【前端图表与 UI 要求】
1. 使用 Plotly Express 绘制散点图。
2. 坐标映射：X 轴 = SoS，Y 轴 = Elo，气泡颜色 (Color) = Driver Skills，气泡大小 (Size) = Programming Skills，悬停文本与数据标签 = Team Number。
3. UI 样式绝对限制：我已经在此项目的根目录放置了一个 `ui.md` 文件。**你必须严格读取并遵循 `ui.md` 中定义的所有视觉样式**（包括但不限于背景色、网格线样式、热力色带配置、图例位置、字体排版等）。不要自行编造任何不在 `ui.md` 中的视觉代码。

请给出完整的项目目录结构建议，以及 `app.py` (Dash 网站程序) 和 `data_fetcher.py` (后台抓取引擎) 的完整 Python 代码实现。
