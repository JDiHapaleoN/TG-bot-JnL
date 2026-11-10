"""
Automated Security, Least Privilege, and VPS Isolation Test Suite.

Verifies:
1. Systemd service sandboxing (No root, ProtectSystem, ProtectHome, InaccessiblePaths).
2. Updater least privilege and scoped sudoers policy (no wildcards).
3. Installer and updater static safety (no apt-get, no reboot, no broad cleanup, fail-closed diagnostics).
4. Strict production storage path enforcement (no silent in-repo fallbacks).
5. SQLite WAL-reset bug mitigation (verification of safe versions: >= 3.51.3, 3.50.7, 3.44.6, rejection of vulnerable runtimes).
"""

import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot.config import (
    APP_ENV,
    PROD_BACKUP_DIR,
    PROD_DATA_DIR,
    PROD_DB_FILE,
    _resolve_production_backup_dir,
    _resolve_production_database_url,
    get_settings,
)
from bot.database.session import is_sqlite_wal_safe, parse_sqlite_version


class SecurityLeastPrivilegeSuite(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parent.parent
        cls.deploy_dir = cls.repo_root / "deploy"
        cls.bot_service_file = cls.deploy_dir / "jnl-bot.service"
        cls.updater_service_file = cls.deploy_dir / "jnl-bot-updater.service"
        cls.sudoers_file = cls.deploy_dir / "jnl-bot.sudoers"
        cls.installer_script = cls.deploy_dir / "install_vps.sh"
        cls.updater_script = cls.deploy_dir / "auto_update.sh"

    def test_01_systemd_bot_service_least_privilege_and_sandboxing(self):
        """Test 1: Verify jnl-bot.service runs as unprivileged user and enforces strict kernel sandboxing."""
        self.assertTrue(self.bot_service_file.exists(), "jnl-bot.service must exist")
        content = self.bot_service_file.read_text(encoding="utf-8")

        # 1. Must run under dedicated unprivileged account, NOT root
        self.assertTrue(
            re.search(r"^User=jnl-bot", content, re.MULTILINE),
            "Service must declare User=jnl-bot",
        )
        self.assertTrue(
            re.search(r"^Group=jnl-bot", content, re.MULTILINE),
            "Service must declare Group=jnl-bot",
        )
        self.assertFalse(
            re.search(r"^User=root", content, re.MULTILINE),
            "Service must NEVER declare User=root",
        )

        # 2. Kernel sandboxing directives
        self.assertIn("NoNewPrivileges=true", content)
        self.assertIn("ProtectSystem=strict", content)
        self.assertIn("ProtectHome=true", content)
        self.assertIn("PrivateTmp=true", content)
        self.assertIn("ProtectKernelTunables=true", content)
        self.assertIn("ProtectKernelModules=true", content)
        self.assertIn("ProtectControlGroups=true", content)
        self.assertIn("RestrictRealtime=true", content)
        self.assertIn("RestrictSUIDSGID=true", content)

        # 3. Drop all capabilities
        self.assertIn("CapabilityBoundingSet=", content)
        self.assertIn("AmbientCapabilities=", content)

        # 4. Explicit filesystem boundaries: Client website and HestiaCP must be Inaccessible
        self.assertIn("InaccessiblePaths=", content)
        for forbidden in ("/home", "/var/www", "/root", "/usr/local/hestia"):
            self.assertIn(forbidden, content, f"InaccessiblePaths must include {forbidden}")

        # 5. ReadWritePaths restricted to jnl-bot data and backups
        self.assertIn("ReadWritePaths=/var/lib/jnl-bot/data /var/lib/jnl-bot/backups", content)
        self.assertIn("ReadOnlyPaths=/opt/jnl-bot /var/lib/jnl-bot/.env", content)

    def test_02_systemd_updater_service_least_privilege(self):
        """Test 2: Verify updater service runs under unprivileged account with tight sandboxing."""
        self.assertTrue(self.updater_service_file.exists(), "jnl-bot-updater.service must exist")
        content = self.updater_service_file.read_text(encoding="utf-8")

        self.assertTrue(
            re.search(r"^User=jnl-bot", content, re.MULTILINE),
            "Updater must declare User=jnl-bot",
        )
        self.assertTrue(
            re.search(r"^Group=jnl-bot", content, re.MULTILINE),
            "Updater must declare Group=jnl-bot",
        )
        self.assertFalse(
            re.search(r"^User=root", content, re.MULTILINE),
            "Updater must NEVER declare User=root",
        )

        self.assertIn("ProtectHome=true", content)
        self.assertIn("ProtectSystem=strict", content)
        self.assertIn("InaccessiblePaths=", content)
        for forbidden in ("/home", "/var/www", "/root", "/usr/local/hestia"):
            self.assertIn(forbidden, content)

    def test_03_sudoers_policy_has_no_wildcards(self):
        """Test 3: Verify sudoers configuration strictly restricts commands with zero wildcards."""
        self.assertTrue(self.sudoers_file.exists(), "jnl-bot.sudoers must exist")
        content = self.sudoers_file.read_text(encoding="utf-8").strip()

        # Must strictly grant restart only to jnl-bot.service
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
        self.assertEqual(len(lines), 1, "There must be exactly one active rule in jnl-bot.sudoers")

        rule = lines[0]
        # Must not contain wildcards in rule
        self.assertNotIn("*", rule, "Sudoers rule must NEVER contain wildcards (*)")
        self.assertTrue(rule.startswith("jnl-bot ALL=(root) NOPASSWD:"))
        self.assertIn("/bin/systemctl restart jnl-bot.service", rule)
        self.assertIn("/bin/systemctl is-active --quiet jnl-bot.service", rule)
        # Ensure no other service can be restarted
        self.assertNotIn("nginx", rule.lower())
        self.assertNotIn("apache", rule.lower())
        self.assertNotIn("hestia", rule.lower())
        self.assertNotIn("mysql", rule.lower())

    def test_04_installer_and_updater_static_safety(self):
        """Test 4: Verify installer and updater never modify system-wide packages or website services."""
        self.assertTrue(self.installer_script.exists())
        self.assertTrue(self.updater_script.exists())

        installer_content = self.installer_script.read_text(encoding="utf-8")
        updater_content = self.updater_script.read_text(encoding="utf-8")

        # 1. Prohibit automatic apt-get commands
        for cmd in ("apt-get install", "apt-get update", "apt-get upgrade", "apt install", "apt update"):
            self.assertNotIn(f"\n{cmd}", installer_content, f"installer must not run '{cmd}' automatically")
            self.assertNotIn(f"    {cmd}", installer_content, f"installer must not run '{cmd}' automatically")
            self.assertNotIn(cmd, updater_content, f"updater must not run '{cmd}'")

        # 2. Prohibit broad cleanup or destructive system commands
        for dangerous in ("rm -rf /", "reboot", "shutdown", "mkfs", "dd if="):
            self.assertNotIn(dangerous, installer_content)
            self.assertNotIn(dangerous, updater_content)

        # 3. Prohibit modifying or touching client website components
        for web_service in ("nginx", "apache2", "php", "hestia", "mysql", "mariadb"):
            self.assertNotRegex(
                installer_content,
                rf"\b(systemctl (restart|reload|stop|disable) {web_service})\b",
                f"installer must not modify web service {web_service}",
            )
            self.assertNotRegex(
                updater_content,
                rf"\b(systemctl (restart|reload|stop|disable) {web_service})\b",
                f"updater must not modify web service {web_service}",
            )

        # 4. Diagnostics in installer must FAIL CLOSED (no '|| true')
        self.assertNotIn(
            "check_sqlite || true",
            installer_content,
            "SQLite diagnostic in installer must fail closed (never ignore errors with '|| true')",
        )

        # 5. Installer must NOT enable auto-updater timer by default
        self.assertNotIn(
            "systemctl enable --now jnl-bot-updater.timer",
            installer_content,
            "Auto-updater timer must NOT be enabled by default to protect client website",
        )

    def test_05_strict_production_storage_path_enforcement(self):
        """Test 5: Verify production storage strictly requires /var/lib/jnl-bot and rejects in-repo fallbacks."""
        # 1. Prohibited in-repo database URL in production must raise RuntimeError
        with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": "sqlite+aiosqlite:///./data/finance.db"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_database_url()
            self.assertIn("Prohibited database path in production", str(ctx.exception))

        with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": "sqlite+aiosqlite:////opt/jnl-bot/data/finance_bot.db"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_database_url()
            self.assertIn("Prohibited database path in production", str(ctx.exception))

        # 2. Prohibited in-repo backup directory in production must raise RuntimeError
        with patch.dict(os.environ, {"APP_ENV": "production", "BACKUP_DIR": "/opt/jnl-bot/backups"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_backup_dir()
            self.assertIn("Prohibited backup path in production", str(ctx.exception))

        with patch.dict(os.environ, {"APP_ENV": "production", "BACKUP_DIR": "/var/backups"}):
            with self.assertRaises(RuntimeError) as ctx:
                _resolve_production_backup_dir()
            self.assertIn("Prohibited backup path in production", str(ctx.exception))

        # 3. Missing or unwritable production directory must raise RuntimeError, never silently fall back
        with tempfile.TemporaryDirectory() as tmpdir:
            non_writable_dir = Path(tmpdir) / "unwritable_prod"
            non_writable_dir.mkdir(parents=True, exist_ok=True)
            non_writable_dir.chmod(0o400)  # Read-only, not writable

            with patch("bot.config.PROD_DATA_DIR", non_writable_dir):
                with patch.dict(os.environ, {"APP_ENV": "production", "DATABASE_URL": ""}):
                    with self.assertRaises(RuntimeError) as ctx:
                        _resolve_production_database_url()
                    self.assertIn("not writable", str(ctx.exception))

    def test_06_sqlite_wal_reset_version_verification(self):
        """Test 6: Verify WAL-reset bug mitigation logic: accept safe versions, reject vulnerable versions."""
        # Safe versions (>= 3.51.3 or official backports 3.50.7, 3.44.6)
        self.assertTrue(is_sqlite_wal_safe((3, 51, 3)))
        self.assertTrue(is_sqlite_wal_safe((3, 51, 4)))
        self.assertTrue(is_sqlite_wal_safe((3, 52, 0)))
        self.assertTrue(is_sqlite_wal_safe((3, 54, 1)))
        self.assertTrue(is_sqlite_wal_safe((3, 50, 7)))
        self.assertTrue(is_sqlite_wal_safe((3, 44, 6)))

        # Vulnerable versions (latent 16-year data-race vulnerability)
        self.assertFalse(is_sqlite_wal_safe((3, 37, 2)))  # Ubuntu 22.04 LTS system default
        self.assertFalse(is_sqlite_wal_safe((3, 44, 5)))
        self.assertFalse(is_sqlite_wal_safe((3, 50, 4)))
        self.assertFalse(is_sqlite_wal_safe((3, 50, 6)))
        self.assertFalse(is_sqlite_wal_safe((3, 51, 0)))
        self.assertFalse(is_sqlite_wal_safe((3, 51, 2)))

        # Test string parsing
        self.assertEqual(parse_sqlite_version("3.51.3"), (3, 51, 3))
        self.assertEqual(parse_sqlite_version("3.50.7"), (3, 50, 7))
        self.assertEqual(parse_sqlite_version("3.37.2"), (3, 37, 2))

    async def test_07_init_db_rejects_vulnerable_sqlite_in_production(self):
        """Test 7: Verify init_db fails closed in production when connected to a vulnerable SQLite engine."""
        from bot.database.session import init_db
        from sqlalchemy.ext.asyncio import create_async_engine

        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = Path(tmpdir) / "test_wal_fail.db"
            mock_engine = create_async_engine(f"sqlite+aiosqlite:///{test_db}")

            # Simulate vulnerable version 3.37.2 returned by 'SELECT sqlite_version()'
            with patch("bot.database.session.settings") as mock_settings:
                mock_settings.app_env = "production"

                with patch("bot.database.session.is_sqlite_wal_safe", return_value=False):
                    with self.assertRaises(RuntimeError) as ctx:
                        await init_db(mock_engine)
                    self.assertIn("Insecure SQLite runtime version", str(ctx.exception))
                    self.assertIn("WAL-reset database corruption bug", str(ctx.exception))

            await mock_engine.dispose()


if __name__ == "__main__":
    unittest.main()
