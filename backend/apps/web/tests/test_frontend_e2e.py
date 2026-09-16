import os
import subprocess
from datetime import datetime
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.management import call_command
from django.utils import timezone

from apps.core.management.commands.seed_frontend_e2e_data import (
    seed_frontend_e2e_data,
)


@skipUnless(
    os.getenv("RUN_FRONTEND_E2E") == "1",
    "E2E do navegador é executado separadamente na CI.",
)
class FrontendE2ETest(StaticLiveServerTestCase):
    """Executa o Chromium contra Django e o banco isolado do test runner."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixed_now = timezone.make_aware(
            datetime(2026, 9, 15, 8),
            timezone.get_current_timezone(),
        )
        cls.clock = patch("django.utils.timezone.now", return_value=cls.fixed_now)
        cls.clock.start()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.clock.stop()

    def setUp(self):
        call_command("seed_demo_data", verbosity=0)
        seed_frontend_e2e_data(now=self.fixed_now)

    def test_documented_browser_flows(self):
        environment = {
            **os.environ,
            "FRONTEND_BASE_URL": self.live_server_url,
        }
        result = subprocess.run(
            ["npm", "run", "test:e2e"],
            cwd=settings.PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )

        if result.returncode:
            self.fail(
                "O fluxo Playwright falhou.\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
