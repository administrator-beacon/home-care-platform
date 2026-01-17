from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Home Care Platform"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/home_care"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


settings = Settings()
