"""python -m workbench"""

import os

import uvicorn

from workbench import config

if __name__ == "__main__":
    uvicorn.run("workbench.main:app", host=os.environ.get("WORKBENCH_HOST", "127.0.0.1"),
                port=config.PORT, log_level="warning")
