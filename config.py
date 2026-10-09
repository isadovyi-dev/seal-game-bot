import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN: str
    ADMIN_PASSWORD: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    PORT: int = 8080
    MAX_TL_PER_REQUEST: int = 10000
    MAX_TL_PER_USER: int = 1000000

def get_env_var(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"❌ Переменная окружения {name} не установлена!")
    return value

def load_config() -> Config:
    return Config(
        BOT_TOKEN=get_env_var("BOT_TOKEN"),
        ADMIN_PASSWORD=get_env_var("ADMIN_PASSWORD"),
        DATABASE_URL=get_env_var("DATABASE_URL"),
        REDIS_URL=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        PORT=int(os.environ.get("PORT", 8080)),
    )
