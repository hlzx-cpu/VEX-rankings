<p align="center">
  <img src="./icons/VEX Robotics 2C.svg" width="180" alt="VEX Logo" />
</p>
<h1 align="center">VEX-Rankings</h1>
<p align="center">
  <strong>🤖 VEX U (VURC) 2025-2026 赛季全自动实时 Elo 排名看板</strong>
</p>
<p align="center">
  Serverless · GitHub Actions 自动更新 · 纯静态 GitHub Pages 托管
</p>
<p align="center">
  <a href="README_EN.md">English</a> | <strong>中文</strong>
</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT License" /></a>
  <a href="https://github.com/hlzx-cpu/VEX-rankings/actions"><img src="https://img.shields.io/github/actions/workflow/status/hlzx-cpu/VEX-rankings/deploy.yml?label=Auto%20Update&logo=github" alt="GitHub Actions" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://plotly.com/"><img src="https://img.shields.io/badge/Plotly-Interactive-3F4F75?logo=plotly&logoColor=white" alt="Plotly" /></a>
  <a href="https://hlzx-cpu.github.io/VEX-rankings/rankings/"><img src="https://img.shields.io/badge/Demo-GitHub%20Pages-222?logo=github&logoColor=white" alt="GitHub Pages" /></a>
</p>

---

## 👀 在线预览

> **🌐 立即查看** → [hlzx-cpu.github.io/VEX-rankings/rankings/](https://hlzx-cpu.github.io/VEX-rankings/rankings/)
>
> 数据每 30 分钟由 GitHub Actions 自动更新，无需安装任何环境，打开即用。

---

## 🌟 核心特性

- 📊 **多维气泡散点图** — Elo（Y 轴）、赛程强度 SoS（X 轴）、驾驶技能分（颜色）、编程技能分（气泡大小）一图尽览
- 🔍 **队伍搜索 & 对比** — 输入框支持 `/` 分隔多队名（如 `SJTU1/SJTU2`），高亮目标队伍 + 详细对比表格
- 🌗 **深色 / 浅色主题** — 右上角一键切换
- 🌐 **中英双语** — 页面内置语言切换按钮
- ⚡ **零服务器** — GitHub Pages 纯静态托管，Token 安全存储在 GitHub Secrets

---

## 📐 核心算法

### 1️⃣ Elo 等级分（Y 轴）

经典国际象棋 Elo，不引入净胜分 (MoV)，防止强队刷分。

- 初始 Elo = **1500**，K-factor = **32**
- 预期胜率 & 赛后更新：

$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}} \qquad R_A' = R_A + K(S_A - E_A)$$

> 全赛季比赛按 `started_at` 全局排序后逐场计算。$S$ = 1 胜 / 0.5 平 / 0 负。

### 2️⃣ 赛程强度 SoS（X 轴）

$$SoS_{raw} = \frac{1}{n}\sum_{i=1}^{n}Elo(\text{opponent}_i) \qquad SoS = 0.30 + \frac{SoS_{raw} - \min}{\max - \min} \times 0.50$$

> 记录每场对手（保留重复交手），取对手最终 Elo 均值，再 Min-Max 归一化到 $[0.30, 0.80]$。

### 3️⃣ 技能分

| 维度                   | 图表映射 | 含义                 |
| ---------------------- | -------- | -------------------- |
| **Driver Skills**      | 颜色深浅 | 本赛季最高驾驶技能分 |
| **Programming Skills** | 气泡大小 | 本赛季最高编程技能分 |

### 4️⃣ 数据来源

