import os
import subprocess
import sys
from pathlib import Path


def test_vercel_storage_uses_writable_temp_directory():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["VERCEL"] = "true"
    env.pop("VERCEL_ENV", None)
    script = """
import tempfile
from pathlib import Path

import config
from database.history import init_db

expected_dir = Path(tempfile.gettempdir()) / "sara-ai"
assert Path(config.DATABASE_PATH).parent == expected_dir / "database"
init_db()
"""

    subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        check=True,
    )
