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


class OperatingScheduleRequired(ConfigurationRequired):
    default_detail = "Nenhum calendário operacional regular atende à data."
    default_code = "OPERATING_SCHEDULE_REQUIRED"


class OperatingScheduleOverlap(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "O calendário sobrepõe outro calendário ativo do mesmo tipo."
    default_code = "OPERATING_SCHEDULE_OVERLAP"


class OperatingScheduleStartInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "Novos calendários devem começar após hoje; use uma substituição futura "
        "ou uma exceção para mudanças no dia atual."
    )
    default_code = "OPERATING_SCHEDULE_START_INVALID"


class CalendarExceptionDateInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "Exceções de calendário só podem ser criadas ou alteradas para hoje "
        "ou datas futuras."
    )
    default_code = "CALENDAR_EXCEPTION_DATE_INVALID"


class TemporaryScheduleEndRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Horário temporário exige uma data final."
    default_code = "TEMPORARY_SCHEDULE_END_REQUIRED"


class OperatingDayConfigurationInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A configuração dos dias de funcionamento é inválida."
    default_code = "OPERATING_DAY_CONFIGURATION_INVALID"


class OperatingWindowOverlap(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "As janelas de funcionamento do mesmo dia se sobrepõem."
    default_code = "OPERATING_WINDOW_OVERLAP"


class OperatingWindowInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A janela de funcionamento é inválida."
    default_code = "OPERATING_WINDOW_INVALID"


class ScheduleChangeAffectsReservations(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "SCHEDULE_CHANGE_AFFECTS_RESERVATIONS"

    def __init__(self, reservation_ids):
        reservation_ids = list(reservation_ids)
        super().__init__(
            {
                "detail": (
                    "A alteração afetará "
                    f"{len(reservation_ids)} reserva(s) confirmada(s)."
                ),
                "reservation_ids": reservation_ids,
            }
        )


class ScheduleReplacementInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A substituição do calendário não é válida para esta versão."
    default_code = "SCHEDULE_REPLACEMENT_INVALID"


class RoomNoticeInvalidPeriod(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "O período do aviso é inválido."
    default_code = "ROOM_NOTICE_INVALID_PERIOD"


class RoomNoticeMessageRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe a mensagem do aviso."
    default_code = "ROOM_NOTICE_MESSAGE_REQUIRED"


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
    default_detail = (
        "O início deve estar alinhado à grade de 15 minutos, ser futuro e o "
        "intervalo deve caber no funcionamento da sala."
    )
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


class OccurrenceLinkInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Computador, sessão e alocação não são compatíveis."
    default_code = "OCCURRENCE_LINK_INVALID"


class OccurrenceTransitionInvalid(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A transição de estado da ocorrência não é permitida."
    default_code = "OCCURRENCE_TRANSITION_INVALID"


class OccurrenceResolutionNotesRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe as notas de resolução da ocorrência."
    default_code = "OCCURRENCE_RESOLUTION_NOTES_REQUIRED"


class SessionCorrectionInvalid(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A correção produziria uma linha do tempo inválida."
    default_code = "SESSION_CORRECTION_INVALID"


class SessionCorrectionReasonRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Informe a justificativa da correção."
    default_code = "SESSION_CORRECTION_REASON_REQUIRED"
