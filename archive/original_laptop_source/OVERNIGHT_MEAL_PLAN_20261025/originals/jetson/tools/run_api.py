"""Launch API using validated API_HOST/API_PORT configuration."""

import uvicorn

from app.config import HardwareConfig


if __name__ == "__main__":
    settings = HardwareConfig.from_env()
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port)
