from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    # Autenticacao servico-a-servico (header X-Internal-API-Key)
    INTERNAL_API_KEY: str = "change-me-in-production"

    # Limiares dos indicadores (todos configuráveis via .env)
    ABANDON_MINUTES: int = 30
    STUCK_MESSAGES: int = 5
    STUCK_SIMILARITY_RATIO: float = 0.7

    GROQ_API_KEY: str = ""

    @property
    def DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
