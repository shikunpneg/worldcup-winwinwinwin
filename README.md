# 世界杯预测 2026

> **Qoder 码力星期四 · 世界杯冠军预测 Agent**  
> 基于 Elo 评分 + 贝叶斯优化 + 历史数据训练的世界杯预测可视化系统

**在线地址 → http://8.148.66.127:8000/**

---

## 功能介绍

### 🎯 赛程预测树
基于 d3.js 的 SVG 赛程树，展示从 32 强到决赛的完整淘汰赛对阵图，每场比赛显示预测比分和胜率。

- **日视图**：选定日期，展示当天已完赛和预测比赛
- **全景图**：查看完整淘汰赛树
- **缩放/拖动**：一键切换，适配大屏浏览
- **晋级连线**：基于 `feeds_from` 元数据的自动连线

### 📊 球队特征面板
点击比赛框，右侧面板展示 11 维球队特征评分：
- Elo 评分 / 赛事积分 / 射手榜进球
- 控球率 / 射正 / 创造力 / 防守
- 体力值 / 逼抢强度 / 传控风格

同时显示预测置信度、胜率分布和模型总准确率。

### ✏️ What-If 推演
支持交互式编辑，探索世界杯的另一种可能性：

- **替换球队**：任意修改对阵双方，重新预测
- **伤停模拟**：滑动条模拟核心球员伤停（0-50% 战力减益）
- **一键运行**：修改后点击"运行预测"重新训练+推演

### 📈 预测模型

| 模块 | 说明 |
|------|------|
| **Elo 评分系统** | 基于比赛结果的动态评分，贝叶斯优化参数（K=7.9, HA=7） |
| **Softmax 回归** | 主胜/平局/客胜概率 |
| **泊松分布** | 比分预测 |
| **Dixon-Coles 攻防** | 独立攻击/防御评分 |
| **历史数据训练** | 1068 场比赛（1930-2022 + 2026） |
| **赔率校准** | bet365 开盘赔率融合（α=0.7） |
| **决赛优化** | 决赛预期进球 x0.7，Poisson best_score 比分 |
| **点球预测** | 基于 246 场淘汰赛统计（89.7% 平局→点球） |

### 🎨 交互体验
- **弹幕系统**：首页展示球迷热门评论，悬停暂停
- **操作指南**：右下角 `?` 按钮
- **导出 PNG**：一键导出赛程树图片

---

## 技术架构

```
frontend/              React 18 + TypeScript + Vite + Tailwind CSS + d3.js
backend_api/           Python FastAPI
src/prediction/        预测引擎 (Elo + Softmax + Poisson + DC)
src/data_collection/   数据采集
data/                  历史比赛数据 + 赔率数据
```

### 数据来源
- 历史比赛：jfjelstul/worldcup 数据库（964 场，1930-2022）
- 实时数据：worldcup26.ir API
- 赔率数据：football-data.co.uk（bet365 开盘赔率）

---

## 本地运行

```bash
# 后端
pip install -r requirements.txt
uvicorn backend_api.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

---

## 部署

阿里云 ECS + Systemd + Uvicorn

```bash
git pull
cd frontend && npm run build && cd ..
sudo systemctl restart worldcup-api
```

---

*2026 年 Qoder 码力星期四·世界杯冠军预测 Agent 开发挑战赛参赛作品*
