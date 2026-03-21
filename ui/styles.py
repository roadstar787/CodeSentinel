APP_CSS = '''
    <style>
        .jetbrains-mono { font-family: 'JetBrains Mono', monospace !important; }
        .hit-file { font-weight: bold; }
        .rebuild-active { animation: pulse 1.5s infinite; color: #fbbf24 !important; border-color: #fbbf24 !important; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        
        /* Status Screen */
        .status-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; width: 100%; border-bottom: 1px solid #2d3748; padding-bottom: 4px; }
        .status-label { font-size: 10px; color: #94a3b8; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; }
        .status-value { font-size: 11px; color: #f1f5f9; font-family: "JetBrains Mono", monospace; font-weight: 500; }
        
        /* Gap Analysis Cards */
        .gap-card { 
            border-left: 4px solid #f87171; background: #fef2f2; padding: 12px; border-radius: 8px; margin-top: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .gap-file { font-size: 0.75rem; font-weight: bold; color: #b91c1c; margin-bottom: 4px; }
        .gap-issue { font-size: 0.85rem; color: #450a0a; line-height: 1.5; }

        /* Mermaid Diagrams */
        .mermaid { 
            background: white; 
            padding: 16px; 
            border-radius: 8px; 
            border: 1px solid #e2e8f0;
            margin-top: 12px;
            margin-bottom: 12px;
            display: flex;
            justify-content: center;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad:true});</script>
'''
