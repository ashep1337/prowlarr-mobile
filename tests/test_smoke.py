"""Smoke tests that do not require running Prowlarr or qBittorrent."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser

import httpx

from main import app


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("src", "href") and value and value.startswith("/static/"):
                self.paths.add(value)


class AppSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_homepage_and_its_assets_are_available(self):
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Prowlarr Mobile", response.text)
        assets = AssetParser()
        assets.feed(response.text)
        self.assertTrue(assets.paths, "Homepage should load its static assets")
        for path in sorted(assets.paths):
            with self.subTest(asset=path):
                response = await self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertTrue(response.content)

    async def test_health_does_not_require_download_services(self):
        response = await self.client.get("/health")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"status": "ok"})


class InstalledPathTest(unittest.TestCase):
    def test_app_imports_outside_its_source_directory(self):
        source = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(source)
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-c", "from main import app"],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
