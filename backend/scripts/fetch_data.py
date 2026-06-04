"""
Stand-alone CLI: `python -m scripts.fetch_data`

Runs the same pipeline as POST /refresh without starting the web server.
Useful for cron jobs and manual debugging.
"""
import asyncio
import sys
from pathlib import Path

# Make the `app` package importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data_pipeline import refresh_all  # noqa: E402
from app.database import SessionLocal, init_db  # noqa: E402


async def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = await refresh_all(db)
        print("Refresh complete:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
