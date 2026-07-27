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


class ReservationSlotInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "O horário deve corresponder a um slot configurado e futuro."
    default_code = "RESERVATION_SLOT_INVALID"


class ReservationUnavailable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "O computador não está disponível para esta reserva."
    default_code = "RESERVATION_UNAVAILABLE"


class ReservationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A reserva conflita com outro intervalo confirmado."
    default_code = "RESERVATION_CONFLICT"


class ReservationLimitReached(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "O limite de reservas futuras para este usuário foi atingido."
    default_code = "RESERVATION_LIMIT_REACHED"


class ReservationCancellationNotAllowed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Este perfil não pode cancelar a reserva informada."
    default_code = "RESERVATION_CANCELLATION_NOT_ALLOWED"


class ReservationCancellationUnavailable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A reserva não pode mais ser cancelada."
    default_code = "RESERVATION_CANCELLATION_UNAVAILABLE"


class ReservationCancellationReasonRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe a justificativa para o cancelamento administrativo."
    default_code = "RESERVATION_CANCELLATION_REASON_REQUIRED"


class UsageSessionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Não foi possível executar a operação na sessão de uso."
    default_code = "USAGE_SESSION_CONFLICT"


class UsageSessionNotActive(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A sessão informada não está ativa."
    default_code = "USAGE_SESSION_NOT_ACTIVE"


class ReservationCheckInUnavailable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A reserva não está disponível para registrar entrada."
    default_code = "RESERVATION_CHECK_IN_UNAVAILABLE"


class UsageSessionIdentityRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe a identidade fictícia do usuário da sessão."
    default_code = "USAGE_SESSION_IDENTITY_REQUIRED"


class UsageSessionNotAllowed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Este perfil não pode operar a sessão informada."
    default_code = "USAGE_SESSION_NOT_ALLOWED"


class UsageSessionReasonRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe a justificativa para encerrar a sessão de terceiro."
    default_code = "USAGE_SESSION_REASON_REQUIRED"


class RoomClosed(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A sala não está aberta neste horário."
    default_code = "ROOM_CLOSED"
