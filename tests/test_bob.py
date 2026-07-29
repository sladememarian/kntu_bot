"""Unit tests for Bob — simplified."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="kntu_bob_test_")
os.environ["DATABASE_URL"] = ""
os.environ["DATA_FILE"] = os.path.join(_TMP, "data.json")
os.environ.setdefault("BOT_TOKEN", "x")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_bob_handlers_import():
    from handlers import bob_ai
    assert callable(bob_ai.bob_cmd)
    assert callable(bob_ai.bobstats_cmd)
