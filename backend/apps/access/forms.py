from copy import deepcopy

from django.contrib.auth.forms import AuthenticationForm


class IdentifierAuthenticationForm(AuthenticationForm):
    username = deepcopy(AuthenticationForm.base_fields["username"])
    username.label = "CPF ou matrícula"
    username.widget.attrs.update(
        {
            "autocomplete": "username",
            "autocapitalize": "none",
            "inputmode": "text",
        }
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "CPF/matrícula ou senha inválidos.",
    }
