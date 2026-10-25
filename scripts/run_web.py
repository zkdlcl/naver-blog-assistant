import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

from core.config import load_config


def main() -> None:
    config = load_config()
    uvicorn.run(
        "webapp.main:create_app",
        factory=True,
        host=config.app_host,
        port=config.app_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
