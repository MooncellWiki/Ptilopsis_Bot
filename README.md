# Ptilopsis Bot

用于自动更新 [PRTS Wiki](https://prts.wiki) 明日方舟相关页面的机器人。

机器人会定期或手动触发，从游戏官方资源中拉取最新游戏数据，解析后通过 MediaWiki API 写入 Wiki 对应页面（干员、敌人、关卡、家具、剧情、皮肤、模组、活动等）。

## 功能概览

- **多服支持**：CN（官服）、JP / US / KR（YoStar 海外服）、TW。
- **资源拉取**：直接从官方 CDN 下载并解包 `hot_update_list`、`ResourceManifest`，使用 [`flatc`](https://github.com/google/flatbuffers) 解析 FlatBuffers 资源，无需依赖 UnityPy。
- **数据来源切换**：可使用本地解包 (`Unpacker`) 或开源仓库 [`ArknightsGameData`](https://github.com/Kengxxiao/ArknightsGameData) / [`ArknightsGameData_YoStar`](https://github.com/Kengxxiao/ArknightsGameData_YoStar) 作为输入。
- **版本对比**：仅在检测到 `resVersion` 变化时执行更新。
- **Wiki 写入**：封装 MediaWiki API 提供 `edit` / `read` / `category` / `protect` / `upload` 等操作，自动登录并带重试。
- **错误追踪**：通过 Sentry 上报运行异常。

## 项目结构

```text
ptilopsis/
├── __main__.py        # 入口，按命令行参数分派任务
├── config.py          # 各服 CDN 地址、登录凭据、FlatBuffers 表名等
├── jobs/              # 各类 Wiki 更新任务
│   ├── basic.py           # 干员基础信息
│   ├── sidebar.py         # 侧边栏干员一览
│   ├── charword.py        # 干员语音 / 档案
│   ├── skin.py            # 皮肤 / 立绘
│   ├── stage.py           # 关卡（含悖论模拟、剿灭等）
│   ├── enemy.py           # 敌人图鉴 / 数据
│   ├── building_buff.py   # 基建技能
│   ├── furni.py           # 家具
│   ├── item.py            # 道具
│   ├── medal.py           # 勋章
│   ├── mission.py         # 任务
│   ├── newModule.py       # 新模组
│   ├── activity.py        # 活动
│   ├── char_attr.py       # 干员属性
│   ├── story_review.py    # 剧情回顾
│   ├── term.py            # 术语
│   ├── update_jp.py       # JP 服增量更新
│   ├── weedy.py           # 高规格自动任务
│   └── ...
└── utils/
    ├── data.py            # GameData，统一访问解包/仓库数据
    ├── unpacker.py        # 官方资源下载 + FlatBuffers 解析
    ├── wiki.py            # MediaWiki API 客户端（带 retry）
    ├── job.py             # Job 基类
    └── richTextStyles.py  # 游戏富文本 → Wiki 模板转换
thirdparty/
├── OpenArknightsFBS/         # FlatBuffers schema (submodule)
├── ArknightsGameData/        # 国服游戏数据 (submodule)
└── ArknightsGameData_YoStar/ # 海外服游戏数据 (submodule)
.github/workflows/         # GitHub Actions 定时 / 手动触发
version_local.json         # 本地已更新到的资源版本
version_remote.json        # 通过 --remote 拉取时使用的版本记录
```

## 环境准备

- Python ≥ 3.13
- [uv](https://docs.astral.sh/uv/)
- `flatc`（FlatBuffers 编译器，运行时位于仓库根目录调用）

```bash
git clone --recurse-submodules https://github.com/MooncellWiki/Ptilopsis_Bot.git
cd Ptilopsis_Bot
uv sync --locked
```

如果忘记 `--recurse-submodules`，可以补一句：

```bash
git submodule update --init --recursive
```

## 运行

`uv sync` 后会注册 `ptil` 命令

```bash
ptil [flags] [modes ...]
```

### 标志位（flags）

| 参数 | 作用 |
| --- | --- |
| `--check` | 检查 CN 服是否有新版本，无更新则退出 |
| `--check-jp` | 检查 JP / US / KR 服是否有新版本 |
| `--check-global` | 检查所有海外服版本后退出 |
| `--remote` | 使用 `ArknightsGameData` 仓库作为数据源，自动 `git submodule update --remote` 并在结束后提交推送 |
| `--force` | 即便没有新版本也强制运行 |
| `--dev` | Wiki 客户端进入预览模式，仅打印将要提交的内容，不实际写入 |
| `-h`, `--help` | 显示完整帮助 |

### 任务模式（modes，可组合）

| 模式 | 包含任务 |
| --- | --- |
| `new` | 新干员相关：`Sidebar` → `Basic` → `Charword` |
| `regular` | 常规更新：基建、关卡、敌人、皮肤、家具、道具、新模组、活动、任务、属性、勋章、剧情、术语 |
| `special` | 干员详情 / 密录、悖论模拟、剿灭、语音补全等 |
| `jp` | JP 服增量更新 |
| `weedy` | 高规格自动任务 |
| `demand` | 占位 / 调试入口 |

### 常用调用示例

```bash
# 仅检查 CN 服并执行常规更新
ptil --check regular

# 通过远程数据仓库拉取最新数据，跑完 new + regular + special 并提交
ptil --check --remote new regular special

# 检查并更新 JP 服
ptil --check-jp --remote jp

# 预览模式：不真正提交到 Wiki
ptil --dev regular
```

## GitHub Actions

| Workflow | 触发 | 命令 |
| --- | --- | --- |
| `main-cn` | `workflow_dispatch` | `ptil --check --remote new regular special` |
| `main-cn-force` | `workflow_dispatch` | 同上，附 `--force` |
| `main-jp` | `workflow_dispatch` | `ptil --check-jp --remote jp` |
| `weedy` | `workflow_dispatch` | `ptil weedy` |
| `ruff` | `push: master` / PR | Ruff lint |

## 开发

使用 [Ruff](https://github.com/astral-sh/ruff)

```bash
uv run ruff check .
uv run ruff format .
```

仓库已配置 `pre-commit`，建议本地启用：

```bash
uv run pre-commit install
```

## 致谢

- [MooncellWiki/OpenArknightsFBS](https://github.com/MooncellWiki/OpenArknightsFBS) — FlatBuffers schema
- [Kengxxiao/ArknightsGameData](https://github.com/Kengxxiao/ArknightsGameData) — 国服游戏数据
- [Kengxxiao/ArknightsGameData_YoStar](https://github.com/Kengxxiao/ArknightsGameData_YoStar) — 海外服游戏数据
