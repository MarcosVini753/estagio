import csv
from dataclasses import dataclass
from io import BytesIO, StringIO

import xlsxwriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.configuration.models import ReportConfiguration
from apps.occurrences.models import Occurrence
from apps.operations.models import Reservation

ROOM_STATUS_LABELS = {
    "OPEN": "Aberta",
    "CLOSED": "Fechada",
    "SPECIAL_HOURS": "Horário especial",
}
CALENDAR_SOURCE_LABELS = {
    "CALENDAR_EXCEPTION": "Exceção de calendário",
    "TEMPORARY_SCHEDULE": "Calendário temporário",
    "REGULAR_SCHEDULE": "Calendário regular",
}


@dataclass(frozen=True)
class ExportTable:
    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple, ...]


@dataclass(frozen=True)
class ExportDocument:
    title: str
    filename_stem: str
    metadata: tuple[tuple[str, object], ...]
    summary: tuple[tuple[str, object], ...]
    tables: tuple[ExportTable, ...]


SUMMARY_LABELS = {
    "visits": "Visitas",
    "distinct_users": "Pessoas distintas",
    "reservations": "Reservas",
    "occurrences": "Ocorrências",
    "computers_used": "Computadores utilizados",
    "allocated_minutes": "Minutos alocados",
    "average_stay_minutes": "Permanência média (min)",
    "operating_minutes": "Minutos de funcionamento da sala",
}


def _summary_rows(report, *, include_occurrences):
    return tuple(
        (label, report["summary"][key])
        for key, label in SUMMARY_LABELS.items()
        if include_occurrences or key != "occurrences"
    ) + (
        ("Minutos de capacidade disponível", report["occupancy"]["available_minutes"]),
        ("Minutos ocupados elegíveis", report["occupancy"]["allocated_minutes"]),
        ("Taxa de ocupação (%)", report["occupancy"]["rate_percent"]),
    )


def _daily_document(report, configuration):
    shift_names = {item["series_key"]: item["name"] for item in report["shifts"]}
    shift_names["NOT_INFORMED"] = "Não informado"
    rows = tuple(
        (shift_names.get(key, key), value)
        for key, value in report["visits_by_shift"].items()
    )
    target_date = report["period"]["date"]
    return ExportDocument(
        title="Relatório diário consolidado",
        filename_stem=f"relatorio-diario-{target_date}",
        metadata=(
            ("Data", target_date),
            (
                "Situação do calendário",
                ROOM_STATUS_LABELS[report["calendar"]["status"]],
            ),
            (
                "Origem do calendário",
                CALENDAR_SOURCE_LABELS[report["calendar"]["source"]],
            ),
            ("Motivo", report["calendar"]["reason"]),
        ),
        summary=_summary_rows(
            report,
            include_occurrences=configuration.include_occurrences,
        ),
        tables=(
            ExportTable(
                "Funcionamento",
                ("Abertura", "Fechamento"),
                tuple(
                    (window["opens_at"], window["closes_at"])
                    for window in report["calendar"]["windows"]
                ),
            ),
            *(
                (ExportTable("Visitas por turno", ("Turno", "Visitas"), rows),)
                if configuration.group_by_shift
                else ()
            ),
        ),
    )


def _monthly_document(report, configuration):
    shift_headers = tuple(item["name"] for item in report["shifts"])
    shift_keys = tuple(item["series_key"] for item in report["shifts"])
    if configuration.group_by_shift:
        shift_headers += ("Não informado",)
        shift_keys += ("NOT_INFORMED",)
    rows = []
    for day in report["days"]:
        row = [
            day["date"],
            ROOM_STATUS_LABELS[day["calendar_status"]],
            CALENDAR_SOURCE_LABELS[day["calendar_source"]],
            day["operating_minutes"],
        ]
        row.extend(day["visits_by_shift"].get(key, 0) for key in shift_keys)
        row.append(day["total"])
        rows.append(tuple(row))
    year = report["period"]["year"]
    month = report["period"]["month"]
    return ExportDocument(
        title="Relatório mensal consolidado",
        filename_stem=f"relatorio-mensal-{year:04d}-{month:02d}",
        metadata=(("Mês", f"{month:02d}/{year:04d}"),),
        summary=_summary_rows(
            report,
            include_occurrences=configuration.include_occurrences,
        ),
        tables=(
            ExportTable(
                "Dias",
                (
                    "Data",
                    "Calendário",
                    "Origem",
                    "Minutos operacionais",
                    *shift_headers,
                    "Total",
                ),
                tuple(rows),
            ),
        ),
    )


