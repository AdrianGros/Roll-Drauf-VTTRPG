"""
M46: PDF Key Batch Generation
Creates beautifully formatted PDF documents for distributing registration keys
"""

from io import BytesIO
from datetime import datetime
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def generate_key_batch_pdf(batch_id, keys_data, theme_settings=None):
    """
    Generate a PDF document for distributing registration keys.

    Args:
        batch_id (str): Unique identifier for this batch
        keys_data (list): List of dicts with 'key_code' and optionally 'name', 'tier'
        theme_settings (dict): Optional theme colors {primary, accent, text, bg}

    Returns:
        bytes: PDF file contents as bytes, or None if reportlab unavailable
    """
    if not HAS_REPORTLAB:
        return _generate_fallback_html(batch_id, keys_data, theme_settings)

    # Default theme colors
    if theme_settings is None:
        theme_settings = {
            'primary': '#4a235a',
            'accent': '#d4af37',
            'text': '#2a2a2a',
            'bg': '#f5e6d3'
        }

    # Convert hex to RGB for reportlab
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    primary_rgb = hex_to_rgb(theme_settings.get('primary', '#4a235a'))
    accent_rgb = hex_to_rgb(theme_settings.get('accent', '#d4af37'))
    text_rgb = hex_to_rgb(theme_settings.get('text', '#2a2a2a'))

    # Create PDF
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Build styles
    styles = getSampleStyleSheet()

    # Custom styles for spellbook theme
    title_style = ParagraphStyle(
        'SpellbookTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor(theme_settings.get('primary', '#4a235a')),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        letterSpacing=2
    )

    subtitle_style = ParagraphStyle(
        'SpellbookSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor(theme_settings.get('accent', '#d4af37')),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    instruction_style = ParagraphStyle(
        'Instructions',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor(theme_settings.get('text', '#2a2a2a')),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica',
        leading=14
    )

    key_label_style = ParagraphStyle(
        'KeyLabel',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor(theme_settings.get('accent', '#d4af37')),
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    key_code_style = ParagraphStyle(
        'KeyCode',
        parent=styles['Normal'],
        fontSize=13,
        textColor=colors.HexColor(theme_settings.get('primary', '#4a235a')),
        spaceAfter=2,
        alignment=TA_CENTER,
        fontName='Courier-Bold',
        letterSpacing=1
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor(theme_settings.get('text', '#2a2a2a')),
        spaceAfter=0,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )

    # Build document content
    story = []

    # Header with decorative border
    story.append(Spacer(1, 0.3*inch))

    # Title
    story.append(Paragraph('✨ SPELLBOOK REGISTRATION KEYS ✨', title_style))
    story.append(Spacer(1, 0.1*inch))

    # Batch ID and date
    batch_info = f'Batch: {batch_id} | Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}'
    story.append(Paragraph(batch_info, subtitle_style))
    story.append(Spacer(1, 0.2*inch))

    # Instructions
    instructions = (
        '<font size="11"><b>Guard these runes carefully.</b></font><br/>'
        'Share only with trusted adventurers. Each incantation grants access to the Spellbook.<br/>'
        '<br/>'
        '<font size="10" color="{accent}">Speak your access incantation at the gates to enter.</font>'
    ).format(accent=theme_settings.get('accent', '#d4af37'))
    story.append(Paragraph(instructions, instruction_style))
    story.append(Spacer(1, 0.3*inch))

    # Create key entries with dividers
    for idx, key_info in enumerate(keys_data):
        if idx > 0 and idx % 3 == 0:
            # Page break after every 3 keys for readability
            story.append(PageBreak())

        key_code = key_info.get('key_code', '')
        key_name = key_info.get('name', f'Key {idx + 1}')
        key_tier = key_info.get('tier', 'player')

        # Key entry box
        key_entry = [
            Paragraph(f'✨ {key_code} ✨', key_label_style),
            Spacer(1, 0.05*inch),
            Paragraph(f'<b>Tier:</b> {key_tier.upper()}', key_code_style),
            Spacer(1, 0.08*inch)
        ]

        for element in key_entry:
            story.append(element)

        # Divider
        story.append(Spacer(1, 0.15*inch))

    # Final spacing
    story.append(Spacer(1, 0.3*inch))

    # Footer
    footer_text = (
        'Generated by the Spellbook Keeper<br/>'
        'Never share these keys in public channels<br/>'
        'Report compromised keys immediately'
    )
    story.append(Paragraph(footer_text, footer_style))

    # Build PDF
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def _generate_fallback_html(batch_id, keys_data, theme_settings):
    """
    Fallback HTML-to-PDF for when reportlab is not available.
    Returns HTML that can be printed to PDF using browser.
    """
    if theme_settings is None:
        theme_settings = {
            'primary': '#4a235a',
            'accent': '#d4af37',
            'text': '#2a2a2a',
            'bg': '#f5e6d3'
        }

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Registration Keys - Batch {batch_id}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Georgia', serif;
                background-color: {theme_settings['bg']};
                color: {theme_settings['text']};
                padding: 0.75in;
            }}
            .container {{
                max-width: 8.5in;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 0.5in;
                border-bottom: 3px solid {theme_settings['accent']};
                padding-bottom: 0.25in;
            }}
            h1 {{
                font-size: 28px;
                color: {theme_settings['primary']};
                margin-bottom: 0.1in;
                letter-spacing: 2px;
            }}
            .batch-info {{
                font-size: 12px;
                color: {theme_settings['accent']};
                margin-bottom: 0.2in;
            }}
            .instructions {{
                background-color: rgba(212, 175, 55, 0.1);
                border-left: 4px solid {theme_settings['accent']};
                padding: 0.25in;
                margin-bottom: 0.3in;
                border-radius: 4px;
                text-align: center;
                line-height: 1.6;
            }}
            .keys-container {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.5in;
                margin-bottom: 0.5in;
            }}
            .key-entry {{
                border: 2px solid {theme_settings['accent']};
                padding: 0.25in;
                border-radius: 6px;
                background-color: white;
                text-align: center;
            }}
            .key-code {{
                font-family: 'Courier New', monospace;
                font-size: 14px;
                color: {theme_settings['primary']};
                font-weight: bold;
                letter-spacing: 2px;
                margin: 0.1in 0;
                word-break: break-all;
            }}
            .key-tier {{
                font-size: 10px;
                color: {theme_settings['accent']};
                text-transform: uppercase;
                font-weight: bold;
                margin-top: 0.05in;
            }}
            .footer {{
                text-align: center;
                font-size: 9px;
                color: {theme_settings['text']};
                border-top: 2px solid {theme_settings['accent']};
                padding-top: 0.2in;
                margin-top: 0.3in;
                font-style: italic;
            }}
            @media print {{
                body {{ padding: 0.5in; }}
                .key-entry {{ page-break-inside: avoid; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✨ SPELLBOOK REGISTRATION KEYS ✨</h1>
                <div class="batch-info">
                    Batch: {batch_id} | Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}
                </div>
            </div>

            <div class="instructions">
                <strong>Guard these runes carefully.</strong><br/>
                Share only with trusted adventurers. Each incantation grants access to the Spellbook.<br/><br/>
                <span style="color: {theme_settings['accent']}">Speak your access incantation at the gates to enter.</span>
            </div>

            <div class="keys-container">
    """

    # Add key entries
    for idx, key_info in enumerate(keys_data):
        key_code = key_info.get('key_code', '')
        key_tier = key_info.get('tier', 'player')
        html_content += f"""
                <div class="key-entry">
                    <div>✨</div>
                    <div class="key-code">{key_code}</div>
                    <div class="key-tier">Tier: {key_tier.upper()}</div>
                    <div>✨</div>
                </div>
        """

    html_content += """
            </div>

            <div class="footer">
                Generated by the Spellbook Keeper<br/>
                Never share these keys in public channels<br/>
                Report compromised keys immediately
            </div>
        </div>
    </body>
    </html>
    """

    return html_content.encode('utf-8')


def generate_key_batch_html(batch_id, keys_data, theme_settings=None):
    """
    Generate HTML version of key batch for web display or printing.
    """
    return _generate_fallback_html(batch_id, keys_data, theme_settings).decode('utf-8')
