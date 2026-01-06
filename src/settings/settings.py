from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    NEO4J_URI: str = Field(..., alias="NEO4J_URI")
    NEO4J_USER: str = Field(..., alias="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(..., alias="NEO4J_PASSWORD")


settings = Settings()
