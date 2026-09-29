from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from apps.access.models import LoginIdentifier
from apps.access.services import create_access_account
from apps.core.enums import AffiliationType, DemoProfile


class AccessAuthenticationAPITest(APITestCase):
    def setUp(self):
        self.room_user = create_access_account(
            profile=DemoProfile.ROOM_USER,
            display_name="Usuária de teste",
            password="Senha123.",
            identifiers=[
                (LoginIdentifier.Kind.CPF, "999.999.999-91"),
                (LoginIdentifier.Kind.MATRICULA, "202312345"),
            ],
            affiliation_type=AffiliationType.STUDENT,
            institutional_unit="Sistemas de Informação",
            user_reference="room-user-account",
        )
        self.monitor = create_access_account(
            profile=DemoProfile.ROOM_MONITOR,
            display_name="Monitor de teste",
            password="Senha123.",
            identifiers=[
                (LoginIdentifier.Kind.CPF, "999.999.999-92"),
                (LoginIdentifier.Kind.MATRICULA, "20260000001"),
            ],
            user_reference="monitor-account",
        )
        self.supervisor = create_access_account(
            profile=DemoProfile.LIBRARY_SUPERVISOR,
            display_name="Supervisora de teste",
            password="Senha123.",
            identifiers=[(LoginIdentifier.Kind.CPF, "999.999.999-93")],
            user_reference="supervisor-account",
        )

    def test_login_accepts_masked_or_unmasked_cpf_and_matricula(self):
        for identifier, expected_profile in (
            ("999.999.999-91", DemoProfile.ROOM_USER),
            ("99999999991", DemoProfile.ROOM_USER),
            ("202312345", DemoProfile.ROOM_USER),
            ("999.999.999-92", DemoProfile.ROOM_MONITOR),
            ("20260000001", DemoProfile.ROOM_MONITOR),
            ("999.999.999-93", DemoProfile.LIBRARY_SUPERVISOR),
        ):
            self.client.logout()
            response = self.client.post(
                "/api/auth/login/",
                {"identifier": identifier, "password": "Senha123."},
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["profile"], expected_profile)
            self.assertNotIn("999", str(response.data))
            self.assertNotIn("user_reference", response.data)

    def test_login_error_does_not_disclose_account_existence(self):
        for identifier in ("88888888888", "99999999991"):
            response = self.client.post(
                "/api/auth/login/",
                {"identifier": identifier, "password": "senha-incorreta"},
                format="json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["code"], "INVALID_CREDENTIALS")
            self.assertEqual(
                response.data["detail"],
                "CPF/matrícula ou senha inválidos.",
            )

    def test_auth_context_and_logout(self):
        self.client.post(
            "/api/auth/login/",
            {"identifier": "999.999.999-91", "password": "Senha123."},
            format="json",
        )

        context = self.client.get("/api/auth/me/")
        logout = self.client.post("/api/auth/logout/", format="json")
        anonymous = self.client.get("/api/auth/me/")

        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.data["display_name"], "Usuária de teste")
        self.assertEqual(context.data["affiliation_type"], AffiliationType.STUDENT)
        self.assertNotIn("user_reference", context.data)
        self.assertNotIn("identifier", context.data)
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(anonymous.status_code, 403)

    def test_legacy_demo_routes_and_session_keys_cannot_select_a_role(self):
        session = self.client.session
        session["demo_profile"] = DemoProfile.LIBRARY_SUPERVISOR
        session["demo_user_reference"] = "privileged-reference"
        session["demo_unknown_legacy_key"] = "must be ignored"
        session.save()

        context = self.client.get("/api/auth/me/")
        old_context = self.client.get("/api/demo/context/")
        old_select = self.client.post(
            "/api/demo/select-profile/",
            {"profile": DemoProfile.LIBRARY_SUPERVISOR},
            format="json",
        )

        self.assertEqual(context.status_code, 403)
        self.assertEqual(old_context.status_code, 404)
        self.assertEqual(old_select.status_code, 404)

        self.client.post(
            "/api/auth/login/",
            {"identifier": "99999999991", "password": "Senha123."},
            format="json",
        )
        self.assertNotIn("demo_profile", self.client.session)
        self.assertNotIn("demo_unknown_legacy_key", self.client.session)

    def test_inactive_account_cannot_login(self):
        self.room_user.user.is_active = False
        self.room_user.user.save(update_fields=["is_active"])

        response = self.client.post(
            "/api/auth/login/",
            {"identifier": "99999999991", "password": "Senha123."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "INVALID_CREDENTIALS")

    def test_login_endpoint_enforces_csrf_for_anonymous_requests(self):
        client = APIClient(enforce_csrf_checks=True)
        client.get("/")

        rejected = client.post(
            "/api/auth/login/",
            {"identifier": "99999999991", "password": "Senha123."},
            format="json",
        )
        accepted = client.post(
            "/api/auth/login/",
            {"identifier": "99999999991", "password": "Senha123."},
            format="json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )

        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 200)

        rejected_logout = client.post("/api/auth/logout/", format="json")
        accepted_logout = client.post(
            "/api/auth/logout/",
            format="json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        self.assertEqual(rejected_logout.status_code, 403)
        self.assertEqual(accepted_logout.status_code, 204)


class AccessAccountModelTest(TestCase):
    def test_password_is_hashed_and_system_admin_account_is_rejected(self):
        account = create_access_account(
            profile=DemoProfile.ROOM_MONITOR,
            display_name="Monitor",
            password="Senha123.",
            identifiers=[(LoginIdentifier.Kind.MATRICULA, "M-123")],
        )

        self.assertNotEqual(account.user.password, "Senha123.")
        self.assertTrue(account.user.check_password("Senha123."))
        self.assertFalse(account.user.is_staff)
        self.assertFalse(account.user.is_superuser)
        self.assertEqual(get_user_model().objects.count(), 1)

        with self.assertRaises(ValueError):
            create_access_account(
                profile=DemoProfile.SYSTEM_ADMIN,
                display_name="Administrador",
                password="Senha123.",
                identifiers=[(LoginIdentifier.Kind.MATRICULA, "ADMIN")],
            )
