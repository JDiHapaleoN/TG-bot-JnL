"""
Automated Security, Least Privilege, Deployment Blocker, and VPS Isolation Test Suite.

Verifies with behavioral and execution tests:
1. Systemd entry point existence (/opt/jnl-bot/main.py), INI structure, sandboxing, and systemd-analyze.
2. Elimination of the NoNewPrivileges / sudo contradiction and removal of sudoers.
3. Installer security: rejection of CLI BOT_TOKEN arguments, bash syntax, -xdev / symlink guards.
4. Strict production .env selection BEFORE loading, aborting when /var/lib/jnl-bot/.env is missing.
5. Strict production storage path enforcement (no silent in-repo fallbacks).
6. SQLite WAL-reset bug mitigation and db_rollback_failed.flag startup blocker.
7. Active bot detection (bot.lock) refusing live schema migrations while bot is running.
8. Real execution of deploy/auto_update.sh: active-bot refusal, full Code + DB rollback, and clean update.
9. Verification that WEBAPP_PORT=0 opens no TCP listening port.
"""

import configparser
import fcntl
import os
import py_compile
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.config import (
    PROD_BACKUP_DIR,
    PROD_DATA_DIR,
    PROD_DB_FILE,
    _detect_app_env,
    _load_environment_file,
    _resolve_production_backup_dir,
    _resolve_production_database_url,
)
from bot.database.crud import add_transaction, create_or_update_user, get_user_balance, get_user_by_telegram_id
from bot.database.migrations import apply_live_migrations, is_bot_active
from bot.database.session import configure_sqlite_engine, init_db, is_sqlite_wal_safe, parse_sqlite_version


def _make_engine(db_path: Path):
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 15})
    configure_sqlite_engine(eng)
    return eng