所有数据通过 [RobotEvents API v2](https://www.robotevents.com/api/v2) 获取，涵盖 Teams、Matches、Skills 三类接口。

---

## 🧮 算法自定义

> Fork 或本地部署后，可自由修改 Elo 和 SoS 的计算逻辑。核心代码均位于 **`data_fetcher.py`**。

### 示例 1：修改 Elo K-factor

K-factor 控制单场比赛对 Elo 的影响幅度。找到 `data_fetcher.py` 顶部（约第 53 行）：

```python
# ── 默认值 ──
K_FACTOR = 32
```

修改为更大的值以增加近期比赛权重：

```python
# ── 修改后：近期比赛影响更大 ──
K_FACTOR = 40
```

> 📌 **推荐范围**：VEX 赛季较短，建议 **24 ~ 48**（国际象棋新手 K=40，职业 K=10）。

### 示例 2：修改 SoS 归一化区间

默认映射到 `[0.30, 0.80]`，可拉宽区间增大图表 X 轴间距。找到 `data_fetcher.py` 中 `run_once()` 的归一化逻辑（约第 1005 行）：

```python
# ── 默认值：映射到 [0.30, 0.80] ──
if raw_max > raw_min:
    df["strength_of_schedule"] = 0.30 + (df["strength_of_schedule"] - raw_min) / (raw_max - raw_min) * 0.50
```

修改为 `[0.10, 0.90]`：

```python
# ── 修改后：映射到 [0.10, 0.90]，X 轴间距更大 ──
if raw_max > raw_min:
    df["strength_of_schedule"] = 0.10 + (df["strength_of_schedule"] - raw_min) / (raw_max - raw_min) * 0.80
```

> 💡 公式：`下界 + ... × (上界 − 下界)`。修改后需同步调整 `generate_interactive_html()` 中 X 轴 `range` 参数。

---

## ☁️ 云端 Serverless 部署（GitHub Pages）

本项目默认采用 **GitHub Actions + GitHub Pages** 全自动架构，无需任何服务器：

```
RobotEvents API ──▶ GitHub Actions (Cron) ──▶ rankings/index.html ──▶ GitHub Pages
```

1. Actions 按 Cron 定时触发 → 执行 `data_fetcher.py`
2. 自动计算 Elo / SoS → 生成 `rankings/index.html`
3. 自动 commit & push → GitHub Pages 立即更新

> 💡 **Fork 即用**，无需自备服务器、数据库或域名。

### ⏱️ 修改云端更新频率

配置文件：**`.github/workflows/deploy.yml`**，修改 `cron` 表达式即可：

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '*/30 * * * *'    # ← 修改这一行
```

常用 Cron 示例：

```yaml
# 🟢 默认：每 30 分钟
- cron: '*/30 * * * *'

# 🔵 每 6 小时（节省 Actions 额度）
- cron: '0 */6 * * *'

# 🟡 每天午夜（赛事空窗期）
- cron: '0 0 * * *'

# 🔴 每 2 小时（赛事密集期）
- cron: '0 */2 * * *'
```

> ⚠️ GitHub Actions 免费额度：私有仓库 **2000 分钟/月**，公开仓库无限制。每次运行约 10-15 分钟，请合理设置。

---

## 🖥️ 本地部署与自动化更新

> 适合希望在本地电脑、私人服务器或树莓派上运行的用户。

### 📋 环境准备

```bash
# 1. 克隆项目
git clone https://github.com/hlzx-cpu/VEX-rankings.git
cd VEX-rankings

# 2. 安装依赖（Python 3.8+）
pip install -r requirements.txt

# 3. 配置 Token
#    前往 https://www.robotevents.com/api/v2 申请
echo "ROBOTEVENTS_TOKEN=你的Token" > .env
```

### ▶️ 运行方式

```bash
# 单次抓取 + 生成 HTML（首次约 8-15 分钟）
python data_fetcher.py

# 内置循环模式（每 600 秒更新一次）
python data_fetcher.py --loop 600

# 启动 Dash 本地看板（可选，http://localhost:8050）
python app.py
```

### 🔄 使用系统 Crontab 自动化（Linux / macOS）

如果你希望用操作系统的定时任务代替 `--loop` 模式实现更可靠的自动化运行：

```bash
# 编辑 crontab
crontab -e
```

在打开的编辑器中添加以下行：

```bash
# ── 每小时整点自动运行一次 ──
0 * * * * cd /你的项目绝对路径/VEX-rankings && /usr/bin/python3 data_fetcher.py >> /tmp/vex-rankings.log 2>&1

# ── 每 30 分钟运行一次 ──
# */30 * * * * cd /你的项目绝对路径/VEX-rankings && /usr/bin/python3 data_fetcher.py >> /tmp/vex-rankings.log 2>&1

# ── 每 6 小时运行一次 ──
# 0 */6 * * * cd /你的项目绝对路径/VEX-rankings && /usr/bin/python3 data_fetcher.py >> /tmp/vex-rankings.log 2>&1
```

> 📌 **注意事项**：
> - 将 `/你的项目绝对路径/` 替换为实际路径（如 `/home/pi/VEX-rankings`）
> - 使用 `python3` 的完整路径（通过 `which python3` 查看）
> - 输出重定向到日志文件方便排查问题
> - 确保 `.env` 文件中的 Token 已正确配置

### 🪟 使用 Windows 任务计划程序自动化

Windows 用户可通过「任务计划程序」实现同等效果：

```powershell
# 创建每小时运行一次的计划任务
schtasks /create /tn "VEX-Rankings-Update" /tr "python E:\你的路径\VEX-rankings\data_fetcher.py" /sc hourly /st 00:00
```

或使用图形界面：**开始菜单 → 搜索「任务计划程序」→ 创建基本任务**，按向导设置触发频率与运行脚本路径。

---

## 📅 每年赛季更新

每年新赛季只需修改以下年份数字：

| #   | 文件              | 位置                          | 当前值                     | 说明                         |
| --- | ----------------- | ----------------------------- | -------------------------- | ---------------------------- |
| 1   | `data_fetcher.py` | `run_once()` 函数             | `get_vurc_season_id(2025)` | **最关键**：决定抓取哪个赛季 |
| 2   | `data_fetcher.py` | `generate_interactive_html()` | `VURC 2025-2026`           | 网页标题                     |
| 3   | `app.py`          | `dash.Dash(title=...)`        | `VURC 2025-2026 战绩看板`  | Dash 看板标题                |

> 💡 全局搜索 `2025-2026` 替换为新赛季年份，再将 `get_vurc_season_id(2025)` 的参数改为对应年份即可。

---

## 🗂️ 项目结构

```
VEX-rankings/
├── .github/workflows/
│   └── deploy.yml              # GitHub Actions 定时任务
├── icons/
│   └── VEX Robotics 2C.svg     # 项目 Logo
├── rankings/
│   └── index.html              # 自动生成的交互式排名页面
├── data_fetcher.py             # 核心引擎：数据抓取 + Elo/SoS + HTML 生成
├── app.py                      # Dash 本地看板（可选）
├── dashboard_data.csv          # 中间数据文件
├── requirements.txt            # Python 依赖
├── readme.md                   # 中文文档
└── README_EN.md                # English documentation
```

---

## ❓ 常见问题

<details>
<summary><b>API Token 需要定期更新吗？</b></summary>

**不需要。** RobotEvents API Token 不会过期，申请后长期有效。
- **GitHub Actions**：仓库 Settings → Secrets → `ROBOTEVENTS_TOKEN`
- **本地**：项目根目录 `.env` 文件

</details>

<details>
<summary><b>首次运行为什么需要 8-15 分钟？</b></summary>

RobotEvents API 限速约 1 req/s，需逐页拉取全部赛事、比赛和技能赛数据。后续运行耗时类似（全量拉取）。

</details>

<details>
<summary><b>如何修改图表配色和布局？</b></summary>

修改 `data_fetcher.py` 中 `generate_interactive_html()` 函数，可调内容：色盘（`colorscale`）、背景色（`paper_bgcolor`/`plot_bgcolor`）、字体等。

</details>

---

## 📄 License

[MIT](LICENSE) © VEX-Rankings Contributors

