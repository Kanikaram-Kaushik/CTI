#!/usr/bin/env python3
"""
Convert Markdown to PDF using reportlab
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
import re
import os

# Read markdown file
with open('PROJECT_DOCUMENTATION.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Create PDF document
pdf_filename = 'PROJECT_DOCUMENTATION.pdf'
doc = SimpleDocTemplate(pdf_filename, pagesize=letter,
                        rightMargin=0.75*inch, leftMargin=0.75*inch,
                        topMargin=0.75*inch, bottomMargin=0.75*inch)

# Container for the 'Flowable' objects
elements = []

# Define styles
styles = getSampleStyleSheet()

# Create custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#1a73e8'),
    spaceAfter=20,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading1_style = ParagraphStyle(
    'CustomHeading1',
    parent=styles['Heading1'],
    fontSize=16,
    textColor=colors.HexColor('#1a73e8'),
    spaceAfter=12,
    spaceBefore=12,
    fontName='Helvetica-Bold'
)

heading2_style = ParagraphStyle(
    'CustomHeading2',
    parent=styles['Heading2'],
    fontSize=12,
    textColor=colors.HexColor('#34495e'),
    spaceAfter=10,
    spaceBefore=10,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=10,
    alignment=TA_JUSTIFY,
    spaceAfter=10
)

# Simple markdown to PDF parser
lines = content.split('\n')
i = 0

while i < len(lines):
    line = lines[i].strip()
    
    if not line:
        elements.append(Spacer(1, 0.1*inch))
        i += 1
        continue
    
    # Handle headings
    if line.startswith('# '):
        text = line[2:].strip()
        elements.append(Paragraph(text, title_style))
        i += 1
    elif line.startswith('## '):
        text = line[3:].strip()
        elements.append(Paragraph(text, heading1_style))
        i += 1
    elif line.startswith('### '):
        text = line[4:].strip()
        elements.append(Paragraph(text, heading2_style))
        i += 1
    elif line.startswith('#### '):
        text = line[5:].strip()
        elements.append(Paragraph(f'<b>{text}</b>', body_style))
        i += 1
    # Handle code blocks
    elif line.startswith('```'):
        code_lines = []
        i += 1
        while i < len(lines) and not lines[i].strip().startswith('```'):
            code_lines.append(lines[i])
            i += 1
        
        code_text = '\n'.join(code_lines)
        code_style = ParagraphStyle(
            'Code',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Courier',
            textColor=colors.HexColor('#333333'),
            backColor=colors.HexColor('#f4f4f4'),
            leftIndent=0.2*inch,
            spaceAfter=10,
            alignment=TA_LEFT
        )
        for code_line in code_lines:
            if code_line.strip():
                elements.append(Paragraph(code_line.replace('<', '&lt;').replace('>', '&gt;'), code_style))
        i += 1
    # Handle unordered lists
    elif line.startswith('- '):
        list_items = []
        while i < len(lines) and lines[i].strip().startswith('- '):
            item_text = lines[i].strip()[2:].strip()
            list_items.append(item_text)
            i += 1
        for item in list_items:
            elements.append(Paragraph(f'• {item}', body_style))
    # Handle bold text
    elif '**' in line:
        formatted = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', line)
        elements.append(Paragraph(formatted, body_style))
        i += 1
    # Handle regular paragraphs
    else:
        elements.append(Paragraph(line, body_style))
        i += 1

# Add page break after every 50 elements to manage document length
final_elements = []
for idx, element in enumerate(elements):
    final_elements.append(element)
    if idx > 0 and idx % 100 == 0:
        final_elements.append(PageBreak())

# Build PDF
try:
    doc.build(final_elements)
    print(f"✓ PDF created successfully: {pdf_filename}")
    file_size = os.path.getsize(pdf_filename) / (1024 * 1024)
    print(f"File size: {file_size:.2f} MB")
    print(f"Location: {os.path.abspath(pdf_filename)}")
except Exception as e:
    print(f"✗ Error creating PDF: {e}")
