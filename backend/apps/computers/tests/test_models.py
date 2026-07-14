from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.computers.models import Computer


class ComputerModelTest(TestCase):
    def test_only_operational_states_are_accepted(self):
        computer = Computer(code="PC-01", operational_state="OCCUPIED")

        with self.assertRaises(ValidationError):
            computer.full_clean()

    def test_default_state_is_available(self):
        computer = Computer.objects.create(code="PC-01")

        self.assertEqual(
            computer.operational_state, Computer.OperationalState.AVAILABLE
        )
