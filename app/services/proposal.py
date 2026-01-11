"""
Proposal PDF Generation Service

Generates professional PDF proposals from estimates using ReportLab.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER

from app.models.estimate import Estimate
from app.models.opportunity import Opportunity


def format_currency(value: Optional[Decimal]) -> str:
    """Format a decimal value as currency."""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def generate_proposal_pdf(
    estimate: Estimate,
    opportunity: Opportunity,
    output_path: str,
    company_name: str = "RevenueOS Construction",
    company_address: str = "123 Business Way, Suite 100\nCity, State 12345",
    company_phone: str = "(555) 123-4567",
    company_email: str = "proposals@triumphos.com",
) -> str:
    """
    Generate a PDF proposal for an estimate.

    Args:
        estimate: The Estimate model
        opportunity: The Opportunity model
        output_path: Path to save the PDF
        company_name: Company name for header
        company_address: Company address
        company_phone: Company phone
        company_email: Company email

    Returns:
        Path to the generated PDF
    """
    # Create the PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # Get styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        spaceAfter=6,
        textColor=colors.HexColor("#1a365d"),
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#4a5568"),
        alignment=TA_CENTER,
    )

    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#2d3748"),
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2d3748"),
    )

    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#718096"),
    )

    # Build document content
    story = []

    # Header
    story.append(Paragraph(company_name, title_style))
    story.append(Paragraph("PROPOSAL", subtitle_style))
    story.append(Spacer(1, 0.3 * inch))

    # Horizontal line
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor("#3182ce"),
            spaceBefore=5,
            spaceAfter=20,
        )
    )

    # Proposal info table
    proposal_date = datetime.now().strftime("%B %d, %Y")
    proposal_number = f"P-{opportunity.id:04d}-{estimate.version}"

    info_data = [
        [
            Paragraph(f"<b>Proposal #:</b> {proposal_number}", body_style),
            Paragraph(f"<b>Date:</b> {proposal_date}", body_style),
        ],
        [
            Paragraph(f"<b>Project:</b> {opportunity.name}", body_style),
            Paragraph(f"<b>Estimate Version:</b> v{estimate.version}", body_style),
        ],
    ]

    info_table = Table(info_data, colWidths=[3.5 * inch, 3.5 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 0.3 * inch))

    # Client information
    story.append(Paragraph("PREPARED FOR", section_header_style))

    account = opportunity.account
    contact = opportunity.primary_contact

    client_info = f"<b>{account.name}</b><br/>"
    if account.address:
        client_info += f"{account.address}<br/>"
    if account.city or account.state or account.zip_code:
        parts = []
        if account.city:
            parts.append(account.city)
        if account.state:
            parts.append(account.state)
        if account.zip_code:
            parts.append(account.zip_code)
        client_info += f"{', '.join(parts)}<br/>"

    if contact:
        client_info += f"<br/><b>Attn:</b> {contact.full_name}"
        if contact.title:
            client_info += f", {contact.title}"
        client_info += "<br/>"
        if contact.email:
            client_info += f"<b>Email:</b> {contact.email}<br/>"
        if contact.phone:
            client_info += f"<b>Phone:</b> {contact.phone}<br/>"

    story.append(Paragraph(client_info, body_style))
    story.append(Spacer(1, 0.3 * inch))

    # Project Scope
    if opportunity.description or opportunity.scopes:
        story.append(Paragraph("PROJECT SCOPE", section_header_style))

        if opportunity.description:
            story.append(Paragraph(opportunity.description, body_style))
            story.append(Spacer(1, 0.15 * inch))

        if opportunity.scopes:
            scope_text = "<b>Scope Packages:</b> " + ", ".join(
                s.name for s in opportunity.scopes
            )
            story.append(Paragraph(scope_text, body_style))

        story.append(Spacer(1, 0.2 * inch))

    # Labor section
    labor_items = [item for item in estimate.line_items if item.line_type == "labor"]
    if labor_items:
        story.append(Paragraph("LABOR", section_header_style))

        labor_data = [["Description", "Qty", "Unit", "Unit Cost", "Total"]]
        for item in labor_items:
            labor_data.append(
                [
                    Paragraph(item.description, body_style),
                    f"{item.quantity:,.2f}",
                    item.unit or "",
                    format_currency(item.unit_cost),
                    format_currency(item.total),
                ]
            )

        # Add subtotal row
        labor_data.append(
            ["", "", "", "Labor Subtotal:", format_currency(estimate.labor_total)]
        )

        labor_table = Table(
            labor_data,
            colWidths=[3 * inch, 0.7 * inch, 0.7 * inch, 1 * inch, 1.1 * inch],
        )
        labor_table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Body
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Subtotal row
                    ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE", (3, -1), (-1, -1), 1, colors.HexColor("#a0aec0")),
                    # Grid
                    ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(labor_table)
        story.append(Spacer(1, 0.2 * inch))

    # Materials section
    material_items = [
        item for item in estimate.line_items if item.line_type == "material"
    ]
    if material_items:
        story.append(Paragraph("MATERIALS", section_header_style))

        material_data = [["Description", "Qty", "Unit", "Unit Cost", "Total"]]
        for item in material_items:
            material_data.append(
                [
                    Paragraph(item.description, body_style),
                    f"{item.quantity:,.2f}",
                    item.unit or "",
                    format_currency(item.unit_cost),
                    format_currency(item.total),
                ]
            )

        # Add subtotal row
        material_data.append(
            [
                "",
                "",
                "",
                "Materials Subtotal:",
                format_currency(estimate.material_total),
            ]
        )

        material_table = Table(
            material_data,
            colWidths=[3 * inch, 0.7 * inch, 0.7 * inch, 1 * inch, 1.1 * inch],
        )
        material_table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Body
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Subtotal row
                    ("FONTNAME", (3, -1), (-1, -1), "Helvetica-Bold"),
                    ("LINEABOVE", (3, -1), (-1, -1), 1, colors.HexColor("#a0aec0")),
                    # Grid
                    ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(material_table)
        story.append(Spacer(1, 0.3 * inch))

    # Summary totals
    story.append(Paragraph("PROPOSAL SUMMARY", section_header_style))

    summary_data = [
        ["Labor Total:", format_currency(estimate.labor_total)],
        ["Materials Total:", format_currency(estimate.material_total)],
        ["Subtotal:", format_currency(estimate.subtotal)],
        [
            f"Markup ({estimate.margin_percent}%):",
            format_currency(estimate.margin_amount),
        ],
        ["TOTAL:", format_currency(estimate.total)],
    ]

    summary_table = Table(summary_data, colWidths=[5 * inch, 1.5 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                # Total row styling
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 14),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#1a365d")),
                ("LINEABOVE", (0, -1), (-1, -1), 2, colors.HexColor("#3182ce")),
                ("TOPPADDING", (0, -1), (-1, -1), 10),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * inch))

    # Terms and conditions
    story.append(Paragraph("TERMS & CONDITIONS", section_header_style))

    terms = """
    <b>1. Validity:</b> This proposal is valid for 30 days from the date above.<br/><br/>
    <b>2. Payment Terms:</b> 50% deposit upon acceptance, balance due upon completion.<br/><br/>
    <b>3. Changes:</b> Any changes to the scope of work may result in additional charges.<br/><br/>
    <b>4. Warranty:</b> All workmanship is warranted for one year from completion date.<br/><br/>
    <b>5. Insurance:</b> Contractor maintains comprehensive liability and workers' compensation insurance.
    """
    story.append(Paragraph(terms, small_style))
    story.append(Spacer(1, 0.5 * inch))

    # Signature section
    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#e2e8f0"),
            spaceBefore=10,
            spaceAfter=20,
        )
    )

    sig_data = [
        ["ACCEPTED BY:", "", "DATE:"],
        ["", "", ""],
        ["_" * 40, "", "_" * 25],
        ["Signature", "", ""],
        ["", "", ""],
        ["_" * 40, "", ""],
        ["Printed Name", "", ""],
    ]

    sig_table = Table(sig_data, colWidths=[3.5 * inch, 0.5 * inch, 2.5 * inch])
    sig_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TEXTCOLOR", (0, 3), (0, 3), colors.HexColor("#718096")),
                ("TEXTCOLOR", (0, 6), (0, 6), colors.HexColor("#718096")),
                ("FONTSIZE", (0, 3), (0, 3), 8),
                ("FONTSIZE", (0, 6), (0, 6), 8),
            ]
        )
    )
    story.append(sig_table)

    # Footer with company contact
    story.append(Spacer(1, 0.5 * inch))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#e2e8f0"),
            spaceBefore=10,
            spaceAfter=10,
        )
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#718096"),
        alignment=TA_CENTER,
    )

    footer_text = f"{company_name} | {company_phone} | {company_email}"
    story.append(Paragraph(footer_text, footer_style))

    # Build the PDF
    doc.build(story)

    return output_path
