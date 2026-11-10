"""
Installer utility for compiling and installing a WAL-safe SQLite runtime (>= 3.51.3)
into the isolated Python virtual environment (.venv).

This ensures the SQLite WAL-reset bug (fixed in 3.51.3, 3.50.7, and 3.44.6)
is completely resolved without modifying any system packages or OS libraries.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from typing import Tuple

# Verified official amalgamation from sqlite.org
SQLITE_AMALGAMATION_URL = "https://www.sqlite.org/2026/sqlite-amalgamation-3510300.zip"
SQLITE_AMALGAMATION_SHA256 = "acb1e6f5d832484bf6d32b681e858c38add8b2acdfd42ac5df24b8afb46552b4"

# Official pysqlite3 source package from PyPI
PYSQLITE3_SDIST_URL = "https://files.pythonhosted.org/packages/a8/a5/4987f812f5dc6e7d37c333e889586aa2b01cba9c86b1dd7f712c871f5d88/pysqlite3-0.6.2.tar.gz"
PYSQLITE3_SDIST_SHA256 = "67b4a2c3e0f3b780cc8e5ac0efdc55a2bb99a63027070b4541eb8acd3dfb55ff"


def is_wal_safe_version(ver_tuple: Tuple[int, ...]) -> bool:
    """Return True if SQLite version contains the official WAL-reset fix."""
    if ver_tuple >= (3, 51, 3):
        return True
    if ver_tuple[:3] in ((3, 50, 7), (3, 44, 6)):
        return True
    return False


def check_existing_runtime() -> bool:
    try:
        import pysqlite3
        ver_info = getattr(pysqlite3, "sqlite_version_info", (0, 0, 0))
        ver_str = getattr(pysqlite3, "sqlite_version", "0.0.0")
        if is_wal_safe_version(ver_info):
            print(f"✅ pysqlite3 is already installed and WAL-safe: SQLite {ver_str}")
            return True
        print(f"⚠️ Installed pysqlite3 has unpatched SQLite version {ver_str}. Rebuilding...")
    except ImportError:
        print("ℹ️ pysqlite3 is not installed in current environment. Proceeding with static build...")
    return False


def build_and_install_pysqlite3() -> None:
    print("=" * 60)
    print("Building WAL-safe SQLite 3.51.3 within isolated virtual environment")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="jnl_sqlite_build_") as tmpdir:
        # 1. Download SQLite amalgamation
        print(f"==> Downloading SQLite 3.51.3 amalgamation...")
        req = urllib.request.Request(
            SQLITE_AMALGAMATION_URL,
            headers={"User-Agent": "JnL-Bot-Build/1.0"},
        )
        amalg_data = urllib.request.urlopen(req, timeout=30).read()
        amalg_hash = hashlib.sha256(amalg_data).hexdigest()
        if amalg_hash != SQLITE_AMALGAMATION_SHA256:
            raise RuntimeError(
                f"SQLite amalgamation SHA-256 mismatch! Expected {SQLITE_AMALGAMATION_SHA256}, got {amalg_hash}"
            )
        print("    Checksum verified.")

        import zipfile
        z = zipfile.ZipFile(io.BytesIO(amalg_data))
        for name in z.namelist():
            if name.endswith("sqlite3.c") or name.endswith("sqlite3.h"):
                base_name = name.split("/")[-1]
                target_path = os.path.join(tmpdir, base_name)
                with open(target_path, "wb") as f:
                    f.write(z.read(name))
        print("    Extracted sqlite3.c and sqlite3.h.")

        # 2. Download pysqlite3 source distribution
        print("==> Downloading pysqlite3 source distribution...")
        req2 = urllib.request.Request(
            PYSQLITE3_SDIST_URL,
            headers={"User-Agent": "JnL-Bot-Build/1.0"},
        )
        sdist_data = urllib.request.urlopen(req2, timeout=30).read()
        sdist_hash = hashlib.sha256(sdist_data).hexdigest()
        if sdist_hash != PYSQLITE3_SDIST_SHA256:
            raise RuntimeError(
                f"pysqlite3 source SHA-256 mismatch! Expected {PYSQLITE3_SDIST_SHA256}, got {sdist_hash}"
            )
        print("    Checksum verified.")

        tar = tarfile.open(fileobj=io.BytesIO(sdist_data), mode="r:gz")
        tar.extractall(path=tmpdir)

        pkg_dir = os.path.join(tmpdir, "pysqlite3-0.6.2")
        shutil.copy(os.path.join(tmpdir, "sqlite3.c"), os.path.join(pkg_dir, "sqlite3.c"))
        shutil.copy(os.path.join(tmpdir, "sqlite3.h"), os.path.join(pkg_dir, "sqlite3.h"))

        # 3. Compile and install statically inside current virtual environment
        print("==> Compiling pysqlite3 statically against SQLite 3.51.3...")
        env = os.environ.copy()
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-deps", "."],
            cwd=pkg_dir,
            capture_output=True,
            text=True,
            env=env,
        )

        if res.returncode != 0:
            print("❌ Compilation failed!")
            print("STDOUT:", res.stdout)
            print("STDERR:", res.stderr)
            raise RuntimeError("Failed to compile pysqlite3 with SQLite 3.51.3 amalgamation.")

        print("    Installation successful.")


def verify_installed_runtime() -> None:
    # Clear cache and import freshly installed pysqlite3
    if "pysqlite3" in sys.modules:
        del sys.modules["pysqlite3"]
    import pysqlite3
    ver_info = getattr(pysqlite3, "sqlite_version_info", (0, 0, 0))
    ver_str = getattr(pysqlite3, "sqlite_version", "0.0.0")

    if not is_wal_safe_version(ver_info):
        raise RuntimeError(
            f"Verification failed: installed SQLite version is {ver_str}, which is not WAL-safe."
        )
    print(f"✅ Verified: pysqlite3 is active with WAL-safe SQLite {ver_str}.")


def main() -> None:
    if check_existing_runtime():
        sys.exit(0)
    build_and_install_pysqlite3()
    verify_installed_runtime()


if __name__ == "__main__":
    main()

