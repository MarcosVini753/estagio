from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    original = response.data
    if isinstance(original, dict) and "detail" in original:
        detail = str(original["detail"])
        fields = {key: value for key, value in original.items() if key != "detail"}
        code = getattr(exc, "default_code", "request_error").upper()
    else:
        detail = "A requisição contém dados inválidos."
        fields = (
            original if isinstance(original, dict) else {"non_field_errors": original}
        )
        code = "VALIDATION_ERROR"

    response.data = {"code": code, "detail": detail, "fields": fields}
    return response
