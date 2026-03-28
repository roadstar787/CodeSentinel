# 必要なライブラリをインポートします。
import asyncio
import psutil
from nicegui import ui, run, app
from rag.base import RAGBackend
from ui.main_page import main_page
from ui.components.sidebar import create_sidebar
from ui.components.header import create_header
from ui.components.preview_dialog import create_preview_dialog
from ui.handlers.event_handlers import EventHandlers
from config import settings

# --- システム設定 ---
# アプリケーションの名前
APP_NAME = "CodeSentinel"
# アプリケーションのバージョン
APP_VERSION = "0.4.0"

# RAGバックエンドの初期化
backend = RAGBackend()

# メインページを定義します。NiceGUIのルート ('/') に関連付けられます。
@ui.page('/')
async def main_page_handler():
    # メインページの初期化
    session, state = await main_page(backend)
    
    # カスタムCSSスタイルをページのheadに追加します。
    ui.add_head_html('''
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
    ''')

    # プレビューダイアログの作成
    preview_dialog, preview_open = create_preview_dialog()

    # イベントハンドラの作成
    event_handlers = EventHandlers(backend, preview_open)

    # --- サイドバーの作成 ---
    drawer, tabs = create_sidebar(backend, lambda: None)

    # --- ヘッダーの作成 ---
    mode_toggle = create_header(APP_NAME, APP_VERSION, lambda v: event_handlers.change_mode(v))

    # チャット結果表示エリア
    chat_results = ui.column().classes('w-full max-w-4xl mx-auto p-8 pb-40 gap-4')

    # --- UIコンポーネントの参照 ---
    # サイドバーのタブコンテナを取得
    tree_container = None
    chat_list_container = None
    todo_stats_container = None
    todo_list_container = None
    path_input = None
    doc_path_input = None
    sort_select = None
    show_completed_toggle = None
    refresh_todo_btn = None
    rebuild_btn = None
    
    # 状態表示用ラベル
    cpu_label = None
    ram_label = None
    lm_status_chip = None
    lm_model_label = None
    status_chip = None
    chunk_count_label = None
    last_update_label = None
    idx_label = None

    # --- ヘルパー関数 ---
    def refresh_explorer():
        """エクスプローラーを更新"""
        nonlocal tree_container
        if tree_container is None:
            return
            
        tree_container.clear()
        from collections import Counter
        state['hit_counts'] = getattr(state, 'hit_counts', Counter())
        
        def build_nodes(path, relative_to):
            rel = str(path.relative_to(relative_to)) if path != relative_to else ""
            hits = state['hit_counts'].get(rel, 0)
            hit_label = f" • {hits}" if hits > 0 else ""
            bg_style = f"background: rgba(99, 102, 241, {min(hits * 0.15, 0.4)});" if hits > 0 else ""
            
            node = {"id": rel if path.is_file() else None, "label": path.name + hit_label, "class": "hit-file" if hits > 0 else "", "style": bg_style}
            if path.is_dir():
                # 表示対象の拡張子
                supported = {".py", ".cs", ".cpp", ".h", ".hpp", ".json", ".pdf", ".md", ".xlsx", ".pptx"}
                node["children"] = [build_nodes(p, relative_to) for p in sorted(path.iterdir())
                                    if not p.name.startswith('.') and (p.is_dir() or p.suffix.lower() in supported)]
                node["icon"] = "folder"
            else:
                ext = path.suffix.lower()
                if ext == ".pdf": node["icon"] = "picture_as_pdf"
                elif ext in {".xlsx", ".xls"}: node["icon"] = "table_view"
                elif ext == ".pptx": node["icon"] = "present_to_all"
                elif ext == ".md": node["icon"] = "article"
                else: node["icon"] = "description"
            return node
        
        try:
            # Code Directory
            from pathlib import Path
            target_dir = backend.config.paths.get_target_dir()
            if target_dir.exists():
                tree_data = [build_nodes(target_dir, target_dir)]
                with tree_container:
                    ui.label('CODE').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    t = ui.tree(nodes=tree_data, label_key='label', on_select=lambda e: preview_open(e.value, str(target_dir))).props('dark dense expand-all')
                    t.add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
            
            # Document Directory
            doc_dir = backend.config.paths.get_doc_dir()
            if doc_dir.exists():
                doc_tree_data = [build_nodes(doc_dir, doc_dir)]
                with tree_container:
                    ui.label('DOCS').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    t_doc = ui.tree(nodes=doc_tree_data, label_key='label', on_select=lambda e: preview_open(e.value, str(doc_dir))).props('dark dense expand-all')
                    t_doc.add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
        except Exception as e:
            print(f"Explorer Refresh Error: {e}")

    async def update_status_loop():
        """ステータス更新ループ"""
        nonlocal cpu_label, ram_label, lm_status_chip, lm_model_label, status_chip, chunk_count_label, last_update_label
        
        while True:
            if cpu_label:
                cpu_label.set_text(f"{psutil.cpu_percent()}%")
            if ram_label:
                mem = psutil.virtual_memory()
                ram_label.set_text(f"{mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB")
            
            connected = await backend.check_lm_studio()
            if lm_status_chip:
                lm_status_chip.set_text('ONLINE' if connected else 'OFFLINE')
                lm_status_chip.classes(replace='bg-green-900/40 text-green-400' if connected else 'bg-red-900/40 text-red-400')
            if lm_model_label:
                lm_model_label.set_text(backend.stats["model"])
            
            # DB状態の更新
            is_loaded = backend.vector_store is not None
            if status_chip:
                status_chip.set_text('ONLINE' if is_loaded else 'OFFLINE')
                status_chip.classes(replace='bg-green-900/40 text-green-400' if is_loaded else 'bg-red-900/40 text-red-400')
            if chunk_count_label:
                chunk_count_label.set_text(str(backend.stats["total_chunks"]))
            if last_update_label:
                last_update_label.set_text(backend.stats["last_rebuild"])
            
            await asyncio.sleep(3)

    # --- イベントハンドラの登録 ---
    input_field = None
    def set_input_field(element):
        nonlocal input_field
        input_field = element

    # --- タブコンテンツの設定 ---
    with ui.tab_panels(tabs, value=tabs.children[0]):
        # エクスプローラータブ
        with ui.tab_panel(tabs.children[0]):
            ui.label('EXPLORER').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
            tree_container = ui.column().classes('w-full gap-0')

        # チャット履歴タブ
        with ui.tab_panel(tabs.children[1]):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('HISTORY').classes('text-[10px] text-slate-600 tracking-widest')
                ui.button(icon='add', on_click=lambda: event_handlers.start_new_chat(chat_results, lambda: refresh_chat_list())).props('flat round dense color=slate-400')
            chat_list_container = ui.column().classes('w-full gap-2')

        # ToDoリストタブ
        with ui.tab_panel(tabs.children[2]):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('TODOS').classes('text-[10px] text-slate-600 tracking-widest')
                ui.button(icon='add', on_click=lambda: ui.notify('ToDo追加機能は実装中')).props('flat round dense color=slate-400')
            
            todo_stats_container = ui.row().classes('w-full gap-4 mb-4')
            todo_list_container = ui.column().classes('w-full gap-2')
            
            with ui.row().classes('w-full items-center justify-between mb-2'):
                with ui.row().classes('gap-2'):
                    sort_select = ui.select(
                        options={
                            'created_at_desc': '作成日時 (新しい順)',
                            'created_at_asc': '作成日時 (古い順)',
                            'updated_at_desc': '更新日時 (新しい順)',
                            'updated_at_asc': '更新日時 (古い順)',
                            'priority_desc': '優先度 (高→低)',
                            'priority_asc': '優先度 (低→高)',
                            'due_date_asc': '期限 (近い順)',
                        },
                        value='created_at_desc',
                        label='ソート',
                    ).props('dense outlined mini').classes('text-xs')
                    sort_select.on('change', lambda e: event_handlers.refresh_todo_list(todo_list_container, todo_stats_container, sort_select, show_completed_toggle))
                
                show_completed_toggle = ui.toggle(
                    options={True: '完了済みを表示', False: '未完了のみ'},
                    value=True,
                ).props('dense mini').classes('text-xs')
                show_completed_toggle.on('change', lambda e: event_handlers.refresh_todo_list(todo_list_container, todo_stats_container, sort_select, show_completed_toggle))
            
            refresh_todo_btn = ui.button(icon='refresh', on_click=lambda: event_handlers.refresh_todo_list(todo_list_container, todo_stats_container, sort_select, show_completed_toggle)).props('flat dense mini color=slate-400')

        # 設定タブ
        with ui.tab_panel(tabs.children[3]):
            ui.label('CONFIG').classes('text-[10px] text-slate-600 mb-4 tracking-widest')
            path_input = ui.input('Code Path', value="").props('dark dense outlined').classes('w-full mb-2')
            doc_path_input = ui.input('Doc Path', value="").props('dark dense outlined').classes('w-full mb-4')
            ui.button('SAVE PATHS', on_click=lambda: event_handlers.save_settings(path_input, doc_path_input, refresh_explorer)).props('flat border').classes('w-full text-xs mb-4')
            rebuild_btn = ui.button('REBUILD', on_click=lambda: event_handlers.rebuild_task(rebuild_btn, idx_label, refresh_explorer)).props('flat icon=refresh').classes('w-full border border-slate-800 text-xs')

        # システムステータスタブ
        with ui.tab_panel(tabs.children[4]).classes('p-6'):
            ui.label('SYSTEM STATUS').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
            
            with ui.element('div').classes('status-item'):
                ui.label('Revision').classes('status-label')
                ui.label(backend.stats["revision"]).classes('status-value text-indigo-400')
            
            with ui.element('div').classes('status-item'):
                ui.label('Vector DB').classes('status-label')
                status_chip = ui.label('OFFLINE').classes('px-2 py-0.5 rounded text-[10px] font-bold')
            
            with ui.element('div').classes('status-item'):
                ui.label('Total Chunks').classes('status-label')
                chunk_count_label = ui.label(str(backend.stats["total_chunks"])).classes('status-value transition-all')
            
            with ui.element('div').classes('status-item'):
                ui.label('Last Build').classes('status-label')
                last_update_label = ui.label(backend.stats["last_rebuild"]).classes('status-value')

            ui.separator().classes('bg-slate-700 my-6 opacity-30')
            
            ui.label('SYSTEM LOAD').classes('text-[10px] font-bold text-indigo-400 mb-4 tracking-widest')
            
            with ui.element('div').classes('status-item'):
                ui.label('LM Studio').classes('status-label')
                lm_status_chip = ui.label('Checking...').classes('px-2 py-0.5 rounded text-[10px] font-bold')
            
            with ui.element('div').classes('status-item'):
                ui.label('Active Model').classes('status-label')
                lm_model_label = ui.label('N/A').classes('status-value truncate max-w-[120px]')

            with ui.element('div').classes('status-item'):
                ui.label('CPU').classes('status-label')
                cpu_label = ui.label('0%').classes('status-value')
            
            with ui.element('div').classes('status-item'):
                ui.label('RAM').classes('status-label')
                ram_label = ui.label('0GB').classes('status-value')

            with ui.element('div').classes('status-item'):
                ui.label('IDX').classes('status-label')
                idx_label = ui.label(f'{backend.stats["total_chunks"]}').classes('status-value')

    # --- ヘッダーのモード切り替えを設定 ---
    def change_mode_handler(value):
        mode_toggle.value = value
        event_handlers.change_mode(value)
    
    mode_toggle.on('change', change_mode_handler)

    # --- チャット履歴関連関数 ---
    def refresh_chat_list():
        """チャットリストを更新"""
        nonlocal chat_list_container
        if chat_list_container:
            event_handlers.refresh_chat_list(chat_list_container)

    def load_chat_session(chat_id):
        """チャットセッションをロード"""
        nonlocal chat_results
        event_handlers.load_chat_session(chat_id, chat_results)

    def start_new_chat():
        """新しいチャットを開始"""
        nonlocal chat_results
        event_handlers.start_new_chat(chat_results, refresh_chat_list)

    def delete_chat_session(chat_id):
        """チャットセッションを削除"""
        event_handlers.delete_chat_session(chat_id)

    # --- フッター ---
    with ui.footer().classes('bg-transparent'):
        with ui.row().classes('w-full max-w-4xl mx-auto p-4 bg-white border border-slate-300 items-end gap-2 shadow-lg rounded-t-xl'):
            input_field = ui.textarea(placeholder='Ask...').classes('flex-grow text-sm').props('borderless autogrow')
            set_input_field(input_field)  # イベントハンドラにinput_fieldを登録
            ui.button(on_click=lambda: event_handlers.handle_query(input_field, chat_results, state, refresh_explorer)).props('flat icon=send color=indigo-600')

    # 初期化
    backend.load_db()
    
    # 初期読込
    if session['history']:
        load_chat_session(session['id'])
    
    refresh_explorer()
    refresh_chat_list()
    asyncio.create_task(update_status_loop())

# アプリケーションを実行
ui.run(title=APP_NAME, storage_secret='sentinel_secret_key')