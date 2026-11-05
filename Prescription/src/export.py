from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.models import PrescriptionExtraction, ValidationReport

DISCLAIMER = (
    "SAFETY NOTICE: This file is an AI transcription aid. It is not a medical "
    "diagnosis, prescription, or dispensing record. Uncertain fields must be "
    "treated as unverified. A licensed clinician or pharmacist must review the "
    "original prescription before any clinical or pharmacy action."
)


def extraction_to_dict(
    extraction: PrescriptionExtraction,
    report: ValidationReport,
    verified: bool,
    reviewer_notes: str,
    corrections: list[dict] | None = None,
) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verified_by_human": verified,
        "reviewer_notes": reviewer_notes,
        "disclaimer": DISCLAIMER,
        "extraction": extraction.model_dump(),
        "validation": report.model_dump(),
        "human_corrections": corrections or [],
    }


def to_json_bytes(
    extraction: PrescriptionExtraction,
    report: ValidationReport,
    verified: bool,
    reviewer_notes: str,
    corrections: list[dict] | None = None,
) -> bytes:
    payload = extraction_to_dict(extraction, report, verified, reviewer_notes, corrections)
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def to_pdf_bytes(
    extraction: PrescriptionExtraction,
    report: ValidationReport,
    verified: bool,
    reviewer_notes: str,
    corrections: list[dict] | None = None,
) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Prescription transcription (unverified unless marked)",
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#0f3d4c"),
        spaceAfter=8,
    )
    warn = ParagraphStyle(
        "Warn",
        parent=styles["Normal"],
        textColor=colors.HexColor("#8a1c1c"),
        fontSize=9,
        leading=12,
        spaceAfter=12,
    )
    heading = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0f3d4c"),
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )
    body = styles["Normal"]

    story = [
        Paragraph("Handwritten Prescription Transcription", title),
        Paragraph(DISCLAIMER, warn),
        Paragraph(f"<b>Human verified:</b> {'Yes' if verified else 'No — do not use clinically'}", body),
        Paragraph(f"<b>Generated (UTC):</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}", body),
        Paragraph(f"<b>Model confidence (not a clinical score):</b> {extraction.overall_confidence}", body),
        Paragraph(f"<b>Patient (original):</b> {extraction.patient_name_original}", body),
        Paragraph(f"<b>Prescriber (original):</b> {extraction.prescriber_name_original}", body),
        Paragraph(f"<b>Date (original):</b> {extraction.date_original}", body),
        Spacer(1, 8),
        Paragraph("Extracted medicines (original transcription)", heading),
    ]

    header = [
        "Medicine (original)",
        "Suggestion (unapplied)",
        "Strength",
        "Dosage",
        "Frequency",
        "Duration",
        "Route",
        "Instructions",
    ]
    rows = [header]
    for medicine in extraction.medicines:
        rows.append(
            [
                medicine.medicine_name_original,
                medicine.medicine_name_suggestion or "—",
                medicine.strength_original,
                medicine.dosage_original,
                medicine.frequency_original,
                medicine.duration_original,
                medicine.route_original,
                medicine.special_instructions_original,
            ]
        )

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d4c")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9bb7c0")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f4fafb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)

    if corrections:
        story.append(Paragraph("Human corrections", heading))
        for row in corrections:
            story.append(Paragraph(str(row), body))

    story.append(Paragraph("Reviewer notes", heading))
    story.append(Paragraph(reviewer_notes or "None", body))
    story.append(Paragraph("Uncertainty and validation flags", heading))
    for issue in report.issues:
        story.append(Paragraph(f"[{issue.level}] {issue.message}", body))

    story.append(Paragraph("Raw transcription", heading))
    story.append(Paragraph((extraction.raw_transcription or "unclear").replace("\n", "<br/>"), body))

    document.build(story)
    return buffer.getvalue()
