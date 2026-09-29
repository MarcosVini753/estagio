from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.core.enums import AffiliationType

from ...models import AccessAccount, LoginIdentifier
from ...services import create_access_account


def is_valid_cpf(value: str) -> bool:
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    first = sum(
        int(digit) * weight for digit, weight in zip(digits[:9], range(10, 1, -1))
    )
    first_digit = (first * 10) % 11 % 10
    second = sum(
        int(digit) * weight for digit, weight in zip(digits[:10], range(11, 1, -1))
    )
    second_digit = (second * 10) % 11 % 10
    return digits[-2:] == f"{first_digit}{second_digit}"


class Command(BaseCommand):
    help = "Cria uma conta de acesso operacional fora da interface pública."

    def add_arguments(self, parser):
        profile_choices = [value for value, _ in AccessAccount.PROFILE_CHOICES]
        parser.add_argument("--profile", required=True, choices=profile_choices)
        parser.add_argument("--name", required=True)
        parser.add_argument("--cpf")
        parser.add_argument("--matricula")
        parser.add_argument(
            "--affiliation-type",
            choices=[
                AffiliationType.STUDENT,
                AffiliationType.PROFESSOR,
                AffiliationType.TECHNICAL_STAFF,
            ],
        )
        parser.add_argument("--institutional-unit", default="")

    def handle(self, *args, **options):
        identifiers = []
        if options["cpf"]:
            if not is_valid_cpf(options["cpf"]):
                raise CommandError("O CPF deve ter dígitos verificadores válidos.")
            identifiers.append((LoginIdentifier.Kind.CPF, options["cpf"]))
        if options["matricula"]:
            identifiers.append((LoginIdentifier.Kind.MATRICULA, options["matricula"]))
        if not identifiers:
            raise CommandError("Informe --cpf, --matricula ou ambos.")

        password = getpass("Senha da conta: ")
        if password != getpass("Confirme a senha: "):
            raise CommandError("As senhas informadas não coincidem.")
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError(str(error)) from error

        try:
            account = create_access_account(
                profile=options["profile"],
                display_name=options["name"],
                password=password,
                identifiers=identifiers,
                affiliation_type=options["affiliation_type"],
                institutional_unit=options["institutional_unit"],
            )
        except (IntegrityError, ValueError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            self.style.SUCCESS(
                "Conta criada: "
                f"{account.display_name} ({account.get_profile_display()})."
            )
        )
