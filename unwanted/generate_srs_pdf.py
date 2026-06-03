#!/usr/bin/env python3
"""
Generate SRS PDF from HTML using FPDF
"""
from fpdf import FPDF
import re

# Read HTML file
with open('SRS.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Extract text content from HTML
def html_to_text(html):
    # Remove style and script tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    # Replace common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('<br>', '\n')
    text = text.replace('<br/>', '\n')
    text = text.replace('<br />', '\n')
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities and remove unicode characters
    text = text.replace('📑', '')  # Remove emoji if any
    text = text.replace('≥', '>=')  # Replace >= symbol
    text = text.replace('≤', '<=')  # Replace <= symbol
    text = text.replace('→', '->')  # Replace arrow
    text = text.replace('–', '-')   # Replace en-dash
    text = text.replace(''', "'")   # Replace smart quote
    text = text.replace(''', "'")   # Replace smart quote
    # Remove any remaining non-latin1 characters
    text = ''.join(c if ord(c) < 256 else '?' for c in text)
    # Clean up whitespace
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()

content = html_to_text(html_content)

# Create PDF with better formatting
class CustomPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        pass
    
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

pdf = CustomPDF()
pdf.add_page()
pdf.set_font("Arial", "B", 14)
pdf.cell(0, 10, "Software Requirements Specification (SRS)", ln=True, align="C")
pdf.set_font("Arial", "", 11)
pdf.cell(0, 8, "Cyber Threat Intelligence RAG Chatbot", ln=True, align="C")
pdf.ln(5)

# Add content with proper formatting
pdf.set_font("Arial", size=9)
pdf.set_text_color(0, 0, 0)

lines = content.split('\n')
for line in lines:
    line = line.strip()
    if not line:
        pdf.ln(2)
        continue
    
    # Check if line is a heading (contains numbers like "1.", "2.", etc.)
    if re.match(r'^[\d]+\.', line):
        pdf.set_font("Arial", "B", 11)
        pdf.ln(2)
        pdf.multi_cell(0, 5, line, border=0)
        pdf.set_font("Arial", "", 9)
    elif line.startswith('##'):
        pdf.set_font("Arial", "B", 10)
        pdf.ln(1)
        pdf.multi_cell(0, 4, line.replace('##', '').strip())
        pdf.set_font("Arial", "", 9)
    else:
        # Regular text - wrap at word boundaries
        pdf.multi_cell(0, 4, line, border=0)

# Save PDF
pdf.output("CTI_RAG_Chatbot_SRS.pdf")
print("✓ SRS PDF generated successfully: CTI_RAG_Chatbot_SRS.pdf")
print("✓ File location: c:\\Users\\kpava\\OneDrive\\Desktop\\anti-rtrp\\CTI_RAG_Chatbot_SRS.pdf")
