import os, re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def escape_html(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')

def format_line(line, is_redacted, code_style, redacted_style):
    m = re.match(r'^(\s+)', line)
    indent = m.group(1) if m else ""
    content = line[len(indent):].rstrip()
    
    html_indent = "&nbsp;" * len(indent)
    html_content = escape_html(content)
    
    if not content:
        return Paragraph("&nbsp;", code_style)
    if is_redacted:
        return Paragraph(html_indent + f"<font color='black'>{html_content}</font>", redacted_style)
    return Paragraph(html_indent + html_content, code_style)

def main():
    pdf_path = "DealEngine_SourceCode_Redacted.pdf"
    doc = SimpleDocTemplate(
        pdf_path, pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#1A365D'), spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        name='SubTitleStyle', fontName='Helvetica-Oblique', fontSize=10, leading=13, textColor=colors.HexColor('#4A5568'), spaceAfter=20
    )
    file_header_style = ParagraphStyle(
        name='FileHeaderStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor('#2B6CB0'), spaceBefore=10, spaceAfter=5, keepWithNext=True
    )
    code_style = ParagraphStyle(
        name='CodeStyle', fontName='Courier', fontSize=7.5, leading=9, textColor=colors.HexColor('#1A202C')
    )
    redacted_style = ParagraphStyle(
        name='RedactedStyle', fontName='Courier', fontSize=7.5, leading=9, textColor=colors.black, backColor=colors.black
    )
    
    story = []
    story.append(Spacer(1, 10))
    story.append(Paragraph("DEALENGINE SOURCE CODE", title_style))
    story.append(Paragraph("Core Acquisitions Underwriting & CRM Webhook Pipeline — Redacted Showcase Edition", subtitle_style))
    
    files = [
        {"path": "schema.py", "name": "schema.py (Pydantic Data Schemas)"},
        {"path": "main.py", "name": "main.py (Production FastAPI Entrypoint)"},
        {"path": "test_engine.py", "name": "test_engine.py (Underwriting Helper Script)"},
        {"path": "system_prompt.txt", "name": "system_prompt.txt (Acquisitions System Prompt)"}
    ]
    
    for f_info in files:
        path = f_info["path"]
        if not os.path.exists(path):
            continue
            
        print(f"Processing: {path}")
        story.append(Paragraph(f"📄 File: /{f_info['name']}", file_header_style))
        story.append(Spacer(1, 4))
        
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        is_redacting = False
        for line in lines:
            if path == "system_prompt.txt":
                is_line_redacted = True
            elif path == "schema.py":
                is_line_redacted = False
            elif path == "main.py":
                if "VALID_API_KEYS = {" in line:
                    is_redacting = True
                elif "is_gemini =" in line and is_redacting:
                    is_redacting = False
                    
                if "async def process_and_update_ghl_contact" in line:
                    story.append(format_line(line, False, code_style, redacted_style))
                    is_redacting = True
                    continue
                elif "@app.post" in line and is_redacting:
                    is_redacting = False
                is_line_redacted = is_redacting
            elif path == "test_engine.py":
                if "def evaluate_deal_api" in line:
                    story.append(format_line(line, False, code_style, redacted_style))
                    is_redacting = True
                    continue
                elif 'if __name__ == "__main__":' in line:
                    is_redacting = False
                is_line_redacted = is_redacting
            else:
                is_line_redacted = False
                
            story.append(format_line(line, is_line_redacted, code_style, redacted_style))
            
        story.append(Spacer(1, 10))
        story.append(PageBreak())
        
    doc.build(story)
    print(f"Successfully generated: {pdf_path}")

if __name__ == "__main__":
    main()
