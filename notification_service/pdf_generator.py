from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
from datetime import datetime

from notification_service.config import settings


def generate_receipt_pdf(receipt_data: dict) -> BytesIO:
    """
    Генерирует PDF чек

    Args:
        receipt_data: Словарь с данными чека

    Returns:
        BytesIO объект с PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = []
    styles = getSampleStyleSheet()

    # Стили
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#2C3E50"),
        alignment=TA_CENTER,
        spaceAfter=30,
    )

    header_style = ParagraphStyle(
        "CustomHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#34495E"),
        spaceAfter=12,
    )

    # Заголовок
    elements.append(Paragraph("PAYMENT RECEIPT", title_style))
    elements.append(Spacer(1, 0.3 * inch))

    # Информация о компании
    company_info = [
        [settings.COMPANY_NAME],
        [settings.COMPANY_ADDRESS],
        [settings.COMPANY_SUPPORT_EMAIL],
    ]

    company_table = Table(company_info, colWidths=[6 * inch])
    company_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#7F8C8D")),
            ]
        )
    )
    elements.append(company_table)
    elements.append(Spacer(1, 0.4 * inch))

    # Детали транзакции
    elements.append(Paragraph("Transaction Details", header_style))

    # Парсим дату
    try:
        completed_dt = datetime.fromisoformat(
            receipt_data["completed_at"].replace("Z", "+00:00")
        )
        date_str = completed_dt.strftime("%B %d, %Y %H:%M:%S UTC")
    except:
        date_str = receipt_data["completed_at"]

    transaction_data = [
        ["Payment ID:", str(receipt_data["payment_id"])],
        ["Order ID:", receipt_data["order_id"]],
        ["Capture ID:", receipt_data["capture_id"]],
        ["Date:", date_str],
        ["Status:", "COMPLETED ✓"],
    ]

    transaction_table = Table(transaction_data, colWidths=[2 * inch, 4 * inch])
    transaction_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ECF0F1")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2C3E50")),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
            ]
        )
    )
    elements.append(transaction_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Информация о клиенте
    elements.append(Paragraph("Customer Information", header_style))

    customer_data = [
        ["Email:", receipt_data["user_email"]],
    ]

    if receipt_data.get("user_name"):
        customer_data.insert(0, ["Name:", receipt_data["user_name"]])

    customer_table = Table(customer_data, colWidths=[2 * inch, 4 * inch])
    customer_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ECF0F1")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2C3E50")),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
            ]
        )
    )
    elements.append(customer_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Описание
    elements.append(Paragraph("Payment Description", header_style))
    elements.append(Paragraph(receipt_data["description"], styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    # Итоговая сумма
    elements.append(Paragraph("Payment Summary", header_style))

    summary_data = [
        ["Amount:", f"{receipt_data['amount']} {receipt_data['currency']}"],
    ]

    if receipt_data.get("transaction_fee"):
        summary_data.append(
            [
                "Transaction Fee:",
                f"{receipt_data['transaction_fee']} {receipt_data['currency']}",
            ]
        )
        try:
            total = float(receipt_data["amount"]) + float(
                receipt_data["transaction_fee"]
            )
            summary_data.append(["Total:", f"{total:.2f} {receipt_data['currency']}"])
        except:
            pass

    summary_table = Table(summary_data, colWidths=[4.5 * inch, 1.5 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEABOVE", (0, 0), (-1, 0), 2, colors.HexColor("#2C3E50")),
                ("LINEBELOW", (0, -1), (-1, -1), 2, colors.HexColor("#2C3E50")),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * inch))

    # Футер
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#95A5A6"),
        alignment=TA_CENTER,
    )
    elements.append(Paragraph("Thank you for your payment!", footer_style))
    elements.append(
        Paragraph(
            "If you have any questions, please contact our support team.", footer_style
        )
    )

    # Генерация
    doc.build(elements)
    buffer.seek(0)

    return buffer
