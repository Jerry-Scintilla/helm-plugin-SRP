# helm-plugin-srp

[Helm](https://github.com/jerrysmh/helm) 的**舰船补损（SRP）**插件，为 EVE Online 舰队组织提供完整的补损管理能力——涵盖申请提交、补损官审核、市场定价、PAP 舰队快捷提交，以及通过 [helm-plugin-mcp](https://github.com/jerrysmh/helm-plugin-mcp) 接入 AI 助手的可选支持。

> **状态**：Alpha，尚无正式发布版本。欢迎贡献和 Fork。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| **ESI 击杀链接输入** | 接受直接从游戏内复制的官方 ESI 击杀链接（`https://esi.evetech.net/killmails/{id}/{hash}`） |
| **市场定价** | 查询 EVE 市场订单（可配置星域及买/卖单价格）计算补损金额 |
| **提交前预览** | 玩家在确认提交前可查看舰船名称、原始损失价值、计算后补损金额及资格检查结果 |
| **PAP 舰队快捷提交** | 拉取玩家的 PAP 记录，展示该舰队活动期间的全部损失，支持一键批量提交 |
| **舰队行动深链接** | 通过 URL 参数 `?fleet_action=<id>` 实现从舰队 MOTD 直接跳转提交 |
| **补损官管理界面** | 支持状态筛选（待审核 / 已批准 / 已拒绝 / 已付款）的补损管理视图，可批准、拒绝或标记付款 |
| **可配置补偿策略** | 价格星域、订单类型（买/卖）、补偿系数、最低损失门槛、允许补损的舰船组 |
| **MCP AI 集成** | 可选功能，通过 `helm-plugin-mcp` 向 AI 助手暴露 6 个工具 |
| **MOTD 片段注册** | 提供 `srp.motd_fragment` 扩展点，供 `helm-plugin-fleet-action` 在发放 PAP 时自动将 SRP 快捷链接插入舰队 MOTD |

---

## 依赖要求

- Python >= 3.12
- Helm >= 1.0
- `helm-plugin-fleet-action` *(可选——启用 PAP 快捷提交标签页)*
- `helm-plugin-mcp` *(可选——启用 AI 助手工具)*

---

## 安装

```bash
# 1. 安装 Python 包（开发模式）
pip install -e /path/to/helm-plugin-srp

# 2. 向运行中的 Helm 后端注册插件
curl -X POST http://localhost:8000/api/v1/admin/plugins/install \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"package_name": "helm-plugin-srp"}'

# 3. 验证安装
curl http://localhost:8000/api/v1/admin/plugins/srp/status \
  -H "Authorization: Bearer <jwt>"
# 预期结果：{"status": "enabled", "is_loaded": true, "router_mounted": true}
```

---

## 快速上手

### 1. 分配权限

在 Helm RBAC 系统中将以下权限分配给相应角色：

| 权限 | 适用对象 |
|------|---------|
| `srp.submit` | 所有可提交补损申请的成员 |
| `srp.officer` | 负责审核申请和标记付款的补损官 |
| `srp.admin` | 负责配置补损系统的管理员 |

### 2. 配置补偿策略

在侧边栏打开 **🛡️ 舰船补损** → **⚙️ 配置** 标签页（需要 `srp.admin` 权限）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 价格星域 ID | `10000002`（The Forge / Jita） | 用于价格查询的 EVE 市场星域 |
| 订单类型 | `buy`（买单价） | 使用买单价或卖单价 |
| 补偿系数 | `1.0` | 市场价格乘以该系数得到补损金额 |
| 最低损失门槛 | `0 ISK` | 低于此价值的申请将自动拒绝 |
| 允许补损的舰船组 | *(全部)* | 限制为特定舰船组 ID |

### 3. 提交补损申请

打开 **🏅 PAP 舰队补损** 标签页（如有 PAP 记录）进行批量提交，或在 **📋 我的申请** 标签页手动提交：

1. 粘贴从游戏内复制的 ESI 击杀链接：`https://esi.evetech.net/killmails/{id}/{hash}…`
2. 点击 **预览补损金额** 查看计算后的补损金额
3. 选择受损角色，点击 **确认提交**

### 4. 审核申请（补损官）

打开 **🛡️ 补损管理** 标签页（需要 `srp.officer` 权限）：

- 通过状态下拉菜单筛选待审核 / 已批准 / 已拒绝 / 已付款的申请
- 对待审核申请点击 **批准** 或 **拒绝**（拒绝时可填写理由）
- 完成转账后，对已批准申请点击 **标记已付款**

---

## 权限说明

| 权限 | 范围 | 说明 |
|------|------|------|
| `srp.submit` | global | 提交补损申请及使用 PAP 快捷提交 |
| `srp.officer` | global | 批准、拒绝申请及标记付款 |
| `srp.admin` | global | 查看和修改补损配置 |

---

## 所需 ESI 授权范围

| 授权范围 | 用途 |
|---------|------|
| `esi-killmails.read_killmails.v1` | 拉取角色近期击杀记录，用于 PAP 快捷提交 |

---

## API 接口

所有接口挂载于 `/api/v1/plugins/srp/`：

| 方法 | 路径 | 所需权限 | 说明 |
|------|------|---------|------|
| `GET` | `/me` | 已认证 | 当前用户的 SRP 权限标志 |
| `GET` | `/config` | `srp.admin` | 查看当前补损配置 |
| `PUT` | `/config` | `srp.admin` | 更新补损配置 |
| `GET` | `/killmail/preview` | `srp.submit` | 预览 ESI 击杀链接对应的补损金额 |
| `POST` | `/requests` | `srp.submit` | 提交新的补损申请 |
| `GET` | `/requests` | 已认证 | 列出申请（补损官可查看全部，普通用户只查看自己的） |
| `GET` | `/requests/{id}` | 已认证 | 查看单条申请详情 |
| `POST` | `/requests/{id}/approve` | `srp.officer` | 批准待审核申请 |
| `POST` | `/requests/{id}/reject` | `srp.officer` | 拒绝待审核申请 |
| `POST` | `/requests/{id}/mark_paid` | `srp.officer` | 将已批准申请标记为已付款 |
| `GET` | `/my-pap-fleets` | `srp.submit` | 获取当前用户的 PAP 舰队记录 |
| `GET` | `/fleet/{fleet_action_id}/kills` | `srp.submit` | 获取角色在舰队活动期间的损失记录 |

---

## MCP 工具集成

安装 `helm-plugin-mcp` 后，SRP 插件会自动注册 6 个可供 AI 助手调用的工具：

| 工具名 | 所需权限 | 说明 |
|--------|---------|------|
| `srp_get_config` | `srp.admin` | 查看当前 SRP 配置 |
| `srp_preview_killmail` | `srp.submit` | 预览指定击杀的补损金额 |
| `srp_submit_request` | `srp.submit` | 提交补损申请 |
| `srp_list_requests` | 已认证 | 按状态 / 角色筛选列出申请 |
| `srp_get_request` | 已认证 | 查看单条申请完整详情 |
| `srp_review_request` | `srp.officer` | 批准、拒绝或标记申请为已付款 |

无需额外配置——当用户拥有对应权限时，工具会自动出现在 AI 客户端的工具列表中。

---

## 扩展点

### 提供：`srp.motd_fragment`

由 `helm-plugin-fleet-action` 消费，在发放 PAP 时自动将 SRP 快捷提交链接插入舰队 MOTD：

```
[SRP补损] https://your-helm-host/plugins/srp?fleet_action=<id>
```

### 消费：`mcp.tool_provider`

若 `helm-plugin-mcp` 已安装，将 `SrpMCPToolProvider` 注册到 MCP 工具列表。MCP 未安装时静默跳过，不影响 SRP 正常功能。

---

## 项目结构

```
helm_plugin_srp/
├── plugin.py           # 入口点——权限声明、侧边栏、生命周期钩子
├── routers.py          # FastAPI 路由——所有 REST 接口
├── models.py           # SQLAlchemy 模型（SrpRequest、SrpConfig、SrpStatus）
├── schemas.py          # Pydantic 请求 / 响应 Schema
├── tool_provider.py    # MCP 工具提供者（SrpMCPToolProvider）
├── services/
│   ├── killmail.py     # ESI 击杀链接解析 + 数据拉取
│   ├── pricing.py      # 市场价格查询 + 补损金额计算
│   └── esi.py          # ESI OAuth Token 管理 + 认证请求
├── frontend/
│   └── dist/
│       └── index.html  # 单文件前端（原生 JS，内联样式）
└── migrations/         # Alembic 数据库迁移
```

---

## 数据库

插件通过 Alembic 迁移管理独立的数据库表：

| 表名 | 说明 |
|------|------|
| `srp_requests` | 每条补损申请一行——击杀信息、计算后的补损金额、状态、审核元数据 |
| `srp_configs` | 键值对配置存储 |

迁移在插件安装 / 启用时由 Helm 插件生命周期自动执行。

---

## 状态

**Alpha** ——正在积极开发中，尚无正式发布版本。API 和数据库结构可能在不通知的情况下变更。

---

## 贡献

欢迎贡献代码。Fork 本仓库，创建功能分支，提交 Pull Request 即可。

---

## 许可证

MIT License
