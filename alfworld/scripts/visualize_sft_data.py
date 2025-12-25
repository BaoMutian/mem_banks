#!/usr/bin/env python3
"""
Visualize SFT training data in a web interface.

This script creates a local web server to browse and visualize SFT data
with a clean, intuitive interface.

Usage:
    python visualize_sft_data.py /path/to/sft_data.jsonl [--port 8080]
"""

import argparse
import json
import html
import os
import re
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from typing import List, Dict, Any

# Global data storage
DATA: List[Dict[str, Any]] = []
DATA_FILE: str = ""


def load_data(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL data from file."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text)


def format_message_content(content: str, role: str) -> str:
    """Format message content with proper styling."""
    content = escape_html(content)
    
    # Highlight Think: and Action: in assistant messages
    if role == "assistant":
        content = re.sub(
            r'^(Think:)',
            r'<span class="label think-label">Think:</span>',
            content,
            flags=re.MULTILINE
        )
        content = re.sub(
            r'^(Action:)',
            r'<span class="label action-label">Action:</span>',
            content,
            flags=re.MULTILINE
        )
    
    # Highlight section headers (===...===)
    content = re.sub(
        r'^(={10,})\n([^\n]+)\n(={10,})$',
        r'<div class="section-header">\2</div>',
        content,
        flags=re.MULTILINE
    )
    
    # Convert newlines to <br>
    content = content.replace('\n', '<br>')
    
    return content


def generate_html_page(page: int = 1, per_page: int = 1, search: str = "") -> str:
    """Generate HTML page for data visualization."""
    
    # Filter data if search term provided
    if search:
        filtered_data = []
        search_lower = search.lower()
        for item in DATA:
            # Search in all message contents and metadata
            found = False
            for msg in item.get("messages", []):
                if search_lower in msg.get("content", "").lower():
                    found = True
                    break
            if not found:
                metadata = item.get("metadata", {})
                if search_lower in str(metadata).lower():
                    found = True
            if found:
                filtered_data.append(item)
    else:
        filtered_data = DATA
    
    total_items = len(filtered_data)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    
    current_items = filtered_data[start_idx:end_idx]
    
    # Generate message HTML
    messages_html = ""
    for idx, item in enumerate(current_items, start=start_idx + 1):
        messages = item.get("messages", [])
        metadata = item.get("metadata", {})
        
        # Metadata card
        meta_html = ""
        if metadata:
            meta_items = []
            for key, value in metadata.items():
                if isinstance(value, bool):
                    value_str = "✓" if value else "✗"
                    value_class = "meta-success" if value else "meta-failed"
                else:
                    value_str = str(value)
                    value_class = ""
                meta_items.append(f'<span class="meta-item {value_class}"><strong>{key}:</strong> {escape_html(value_str)}</span>')
            meta_html = '<div class="metadata">' + ' '.join(meta_items) + '</div>'
        
        # Messages
        msg_cards = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            role_class = f"role-{role}"
            role_icon = {"system": "⚙️", "user": "👤", "assistant": "🤖"}.get(role, "❓")
            
            formatted_content = format_message_content(content, role)
            
            # Truncate very long content with expand option
            if len(content) > 3000:
                content_id = f"content-{idx}-{role}"
                msg_cards += f'''
                <div class="message-card {role_class}">
                    <div class="message-header">
                        <span class="role-icon">{role_icon}</span>
                        <span class="role-name">{role.upper()}</span>
                        <span class="content-length">({len(content):,} chars)</span>
                    </div>
                    <div class="message-content collapsed" id="{content_id}">
                        {formatted_content}
                    </div>
                    <button class="expand-btn" onclick="toggleExpand('{content_id}')">
                        展开 / 收起
                    </button>
                </div>
                '''
            else:
                msg_cards += f'''
                <div class="message-card {role_class}">
                    <div class="message-header">
                        <span class="role-icon">{role_icon}</span>
                        <span class="role-name">{role.upper()}</span>
                        <span class="content-length">({len(content):,} chars)</span>
                    </div>
                    <div class="message-content">
                        {formatted_content}
                    </div>
                </div>
                '''
        
        messages_html += f'''
        <div class="sample-card">
            <div class="sample-header">
                <span class="sample-index">#{idx}</span>
                {meta_html}
            </div>
            <div class="messages-container">
                {msg_cards}
            </div>
        </div>
        '''
    
    # Pagination
    pagination_html = '<div class="pagination">'
    
    # Previous button
    if page > 1:
        pagination_html += f'<a href="/?page={page-1}&search={escape_html(search)}" class="page-btn">◀ 上一条</a>'
    else:
        pagination_html += '<span class="page-btn disabled">◀ 上一条</span>'
    
    # Page info
    pagination_html += f'<span class="page-info">第 {page} / {total_pages} 条 (共 {total_items} 条)</span>'
    
    # Next button
    if page < total_pages:
        pagination_html += f'<a href="/?page={page+1}&search={escape_html(search)}" class="page-btn">下一条 ▶</a>'
    else:
        pagination_html += '<span class="page-btn disabled">下一条 ▶</span>'
    
    pagination_html += '</div>'
    
    # Quick navigation
    quick_nav = f'''
    <div class="quick-nav">
        <form action="/" method="get" class="nav-form">
            <input type="hidden" name="search" value="{escape_html(search)}">
            <label>跳转到:</label>
            <input type="number" name="page" min="1" max="{total_pages}" value="{page}" class="page-input">
            <button type="submit" class="go-btn">Go</button>
        </form>
    </div>
    '''
    
    # Full HTML page
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SFT Data Viewer - {escape_html(os.path.basename(DATA_FILE))}</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --border-color: #30363d;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-purple: #a371f7;
            --accent-orange: #d29922;
            --accent-red: #f85149;
            --system-bg: #1c2128;
            --user-bg: #0d419d;
            --assistant-bg: #238636;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 12px;
        }}
        
        h1 {{
            font-size: 1.5rem;
            margin-bottom: 15px;
            color: var(--accent-blue);
        }}
        
        .file-info {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .search-bar {{
            margin-top: 15px;
        }}
        
        .search-bar form {{
            display: flex;
            gap: 10px;
        }}
        
        .search-input {{
            flex: 1;
            padding: 10px 15px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 1rem;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
        }}
        
        .search-btn {{
            padding: 10px 20px;
            background: var(--accent-blue);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
        }}
        
        .search-btn:hover {{
            opacity: 0.9;
        }}
        
        .sample-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        
        .sample-header {{
            background: var(--bg-tertiary);
            padding: 15px 20px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .sample-index {{
            font-size: 1.2rem;
            font-weight: bold;
            color: var(--accent-purple);
        }}
        
        .metadata {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .meta-item {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            background: var(--bg-primary);
            padding: 4px 10px;
            border-radius: 6px;
        }}
        
        .meta-success {{
            color: var(--accent-green);
        }}
        
        .meta-failed {{
            color: var(--accent-red);
        }}
        
        .messages-container {{
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        
        .message-card {{
            border-radius: 10px;
            overflow: hidden;
        }}
        
        .message-header {{
            padding: 10px 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
        }}
        
        .role-icon {{
            font-size: 1.2rem;
        }}
        
        .role-name {{
            font-size: 0.9rem;
            letter-spacing: 1px;
        }}
        
        .content-length {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            font-weight: normal;
        }}
        
        .message-content {{
            padding: 15px;
            font-size: 0.95rem;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 600px;
            overflow-y: auto;
        }}
        
        .message-content.collapsed {{
            max-height: 300px;
            overflow: hidden;
            position: relative;
        }}
        
        .message-content.collapsed::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 60px;
            background: linear-gradient(transparent, var(--bg-secondary));
        }}
        
        .expand-btn {{
            width: 100%;
            padding: 8px;
            background: var(--bg-tertiary);
            border: none;
            color: var(--accent-blue);
            cursor: pointer;
            font-size: 0.85rem;
        }}
        
        .expand-btn:hover {{
            background: var(--border-color);
        }}
        
        .role-system .message-header {{
            background: var(--system-bg);
        }}
        
        .role-system .message-content {{
            background: #161b22;
            border-left: 3px solid var(--accent-orange);
        }}
        
        .role-user .message-header {{
            background: var(--user-bg);
        }}
        
        .role-user .message-content {{
            background: #0c2d6b;
            border-left: 3px solid var(--accent-blue);
        }}
        
        .role-assistant .message-header {{
            background: var(--assistant-bg);
        }}
        
        .role-assistant .message-content {{
            background: #1a4d2e;
            border-left: 3px solid var(--accent-green);
        }}
        
        .section-header {{
            background: var(--bg-tertiary);
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: 6px;
            font-weight: bold;
            color: var(--accent-blue);
            display: inline-block;
        }}
        
        .label {{
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 5px;
        }}
        
        .think-label {{
            background: var(--accent-purple);
            color: white;
        }}
        
        .action-label {{
            background: var(--accent-orange);
            color: black;
        }}
        
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin: 30px 0;
        }}
        
        .page-btn {{
            padding: 10px 20px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .page-btn:hover:not(.disabled) {{
            background: var(--accent-blue);
            border-color: var(--accent-blue);
        }}
        
        .page-btn.disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .page-info {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        .quick-nav {{
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
        }}
        
        .nav-form {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .nav-form label {{
            color: var(--text-secondary);
        }}
        
        .page-input {{
            width: 80px;
            padding: 8px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-primary);
            text-align: center;
        }}
        
        .go-btn {{
            padding: 8px 16px;
            background: var(--accent-purple);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }}
        
        .no-data {{
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
        }}
        
        .no-data h2 {{
            margin-bottom: 10px;
            color: var(--accent-red);
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: var(--bg-primary);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--border-color);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 SFT Data Viewer</h1>
            <div class="file-info">
                📁 {escape_html(DATA_FILE)} | 📊 共 {len(DATA):,} 条数据
            </div>
            <div class="search-bar">
                <form action="/" method="get">
                    <input type="text" name="search" class="search-input" 
                           placeholder="搜索内容 (支持 game_id, action, 任意文本...)" 
                           value="{escape_html(search)}">
                    <button type="submit" class="search-btn">🔍 搜索</button>
                    {f'<a href="/" class="search-btn" style="background: var(--accent-red); text-decoration: none;">✕ 清除</a>' if search else ''}
                </form>
            </div>
        </header>
        
        {pagination_html}
        {quick_nav}
        
        {messages_html if messages_html else '<div class="no-data"><h2>没有找到数据</h2><p>请检查搜索条件或文件内容</p></div>'}
        
        {pagination_html}
        
        <footer>
            SFT Data Viewer | 按 Ctrl+C 停止服务器
        </footer>
    </div>
    
    <script>
        function toggleExpand(contentId) {{
            const content = document.getElementById(contentId);
            content.classList.toggle('collapsed');
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', function(e) {{
            if (e.target.tagName === 'INPUT') return;
            
            const currentPage = {page};
            const totalPages = {total_pages};
            const search = '{escape_html(search)}';
            
            if (e.key === 'ArrowLeft' && currentPage > 1) {{
                window.location.href = '/?page=' + (currentPage - 1) + '&search=' + encodeURIComponent(search);
            }} else if (e.key === 'ArrowRight' && currentPage < totalPages) {{
                window.location.href = '/?page=' + (currentPage + 1) + '&search=' + encodeURIComponent(search);
            }}
        }});
    </script>
</body>
</html>'''


class SFTDataHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for SFT data visualization."""
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        
        if parsed.path == '/' or parsed.path == '':
            # Parse query parameters
            params = parse_qs(parsed.query)
            page = int(params.get('page', ['1'])[0])
            search = params.get('search', [''])[0]
            
            # Generate HTML
            html_content = generate_html_page(page=page, search=search)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        else:
            self.send_error(404, "Not Found")
    
    def log_message(self, format, *args):
        """Suppress default logging, show simplified version."""
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Visualize SFT training data in a web interface."
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to the SFT data file (JSONL format)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Port to run the server on (default: 8080)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )
    
    args = parser.parse_args()
    
    # Validate file
    if not os.path.isfile(args.file):
        print(f"Error: {args.file} is not a valid file")
        sys.exit(1)
    
    # Load data
    global DATA, DATA_FILE
    DATA_FILE = args.file
    print(f"📂 Loading data from: {args.file}")
    DATA = load_data(args.file)
    print(f"✅ Loaded {len(DATA):,} samples")
    
    # Start server
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, SFTDataHandler)
    
    print(f"\n🚀 Server running at: http://{args.host}:{args.port}")
    print(f"📖 Press Ctrl+C to stop\n")
    print("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        httpd.shutdown()


if __name__ == "__main__":
    main()

