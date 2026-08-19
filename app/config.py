from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str="sqlite:///./feed_builder.db"
    REDIS_URL: str
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_INTERACTIONS_TOPIC: str = "interactions_topic"
    KAFKA_COMMENTS_TOPIC: str = "comments_topic"
    REDIS_REBUILD_INTERVAL: str = "6h"
    DB_ECHO: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()