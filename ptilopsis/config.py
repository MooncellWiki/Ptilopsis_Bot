"""配置加载与校验。

非敏感配置放在仓库根目录的 config.json，由 pydantic 校验后使用；
Wiki 登录凭据、Sentry DSN 等敏感信息一律走环境变量（本地开发可用 .env）。
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_ENV_VAR = "PTILOPSIS_CONFIG_PATH"
"""与 Settings.config_path 对应（env_prefix + 字段名），仅用于报错提示。"""
CONFIG_FILENAME = "config.json"


class ServerConfig(BaseModel):
    """config.json 中 serverList 下单个服务器的配置。"""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    folder: str
    """解包数据落盘的目录名，如 zh_CN。"""
    files: str
    """需要解包的资源前缀，如 gamedata / gamedata/excel。"""
    update_msg: str
    """检测到更新时输出的日志模板，占位符为 {0} 客户端版本、{1} 资源版本。"""
    res_url: str
    """资源 CDN 根地址。"""
    config_url: str
    """版本号 / network_config 接口根地址。"""
    chat_mask: str
    """该服务器数据解密使用的 chatMask。"""
    enable_flat_buffers: bool = False
    """该服务器的 gamedata 是否为 FlatBuffers 格式。"""
    flat_buffers: list[str] = []
    """需要按 FlatBuffers 解析的表名，仅在 enable_flat_buffers 为真时有意义。"""


class Config(BaseModel):
    """config.json 的整体结构，不包含任何敏感信息。"""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )

    api_url: str
    """MediaWiki api.php 地址。"""
    torappu_url: str
    """torappu 资源仓库地址,国服 gamedata 从这里读取。"""
    version: str
    """记录各服版本号的 json 文件路径。"""
    server_list: dict[str, ServerConfig]
    """按服务器代号索引的配置。"""
    chat_mask_list: list[str]
    """历史上出现过的 chatMask，解密时逐个尝试。"""


class Settings(BaseSettings):
    """敏感配置，全部来自环境变量（前缀 PTILOPSIS_）。"""

    model_config = SettingsConfigDict(
        env_prefix="PTILOPSIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    config_path: str = ""
    """config.json 路径覆盖，对应 PTILOPSIS_CONFIG_PATH。

    走 BaseSettings 而非直接读 os.environ，才能同时支持真实环境变量与 .env。
    """
    username: str = ""
    """Wiki 登录用户名，对应 PTILOPSIS_USERNAME。"""
    password: SecretStr = SecretStr("")
    """Wiki 登录密码，建议使用 Special:BotPasswords 生成，对应 PTILOPSIS_PASSWORD。"""
    sentry_dsn: str = ""
    """Sentry DSN，对应 PTILOPSIS_SENTRY_DSN，留空则不启用上报。"""

    def require_wiki_credentials(self) -> tuple[str, str]:
        """返回 (username, password)，缺失时抛出带指引的异常。"""
        missing = [
            name
            for name, value in (
                ("PTILOPSIS_USERNAME", self.username),
                ("PTILOPSIS_PASSWORD", self.password.get_secret_value()),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"缺少 Wiki 登录凭据环境变量: {', '.join(missing)}。"
                "CI 请在仓库 Settings → Secrets 中配置并注入；"
                "本地开发可在项目根目录创建 .env（参考 .env.example）。"
            )
        return self.username, self.password.get_secret_value()


def _resolve_config_path() -> Path:
    """按 环境变量 / .env → 当前工作目录 → 包同级目录 的顺序定位 config.json。"""
    if override := get_settings().config_path:
        return Path(override)
    cwd_candidate = Path.cwd() / CONFIG_FILENAME
    if cwd_candidate.is_file():
        return cwd_candidate
    return Path(__file__).resolve().parent.parent / CONFIG_FILENAME


def load_config(path: Path | None = None) -> Config:
    """读取并校验 config.json。"""
    config_path = path or _resolve_config_path()
    if not config_path.is_file():
        raise FileNotFoundError(
            f"找不到配置文件 {config_path}；"
            f"可通过环境变量 {CONFIG_ENV_VAR} 指定其他路径。"
        )
    with config_path.open(encoding="utf-8") as f:
        return Config.model_validate(json.load(f))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """惰性读取环境变量，避免仅解包 / 跑测试时也要求提供凭据。"""
    return Settings()


config = load_config()