def _annual_document(report, configuration):
    shift_headers = tuple(item["name"] for item in report["shifts"])
    shift_keys = tuple(item["series_key"] for item in report["shifts"])
    if configuration.group_by_shift:
        shift_headers += ("Não informado",)
        shift_keys += ("NOT_INFORMED",)
    rows = []
    for month in report["months"]:
        row = [
            month["month"],
            month["summary"]["operating_minutes"],
            month["summary"]["allocated_minutes"],
        ]
        row.extend(month["visits_by_shift"].get(key, 0) for key in shift_keys)
        row.append(month["total"])
        rows.append(tuple(row))
    year = report["period"]["year"]
    return ExportDocument(
        title="Relatório anual consolidado",
        filename_stem=f"relatorio-anual-{year:04d}",
        metadata=(("Ano", year),),
        summary=_summary_rows(
            report,
            include_occurrences=configuration.include_occurrences,
        ),
        tables=(
            ExportTable(
                "Meses",
                (
                    "Mês",
                    "Minutos operacionais",
                    "Minutos alocados",
                    *shift_headers,
                    "Total",
                ),
                tuple(rows),
            ),
        ),
    )


def _indicator_tables(report, configuration):
    tables = []
    if configuration.group_by_shift:
        tables.append(
            ExportTable(
                "Turnos",
                ("Turno", "Visitas", "Minutos alocados"),
                tuple(
                    (row["label"], row["visits"], row["allocated_minutes"])
                    for row in report["by_shift"]
                ),
            )
        )
    for title, key in (
        ("Vínculos", "by_affiliation"),
        ("Unidades", "by_institutional_unit"),
    ):
        tables.append(
            ExportTable(
                title,
                ("Grupo", "Visitas", "Pessoas distintas", "Minutos alocados"),
                tuple(
                    (
                        row["label"],
                        row["visits"],
                        row["distinct_users"],
                        row["allocated_minutes"],
                    )
                    for row in report[key]
                ),
            )
        )
    computer_headers = [
        "Computador",
        "Descrição",
        "Visitas",
        "Minutos alocados",
        "Minutos disponíveis",
        "Taxa (%)",
    ]
    if configuration.include_occurrences:
        computer_headers.append("Ocorrências")
    computer_rows = []
    for row in report["by_computer"]:
        values = [
            row["code"],
            row["description"],
            row["visits"],
            row["allocated_minutes"],
            row["available_minutes"],
            row["occupancy_rate_percent"],
        ]
        if configuration.include_occurrences:
            values.append(row["occurrences"])
        computer_rows.append(tuple(values))
    tables.extend(
        [
            ExportTable(
                "Computadores",
                tuple(computer_headers),
                tuple(computer_rows),
            ),
            ExportTable(
                "Dias",
                (
                    "Data",
                    "Visitas",
                    "Minutos alocados",
                    "Minutos disponíveis",
                    "Taxa (%)",
                ),
                tuple(
                    (
                        row["date"],
                        row["visits"],
                        row["allocated_minutes"],
                        row["available_minutes"],
                        row["occupancy_rate_percent"],
                    )
                    for row in report["by_day"]
                ),
            ),
            ExportTable(
                "Horários",
                (
                    "Início",
                    "Minutos alocados",
                    "Minutos disponíveis",
                    "Taxa (%)",
                ),
                tuple(
                    (
                        row["starts_at"],
                        row["allocated_minutes"],
                        row["available_minutes"],
                        row["occupancy_rate_percent"],
                    )
                    for row in report["by_time_slot"]
                ),
            ),
        ]
    )
    reservation_labels = dict(Reservation.Status.choices)
    tables.append(
        ExportTable(
            "Reservas por situação",
            ("Situação", "Quantidade"),
            tuple(
                (reservation_labels[status], amount)
                for status, amount in report["reservations_by_status"].items()
            ),
        )
    )
    if configuration.include_occurrences:
        occurrence_labels = dict(Occurrence.Status.choices)
        tables.append(
            ExportTable(
                "Ocorrências por situação",
                ("Situação", "Quantidade"),
                tuple(
                    (occurrence_labels[status], amount)
                    for status, amount in report["occurrences_by_status"].items()
                ),
            )
        )
    return tuple(tables)


