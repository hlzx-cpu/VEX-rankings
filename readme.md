[English](README_EN.md) | 中文

# VURC 2025-2026 赛季实时排名看板

> **在线查看** → [hlzx-cpu.github.io/VEX-rankings/rankings/](https://hlzx-cpu.github.io/VEX-rankings/rankings/)

本项目为 VEX U (VURC) 2025-2026 赛季提供自动化的实时战绩分析。数据每 30 分钟由 GitHub Actions 自动更新，无需本地运行任何服务。

---

## 📊 网页功能

- **多维气泡散点图**：一张图同时展示 Elo（Y 轴）、赛程强度 SoS（X 轴）、驾驶技能分（颜色）、编程技能分（气泡大小）
- **队伍搜索 & 对比**：输入框支持 `/` 分隔多队名（如 `SJTU1/SJTU2`），高亮目标并在表格中显示详细数据
- **深色 / 浅色主题**：右上角一键切换
- **纯静态部署**：GitHub Pages 直接托管，无后端服务器，Token 安全存储在 GitHub Secrets 中

---

## 📐 核心算法

### 1. Elo 等级分（Y 轴）

采用经典国际象棋 Elo 算法，不引入净胜分 (MoV)，防止强队刷分。

- 初始值：所有队伍 Elo = **1500**，K = **32**
- 预期胜率：

$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$

- 赛后更新（S = 1 胜 / 0.5 平 / 0 负）：

$$R_A' = R_A + K(S_A - E_A)$$

- 全赛季所有比赛按 `started_at` 时间全局排序后逐场更新

### 2. 赛程强度 SoS（X 轴）

衡量对手平均真实实力，步骤：

1. **记录对手**：每场比赛结束后记录双方遭遇的所有对手（保留重复交手）
2. **计算均值**：所有对手的最终 Elo 均值

$$SoS_{raw} = \frac{1}{n}\sum_{i=1}^{n}Elo(opponent_i)$$

3. **归一化**：Min-Max 映射到 $[0.30,\;0.80]$

$$SoS = 0.30 + \frac{SoS_{raw} - \min}{\max - \min} \times 0.50$$

### 3. 技能分

- **Driver Skills**（颜色）：本赛季最高驾驶技能分
- **Programming Skills**（气泡大小）：本赛季最高编程技能分

### 4. 数据来源

所有数据通过 [RobotEvents API v2](https://www.robotevents.com/api/v2) 获取，涵盖 Teams、Matches、Skills 三类接口。

---

## 🛠️ 本地部署（可选）

如果你想自行修改或加快更新频率，可以在本地运行。

### 环境要求

- Python 3.8+
- 依赖安装：`pip install -r requirements.txt`

### 配置 Token

1. 前往 [RobotEvents API](https://www.robotevents.com/api/v2) 申请 Token
2. 在项目根目录创建 `.env` 文件：

```
ROBOTEVENTS_TOKEN=你的Token
```

### 运行

```bash
# 抓取数据 + 生成 HTML（首次约 8-15 分钟）
python data_fetcher.py

# 循环模式（每 600 秒更新一次）
python data_fetcher.py --loop 600

# 启动 Dash 本地看板（可选，http://localhost:8050）
python app.py
```

### 自定义修改

| 需求                | 修改位置                                                          |
| ------------------- | ----------------------------------------------------------------- |
| 更快的更新频率      | `.github/workflows/deploy.yml` 中 `cron` 表达式，或 `--loop` 参数 |
| 调整 K-factor       | `data_fetcher.py` 中 `K_FACTOR` 常量                              |
| 修改 SoS 归一化范围 | `data_fetcher.py` 中 `run_once()` 的映射系数                      |
| 修改图表配色/布局   | `data_fetcher.py` 中 `generate_interactive_html()`                |
| 添加新赛季          | `get_vurc_season_id()` 中修改年份参数                             |

---

## � 每年赛季更新指南

每年新赛季开始时，需要修改以下位置的年份数字，项目即可自动抓取新赛季数据。

### 需要修改的文件一览

| #   | 文件              | 位置                                                                    | 当前值                        | 说明                                                                |
| --- | ----------------- | ----------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------- |
| 1   | `data_fetcher.py` | `run_once()` 函数（约 L966）                                            | `get_vurc_season_id(2025)`    | **最关键**：决定抓取哪个赛季的数据。改为新赛季的起始年份，如 `2026` |
| 2   | `data_fetcher.py` | `generate_interactive_html()` 中的 `<title>` 和 `<h1>`（约 L479、L633） | `VURC 2025-2026`              | 网页标题和页面大标题的显示文字                                      |
| 3   | `data_fetcher.py` | `generate_interactive_html()` 中的两处 `chartTitle`（约 L668、L684）    | `---VURC--- 2025-2026`        | 图表标题（中英文各一处）                                            |
| 4   | `app.py`          | `dash.Dash(title=...)`（L45）                                           | `VURC 2025-2026 战绩看板`     | Dash 本地看板浏览器标签标题                                         |
| 5   | `app.py`          | 页面 H2 标题（L67）                                                     | `VURC 2025-2026 实时战绩看板` | Dash 本地看板页面标题                                               |
| 6   | `app.py`          | 图表标题（L289）                                                        | `---VURC--- 2025-2026`        | Dash 本地看板图表标题                                               |

> **快速操作**：在编辑器中全局搜索 `2025-2026`，替换为新赛季年份（如 `2026-2027`）即可覆盖大部分位置。  
> 另外记得把 `data_fetcher.py` 中 `get_vurc_season_id(2025)` 的参数 `2025` 改为 `2026`。

### 网页端（GitHub Actions 自动部署）

只需修改仓库中的源码文件，推送到 GitHub 后 Actions 会自动运行并更新 `rankings/index.html`：

1. **修改 `data_fetcher.py`**：将 `run_once()` 中的年份参数改为新赛季年份
2. **修改标题文字**（可选但建议）：全局替换 `2025-2026` → 新赛季年份
3. 推送代码，GitHub Actions 会在 30 分钟内自动生成新赛季的排名页面

### 本地端

1. 同样修改上述文件中的年份
2. 重新运行 `python data_fetcher.py` 抓取新赛季数据
3. 如需本地看板，运行 `python app.py`

### API Token 是否需要定期更新？

- **RobotEvents API Token 不会过期**，一旦申请后可以长期使用，无需每年更新
- Token 存储位置：
  - **GitHub Actions**：仓库 Settings → Secrets → `ROBOTEVENTS_TOKEN`
  - **本地**：项目根目录 `.env` 文件中的 `ROBOTEVENTS_TOKEN=...`
- 如果 Token 失效（如账号变更或被 revoke），前往 [RobotEvents API](https://www.robotevents.com/api/v2) 重新申请即可

---

## �📄 License

MIT

