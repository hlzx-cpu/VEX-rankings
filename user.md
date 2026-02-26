# VURC 2025-2026 战绩看板 · 用户手册

## 快速开始

### 1. 安装依赖（仅首次）
```powershell
cd e:\SJTU\VEX\VEX-rankings
pip install -r requirements.txt
```

### 2. 抓取真实数据
```powershell
python data_fetcher.py
```
- 首次运行约需 **8-15 分钟**（受 RobotEvents API 限速影响）
- 完成后会在当前目录生成 `dashboard_data.csv`
- 包含所有 VEX U 队伍的 Elo、SoS、Driver Skills、Programming Skills

### 3. 启动看板
```powershell
python app.py
```
- 浏览器访问 **http://localhost:8050**
- 看板每 30 秒自动刷新 CSV 数据

---

## 功能说明

### 气泡散点图
| 维度 | 含义 |
|------|------|
| X 轴 | Strength of Schedule（对手强度指数） |
| Y 轴 | Elo 评分（基于比赛胜负计算的综合实力） |
| 气泡大小 | Programming Skills 分数（半径 ∝ 分数的平方根） |
| 气泡颜色 | Driver Skills 分数（紫色=低 → 黄色=高） |
| 灰色小点 | 该队伍无 Skills 分数记录 |

### 队伍对比
1. 在右侧 **"🔍 队伍对比"** 面板中输入队伍编号（如 `SJTU1`）
2. 支持多选——可同时对比多支队伍
3. 选中的队伍会在图中以 **红色边框** 高亮显示
4. 下方自动展示对比表格（排名、Elo、SoS、Skills）

### 鼠标交互
- **悬停** 任意气泡：查看该队伍的完整数据
- **滚轮缩放**：放大/缩小查看密集区域
- **拖拽**：平移图表
- **双击图表**：重置视图

---

## 数据更新

| 项目 | 说明 |
|------|------|
| 数据来源 | RobotEvents API v2（官方数据） |
| 刷新方式 | 手动运行 `python data_fetcher.py`，或使用 `--loop 600` 参数开启每 10 分钟自动刷新 |
| 看板刷新 | 启动后每 30 秒自动读取最新的 `dashboard_data.csv` |
| 赛季切换 | 修改 `data_fetcher.py` 中 `get_vurc_season_id(2025)` 的年份参数 |

### 建议的工作流
```
# 终端 1：持续抓取数据（每 10 分钟更新一次）
python data_fetcher.py --loop 600

# 终端 2：启动看板
python app.py
```

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `app.py` | 看板前端（Dash 应用） |
| `data_fetcher.py` | 数据抓取引擎（API → CSV） |
| `dashboard_data.csv` | 计算后的队伍数据（自动生成） |
| `.env` | API Token 配置（**不要提交到 Git**） |
| `requirements.txt` | Python 依赖列表 |

---

## 常见问题

**Q: 为什么看板页面上没有图表？**
A: 需要先运行 `python data_fetcher.py` 生成 `dashboard_data.csv`。

**Q: data_fetcher 运行时报 429 错误怎么办？**
A: 这是 API 限速，程序会自动等待 30-90 秒后重试，无需手动干预。

**Q: Elo 是怎么计算的？**
A: 使用标准 Elo 算法，初始值 1500，K 因子 32。每场比赛根据队伍当前 Elo 差计算预期胜率，然后根据实际结果更新。

**Q: Skills 分数取的是什么？**
A: 每支队伍在该赛季所有赛事中的 **最高** Driver Skills 和 Programming Skills 分数。