def _indicators_document(report, configuration):
    starts_on = report["period"]["starts_on"]
    ends_on = report["period"]["ends_on"]
    return ExportDocument(
        title="Indicadores gerenciais de uso da sala",
        filename_stem=f"indicadores-{starts_on}-a-{ends_on}",
        metadata=(("Período", f"{starts_on} a {ends_on}"),),
        summary=_summary_rows(
            report,
            include_occurrences=configuration.include_occurrences,
        ),
        tables=_indicator_tables(report, configuration),
    )


DOCUMENT_BUILDERS = {
    "daily": _daily_document,
    "monthly": _monthly_document,
    "annual": _annual_document,
    "indicators": _indicators_document,
}


def build_export_document(kind, report, configuration):
    return DOCUMENT_BUILDERS[kind](report, configuration)


def render_csv(document):
    output = StringIO(newline="")
    all_headers = ["Seção", "Indicador", "Valor"]
    for table in document.tables:
        for header in table.headers:
            if header not in all_headers:
                all_headers.append(header)
    writer = csv.DictWriter(output, fieldnames=all_headers, delimiter=";")
    writer.writeheader()
    for label, value in (*document.metadata, *document.summary):
        writer.writerow({"Seção": "Resumo", "Indicador": label, "Valor": value})
    for table in document.tables:
        for row in table.rows:
            values = {header: value for header, value in zip(table.headers, row)}
            writer.writerow({"Seção": table.title, **values})
    return output.getvalue().encode("utf-8-sig")


def render_xlsx(document):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    heading = workbook.add_format(
        {"bold": True, "bg_color": "#0C4CA4", "font_color": "#FFFFFF"}
    )
    label = workbook.add_format({"bold": True})
    summary = workbook.add_worksheet("Resumo")
    summary.set_column(0, 0, 34)
    summary.set_column(1, 1, 20)
    summary.write_row(0, 0, (document.title, ""), heading)
    row_number = 2
    for key, value in (*document.metadata, *document.summary):
        summary.write(row_number, 0, key, label)
        summary.write(row_number, 1, value)
        row_number += 1
    for table in document.tables:
        worksheet = workbook.add_worksheet(table.title[:31])
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, max(0, len(table.rows)), len(table.headers) - 1)
        worksheet.write_row(0, 0, table.headers, heading)
        for index, row in enumerate(table.rows, start=1):
            worksheet.write_row(index, 0, row)
        for column, header in enumerate(table.headers):
            worksheet.set_column(column, column, min(max(len(header) + 2, 12), 32))
    workbook.close()
    return output.getvalue()


def _pdf_value(value):
    return "—" if value is None else str(value)


def render_pdf(document):
    output = BytesIO()
    pdf = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=document.title,
        author="Biblioteca UFAC",
        pageCompression=0,
    )
    styles = getSampleStyleSheet()
    story = [Paragraph(document.title, styles["Title"]), Spacer(1, 5 * mm)]
    summary_rows = [["Indicador", "Valor"]] + [
        [label, _pdf_value(value)]
        for label, value in (*document.metadata, *document.summary)
    ]
    summary_table = Table(summary_rows, repeatRows=1, hAlign="LEFT")
    summary_table.setStyle(_pdf_table_style())
    story.extend([summary_table, Spacer(1, 6 * mm)])
    for index, table in enumerate(document.tables):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(table.title, styles["Heading2"]))
        rows = [list(table.headers)] + [
            [_pdf_value(value) for value in row] for row in table.rows
        ]
        report_table = Table(rows, repeatRows=1, hAlign="LEFT")
        report_table.setStyle(_pdf_table_style())
        story.append(report_table)
    pdf.build(story)
    return output.getvalue()


def _pdf_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0C4CA4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DCE2E9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, colors.HexColor("#F7F8FA")],
            ),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )


EXPORT_RENDERERS = {
    ReportConfiguration.ExportFormat.CSV: (
        render_csv,
        "text/csv; charset=utf-8",
        "csv",
    ),
    ReportConfiguration.ExportFormat.XLSX: (
        render_xlsx,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
    ),
    ReportConfiguration.ExportFormat.PDF: (
        render_pdf,
        "application/pdf",
        "pdf",
    ),
}


def render_export(document, export_format):
    renderer, content_type, extension = EXPORT_RENDERERS[export_format]
    return renderer(document), content_type, extension


__all__ = [
    "ExportDocument",
    "ExportTable",
    "build_export_document",
    "render_export",
]
