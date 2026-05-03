# Mercari 订单与库存管理

前后端分离的本地 Web 应用：在管理库存、出入库与成本的同时，对接日本 Mercari（煤炉）账号，同步订单、在售商品等数据。适合单机或小团队在内网使用。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3、Vite、Vue Router、Pinia、Element Plus、Axios |
| 后端 | Python 3、FastAPI、Uvicorn |
| 认证 | JWT（Bearer Token） |
| 数据库 | SQLite（`backend/mercariDB.db`，WAL 模式） |
| 其他 | 扫码（ZXing）、OCR（EasyOCR）、图片本地目录挂载 |

建议 Python **3.11+**（仓库中亦有 3.12/3.13 使用记录）。

## 主要功能

- **控制台**：数据概览与常用入口  
- **库存管理**：商品与多仓库库存（对应前端路由 `inventory`，页面为商品维度的管理）  
- **订单管理**：订单列表与 Mercari 同步相关操作  
- **在售商品**：与煤炉在售列表同步、查看  
- **库存记录**：出入库等流水  
- **成本记录**：成本数据维护  
- **煤炉账号**：Mercari 账号、请求头（JSON 存于 `value` 字段）、卖家 ID、自动拉取间隔等配置  
- **仓库 / 游戏分类**：基础主数据  
- **系统管理**：用户与系统项（见 `System.vue`）  
- **登录**：首次无用户时自动创建默认管理员（见下文）

Mercari 相关 HTTP 接口挂载在 **`/api/mercari`** 下（例如增量同步、批量刷新订单状态、历史同步校验等），需登录后携带 Token 调用。

## 目录结构（摘要）

```
mercari/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── requirements.txt
│   ├── mercariDB.db            # 运行时 SQLite（若未提交到版本库则本地生成）
│   └── src/
│       ├── auth.py             # JWT 签发与校验
│       ├── db_manage/          # 数据库与模型
│       ├── image_storage.py    # 商品图片目录
│       ├── operation_mercari/  # 煤炉 API 调用与同步逻辑
│       └── routes/             # REST 路由（auth、orders、products、…）
├── webside/
│   ├── package.json
│   ├── vite.config.js          # 开发端口 9600，/api 与 /imges 代理到后端
│   └── src/
│       ├── api/
│       ├── router/
│       ├── views/
│       └── components/
└── README.md
```

## 环境变量（后端）

| 变量 | 说明 | 默认 |
|------|------|------|
| `JWT_SECRET` | JWT 签名密钥 | `CHANGE_ME_IN_PRODUCTION`（生产环境务必修改） |
| `JWT_EXPIRE_HOURS` | Token 有效小时数 | `12` |

## 快速开始

### 1. 后端

在仓库根目录下：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 9601
```

首次启动会初始化数据库与默认管理员（若 `users` 表为空）：

- 默认用户名：`admin`  
- 默认密码：`admin`  

**登录后请立即在系统管理中修改密码**，并设置强随机 `JWT_SECRET`。

### 2. 前端

```powershell
cd webside
npm install
npm run dev
```

开发服务器默认 **http://localhost:9600**（`vite.config.js` 中 `server.port`）。  
接口与静态图片通过代理转发到 **http://localhost:9601**（路径 `/api`、`/imges`）。

### 3. 访问与文档

| 说明 | 地址 |
|------|------|
| 前端 | http://localhost:9600 |
| 后端健康检查 | http://localhost:9601/api/health |
| OpenAPI（Swagger） | http://localhost:9601/docs |

同一局域网内其他设备可使用 `http://<本机局域网IP>:9600` 访问前端（Vite 已配置 `host: true`）。

## 煤炉（Mercari）对接说明

1. 在 Web 端进入 **煤炉账号**，添加账号并填写必要字段（含 **`value`**：用于存放请求头等 JSON，具体字段以后端/前端表单为准）。  
2. 将需要用于同步的账号设为可用状态，并配置 **`seller_id`** 等与订单归属相关的信息。  
3. 在订单或系统提供的入口触发同步；失败时查看后端日志与接口返回的 `detail`。

调用官方或非官方接口可能受煤炉条款与风控影响，请自行评估合规与账号风险。

## 生产构建（前端）

```powershell
cd webside
npm run build
```

产物在 `webside/dist`。生产环境需将 `/api`、`/imges` 反向代理到同一 FastAPI 进程，或由 FastAPI 挂载构建后的静态文件（当前仓库默认开发态为 Vite 代理，部署时请按需调整）。

## 依赖说明（后端）

`requirements.txt` 中含 **EasyOCR** 等较重依赖，首次 `pip install` 可能较慢且会下载模型相关资源；若部署环境不需要 OCR，可自行裁剪依赖并确认对应路由未启用。

---

如有脚本化启动需求，可自行在仓库根目录添加 `start.ps1` 分别拉起 Uvicorn 与 `npm run dev`，并与上述端口保持一致。
