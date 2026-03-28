# イベントハンドラ
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from nicegui import ui, run
from rag.base import RAGBackend
from rag.chat_service import ChatService
from todo_service import TodoService


class EventHandlers:
    """イベントハンドラを管理するクラス"""
    
    def __init__(self, backend: RAGBackend, preview_open_func):
        self.backend = backend
        self.preview_open = preview_open_func
        self.chat_service = backend.chat_service
        self.todo_service = backend.todo_service
    
    # --- チャット関連イベントハンドラ ---
    
    async def handle_query(self, input_field, chat_results, state, refresh_explorer_func):
        """クエリ処理"""
        query = input_field.value.strip()
        if not query: return
        input_field.value = ''
        
        # 履歴に追加
        session = {'history': self.backend.get_chat_history()}
        session['history'].append({"role": "user", "content": query})

        with chat_results:
            ui.label(f"Q: {query}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
            md = ui.markdown('Thinking...').classes('text-slate-700 text-sm p-4 w-full border-b')
            source_row = ui.row().classes('gap-2 mt-1')

        try:
            retriever = self.backend.get_retriever()
            if not retriever:
                md.set_content("Database not loaded.")
                return
            docs = await run.io_bound(retriever.invoke, query)
            hits = [d.metadata['source'] for d in docs]
            state['hit_counts'] = hits
            refresh_explorer_func()
            
            unique_hits = self.chat_service.process_search_results(docs)
            
            with source_row:
                for p, t in unique_hits:
                    b_dir = self.backend.config.paths.get_target_dir() if t == 'code' else self.backend.config.paths.get_doc_dir()
                    self.preview_open(p, str(b_dir))
            
            context = self.chat_service.format_context(docs)
            llm_response = await self.chat_service.generate_response(query, context, self.backend.mode)
            
            full = llm_response['content']
            # Gap データの解析と可視化
            if self.backend.mode == 'Gap' and llm_response['gaps']:
                self._display_gap_analysis(llm_response['gaps'], chat_results)

            # コピーボタンを追加
            with chat_results:
                ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=full: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                    .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
            
            # 履歴に追加して保存
            session['history'].append({"role": "ai", "content": full, "sources": unique_hits})
            title = query[:20] + ("..." if len(query) > 20 else "")
            self.backend.save_chat(session['id'], session['history'], title if len(session['history']) <= 2 else None)
            
        except Exception as e:
            md.set_content(f"Error: {str(e)}")
    
    def _display_gap_analysis(self, gaps: List[Dict], chat_results):
        """ギャップ分析の結果を表示"""
        with chat_results:
            ui.label('ANALYSIS RESULTS (GAPS)').classes('text-[10px] text-red-500 font-bold mt-2 tracking-widest')
            for gap in gaps:
                f_path = gap.get("file", "Unknown")
                l_num = gap.get("line")
                issue = gap.get("issue", "Unknown")
                with ui.element('div').classes('gap-card w-full'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f"FILE: {f_path} (Line {l_num})" if l_num else f"FILE: {f_path}").classes('gap-file')
                        if f_path != "Unknown":
                            ui.button('JUMP', icon='launch', on_click=lambda e, fp=f_path, ln=l_num: self.preview_open(fp, self.backend.config.paths.get_target_dir(), ln))\
                                .props('flat dense size=xs color=red-7').classes('text-[9px]')
                    ui.label(issue).classes('gap-issue')
    
    # --- チャット履歴関連イベントハンドラ ---
    
    def refresh_chat_list(self, chat_list_container):
        """チャットリストを更新"""
        chat_list_container.clear()
        chats = self.backend.list_chats()
        with chat_list_container:
            if not chats:
                ui.label('No history').classes('text-[10px] text-slate-500 italic p-2')
            for c in chats:
                with ui.row().classes('w-full items-center gap-1 group'):
                    btn = ui.button(on_click=lambda e, cid=c['id']: self.load_chat_session(cid)).props('flat no-caps dense').classes('flex-grow text-left justify-start px-2 py-1 rounded hover:bg-slate-700/50')
                    with btn:
                        with ui.column().classes('gap-0'):
                            ui.label(c['title']).classes('text-xs text-slate-200 line-clamp-1')
                            ui.label(c['date']).classes('text-[9px] text-slate-500')
                    ui.button(icon='delete', on_click=lambda e, cid=c['id']: self.delete_chat_session(cid)).props('flat round dense size=sm color=red-4').classes('opacity-0 group-hover:opacity-100 transition-opacity')
    
    def load_chat_session(self, chat_id, chat_results):
        """チャットセッションをロード"""
        data = self.backend.load_chat(chat_id)
        if not data: return
        
        session = {'id': chat_id, 'history': data.get('messages', [])}
        
        chat_results.clear()
        with chat_results:
            for msg in session['history']:
                if msg['role'] == 'user':
                    ui.label(f"Q: {msg['content']}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
                else:
                    ui.markdown(msg['content']).classes('text-slate-700 text-sm p-4 w-full border-b')
                    ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=msg['content']: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                        .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
                    
                    if msg.get('sources'):
                        with ui.row().classes('gap-2 mt-1'):
                            for p, t in msg['sources']:
                                b_dir = self.backend.config.paths.get_target_dir() if t == 'code' else self.backend.config.paths.get_doc_dir()
                                self.preview_open(p, str(b_dir))
        ui.notify(f"Chat loaded: {data['title']}")
        self.refresh_chat_list(chat_list_container)
    
    def start_new_chat(self, chat_results, refresh_chat_list_func):
        """新しいチャットを開始"""
        new_id = str(uuid.uuid4())
        session = {'id': new_id, 'history': []}
        chat_results.clear()
        ui.notify("New chat started")
        refresh_chat_list_func()
    
    def delete_chat_session(self, chat_id):
        """チャットセッションを削除"""
        self.backend.delete_chat(chat_id)
        ui.notify("Chat deleted")
    
    # --- ToDo関連イベントハンドラ ---
    
    def refresh_todo_list(self, todo_list_container, todo_stats_container, sort_select, show_completed_toggle):
        """ToDoリストを更新"""
        todo_list_container.clear()
        todo_stats_container.clear()
        
        # ソートとフィルタリングオプションを取得
        sort_value = sort_select.value
        show_completed = show_completed_toggle.value
        
        # ソートオプションを解析
        try:
            sort_by, sort_order = sort_value.rsplit('_', 1)
        except Exception as e:
            print(f"Sort parsing error: {e}")
            sort_by = 'created_at'
            sort_order = 'desc'
        
        # ToDoリストを取得
        todos = self.todo_service.list_todos(
            show_completed=show_completed,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 統計情報を更新
        self._refresh_todo_stats(todo_stats_container)
        
        with todo_list_container:
            if not todos:
                ui.label('ToDoがありません').classes('text-[10px] text-slate-500 italic p-2')
            else:
                for todo in todos:
                    self._render_todo_item(todo, todo_list_container)
    
    def _refresh_todo_stats(self, todo_stats_container):
        """ToDo統計情報を更新"""
        stats = self.todo_service.get_todo_statistics()
        
        with todo_stats_container:
            with ui.column().classes('items-center p-3 bg-slate-700/50 rounded-lg'):
                ui.label(f'総数: {stats["total"]}').classes('text-xs font-bold text-slate-300')
                with ui.row().classes('gap-4 mt-1'):
                    ui.label(f'未完了: {stats["pending"]}').classes('text-xs text-amber-400')
                    ui.label(f'完了: {stats["completed"]}').classes('text-xs text-green-400')
            
            # 優先度分布
            with ui.column().classes('items-center p-3 bg-slate-700/50 rounded-lg'):
                ui.label('優先度分布').classes('text-xs font-bold text-slate-300 mb-1')
                with ui.row().classes('gap-2'):
                    high_color = 'text-red-400' if stats["priority_distribution"]["high"] > 0 else 'text-slate-600'
                    ui.label(f'高: {stats["priority_distribution"]["high"]}').classes(f'text-xs {high_color}')
                    medium_color = 'text-yellow-400' if stats["priority_distribution"]["medium"] > 0 else 'text-slate-600'
                    ui.label(f'中: {stats["priority_distribution"]["medium"]}').classes(f'text-xs {medium_color}')
                    low_color = 'text-blue-400' if stats["priority_distribution"]["low"] > 0 else 'text-slate-600'
                    ui.label(f'低: {stats["priority_distribution"]["low"]}').classes(f'text-xs {low_color}')
    
    def _render_todo_item(self, todo: Dict, todo_list_container):
        """ToDoアイテムを表示"""
        # 優先度に応じた色を設定
        priority_colors = {
            'high': 'border-red-500 bg-red-500/10',
            'medium': 'border-yellow-500 bg-yellow-500/10',
            'low': 'border-blue-500 bg-blue-500/10'
        }
        priority_color = priority_colors.get(todo.get('priority', 'medium'), 'border-slate-500')
        
        # 完了状態に応じたスタイル
        completed_style = 'opacity-50 line-through' if todo.get('completed', False) else ''
        
        with todo_list_container:
            with ui.card().classes(f'w-full p-3 border-l-4 {priority_color} {completed_style}'):
                with ui.row().classes('w-full items-start justify-between'):
                    # 左側：ToDo内容
                    with ui.column().classes('flex-grow gap-1'):
                        # タイトル
                        title = todo.get('title', '無題')
                        title_label = ui.label(title if title else '無題').classes('text-sm font-semibold text-slate-200')
                        
                        # 説明
                        if todo.get('description'):
                            desc = todo.get('description', '')
                            desc_label = ui.label(desc if desc else '').classes('text-xs text-slate-400 leading-relaxed')
                        
                        # メタ情報
                        with ui.row().classes('items-center gap-3 mt-1'):
                            # 優先度
                            priority_labels = {
                                'high': '高',
                                'medium': '中',
                                'low': '低'
                            }
                            priority_label = priority_labels.get(todo.get('priority', 'medium'), '中')
                            priority_colors_classes = {
                                'high': 'text-red-400',
                                'medium': 'text-yellow-400',
                                'low': 'text-blue-400'
                            }
                            priority_color_class = priority_colors_classes.get(todo.get('priority', 'medium'), 'text-slate-400')
                            ui.label(f'優先度: {priority_label}').classes(f'text-xs {priority_color_class}')
                            
                            # 作成日時
                            created = todo.get('created_at', '')
                            created_label = ui.label(created[:10] if created else '').classes('text-xs text-slate-500')
                            
                            # 期限
                            due_date = todo.get('due_date')
                            if due_date:
                                # 期限が切れているかチェック
                                today = datetime.now().strftime('%Y-%m-%d')
                                try:
                                    if due_date < today and not todo.get('completed', False):
                                        due_color = 'text-red-400'
                                    else:
                                        due_color = 'text-slate-400'
                                    ui.label(f'期限: {due_date}').classes(f'text-xs {due_color}')
                                except:
                                    ui.label(f'期限: {due_date}').classes('text-xs text-slate-400')
                    
                    # 右側：操作ボタン
                    with ui.row().classes('items-center gap-1'):
                        # 完了チェックボックス
                        completed = todo.get('completed', False)
                        checkbox = ui.checkbox(
                            value=completed,
                            on_change=lambda e, tid=todo['id']: self.toggle_todo_completion(tid)
                        ).props('dense color=green-5')
                        
                        # 編集ボタン
                        ui.button(
                            icon='edit',
                            on_click=lambda e, tid=todo['id']: self.show_edit_todo_dialog(tid)
                        ).props('flat dense mini color=slate-400 size=xs')
                        
                        # 削除ボタン
                        ui.button(
                            icon='delete',
                            on_click=lambda e, tid=todo['id']: self.delete_todo(tid)
                        ).props('flat dense mini color=red-400 size=xs')
    
    def toggle_todo_completion(self, todo_id):
        """ToDoの完了状態を切り替え"""
        updated = self.todo_service.toggle_todo_completion(todo_id)
        if updated:
            ui.notify('状態を更新しました', color='positive')
        else:
            ui.notify('更新に失敗しました', color='negative')
    
    def delete_todo(self, todo_id):
        """ToDoを削除"""
        if ui.confirm('このToDoを削除しますか？'):
            success = self.todo_service.delete_todo(todo_id)
            if success:
                ui.notify('ToDoを削除しました', color='positive')
            else:
                ui.notify('削除に失敗しました', color='negative')
    
    # --- 設定関連イベントハンドラ ---
    
    def save_settings(self, path_input, doc_path_input, refresh_explorer_func):
        """設定を保存"""
        user_settings = {
            'target_dir': path_input.value,
            'doc_dir': doc_path_input.value,
            'mode': self.backend.mode
        }
        app.storage.user['user_settings'] = user_settings
        self.backend.update_user_settings(user_settings)
        refresh_explorer_func()
        ui.notify('設定を保存しました', color='positive')
    
    def change_mode(self, mode_value):
        """モードを変更"""
        app.storage.user['mode'] = mode_value
        self.backend.mode = mode_value
        ui.notify(f"Mode changed to: {mode_value}")
    
    async def rebuild_task(self, rebuild_btn, idx_label, refresh_explorer_func):
        """再構築タスク"""
        if self.backend.stats["is_rebuilding"]: return
        
        # 通知の開始 (スピナー付き)
        n = ui.notification('Rebuilding Vector DB...', spinner=True, infinite=True, position='top-right')
        
        # ボタンをアニメーション状態に変更
        rebuild_btn.classes(add='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20')
        rebuild_btn.classes(remove='border-slate-800')
        rebuild_btn.set_text('BUILDING...')
        
        try:
            # バックグラウンドで再構築を実行
            success, msg = await self.backend.rebuild_db()
            
            # 通知の更新
            n.dismiss()
            if success:
                ui.notify('Rebuild successful!', color='positive', position='top-right', icon='check_circle')
            else:
                ui.notify(f'Rebuild failed: {msg}', color='negative', position='top-right', icon='error')
        except Exception as e:
            n.dismiss()
            ui.notify(f'System Error: {e}', color='negative', position='top-right')
        finally:
            # アニメーション状態を解除してテキストを元に戻す
            rebuild_btn.classes(remove='rebuild-active text-yellow-400 border-yellow-400 bg-yellow-900/20')
            rebuild_btn.classes(add='border-slate-800')
            rebuild_btn.set_text('REBUILD')
            
            idx_label.set_text(f'IDX: {self.backend.stats["total_chunks"]}')
            refresh_explorer_func()