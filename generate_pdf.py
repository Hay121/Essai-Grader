"""
Generate Mathematical Foundations PDF for EssayGrader
=====================================================
Script ini mengkonversi mathematical_foundations.md menjadi PDF profesional.

Pendekatan: Membuat file HTML dengan styling profesional dan KaTeX untuk
rendering matematika, lalu mengkonversi ke PDF menggunakan browser.
"""

import re
import os
import subprocess
import sys

def md_to_styled_html(md_content: str) -> str:
    """Convert markdown content to beautifully styled HTML with KaTeX math support."""
    
    # =========================================================================
    # STEP 1: Extract and protect math blocks
    # =========================================================================
    math_blocks = {}
    counter = [0]
    
    def replace_display_math(match):
        counter[0] += 1
        key = f"%%DISPLAYMATH{counter[0]}%%"
        formula = match.group(1).strip()
        math_blocks[key] = f'<div class="math-display">\\[{formula}\\]</div>'
        return key
    
    def replace_inline_math(match):
        counter[0] += 1
        key = f"%%INLINEMATH{counter[0]}%%"
        formula = match.group(1).strip()
        math_blocks[key] = f'<span class="math-inline">\\({formula}\\)</span>'
        return key
    
    # Protect code blocks first
    code_blocks = {}
    code_counter = [0]
    
    def replace_code_block(match):
        code_counter[0] += 1
        key = f"%%CODEBLOCK{code_counter[0]}%%"
        lang = match.group(1) or ''
        code = match.group(2)
        if lang.strip() == 'mermaid':
            code_blocks[key] = f'<div class="mermaid-placeholder"><div class="mermaid-label">📊 Diagram Alur (Mermaid)</div><pre class="mermaid-code">{html_escape(code)}</pre></div>'
        else:
            code_blocks[key] = f'<pre class="code-block"><code class="language-{lang}">{html_escape(code)}</code></pre>'
        return key
    
    # Replace code blocks
    md_content = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, md_content, flags=re.DOTALL)
    
    # Replace display math ($$...$$)
    md_content = re.sub(r'\$\$(.*?)\$\$', replace_display_math, md_content, flags=re.DOTALL)
    
    # Replace inline math ($...$)
    md_content = re.sub(r'\$([^\$\n]+?)\$', replace_inline_math, md_content)
    
    # =========================================================================
    # STEP 2: Convert Markdown to HTML
    # =========================================================================
    lines = md_content.split('\n')
    html_lines = []
    in_table = False
    table_rows = []
    in_blockquote = False
    blockquote_lines = []
    in_ul = False
    ul_items = []
    
    def flush_table():
        nonlocal in_table, table_rows
        if table_rows:
            html = '<div class="table-wrapper"><table>\n'
            for i, row in enumerate(table_rows):
                cells = [c.strip() for c in row.strip('|').split('|')]
                if i == 0:
                    html += '<thead><tr>' + ''.join(f'<th>{process_inline(c)}</th>' for c in cells) + '</tr></thead>\n<tbody>\n'
                elif all(set(c.strip()) <= set('-: ') for c in cells):
                    continue  # separator row
                else:
                    html += '<tr>' + ''.join(f'<td>{process_inline(c)}</td>' for c in cells) + '</tr>\n'
            html += '</tbody></table></div>\n'
            html_lines.append(html)
        table_rows = []
        in_table = False
    
    def flush_blockquote():
        nonlocal in_blockquote, blockquote_lines
        if blockquote_lines:
            content = '\n'.join(blockquote_lines)
            # Check for alert types
            alert_type = None
            alert_map = {
                '[!NOTE]': ('note', '📝 Catatan'),
                '[!TIP]': ('tip', '💡 Tips'),
                '[!IMPORTANT]': ('important', '⚠️ Penting'),
                '[!WARNING]': ('warning', '⚠️ Peringatan'),
                '[!CAUTION]': ('caution', '🚫 Perhatian'),
            }
            for marker, (cls, label) in alert_map.items():
                if marker in content:
                    content = content.replace(marker, '').strip()
                    content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE).strip()
                    alert_type = cls
                    html_lines.append(f'<div class="alert alert-{cls}"><div class="alert-title">{label}</div><p>{process_inline(content)}</p></div>')
                    break
            if not alert_type:
                content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE).strip()
                html_lines.append(f'<blockquote><p>{process_inline(content)}</p></blockquote>')
        blockquote_lines = []
        in_blockquote = False
    
    def flush_ul():
        nonlocal in_ul, ul_items
        if ul_items:
            html = '<ul>\n'
            for item in ul_items:
                html += f'<li>{process_inline(item)}</li>\n'
            html += '</ul>\n'
            html_lines.append(html)
        ul_items = []
        in_ul = False
    
    def process_inline(text):
        """Process inline markdown elements."""
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', text)
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # Strikethrough
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        # Emoji-like symbols
        text = text.replace('❌', '<span class="emoji">❌</span>')
        text = text.replace('✅', '<span class="emoji">✅</span>')
        return text
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Empty line
        if not stripped:
            if in_table: flush_table()
            if in_blockquote: flush_blockquote()
            if in_ul: flush_ul()
            i += 1
            continue
        
        # Horizontal rule
        if stripped == '---' or stripped == '***' or stripped == '___':
            if in_table: flush_table()
            if in_blockquote: flush_blockquote()
            if in_ul: flush_ul()
            html_lines.append('<hr class="section-divider">')
            i += 1
            continue
        
        # Headers
        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            if in_table: flush_table()
            if in_blockquote: flush_blockquote()
            if in_ul: flush_ul()
            level = len(header_match.group(1))
            text = header_match.group(2)
            # Create an id for the header
            header_id = re.sub(r'[^\w\s-]', '', text.lower())
            header_id = re.sub(r'\s+', '-', header_id).strip('-')
            classes = f'h{level}'
            if level == 1:
                html_lines.append(f'<h1 id="{header_id}" class="main-title">{process_inline(text)}</h1>')
            elif level == 2:
                html_lines.append(f'<h2 id="{header_id}" class="section-title"><span class="section-number"></span>{process_inline(text)}</h2>')
            elif level == 3:
                html_lines.append(f'<h3 id="{header_id}" class="subsection-title">{process_inline(text)}</h3>')
            elif level == 4:
                html_lines.append(f'<h4 id="{header_id}">{process_inline(text)}</h4>')
            else:
                html_lines.append(f'<h{level} id="{header_id}">{process_inline(text)}</h{level}>')
            i += 1
            continue
        
        # Table
        if '|' in stripped and not stripped.startswith('>'):
            if in_blockquote: flush_blockquote()
            if in_ul: flush_ul()
            in_table = True
            table_rows.append(stripped)
            i += 1
            continue
        
        # Blockquote
        if stripped.startswith('>'):
            if in_table: flush_table()
            if in_ul: flush_ul()
            in_blockquote = True
            blockquote_lines.append(stripped)
            i += 1
            continue
        
        # Unordered list
        list_match = re.match(r'^[-*]\s+(.+)$', stripped)
        if list_match:
            if in_table: flush_table()
            if in_blockquote: flush_blockquote()
            in_ul = True
            ul_items.append(list_match.group(1))
            i += 1
            continue
        
        # Ordered list
        ol_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if ol_match:
            if in_table: flush_table()
            if in_blockquote: flush_blockquote()
            if in_ul: flush_ul()
            # Collect all ordered list items
            ol_items = []
            while i < len(lines):
                ol_m = re.match(r'^\d+\.\s+(.+)$', lines[i].strip())
                if ol_m:
                    ol_items.append(ol_m.group(1))
                    i += 1
                elif lines[i].strip().startswith('   ') and ol_items:
                    # continuation of previous item
                    ol_items[-1] += ' ' + lines[i].strip()
                    i += 1
                elif lines[i].strip() == '':
                    break
                else:
                    break
            html = '<ol>\n'
            for item in ol_items:
                html += f'<li>{process_inline(item)}</li>\n'
            html += '</ol>\n'
            html_lines.append(html)
            continue
        
        # Regular paragraph
        if in_table: flush_table()
        if in_blockquote: flush_blockquote()
        if in_ul: flush_ul()
        
        # Check if it's a placeholder for math/code
        if stripped.startswith('%%'):
            html_lines.append(stripped)
        else:
            html_lines.append(f'<p>{process_inline(stripped)}</p>')
        i += 1
    
    # Flush remaining
    if in_table: flush_table()
    if in_blockquote: flush_blockquote()
    if in_ul: flush_ul()
    
    body_html = '\n'.join(html_lines)
    
    # =========================================================================
    # STEP 3: Restore math and code blocks
    # =========================================================================
    for key, value in code_blocks.items():
        body_html = body_html.replace(key, value)
        # Also handle wrapped in <p>
        body_html = body_html.replace(f'<p>{key}</p>', value)
    
    for key, value in math_blocks.items():
        body_html = body_html.replace(key, value)
        body_html = body_html.replace(f'<p>{key}</p>', value)
    
    # =========================================================================
    # STEP 4: Wrap in full HTML document with styling
    # =========================================================================
    full_html = f'''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landasan Matematika — EssayGrader</title>
    
    <!-- KaTeX CSS & JS for math rendering -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {{
            delimiters: [
                {{left: '\\\\[', right: '\\\\]', display: true}},
                {{left: '\\\\(', right: '\\\\)', display: false}}
            ],
            throwOnError: false
        }});"></script>
    
    <style>
        /* ============================================================
           PROFESSIONAL PDF STYLING - EssayGrader Mathematical Foundations
           ============================================================ */
        
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&family=STIX+Two+Text:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');
        
        :root {{
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #3182ce;
            --accent-light: #63b3ed;
            --bg: #ffffff;
            --text: #1a202c;
            --text-secondary: #4a5568;
            --text-muted: #718096;
            --border: #e2e8f0;
            --border-light: #edf2f7;
            --code-bg: #f7fafc;
            --note-bg: #ebf8ff;
            --note-border: #3182ce;
            --tip-bg: #f0fff4;
            --tip-border: #38a169;
            --important-bg: #fffbeb;
            --important-border: #d69e2e;
            --warning-bg: #fff5f5;
            --warning-border: #e53e3e;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'STIX Two Text', 'Inter', 'Georgia', serif;
            font-size: 11pt;
            line-height: 1.7;
            color: var(--text);
            background: var(--bg);
            max-width: 210mm;
            margin: 0 auto;
            padding: 25mm 20mm 25mm 25mm;
        }}
        
        /* ---- Page break & print settings ---- */
        @media print {{
            body {{
                padding: 0;
                max-width: none;
            }}
            
            @page {{
                size: A4;
                margin: 25mm 20mm 25mm 25mm;
            }}
            
            h1, h2, h3, h4 {{
                page-break-after: avoid;
            }}
            
            table, pre, .math-display, .alert {{
                page-break-inside: avoid;
            }}
            
            .section-divider {{
                page-break-before: auto;
            }}
        }}
        
        /* ---- Cover / Title ---- */
        .main-title {{
            font-family: 'Inter', sans-serif;
            font-size: 26pt;
            font-weight: 800;
            color: var(--primary);
            text-align: center;
            margin-top: 40px;
            margin-bottom: 8px;
            line-height: 1.2;
            letter-spacing: -0.5px;
        }}
        
        /* ---- Subtitle (first h2 used as subtitle) ---- */
        .section-title {{
            font-family: 'Inter', sans-serif;
            font-size: 16pt;
            font-weight: 700;
            color: var(--primary);
            border-bottom: 3px solid var(--accent);
            padding-bottom: 8px;
            margin-top: 35px;
            margin-bottom: 18px;
            line-height: 1.3;
        }}
        
        .subsection-title {{
            font-family: 'Inter', sans-serif;
            font-size: 13pt;
            font-weight: 600;
            color: var(--primary-light);
            margin-top: 25px;
            margin-bottom: 12px;
            border-left: 4px solid var(--accent);
            padding-left: 12px;
        }}
        
        h4 {{
            font-family: 'Inter', sans-serif;
            font-size: 11.5pt;
            font-weight: 600;
            color: var(--text);
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        /* ---- Body Text ---- */
        p {{
            margin-bottom: 10px;
            text-align: justify;
            hyphens: auto;
        }}
        
        strong {{
            font-weight: 600;
            color: var(--primary);
        }}
        
        em {{
            font-style: italic;
            color: var(--text-secondary);
        }}
        
        /* ---- Lists ---- */
        ol, ul {{
            margin: 10px 0 10px 25px;
        }}
        
        li {{
            margin-bottom: 5px;
            line-height: 1.6;
        }}
        
        /* ---- Horizontal Rule ---- */
        .section-divider {{
            border: none;
            height: 1px;
            background: linear-gradient(to right, transparent, var(--border), var(--accent-light), var(--border), transparent);
            margin: 30px 0;
        }}
        
        /* ---- Tables ---- */
        .table-wrapper {{
            margin: 15px 0;
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 10pt;
            margin: 0 auto;
        }}
        
        thead {{
            background: var(--primary);
            color: white;
        }}
        
        th {{
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            padding: 10px 14px;
            text-align: left;
            font-size: 9.5pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 9px 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}
        
        tbody tr:nth-child(even) {{
            background-color: var(--border-light);
        }}
        
        tbody tr:hover {{
            background-color: #edf2f7;
        }}
        
        /* ---- Code ---- */
        .inline-code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9.5pt;
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 3px;
            padding: 1px 5px;
            color: #c7254e;
        }}
        
        .code-block {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 9pt;
            background: #1a202c;
            color: #e2e8f0;
            border-radius: 8px;
            padding: 16px 20px;
            margin: 15px 0;
            overflow-x: auto;
            line-height: 1.5;
        }}
        
        .code-block code {{
            font-family: inherit;
        }}
        
        /* ---- Mermaid Placeholder ---- */
        .mermaid-placeholder {{
            background: linear-gradient(135deg, #ebf8ff 0%, #e9d8fd 100%);
            border: 2px dashed var(--accent);
            border-radius: 8px;
            padding: 20px;
            margin: 15px 0;
            text-align: center;
        }}
        
        .mermaid-label {{
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            color: var(--primary);
            font-size: 12pt;
            margin-bottom: 10px;
        }}
        
        .mermaid-code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 8pt;
            text-align: left;
            background: rgba(255,255,255,0.7);
            padding: 12px;
            border-radius: 6px;
            color: var(--text-secondary);
            white-space: pre-wrap;
        }}
        
        /* ---- Math ---- */
        .math-display {{
            margin: 18px 0;
            text-align: center;
            overflow-x: auto;
            padding: 10px 0;
        }}
        
        .math-inline {{
            padding: 0 2px;
        }}
        
        /* ---- Alerts / Callouts ---- */
        .alert {{
            border-radius: 8px;
            padding: 14px 18px;
            margin: 15px 0;
            border-left: 5px solid;
            font-size: 10pt;
        }}
        
        .alert-title {{
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 10pt;
            margin-bottom: 6px;
        }}
        
        .alert-note {{
            background: var(--note-bg);
            border-color: var(--note-border);
        }}
        .alert-note .alert-title {{ color: var(--note-border); }}
        
        .alert-tip {{
            background: var(--tip-bg);
            border-color: var(--tip-border);
        }}
        .alert-tip .alert-title {{ color: var(--tip-border); }}
        
        .alert-important {{
            background: var(--important-bg);
            border-color: var(--important-border);
        }}
        .alert-important .alert-title {{ color: var(--important-border); }}
        
        .alert-warning, .alert-caution {{
            background: var(--warning-bg);
            border-color: var(--warning-border);
        }}
        .alert-warning .alert-title,
        .alert-caution .alert-title {{ color: var(--warning-border); }}
        
        /* ---- Blockquote ---- */
        blockquote {{
            border-left: 4px solid var(--border);
            padding: 10px 16px;
            margin: 15px 0;
            background: var(--border-light);
            border-radius: 0 6px 6px 0;
            color: var(--text-secondary);
            font-style: italic;
        }}
        
        /* ---- Links ---- */
        a {{
            color: var(--accent);
            text-decoration: none;
            border-bottom: 1px dotted var(--accent-light);
        }}
        
        /* ---- Table of Contents ---- */
        ol li a {{
            border-bottom: none;
        }}
        
        /* ---- Footer Info ---- */
        .doc-footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid var(--border);
            font-family: 'Inter', sans-serif;
            font-size: 8.5pt;
            color: var(--text-muted);
            text-align: center;
        }}
        
        /* ---- Page numbers (print) ---- */
        @media print {{
            body {{
                counter-reset: page-num;
            }}
            .doc-footer {{
                display: none;
            }}
        }}
        
        /* ---- Emoji ---- */
        .emoji {{
            font-style: normal;
        }}
    </style>
</head>
<body>
    <div class="document-content">
        {body_html}
    </div>
    
    <div class="doc-footer">
        <p>Dokumen ini digenerate secara otomatis dari <strong>mathematical_foundations.md</strong></p>
        <p>EssayGrader — Sistem Penilaian Esai Otomatis Berbasis Aljabar Linier</p>
    </div>
</body>
</html>'''
    
    return full_html


