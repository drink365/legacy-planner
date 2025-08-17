from __future__ import annotations
from io import BytesIO
from typing import Dict, Any
from datetime import datetime
import os
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------- 1) 註冊支援繁中的字型 ----------
FONT_DIR = os.path.join("assets", "fonts")
REGULAR_TTF = os.path.join(FONT_DIR, "NotoSansTC-Regular.ttf")
BOLD_TTF    = os.path.join(FONT_DIR, "NotoSansTC-Bold.ttf")

def _register_fonts():
    try:
        if os.path.exists(REGULAR_TTF) and os.path.exists(BOLD_TTF):
            pdfmetrics.registerFont(TTFont("NotoTC", REGULAR_TTF))
            pdfmetrics.registerFont(TTFont("NotoTC-Bold", BOLD_TTF))
            return "NotoTC", "NotoTC-Bold"
    except Exception:
        pass
    # 找不到字型檔則退回預設（英文字可，但中文會方塊）
    return "Helvetica", "Helvetica-Bold"

BASE_FONT, BASE_FONT_BOLD = _register_fonts()

# ---------- 2) 元件 ----------
def _kv_table(data: Dict[str, Any], col1: str = "欄位", col2: str = "內容"):
    rows = [[col1, col2]] + [[str(k), str(v)] for k, v in data.items()]
    t = Table(rows, colWidths=[140, 360])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),

        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), BASE_FONT_BOLD),

        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,0), (-1,0), 6),
    ]))
    return t

def _try_logo(story):
    brand = st.secrets.get("brand", {})
    logo_url = brand.get("logo_url", "")
    # 先試遠端 URL；失敗就用本地佔位
    if logo_url:
        try:
            story.append(RLImage(logo_url, width=120, height=120 * 0.28))
            return
        except Exception:
            pass
    local = os.path.join("assets", "logo_placeholder.png")
    if os.path.exists(local):
        try:
            story.append(RLImage(local, width=120, height=120 * 0.28))
        except Exception:
            pass

# ---------- 3) 產生 PDF ----------
def build_pdf(*, inputs_summary: Dict[str, Any], result_summary: Dict[str, Any],
              recommendations: Dict[str, Any], comparisons: Dict[str, Any] | None = None) -> bytes:
    brand = st.secrets.get("brand", {})
    brand_title = brand.get("title", "Grace Family Office｜永傳家族辦公室")
    footer = brand.get("footer", "")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # 改掉預設字型，避免段落出現方塊字
    styles["Normal"].fontName = BASE_FONT
    styles["Normal"].fontSize = 11
    styles["Heading3"].fontName = BASE_FONT_BOLD
    styles["Heading3"].fontSize = 13

    story = []
    _try_logo(story)

    title_style = ParagraphStyle(
        "TitleTW",
        parent=styles["Normal"],
        fontName=BASE_FONT_BOLD,
        fontSize=18,
        leading=22,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleTW",
        parent=styles["Normal"],
        fontName=BASE_FONT,
        fontSize=12,
        leading=16,
    )

    story.append(Paragraph(brand_title, title_style))
    story.append(Paragraph(f"顧問建議報告｜{datetime.now().strftime('%Y-%m-%d')}", subtitle_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph("一、您的基本情境", styles["Heading3"]))
    story.append(_kv_table(inputs_summary))
    story.append(Spacer(1, 12))

    story.append(Paragraph("二、重點結果摘要", styles["Heading3"]))
    story.append(_kv_table(result_summary, "項目", "數值／說明"))
    story.append(Spacer(1, 12))

    if comparisons:
        story.append(Paragraph("三、情境比較（基準 vs. 規劃）", styles["Heading3"]))
        rows = [["情境", "稅費合計", "備註"]]
        for name, info in comparisons.items():
            rows.append([name, str(info.get("total_tax", "-")), info.get("note", "")])
        t = Table(rows, colWidths=[160, 130, 210])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 10),

            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0F766E")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), BASE_FONT_BOLD),

            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D1FAE5")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#ECFEFF")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    story.append(Paragraph("四、顧問建議", styles["Heading3"]))
    story.append(_kv_table(recommendations, "重點", "說明"))
    story.append(Spacer(1, 18))

    if footer:
        story.append(Paragraph(footer.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
