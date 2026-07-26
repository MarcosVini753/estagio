from rest_framework import status
from rest_framework.exceptions import APIException


class DateOutsideAllowedWindow(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A data deve ser hoje ou amanhã."
    default_code = "DATE_OUTSIDE_ALLOWED_WINDOW"


class ConfigurationRequired(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A configuração necessária para esta operação não está disponível."
    default_code = "CONFIGURATION_REQUIRED"


class ComputerStateUnchanged(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "O computador já possui o estado operacional informado."
    default_code = "COMPUTER_STATE_UNCHANGED"


class StateChangeReasonRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe uma justificativa para indisponibilizar o computador."
    default_code = "STATE_CHANGE_REASON_REQUIRED"


class ShiftReplacementInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A substituição do turno não é válida para esta versão."
    default_code = "SHIFT_REPLACEMENT_INVALID"


class ShiftReplacementConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "O novo turno sobrepõe outro turno ativo."
    default_code = "SHIFT_REPLACEMENT_CONFLICT"
