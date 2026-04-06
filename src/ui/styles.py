"""グローバルCSSスタイルを定義します。"""

from nicegui import ui

def apply_global_styles() -> None:
    """カスタムCSSスタイルをページのheadに追加します。"""
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
        <style>
            .hit-file { font-weight: bold; }
            .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; border-color: #fbbf24 !important; }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
            
            /* モダンチャットUI用 */
            .chat-results-container { scroll-behavior: smooth; }
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
            
            /* Gap Analysis カードスタイル (old_src から復元) */
            .gap-card { 
                border-left: 4px solid #f87171 !important; 
                background: #fef2f2 !important; 
                padding: 12px !important; 
                border-radius: 8px !important; 
                margin-top: 8px !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
            }
            .gap-file { font-size: 0.75rem !important; font-weight: bold !important; color: #b91c1c !important; margin-bottom: 4px !important; }
            .gap-issue { font-size: 0.85rem !important; color: #450a0a !important; line-height: 1.5 !important; }
            
            /* JSONデータカード用スタイル */
            .json-card-container { margin-top: 8px; width: 100%; }
            .json-card { border-radius: 8px; background: #f8fafc; border: 1px solid #e2e8f0; overflow: hidden; }
            .json-card-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f1f5f9; border-bottom: 1px solid #e2e8f0; cursor: pointer; }
            .json-card-key { font-size: 10px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
            .json-card-toggle { font-size: 10px; color: #94a3b8; }
            .json-card-value { margin: 0; padding: 12px; font-family: "JetBrains Mono", monospace; font-size: 12px; overflow-x: auto; max-height: 300px; }

            /* textarea入力欄の文字色を確実に適用（ダークテーマ用） */
            textarea, .q-field__native, .q-field__input {
                color: #ffffff !important;
            }
            textarea::placeholder, .q-field__native::placeholder {
                color: #94a3b8 !important;
            }
        </style>
    ''')
