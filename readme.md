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

## 📄 License

MIT

