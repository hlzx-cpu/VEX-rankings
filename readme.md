# VURC (VEX U) 2025-2026 Season Analytics Dashboard

这是一个针对 VEX U (VURC) 2025-2026 赛季的实时战绩分析与可视化 Web 看板。本项目通过接入 RobotEvents API v2 抓取全赛季的赛事数据，计算每支队伍的实时 Elo 等级分和赛程强度（Strength of Schedule, SoS），并使用 Dash + Plotly 渲染多维气泡散点图。

## 🌟 核心特性与系统架构

为了防止高频请求导致 API Token 被官方封禁（Rate Limit），本项目严格采用了 **“后台数据抓取 + 前台轮询读取”** 的解耦架构：
1. **后台数据引擎 (`data_fetcher.py`)**：负责通过 API 获取赛事数据，执行复杂的 Elo 和 SoS 数学运算，并将最终结果保存为本地的 `dashboard_data.csv`。
2. **实时 Web 看板 (`app.py`)**：基于 Dash 框架搭建。网页前端使用 `dcc.Interval` 组件，每 5 秒钟自动读取本地缓存文件并刷新图表，实现“零 API 消耗”的实时更新。
3. **多维数据映射**：单张图表同时直观展示战绩 (Elo)、赛程难度 (SoS)、驾驶技能分 (Color) 和编程技能分 (Size)。

---

## 🔑 API 密钥申请与配置

本项目需要依赖 RobotEvents API v2 的数据权限。请按照以下步骤获取您的专属 Token：

1. 访问 [RobotEvents API Request Access 页面](https://www.robotevents.com/api/v2)。
2. 在左侧菜单点击 **Request Access**。
3. 在申请理由框中填写（可直接使用以下文案）：
   > "I am developing a data analysis and visualization tool for the VURC (VEX U) 2025-2026 season. I plan to use the API to retrieve match results, event data, and skills scores. This data will be used to calculate real-time team Elo ratings and Strength of Schedule (SoS), which will be rendered into a multi-dimensional scatter plot for performance tracking. This project is strictly for analytical and educational purposes within the VEX community."
4. 勾选同意条款并提交申请。系统会生成一串很长的字符（Bearer Token）。
5. **安全提示**：请妥善保管此 Token，绝不要将其上传至公开的 GitHub 仓库。

---

## 🛠️ 安装与运行指南

### 1. 环境准备
建议在 Python 3.8+ 环境下运行。克隆此仓库后，安装必要的依赖库：
```bash
pip install requests pandas plotly dash
2. VS Code 开发设置推荐 (Pylance)如果你使用 VS Code 进行开发，建议将 Python Pylance 插件的类型检查模式 (Type Checking Mode) 从 off 设置为 basic。这能在编写 pandas 和 requests 逻辑时，为你捕捉大量潜在的类型错误，同时又不会像 strict 模式那样产生过多干扰。3. 配置密钥在项目根目录创建一个 .env 文件，或者直接在 data_fetcher.py 顶部的配置区填入你的 API Token：PythonROBOTEVENTS_TOKEN = "你的_BEARER_TOKEN"
4. 运行服务第一步：启动数据抓取 (后端)Bashpython data_fetcher.py
提示：脚本会按时间顺序遍历合并本赛季所有比赛。首次运行可能需要一定时间，完成后会生成本地数据文件。第二步：启动 Web 看板 (前端)Bashpython app.py
提示：打开终端提示的本地地址（通常为 http://127.0.0.1:8050/），即可查看每 5 秒自动刷新的实时图表。📊 核心算法与原理计算1. Elo 等级分模型 (Y轴)本项目针对 VEX U 组别（1v1 对抗）采用了经典的国际象棋 Elo 算法，不引入净胜分 (Margin of Victory)，以防止强队恶意刷分，客观反映真实胜负关系。初始设置：所有队伍初始 Elo = 1500，K-factor 常数设为 32。预期胜率：每场比赛前，计算队伍 A 对战队伍 B 的预期胜率 $E_A$：$$E_A = \frac{1}{1 + 10^{(R_B - R_A)/400}}$$赛后更新：根据实际比赛结果 $S_A$（胜利=1，平局=0.5，失败=0），更新最新等级分 $R_A'$：$$R_A' = R_A + K(S_A - E_A)$$2. 赛程强度 SoS 计算 (X轴)SoS (Strength of Schedule) 衡量的是一支队伍遇到的对手的平均真实实力。计算严格分为三步：Step 1: 收集对手：每场比赛结束后，记录双方遭遇的所有对手（保留重复交手，以体现真实比赛负荷）。Step 2: 对手 Elo 均值：计算该队伍遭遇过的所有对手的最新最终 Elo 均值 $SoS_{raw}$（从未参赛队伍视为 1500）：$$SoS_{raw} = \frac{1}{n}\sum_{i=1}^{n}Elo(opponent_i)$$Step 3: 归一化映射：为适配前端 UI 展示，进行 Min-Max 缩放，将数据拉伸至 $[0.30, 0.80]$ 区间：$$SoS = 0.30 + \frac{SoS_{raw} - \min}{\max - \min} \times 0.50$$🎨 可视化与 UI 规范图表使用 plotly.express.scatter 渲染，数据映射关系如下：X 轴：赛程强度 (SoS)Y 轴：等级分 (Elo)气泡大小 (Size)：本赛季最高编程技能分 (Programming Skills)气泡颜色 (Color)：本赛季最高驾驶技能分 (Driver Skills)标签 (Text/Hover)：队伍编号⚠️ UI 样式严格声明：本项目的图表背景、网格线、热力色带配置、字体排版及图例位置等所有视觉层面的样式代码，均严格读取并遵循当前目录下的 ui.md 文件配置。开发或维护时，请勿在代码中硬编码任何偏离 ui.md 规范的视觉样式。