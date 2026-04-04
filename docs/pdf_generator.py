"""
PDF Generator Modul.
Nimmt die Markdown-Dokumentation, fixt Listen und LaTeX-Formeln und rendert via xhtml2pdf.
"""
import io
import base64
import re
import streamlit as st
from i18n import T

from docs.doc_de import DOC_DE
from docs.doc_en import DOC_EN

def get_docs(lang):
    """Holt die Dokumentation basierend auf der gewählten Sprache."""
    return DOC_DE if lang == "de" else DOC_EN

@st.cache_data(show_spinner=False)
def generate_pdf_doc(lang, logo_b64, version):
    """Generiert ein PDF aus dem lokaliserten Markdown-String."""
    try:
        import markdown
        from xhtml2pdf import pisa
        from PIL import Image
    except ImportError:
        return None

    try:
        img_data = base64.b64decode(logo_b64)
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        clean_img = Image.alpha_composite(bg, img).convert("RGB")
        out_buf = io.BytesIO()
        clean_img.save(out_buf, format="JPEG", quality=95)
        pdf_logo_src = f"data:image/jpeg;base64,{base64.b64encode(out_buf.getvalue()).decode()}"
    except Exception:
        pdf_logo_src = f"data:image/png;base64,{logo_b64}"

    md_text = get_docs(lang)
    md_text = md_text.replace("---", "", 1) 
    
    # --- PRE-PROCESSING FÜR PDF ---
    # 1. Listen-Fix: Die Markdown-Library erfordert zwingend eine Leerzeile vor Listen. 
    md_text = re.sub(r"([^\n])\n(\s*\*)", r"\1\n\n\2", md_text)

    # 2. LaTeX Formel-Fix: xhtml2pdf kann kein MathJax. Wir übersetzen die Formeln hart in HTML.
    math_replacements = {
        "$$SNR_{norm} = SNR_{measured} - P_{TX(dBm)} + 30$$": "<br><br><b>SNR<sub>norm</sub> = SNR<sub>measured</sub> - P<sub>TX(dBm)</sub> + 30</b><br>",
        r"$\Delta SNR_{TX} = SNR_{norm,target} - SNR_{norm,benchmark}$": "<b>&Delta; SNR<sub>TX</sub> = SNR<sub>norm,target</sub> - SNR<sub>norm,benchmark</sub></b>",
        r"$\Delta SNR_{RX} = SNR_{measured,target} - SNR_{measured,benchmark}$": "<b>&Delta; SNR<sub>RX</sub> = SNR<sub>measured,target</sub> - SNR<sub>measured,benchmark</sub></b>",
        r"$\Delta$ SNR": "&Delta; SNR",
        r"$\Delta$": "&Delta;",
        r"$2^\circ \times 1^\circ$": "2&deg; &times; 1&deg;",
        r"$150 \times 111$": "150 &times; 111",
        r"$5' \times 2.5'$": "5&apos; &times; 2.5&apos;",
        r"$6 \times 4$": "6 &times; 4"
    }
    for latex, html in math_replacements.items():
        md_text = md_text.replace(latex, html)

    html_content = markdown.markdown(md_text, extensions=['tables'])

    # Lokalisierte Credits laden und Neongrün in dunkles Blau (#0a318f) für den weißen PDF-Hintergrund ändern
    dev_credit_pdf = T[lang]["dev_credit"].replace("#39ff14", "#0a318f")

    template = f"""
    <html>
    <head>
    <style>
        @page {{ size: a4 portrait; margin: 2cm;
                @frame footer {{ -pdf-frame-content: footerContent; bottom: 1cm; margin-left: 2cm; margin-right: 2cm; height: 1cm; text-align: right; font-size: 8pt; color: #999; }}
        }}
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; color: #333; line-height: 1.5; }}
        h1, h2, h3, h4 {{ color: #0a1428; margin-bottom: 10px; }}
        h3 {{ border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .logo {{ width: 100px; margin-bottom: 15px; }}
        .title {{ font-size: 24pt; font-weight: bold; margin: 0; color: #000; letter-spacing: 1px; }}
        .subtitle {{ font-size: 11pt; color: #666; margin-top: 5px; }}
        code {{ font-family: Courier, monospace; background-color: #f4f4f4; padding: 2px 4px; font-size: 9pt; border-radius: 3px; }}
        th {{ text-align: left; background-color: #eee; padding: 5px; }}
        td {{ padding: 5px; border-bottom: 1px solid #eee; }}
        /* Explizites CSS für Listen im PDF */
        ul {{ margin-top: 5px; margin-bottom: 10px; padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
    </style>
    </head>
    <body>
        <div class="header">
            <img class="logo" src="{pdf_logo_src}">
            <div class="title">WSPRadar.org</div>
            <div class="subtitle">HAM RADIO STATION & ANTENNA BENCHMARKING<br><br><span style="font-size: 9pt; line-height: 1.4;">{dev_credit_pdf}</span></div>
        </div>
        {html_content}
        <div id="footerContent">
            WSPRadar {version} - Seite <pdf:pagenumber>
        </div>
    </body>
    </html>
    """
    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(template), dest=result)
    return result.getvalue() if not pisa_status.err else None