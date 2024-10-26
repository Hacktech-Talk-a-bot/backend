from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./forms.db"
    API_V1_STR: str = "/api"
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    NGROK_AUTH_TOKEN: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
