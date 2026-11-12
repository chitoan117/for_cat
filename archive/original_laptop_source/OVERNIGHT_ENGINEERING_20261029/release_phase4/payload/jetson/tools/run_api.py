"""Launch API using validated API_HOST/API_PORT configuration."""

import uvicorn

from app.config import HardwareConfig


if __name__ == "__main__":
    settings = HardwareConfig.from_env()
    # Keep the real loopback peer for the trusted Tailscale Serve boundary.
    # Forwarded headers are validated by the camera access middleware itself.
    uvicorn.run("app.main:app", host=settings.api_host, port=settings.api_port, proxy_headers=False)
