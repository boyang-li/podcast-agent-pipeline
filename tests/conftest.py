import asyncio
import sys
from pathlib import Path

import os

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    path_str = str(candidate)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _configure_storage_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("pap-storage")
    os.environ["PAP_STORAGE_ROOT"] = str(root)
    os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
    os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
