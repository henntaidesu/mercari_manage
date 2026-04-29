# 仓储管理系统

前后端分离的仓储管理系统，支持手机端与电脑端同步使用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus |
| 后端 | Python + FastAPI |
| 数据库 | SQLite（图片以 Base64 格式存储） |

## 功能模块

- **控制台** — 统计概览、库存预警、最近出入库
- **商品管理** — 商品增删改查、图片上传（Base64存储）
- **库存管理** — 各仓库库存查看、入库/出库/调拨操作
- **出入库记录** — 完整操作记录，支持筛选翻页
- **仓库管理** — 多仓库管理
- **分类管理** — 商品分类维护

## 目录结构

```
mercari/
├── backend/          # Python 后端
│   ├── main.py       # FastAPI 入口
│   ├── database.py   # SQLite 数据库初始化
│   ├── routes/       # API 路由
│   │   ├── categories.py
│   │   ├── warehouses.py
│   │   ├── inventory.py
│   │   ├── inventory.py
│   │   └── transactions.py
│   └── requirements.txt
├── webside/          # Vue 前端
│   ├── src/
│   │   ├── api/      # Axios API 封装
│   │   ├── router/   # Vue Router
│   │   ├── views/    # 各功能页面
│   │   └── components/ # 布局组件
│   ├── package.json
│   └── vite.config.js
├── start.ps1         # 一键启动脚本
└── README.md
```

## 快速启动

### 方式一：一键启动（推荐）

```powershell
.\start.ps1
```

### 方式二：手动启动

**后端：**
```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**
```powershell
cd webside
npm install
npm run dev
```

## 访问地址

- 前端界面：http://localhost:9600
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs（Swagger UI）

## 移动端访问

启动后，在同一局域网内的手机浏览器访问 `http://[电脑IP]:5173` 即可使用。
