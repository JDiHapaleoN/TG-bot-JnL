"""Smoke tests for aiogram Dispatcher routers and aiohttp WebApp server."""

import unittest

from main import build_dispatcher
from bot.webapp.server import create_webapp


class TestAppWiring(unittest.TestCase):
    def test_build_dispatcher(self):
        dp = build_dispatcher()
        self.assertIsNotNone(dp)
        self.assertEqual(len(dp.sub_routers), 6)

    def test_create_webapp(self):
        app = create_webapp()
        self.assertIsNotNone(app)
        routes = [r.resource.canonical for r in app.router.routes() if r.resource]
        self.assertIn("/", routes)
        self.assertIn("/api/dashboard", routes)
        self.assertIn("/api/transactions", routes)
        self.assertIn("/api/recurring", routes)
        self.assertIn("/api/profile", routes)


if __name__ == "__main__":
    unittest.main()