class SecurityLeastPrivilegeSuite(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.deploy_dir = cls.repo_root / "deploy"
        cls.bot_service_file = cls.deploy_dir / "jnl-bot.service"
        cls.updater_service_file = cls.deploy_dir / "jnl-bot-updater.service"
        cls.updater_timer_file = cls.deploy_dir / "jnl-bot-updater.timer"
        cls.sudoers_file = cls.deploy_dir / "jnl-bot.sudoers"
        cls.installer_script = cls.deploy_dir / "install_vps.sh"
        cls.updater_script = cls.deploy_dir / "auto_update.sh"

    def test_01_systemd_entrypoint_and_unit_verification(self):
        """Test 1: Parse ExecStart in systemd unit files, verify target files exist and compile, and validate directives."""
        self.assertTrue(self.bot_service_file.exists(), "jnl-bot.service must exist")
        self.assertTrue(self.updater_service_file.exists(), "jnl-bot-updater.service must exist")

        # Parse both unit files as strict INI structures
        for unit_file in (self.bot_service_file, self.updater_service_file, self.updater_timer_file):
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.read(unit_file, encoding="utf-8")
            self.assertIn("Unit", cp.sections(), f"[Unit] missing in {unit_file.name}")

        bot_cp = configparser.ConfigParser(interpolation=None, strict=False)
        bot_cp.read(self.bot_service_file, encoding="utf-8")
        self.assertIn("Service", bot_cp.sections())

        # Verify WorkingDirectory and ExecStart target file actually exists in repository
        work_dir = bot_cp.get("Service", "WorkingDirectory")
        exec_start = bot_cp.get("Service", "ExecStart")
        self.assertEqual(work_dir, "/opt/jnl-bot")
        self.assertEqual(exec_start, "/opt/jnl-bot/.venv/bin/python /opt/jnl-bot/main.py")
        self.assertNotIn("run.py", exec_start, "ExecStart must not reference non-existent run.py")

        parts = exec_start.split()
        self.assertEqual(len(parts), 2)
        script_rel = Path(parts[1]).relative_to("/opt/jnl-bot")
        actual_entrypoint = self.repo_root / script_rel
        self.assertTrue(
            actual_entrypoint.exists() and actual_entrypoint.is_file(),
            f"Entrypoint file {actual_entrypoint} referenced by ExecStart does not exist!",
        )
        # Compile entrypoint to verify valid Python syntax
        py_compile.compile(str(actual_entrypoint), doraise=True)

        # Verify updater ExecStart target exists
        upd_cp = configparser.ConfigParser(interpolation=None, strict=False)
        upd_cp.read(self.updater_service_file, encoding="utf-8")
        upd_exec = upd_cp.get("Service", "ExecStart")
        self.assertEqual(upd_exec, "/opt/jnl-bot/deploy/auto_update.sh")
        upd_rel = Path(upd_exec).relative_to("/opt/jnl-bot")
        actual_updater = self.repo_root / upd_rel
        self.assertTrue(actual_updater.exists() and actual_updater.is_file())

        # Verify sandboxing & identity on both services
        for svc_cp, svc_name in ((bot_cp, "jnl-bot.service"), (upd_cp, "jnl-bot-updater.service")):
            self.assertEqual(svc_cp.get("Service", "User"), "jnl-bot", f"{svc_name} must run as User=jnl-bot")
            self.assertEqual(svc_cp.get("Service", "Group"), "jnl-bot", f"{svc_name} must run as Group=jnl-bot")
            self.assertEqual(svc_cp.get("Service", "EnvironmentFile"), "/var/lib/jnl-bot/.env")
            self.assertEqual(svc_cp.get("Service", "NoNewPrivileges"), "true")
            self.assertEqual(svc_cp.get("Service", "ProtectSystem"), "strict")
            self.assertEqual(svc_cp.get("Service", "ProtectHome"), "true")
            self.assertEqual(svc_cp.get("Service", "PrivateTmp"), "true")
            self.assertEqual(svc_cp.get("Service", "RestrictSUIDSGID"), "true")
            self.assertEqual(svc_cp.get("Service", "CapabilityBoundingSet"), "")
            self.assertEqual(svc_cp.get("Service", "AmbientCapabilities"), "")

            inaccessible = svc_cp.get("Service", "InaccessiblePaths")
            for forbidden in ("/home", "/var/www", "/root", "/usr/local/hestia"):
                self.assertIn(forbidden, inaccessible, f"{svc_name} must block {forbidden}")

        # Run systemd-analyze verify if available on Linux host
        if shutil.which("systemd-analyze"):
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                for unit in (self.bot_service_file, self.updater_service_file):
                    text = unit.read_text(encoding="utf-8")
                    # Substitute /opt/jnl-bot/.venv/bin/python and scripts with /bin/true so systemd-analyze
                    # can verify unit syntax even before /opt/jnl-bot is populated
                    text = re.sub(r"^ExecStart=.*$", "ExecStart=/bin/true", text, flags=re.MULTILINE)
                    target_unit = tmp_path / unit.name
                    target_unit.write_text(text, encoding="utf-8")
                    res = subprocess.run(
                        ["systemd-analyze", "verify", str(target_unit)],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        res.returncode,
                        0,
                        f"systemd-analyze verify failed for {unit.name}: {res.stderr}",
                    )

    def test_02_no_sudo_contradiction_and_no_sudoers(self):
        """Test 2: Verify sudoers is removed and updater never invokes sudo or privileged systemctl commands."""
        self.assertFalse(
            self.sudoers_file.exists(),
            "jnl-bot.sudoers must not exist; jnl-bot must have zero sudo privileges",
        )

        updater_content = self.updater_script.read_text(encoding="utf-8")
        active_lines = [
            line.strip()
            for line in updater_content.splitlines()
            if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("echo ")
        ]
        active_code = "\n".join(active_lines)

        self.assertNotRegex(
            active_code,
            r"\bsudo\b",
            "auto_update.sh must never execute sudo (incompatible with NoNewPrivileges=true)",
        )
        self.assertNotRegex(
            active_code,
            r"\bsystemctl\s+(restart|start|stop|reload|enable|disable)\b",
            "auto_update.sh must never attempt privileged systemctl service management",
        )

    def test_03_installer_security_and_cli_token_rejection(self):
        """Test 3: Execute install_vps.sh with a CLI argument to verify it rejects exposing BOT_TOKEN, and check bash syntax."""
        # 1. Verify bash syntax of both scripts
        for script in (self.installer_script, self.updater_script):
            res = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Syntax error in {script.name}: {res.stderr}")

        # 2. Behavioral test: passing BOT_TOKEN as CLI argument must fail closed immediately
        res_cli = subprocess.run(
            ["bash", str(self.installer_script), "123456:SECRET_TOKEN_ARG"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertNotEqual(res_cli.returncode, 0, "install_vps.sh must reject CLI arguments")
        self.assertIn("Do not pass BOT_TOKEN or arguments on the command line", res_cli.stderr)

        # 3. Verify installer filesystem hardening directives
        installer_content = self.installer_script.read_text(encoding="utf-8")
        for cmd in ("apt-get install", "apt-get update", "apt-get upgrade", "apt install", "apt update"):
            self.assertNotIn(f"\n{cmd}", installer_content)
            self.assertNotIn(f"    {cmd}", installer_content)

        self.assertIn("find -P \"$INSTALL_DIR\" -xdev -not -type l -exec chown -h", installer_content)
        self.assertIn("find -P \"$PERSISTENT_ROOT\" -xdev -not -type l -exec chown -h", installer_content)
        self.assertIn("verify_canonical_dir", installer_content)
        self.assertIn("verify_no_external_symlinks", installer_content)
        self.assertIn("systemctl disable --now jnl-bot-updater.timer", installer_content)
        self.assertNotIn("check_sqlite || true", installer_content)

    def test_04_production_env_selection_and_missing_env_abort(self):
        """Test 4: Verify production environment is determined first and aborts if /var/lib/jnl-bot/.env is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            missing_prod_env = tmp / "nonexistent_prod.env"
            dev_env = tmp / "local_dev.env"
            dev_env.write_text("BOT_TOKEN=DEV_FALLBACK_TOKEN\n", encoding="utf-8")

            # 1. In production, missing canonical .env must raise RuntimeError and NEVER load dev_env
            with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
                os.environ.pop("BOT_TOKEN", None)
                self.assertEqual(_detect_app_env(), "production")
                with self.assertRaises(RuntimeError) as ctx:
                    _load_environment_file("production", prod_env_file=missing_prod_env, dev_env_file=dev_env)
                self.assertIn("Canonical production configuration file", str(ctx.exception))
                self.assertIsNone(os.environ.get("BOT_TOKEN"), "Must not load dev .env in production!")

            # 2. In production, existing canonical .env loads properly
            real_prod_env = tmp / "prod.env"
            real_prod_env.write_text("BOT_TOKEN=PROD_VERIFIED_TOKEN\n", encoding="utf-8")
            real_prod_env.chmod(0o600)
            with patch.dict(os.environ, {"APP_ENV": "production"}, clear=False):
                os.environ.pop("BOT_TOKEN", None)
                loaded_path = _load_environment_file(
                    "production", prod_env_file=real_prod_env, dev_env_file=dev_env
                )
                self.assertEqual(loaded_path, real_prod_env)
                self.assertEqual(os.environ.get("BOT_TOKEN"), "PROD_VERIFIED_TOKEN")
                os.environ.pop("BOT_TOKEN", None)

    def test_05_strict_production_storage_path_enforcement(self):
        """Test 5: Verify production storage strictly requires /var/lib/jnl-bot and rejects in-repo fallbacks."""
        with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": "sqlite+aiosqlite:///./data/finance.db"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_database_url()
            self.assertIn("Prohibited database path in production", str(ctx.exception))

        with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": "sqlite+aiosqlite:////opt/jnl-bot/data/finance_bot.db"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_database_url()
            self.assertIn("Prohibited database path in production", str(ctx.exception))

        with patch.dict(os.environ, {"APP_ENV": "production", "BACKUP_DIR": "/opt/jnl-bot/backups"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_backup_dir()
            self.assertIn("Prohibited backup path in production", str(ctx.exception))

        with patch.dict(os.environ, {"APP_ENV": "production", "BACKUP_DIR": "/var/backups"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_backup_dir()
            self.assertIn("Prohibited backup path in production", str(ctx.exception))

        with tempfile.TemporaryDirectory() as tmpdir:
            non_writable_dir = Path(tmpdir) / "unwritable_prod"
            non_writable_dir.mkdir(parents=True, exist_ok=True)
            non_writable_dir.chmod(0o400)
            try:
                with patch("bot.config.PROD_DATA_DIR", non_writable_dir):
                    with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": ""}):
                        with self.assertRaises(RuntimeError) as ctx:
                            _resolve_production_database_url()
                        self.assertIn("not writable", str(ctx.exception))
            finally:
                non_writable_dir.chmod(0o700)

    async def test_06_sqlite_wal_reset_and_rollback_flag_gate(self):
        """Test 6: Verify WAL-reset version checks and verify init_db blocks startup when db_rollback_failed.flag exists."""
        self.assertTrue(is_sqlite_wal_safe((3, 51, 3)))
        self.assertTrue(is_sqlite_wal_safe((3, 52, 0)))
        self.assertTrue(is_sqlite_wal_safe((3, 50, 7)))
        self.assertTrue(is_sqlite_wal_safe((3, 44, 6)))
        self.assertFalse(is_sqlite_wal_safe((3, 37, 2)))
        self.assertFalse(is_sqlite_wal_safe((3, 50, 4)))
        self.assertFalse(is_sqlite_wal_safe((3, 51, 2)))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            test_db = tmp / "test_wal_fail.db"
            mock_engine = _make_engine(test_db)

            # 1. Vulnerable SQLite version in production raises RuntimeError
            with patch("bot.database.session.settings") as mock_settings:
                mock_settings.app_env = "production"
                with patch("bot.database.session.is_sqlite_wal_safe", return_value=False):
                    with self.assertRaises(RuntimeError) as ctx:
                        await init_db(mock_engine)
                    self.assertIn("Insecure SQLite runtime version", str(ctx.exception))

            # 2. Presence of db_rollback_failed.flag blocks startup
            flag_file = tmp / "db_rollback_failed.flag"
            flag_file.write_text("Rollback failed", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx2:
                await init_db(mock_engine)
            self.assertIn("db_rollback_failed.flag", str(ctx2.exception))
            flag_file.unlink()

            await mock_engine.dispose()

    def test_07_updater_refuses_live_migration_when_bot_is_active(self):
        """Test 7: Verify that holding bot.lock causes is_bot_active and apply_live_migrations to refuse execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_path = tmp / "active_test.db"
            sqlite3.connect(str(db_path)).close()
            lock_path = tmp / "bot.lock"

            # Spawn a child process that holds an exclusive flock on bot.lock
            holder_proc = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import fcntl, sys, time; "
                        f"f = open({str(lock_path)!r}, 'w'); "
                        "fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB); "
                        "sys.stdout.write('LOCKED\\n'); sys.stdout.flush(); "
                        "time.sleep(30)"
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                line = holder_proc.stdout.readline().strip()
                self.assertEqual(line, "LOCKED")

                # 1. is_bot_active must detect the held lock
                self.assertTrue(is_bot_active(db_path, check_systemd=False))

                # 2. apply_live_migrations must refuse to run while bot is active
                with self.assertRaises(RuntimeError) as ctx:
                    apply_live_migrations(db_path, check_systemd=False)
                self.assertIn("REFUSED: Active JnL-Bot instance detected", str(ctx.exception))
            finally:
                holder_proc.terminate()
                holder_proc.wait(timeout=5)
                if holder_proc.stdout:
                    holder_proc.stdout.close()
                if holder_proc.stderr:
                    holder_proc.stderr.close()

            # Once lock holder stops, is_bot_active returns False
            self.assertFalse(is_bot_active(db_path, check_systemd=False))

    async def test_08_controlled_updater_end_to_end_and_full_db_rollback(self):
        """
        Test 8: Execute deploy/auto_update.sh in an isolated git & database environment:
        - Case A: Refuses to update when bot.lock is held.
        - Case B: Performs full Code + Database Rollback when post-migration step fails after modifying DB.
        - Case C: Completes clean update and database verification when bot is stopped.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir).resolve()
            remote_repo = tmp / "remote_origin.git"
            work_clone = tmp / "work_tree"
            install_dir = tmp / "opt_jnl_bot"
            persistent_root = tmp / "var_lib_jnl_bot"
            data_dir = persistent_root / "data"
            backup_dir = persistent_root / "backups"
            data_dir.mkdir(parents=True)
            backup_dir.mkdir(parents=True)

            # Initialize bare remote repository and populate it with current codebase
            subprocess.run(["git", "init", "--bare", str(remote_repo)], check=True, capture_output=True)
            subprocess.run(["git", "clone", str(remote_repo), str(work_clone)], check=True, capture_output=True)

            for item in ("bot", "deploy", "tests", "main.py", "requirements.txt", ".env.example"):
                src_item = self.repo_root / item
                dst_item = work_clone / item
                if src_item.is_dir():
                    shutil.copytree(
                        src_item,
                        dst_item,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    )
                else:
                    shutil.copy2(src_item, dst_item)

            subprocess.run(["git", " config", "user.email", "test@example.com"], cwd=work_clone, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work_clone, check=True)
            subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=work_clone, check=True)
            subprocess.run(["git", "checkout", "-b", "main"], cwd=work_clone, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=work_clone, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial v1"], cwd=work_clone, check=True, capture_output=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=work_clone, check=True, capture_output=True)

            # Clone into simulated /opt/jnl-bot
            subprocess.run(["git", "clone", "-b", "main", str(remote_repo), str(install_dir)], check=True, capture_output=True)
            v1_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=install_dir, check=True, capture_output=True, text=True
            ).stdout.strip()

            # Create and populate live database in simulated /var/lib/jnl-bot/data/finance_bot.db
            db_file = data_dir / "finance_bot.db"
            eng = _make_engine(db_file)
            await init_db(eng)
            sf = async_sessionmaker(eng, expire_on_commit=False)
            async with sf() as session:
                u = await create_or_update_user(session, 777001, "Prod User", currency="EUR")
                await add_transaction(session, u.id, "income", Decimal("1000.00"), "EUR", "Salary")
                await add_transaction(session, u.id, "expense", Decimal("150.00"), "EUR", "Rent")
            await eng.dispose()

            env = os.environ.copy()
            env.update(
                {
                    "APP_ENV": "testing",
                    "DATABASE_URL": f"sqlite+aiosqlite:///{db_file}",
                    "BACKUP_DIR": str(backup_dir),
                    "JNL_INSTALL_DIR": str(install_dir),
                    "JNL_PERSISTENT_ROOT": str(persistent_root),
                    "JNL_DATA_DIR": str(data_dir),
                    "JNL_BACKUP_DIR": str(backup_dir),
                    "JNL_VENV_PYTHON": sys.executable,
                    "JNL_SKIP_PIP_INSTALL": "1",
                    "JNL_SKIP_SQLITE_BUILD": "1",
                    "JNL_SKIP_UNITTESTS": "1",
                    "JNL_SKIP_SYSTEMCTL_CHECK": "1",
                }
            )

            # --- Case A: Bot is running (bot.lock held) -> updater must refuse ---
            lock_path = data_dir / "bot.lock"
            holder = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    (
                        "import fcntl, sys, time; "
                        f"f = open({str(lock_path)!r}, 'w'); "
                        "fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB); "
                        "sys.stdout.write('LOCKED\\n'); sys.stdout.flush(); "
                        "time.sleep(30)"
                    ),
                ],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(holder.stdout.readline().strip(), "LOCKED")
                res_active = subprocess.run(
                    ["bash", str(install_dir / "deploy" / "auto_update.sh")],
                    cwd=install_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(res_active.returncode, 0)
                self.assertIn("REFUSED: JnL-Bot is currently running", res_active.stderr)
            finally:
                holder.terminate()
                holder.wait(timeout=5)
                if holder.stdout:
                    holder.stdout.close()

            # --- Case B: Broken migration that deletes a transaction and then fails -> Full Code + DB Rollback ---
            migrations_py = work_clone / "bot" / "database" / "migrations.py"
            orig_migrations_code = migrations_py.read_text(encoding="utf-8")
            broken_code = orig_migrations_code.replace(
                'logger.info("Migrations successfully applied and verified on %s", src)',
                (
                    'with eng.begin() as c_bad:\n'
                    '        c_bad.execute(text("DELETE FROM transactions"))\n'
                    '    raise RuntimeError("Simulated failure after mutating live database!")'
                ),
            )
            migrations_py.write_text(broken_code, encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=work_clone, check=True)
            subprocess.run(["git", "commit", "-m", "Broken v2 migration"], cwd=work_clone, check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=work_clone, check=True, capture_output=True)

            res_fail = subprocess.run(
                ["bash", str(install_dir / "deploy" / "auto_update.sh")],
                cwd=install_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_fail.returncode, 1, f"Expected rollback exit 1, got {res_fail.returncode}: {res_fail.stderr}")
            self.assertIn("Full rollback complete: Git code reverted", res_fail.stderr)
            self.assertIn("AND database restored and verified from pre-update backup", res_fail.stderr)
            self.assertFalse((data_dir / "db_rollback_failed.flag").exists())

            # Verify Git commit reverted to v1_hash AND all transactions are restored in finance_bot.db
            curr_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=install_dir, check=True, capture_output=True, text=True
            ).stdout.strip()
            self.assertEqual(curr_hash, v1_hash)

            eng_verify = _make_engine(db_file)
            sf_verify = async_sessionmaker(eng_verify, expire_on_commit=False)
            async with sf_verify() as session:
                u_check = await get_user_by_telegram_id(session, 777001)
                self.assertIsNotNone(u_check)
                bal = await get_user_balance(session, u_check.id)
                self.assertEqual(bal, Decimal("850.00"), "Database rollback must restore exact pre-update transactions!")
            await eng_verify.dispose()

            # --- Case C: Valid v3 commit -> Clean update and verification ---
            migrations_py.write_text(orig_migrations_code, encoding="utf-8")
            (work_clone / "README.md").write_text("# Updated in v3\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=work_clone, check=True)
            subprocess.run(["git", "commit", "-m", "Clean v3 update"], cwd=work_clone, check=True, capture_output=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=work_clone, check=True, capture_output=True)
            v3_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=work_clone, check=True, capture_output=True, text=True
            ).stdout.strip()

            res_ok = subprocess.run(
                ["bash", str(install_dir / "deploy" / "auto_update.sh")],
                cwd=install_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(res_ok.returncode, 0, f"Expected clean update exit 0, got: {res_ok.stderr}\n{res_ok.stdout}")
            self.assertIn("Update to", res_ok.stdout)
            self.assertFalse((data_dir / "update_failed.flag").exists())
            self.assertFalse((data_dir / "db_rollback_failed.flag").exists())

            final_hash = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=install_dir, check=True, capture_output=True, text=True
            ).stdout.strip()
            self.assertEqual(final_hash, v3_hash)

    async def test_09_webapp_port_zero_opens_no_listening_socket(self):
        """Test 9: Verify main.py does not start an HTTP listener when WEBAPP_PORT=0."""
        import main as main_mod

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_db = Path(tmpdir) / "port_zero.db"
            with patch.object(main_mod, "resolve_sqlite_db_path", return_value=tmp_db), \
                 patch.object(main_mod, "init_db", return_value=None), \
                 patch.object(main_mod, "dispose_db", return_value=None), \
                 patch.object(main_mod, "create_database_backup", return_value=None), \
                 patch.object(main_mod, "create_webapp") as mock_create_webapp, \
                 patch.object(main_mod.web, "TCPSite") as mock_tcp_site, \
                 patch.object(main_mod, "scheduler_loop", return_value=None), \
                 patch.object(main_mod.asyncio, "Event") as mock_event:
                mock_evt_inst = mock_event.return_value

                async def _immediate_done():
                    return None

                mock_evt_inst.wait = _immediate_done

                with patch.object(main_mod, "settings") as mock_settings:
                    mock_settings.database_url = f"sqlite+aiosqlite:///{tmp_db}"
                    mock_settings.backup_dir = Path(tmpdir)
                    mock_settings.s3_backup_enabled = False
                    mock_settings.webapp_port = 0
                    mock_settings.webapp_host = "127.0.0.1"
                    mock_settings.bot_token = ""

                    await main_mod.main()

                    mock_create_webapp.assert_not_called()
                    mock_tcp_site.assert_not_called()


if __name__ == "__main__":
    unittest.main()