def html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def main():
    # Read the markdown file
    md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mathematical_foundations.md')
    
    if not os.path.exists(md_path):
        print(f"ERROR: File tidak ditemukan: {md_path}")
        sys.exit(1)
    
    print(f"📖 Membaca: {md_path}")
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML
    print("🔄 Mengkonversi Markdown → HTML...")
    html_content = md_to_styled_html(md_content)
    
    # Save HTML
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mathematical_foundations.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML berhasil dibuat: {html_path}")
    
    # Try to convert to PDF using different methods
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mathematical_foundations.pdf')
    
    # Method 1: Try using Microsoft Edge / Chrome headless to print PDF
    pdf_generated = False
    
    # Try Chrome
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    ]
    
    # Try Edge
    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]
    
    browser_path = None
    for p in chrome_paths + edge_paths:
        if os.path.exists(p):
            browser_path = p
            break
    
    if browser_path:
        print(f"🖨️  Menggunakan browser untuk generate PDF: {os.path.basename(browser_path)}")
        try:
            # Use headless browser to print PDF
            abs_html = os.path.abspath(html_path)
            file_url = f'file:///{abs_html.replace(os.sep, "/")}'
            
            cmd = [
                browser_path,
                '--headless',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-software-rasterizer',
                '--run-all-compositor-stages-before-draw',
                '--virtual-time-budget=10000',
                f'--print-to-pdf={pdf_path}',
                '--print-to-pdf-no-header',
                '--no-pdf-header-footer',
                file_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                pdf_generated = True
                print(f"✅ PDF berhasil dibuat: {pdf_path}")
                print(f"   Ukuran: {os.path.getsize(pdf_path):,} bytes")
            else:
                print(f"⚠️  PDF generation via browser gagal.")
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}")
        except Exception as e:
            print(f"⚠️  Browser PDF generation error: {e}")
    
    if not pdf_generated:
        print("\n" + "="*60)
        print("📋 INSTRUKSI MANUAL untuk membuat PDF:")
        print("="*60)
        print(f"\n1. Buka file HTML di browser:")
        print(f"   {os.path.abspath(html_path)}")
        print(f"\n2. Tunggu beberapa detik hingga rumus matematika ter-render")
        print(f"\n3. Tekan Ctrl+P (Print)")
        print(f"\n4. Pilih 'Save as PDF' / 'Microsoft Print to PDF'")
        print(f"\n5. Simpan sebagai: mathematical_foundations.pdf")
        print("="*60)
    
    return pdf_generated


if __name__ == '__main__':
    main()
