APP_CSS = '''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        .hit-file { font-weight: bold; }
        .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; border-color: #fbbf24 !important; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        /* モダンチャットUI用 */
        .chat-bubble { font-family: "Inter", sans-serif; font-size: 0.95rem; line-height: 1.7; border-radius: 1.25rem; }
        .code-preview { background-color: #0d1117 !important; border-radius: 8px; color: #e6edf3; }
        .code-preview pre, .code-preview code { font-family: "JetBrains Mono", monospace !important; font-size: 13px !important; }
        /* Prismの背景と余白を完全に除去して親に合わせる */
        .code-preview .nicegui-code { padding: 0 !important; background: transparent !important; }
        .code-preview .nicegui-code pre { background: transparent !important; margin: 0 !important; padding: 0 !important; color: inherit !important; overflow: visible !important; }
        .line-numbers-col { 
            border-right: 1px solid #30363d; 
            color: #6e7681; 
            text-align: right; 
            padding-right: 12px !important; 
            user-select: none;
            line-height: 20px; /* 重要: コードの行高さと合わせる */
        }
        .code-col {
            padding-left: 12px !important;
            line-height: 20px; /* 重要: 行番号と合わせる */
        }
        .search-highlight-line {
            background-color: rgba(96, 165, 250, 0.2) !important;
            width: 100%;
            display: inline-block;
        }
        /* ステータス画面用スタイル (rag_web_ui.py 互換) */
        .status-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%; }
        .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
        .status-value { font-size: 12px; color: #f1f5f9; font-family: "JetBrains Mono", monospace; font-weight: 500; }
        
        /* Gap Analysis カードスタイル */
        .gap-card { 
            border-left: 4px solid #f87171; 
            background: #fef2f2; 
            padding: 12px; 
            border-radius: 8px; 
            margin-top: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .gap-file { font-size: 0.75rem; font-weight: bold; color: #b91c1c; margin-bottom: 4px; }
        .gap-issue { font-size: 0.85rem; color: #450a0a; line-height: 1.5; }
    </style>
'''
