"""Application configuration, read from environment variables."""

import os

# Defaults to a local SQLite file so the app runs with zero setup.
# docker-compose overrides this with a PostgreSQL URL.
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./index_tracker.db")
