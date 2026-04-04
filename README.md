# Department-quality-control

科室业务平台 V3，当前仓库同时包含：

- Flask 后端服务
- Vue 3 Web 前端
- PyQt5 桌面客户端
- Windows 本地启动、部署与打包脚本

本文档面向开发者，重点说明如何在本地启动、调试和维护这个项目。

## 1. 项目结构

```text
.
├─client/                 PyQt5 桌面客户端
├─frontend/               Vue 3 + Vite 前端工程
├─server/                 Flask 后端服务
├─scripts/windows/        Windows 启动与打包脚本
├─docs/                   设计文档与补充说明
├─启动全部.bat            根目录一键启动入口
├─启动客户端.bat          根目录客户端启动入口
├─启动服务器.bat          根目录服务端启动入口
├─重启全部.bat            根目录重启入口
└─退出运行.bat            根目录停止入口
```

## 2. 技术栈

### 后端

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-JWT-Extended
- Flask-CORS
- APScheduler
- SQLite
- openpyxl
- python-docx

### 前端

- Vue 3
- Vite 5
- Vue Router 4
- Pinia
- Element Plus
- Axios

### 桌面端

- PyQt5
- requests

## 3. 核心模块

当前业务能力主要包括：

- 用户认证与用户管理
- 仪表盘
- 任务管理
- 病例讨论
- 业务学习
- 病历质控检查
- 出院患者导入
- 患者随访
- 报表统计

后端 API 蓝图位于 `server/app/api/`，主要路由如下：

- `/api/auth`
- `/api/tasks`
- `/api/discussions`
- `/api/studies`
- `/api/checks`
- `/api/patients`
- `/api/followups`
- `/api/reports`

## 4. 环境要求

建议环境：

- Windows 10/11
- Python 3.10+
- Node.js 18+
- npm 9+

兼容性相关文件还包含：

- `server/requirements-win7.txt`
- `server/deploy/start_server_win7.bat`
- `server/deploy/start_server_server2016.bat`

如果你是在较老的 Windows 环境上部署，优先参考这些脚本。

## 5. 快速启动

### 方式 A：根目录一键启动

适合本地快速联调。

直接运行：

```bat
启动全部.bat
```

它会转到 `scripts/windows/启动全部.bat`，按顺序完成：

1. 启动后端
2. 等待服务可访问
3. 启动桌面客户端

停止运行使用：

```bat
退出运行.bat
```

### 方式 B：分别启动后端和客户端

先启动后端：

```bat
启动服务器.bat
```

再启动客户端：

```bat
启动客户端.bat
```

## 6. 后端开发

### 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\server\requirements.txt
```

### 启动后端

```powershell
.\.venv\Scripts\python.exe .\server\run.py
```

或者在 `server` 目录下执行：

```powershell
cd .\server
..\.venv\Scripts\python.exe run.py
```

上面第二种写法在某些终端里不方便复制，更稳妥的方式是直接在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe .\server\run.py
```

日常开发仍然更推荐直接使用仓库自带 `启动服务器.bat`。

后端默认监听：

- `http://0.0.0.0:5000`
- 本地访问地址：`http://localhost:5000`

### 后端运行特性

- 启动时会自动创建 SQLite 数据库表
- 启动时会自动补充部分历史缺失字段和索引
- SQLite 启用了 WAL 模式
- 如果能找到前端构建产物，后端会直接托管前端静态文件

静态资源查找顺序：

1. 环境变量 `KSQC_STATIC_DIR`
2. `frontend/dist`
3. `server/dist`

### 默认管理员账号

后端首次启动会自动初始化管理员：

- 用户名：`admin`
- 密码：`admin123`

建议本地启动后第一时间修改密码。

## 7. 前端开发

### 安装依赖

```powershell
cd .\frontend
npm install
```

### 开发模式

```powershell
cd .\frontend
npm run dev
```

### 构建

```powershell
cd .\frontend
npm run build
```

构建产物默认输出到：

- `frontend/dist`

后端在启动时如果检测不到 `frontend/dist/index.html`，某些启动脚本会自动尝试构建前端。

## 8. 桌面客户端开发

### 安装依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\client\requirements.txt
```

### 启动客户端

```powershell
.\.venv\Scripts\python.exe .\client\main.py
```

桌面客户端本地配置文件位于：

- `%USERPROFILE%\.ks_qc_client.json`

当前默认配置中，客户端会连接：

- `http://localhost:5000`

如果后端地址变更，可以修改这个配置文件中的 `server_url`。

## 9. 数据与运行目录

### 主要数据目录

- `server/data/app.db`：主数据库
- `server/data/app.db-shm`
- `server/data/app.db-wal`
- `server/uploads/`：上传文件和模板

### 运行日志目录

- `.runtime/`
- `.runtime/logs/`
- `server/deploy/.runtime/`

这些目录里通常会产生本地运行日志、PID 文件和调试残留，开发时要注意不要误提交。

## 10. 常用脚本

### 根目录入口

- `启动全部.bat`
- `启动服务器.bat`
- `启动客户端.bat`
- `重启全部.bat`
- `退出运行.bat`

### Windows 脚本目录

- `scripts/windows/start_server.bat`
- `scripts/windows/start_server_server2016.bat`
- `scripts/windows/package_backend.bat`
- `scripts/windows/package_backend_server2016.bat`

这些脚本已经包含：

- `.venv` 检查与创建
- `pip` 安装依赖
- 前端构建检测
- 后端后台启动
- 日志输出到 `.runtime/logs`

## 11. 开发建议

### 推荐联调顺序

1. 先确认后端 `http://localhost:5000` 可访问
2. 再启动桌面客户端
3. 需要查 Web 页面时，再单独启动 `frontend` 开发模式

### 推荐提交习惯

建议将以下内容视为本地运行产物，谨慎提交：

- `.runtime/`
- `server/deploy/.runtime/`
- `server/data/app.db-shm`
- `server/data/app.db-wal`
- 临时 Excel 文件
- 本地测试日志

## 12. 已知说明

- 当前仓库里同时存在 `frontend/dist` 和 `server/dist` 两套静态产物来源，实际以后端启动时的静态目录解析结果为准。
- 数据库使用 SQLite，本地开发方便，但多人并发协作和大数据量场景要特别关注锁与文件同步问题。
- 客户端、后端、前端都偏向 Windows 本地运行方式，跨平台支持目前不是主要目标。

## 13. 后续可继续完善的文档

如果后面要继续完善开发者文档，建议补充：

- 接口清单
- 数据库表结构说明
- 打包发布流程
- Win7 / Server 2016 部署步骤
- 常见故障排查
