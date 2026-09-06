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
├── config.py          # config.json 的 pydantic 模型 + 环境变量读取
├── gamedata/          # 各表的 pydantic 模型（由 FBS 生成）+ 客户端展示规则
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
│   ├── params.py          # job 可注入的现成依赖（gamedata / RichText / CharIdTable …）
│   └── ...
└── utils/
    ├── data.py            # GameData，统一访问解包/仓库数据
    ├── unpacker.py        # 官方资源下载 + FlatBuffers 解析
    ├── wiki.py            # MediaWiki API 客户端（带 retry）
    ├── di.py              # 依赖注入：Depends / analyze / Resolver
    ├── job.py             # @job 注册表、JobContext、按名字调度
    └── richTextStyles.py  # 游戏富文本 → Wiki 模板转换
thirdparty/
├── OpenArknightsFBS/         # FlatBuffers schema (submodule)
├── ArknightsGameData/        # 国服游戏数据 (submodule)
└── ArknightsGameData_YoStar/ # 海外服游戏数据 (submodule)
.github/workflows/         # GitHub Actions 定时 / 手动触发
config.json                # 非敏感配置：各服 CDN 地址、FlatBuffers 表名等
.env.example               # 敏感配置的环境变量样例
version_local.json         # 本地已更新到的资源版本
version_remote.json        # 通过 --remote 拉取时使用的版本记录
```

## 配置

配置分为两部分，**敏感信息一律不入库**：

| 内容 | 位置 | 说明 |
| --- | --- | --- |
| 各服 CDN 地址、FlatBuffers 表名、chatMask 等 | `config.json` | 随仓库提交，由 `ptilopsis/config.py` 中的 pydantic 模型校验；字段名以 camelCase 书写，多余或缺失字段会直接报错 |
| Wiki 登录凭据、Sentry DSN | 环境变量 | 本地开发用 `.env`（已被 `.gitignore` 忽略），CI 用 GitHub Actions Secrets |

需要的环境变量：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `PTILOPSIS_USERNAME` | 是 | Wiki 用户名，不带 `@BotName` 后缀 |
| `PTILOPSIS_PASSWORD` | 是 | 请使用 [Special:BotPasswords](https://prts.wiki/w/Special:BotPasswords) 生成的机器人密码，格式为 `<BotName>@<32位随机串>`，**不要使用主账号密码** |
| `PTILOPSIS_SENTRY_DSN` | 否 | 留空则不启用错误上报 |
| `PTILOPSIS_CONFIG_PATH` | 否 | 指定 `config.json` 路径，默认取工作目录 / 仓库根目录 |

本地开发：

```bash
cp .env.example .env   # 然后填入真实值
```

CI：在仓库 Settings → Secrets and variables → Actions 中添加同名 Secret，
`main1` ~ `main4` 四个 workflow 会自动注入。

> 注意：改动主账号密码会使该账号下**所有** BotPassword 失效，需要重新生成并更新 Secret。

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
| `new` | 新干员相关：`sidebar.update` → `basic.run` → `charword.run` |
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

### 数据模型

`ptilopsis/gamedata/` 下的整表模型由 `thirdparty/OpenArknightsFBS/FBS/*.fbs` 生成，
FBS 更新后重新生成对应的表即可：

```bash
uv run python scripts/gen_gamedata_models.py character_table skill_table
```

FlatBuffers 里 string / table / vector 字段都可能缺失，生成的模型把它们一律声明成
`T | None`，未判空的访问会被 pyright 指出；标量按 FBS 默认值填充，枚举字段保留成员名字符串。

### 页面比对

改动 `basic` / `char_attr` 的渲染逻辑后，用 `scripts/parity_basic.py` 把重构前后的页面落盘做 diff：

```bash
PYTHONHASHSEED=0 uv run python scripts/parity_basic.py out/before
# 切换分支后
PYTHONHASHSEED=0 uv run python scripts/parity_basic.py out/after
diff -r out/before out/after
```

仓库已配置 `pre-commit`，建议本地启用：

```bash
uv run pre-commit install
```

### 编写 job

job 是用 `@job` 注册的普通函数，参数按注解注入（实现见 `ptilopsis/utils/di.py`，
借鉴 torappu 的 task 写法）：

```python
from typing import Annotated, Any

from ptilopsis.jobs.params import CharIdTable, RawItemTable, RichText, category, gamedata
from ptilopsis.utils.job import SkipJob, job
from ptilopsis.utils.wiki import Wiki


@job
def run(
    wiki: Wiki,
    item_table: RawItemTable,
    stage_table: Annotated[dict[str, Any], gamedata("excel/stage_table.json")],
    id_table: CharIdTable,
    rts: RichText,
    pages: Annotated[list[str], category("分类:道具")],
) -> None:
    ...
```

- `Wiki` / `GameData` / `Config` / `JobContext` 直接按类型注入，其余依赖用 `Depends`
  标记；`params.py` 里放着各 job 共用的表、富文本转换器、干员序号表等。
- 同一次运行里相同的依赖只解析一次；依赖或 job 抛 `SkipJob` 表示这次没事可做。
- job 名默认是 `<模块>.<函数>`，`__main__.py` 的 `MODE_JOBS` 用它编排各模式的执行顺序。
  签名有问题（参数注不进去）会在导入时就报错。
- 旧写法 `def run(ctx: JobContext)` 仍然可用，逐个改写即可。

## 致谢

- [MooncellWiki/OpenArknightsFBS](https://github.com/MooncellWiki/OpenArknightsFBS) — FlatBuffers schema
- [Kengxxiao/ArknightsGameData](https://github.com/Kengxxiao/ArknightsGameData) — 国服游戏数据
- [Kengxxiao/ArknightsGameData_YoStar](https://github.com/Kengxxiao/ArknightsGameData_YoStar) — 海外服游戏数据
