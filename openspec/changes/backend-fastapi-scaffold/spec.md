# Spec: 后端 FastAPI 脚手架

## ADDED Requirements

### Requirement: FastAPI 应用可启动
后端服务必须能在本地通过 `uv run uvicorn` 启动并监听 8000 端口。

#### Scenario: 启动 uvicorn 后可访问根路径
- Given 已运行 `uv sync` 安装依赖
- When 用户执行 `uv run uvicorn app.main:app --reload --port 8000`
- Then 服务监听 0.0.0.0:8000 且无启动错误

#### Scenario: OpenAPI 文档可访问
- Given FastAPI 应用已启动
- When 用户访问 `http://localhost:8000/docs`
- Then 返回 Swagger UI 页面，列出已注册的路由

#### Scenario: ReDoc 文档可访问
- Given FastAPI 应用已启动
- When 用户访问 `http://localhost:8000/redoc`
- Then 返回 ReDoc 页面

### Requirement: 健康检查端点
后端必须提供 `GET /health` 用于基础存活探针。

#### Scenario: 健康检查成功
- Given 服务已启动
- When 客户端 `GET /health`
- Then 返回 HTTP 200 与 JSON `{"status":"ok"}`

#### Scenario: 健康检查不依赖外部资源
- Given 服务已启动且未连接任何数据库或外部 API
- When 客户端 `GET /health`
- Then 仍返回 HTTP 200（健康检查不应失败因为缺少下游依赖）

### Requirement: API 路径前缀规划
所有业务 API 必须挂在 `/api/v1` 前缀下，便于后续版本管理。

#### Scenario: 业务路径遵循前缀
- Given 已注册的任意业务路由
- When 检查其完整路径
- Then 必须以 `/api/v1` 开头（如 `/api/v1/etfs`、`/api/v1/signals`）

### Requirement: 项目结构遵循 spec/design.md
后端目录结构必须与 `spec/design.md` 中描述的布局保持一致。

#### Scenario: 关键目录存在
- Given 项目初始化完成
- When 检查 `backend/` 子目录
- Then 必须存在 `app/` 与 `tests/` 子目录
- And `app/` 下必须存在 `main.py`

### Requirement: 依赖通过 uv 管理
项目使用 `uv` 作为依赖管理工具，不引入 Poetry 或 pipenv。

#### Scenario: pyproject.toml 存在
- Given 项目初始化完成
- When 检查 `backend/` 根目录
- Then 存在 `pyproject.toml` 文件，声明 FastAPI、uvicorn、pytest 等依赖

#### Scenario: 安装命令为 uv sync
- Given 用户克隆项目后
- When 用户执行 `cd backend && uv sync`
- Then 创建虚拟环境并安装所有依赖

### Requirement: 健康检查具备测试覆盖
`/health` 端点必须有自动化测试，防止后续重构破坏基础探针。

#### Scenario: pytest 通过
- Given 在 `backend/` 下执行 `uv run pytest`
- When 收集到 `/health` 的测试用例
- Then 该用例通过且整体测试套件返回 exit code 0
