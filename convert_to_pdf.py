import markdown
from weasyprint import HTML, CSS
import os

# Read the markdown file
with open('PROJECT_DOCUMENTATION.md', 'r', encoding='utf-8') as f:
    md_content = f.read()

# Convert markdown to HTML
html_content = markdown.markdown(
    md_content,
    extensions=['tables', 'fenced_code', 'toc']
)

# Add CSS styling for PDF
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: white;
            padding: 40px;
            font-size: 11pt;
        }}
        
        h1 {{
            font-size: 28pt;
            color: #1a73e8;
            margin-top: 30px;
            margin-bottom: 20px;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
            page-break-after: avoid;
        }}
        
        h2 {{
            font-size: 18pt;
            color: #1a73e8;
            margin-top: 25px;
            margin-bottom: 15px;
            page-break-after: avoid;
        }}
        
        h3 {{
            font-size: 14pt;
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 12px;
            page-break-after: avoid;
        }}
        
        h4 {{
            font-size: 12pt;
            color: #555;
            margin-top: 15px;
            margin-bottom: 10px;
            font-weight: 600;
            page-break-after: avoid;
        }}
        
        p {{
            margin-bottom: 12px;
            text-align: justify;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
        }}
        
        th {{
            background-color: #1a73e8;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
            border: 1px solid #1a73e8;
        }}
        
        td {{
            padding: 10px 12px;
            border: 1px solid #ddd;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        tr:hover {{
            background-color: #f0f0f0;
        }}
        
        ul, ol {{
            margin-left: 30px;
            margin-bottom: 15px;
        }}
        
        li {{
            margin-bottom: 8px;
        }}
        
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 10pt;
            color: #d63384;
        }}
        
        pre {{
            background-color: #f4f4f4;
            border-left: 4px solid #1a73e8;
            padding: 15px;
            margin: 15px 0;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 9pt;
            border-radius: 4px;
            page-break-inside: avoid;
        }}
        
        pre code {{
            background-color: transparent;
            padding: 0;
            color: #333;
        }}
        
        blockquote {{
            border-left: 4px solid #ddd;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
        }}
        
        strong {{
            color: #1a73e8;
            font-weight: 600;
        }}
        
        em {{
            font-style: italic;
            color: #555;
        }}
        
        a {{
            color: #1a73e8;
            text-decoration: none;
            border-bottom: 1px dashed #1a73e8;
        }}
        
        .toc {{
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            padding: 20px;
            margin: 20px 0;
            page-break-inside: avoid;
            border-radius: 4px;
        }}
        
        .toc ul {{
            margin-left: 20px;
        }}
        
        .toc a {{
            text-decoration: none;
            border-bottom: 1px dashed #1a73e8;
        }}
        
        hr {{
            margin: 30px 0;
            border: none;
            border-top: 2px solid #ddd;
        }}
        
        /* Page breaks and spacing */
        h1 {{
            page-break-before: avoid;
        }}
        
        /* For title page */
        .document-title {{
            text-align: center;
            margin-top: 100px;
            margin-bottom: 100px;
        }}
        
        .document-title h1 {{
            font-size: 36pt;
            color: #1a73e8;
        }}
        
        .document-meta {{
            text-align: center;
            font-size: 12pt;
            color: #666;
            margin-top: 50px;
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""

# Convert HTML to PDF
try:
    HTML(string=full_html).write_pdf('PROJECT_DOCUMENTATION.pdf')
    print("✓ PDF created successfully: PROJECT_DOCUMENTATION.pdf")
    file_size = os.path.getsize('PROJECT_DOCUMENTATION.pdf') / (1024 * 1024)
    print(f"File size: {file_size:.2f} MB")
except Exception as e:
    print(f"✗ Error creating PDF: {e}")
    print("Attempting alternative method...")

