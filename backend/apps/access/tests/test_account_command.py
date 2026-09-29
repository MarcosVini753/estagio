from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.access.models import AccessAccount


class CreateAccessAccountCommandTest(TestCase):
    @patch(
        "apps.access.management.commands.create_access_account.getpass",
        side_effect=["Complex-2026!Password", "Complex-2026!Password"],
    )
    def test_creates_room_user_with_cpf_and_matricula(self, _getpass):
        call_command(
            "create_access_account",
            profile="ROOM_USER",
            name="Joana da Silva",
            cpf="529.982.247-25",
            matricula="202312345",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
        )

        account = AccessAccount.objects.get()
        self.assertEqual(account.profile, "ROOM_USER")
        self.assertNotEqual(account.user_reference, "52998224725")
        self.assertEqual(account.identifiers.count(), 2)
        self.assertTrue(account.user.check_password("Complex-2026!Password"))
        self.assertEqual(
            set(account.identifiers.values_list("normalized_value", flat=True)),
            {"52998224725", "202312345"},
        )

    @patch(
        "apps.access.management.commands.create_access_account.getpass",
        side_effect=["Complex-2026!Password", "Complex-2026!Password"],
    )
    def test_rejects_invalid_cpf_and_admin_without_creating_users(self, _getpass):
        with self.assertRaises(CommandError):
            call_command(
                "create_access_account",
                profile="ROOM_MONITOR",
                name="Monitor",
                cpf="999.999.999-92",
            )
        with self.assertRaises(CommandError):
            call_command(
                "create_access_account",
                profile="SYSTEM_ADMIN",
                name="Admin",
                matricula="admin-1",
            )

        self.assertEqual(AccessAccount.objects.count(), 0)
