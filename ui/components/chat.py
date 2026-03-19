import json
from nicegui import ui

def render_gap_results(chat_results, full_text, open_preview_func, target_dir):
    """
    AIが生成した回答に <gaps> タグが含まれている場合、
    それをパースして不一致箇所の警告カード(Gap Card)として描画します。
    """
    if "<gaps>" not in full_text:
        return
    
    try:
        # タグ内のJSON文字列を抽出
        gap_json_str = full_text.split("<gaps>")[1].split("</gaps>")[0].strip()
        gaps = json.loads(gap_json_str)
        if gaps:
            with chat_results:
                ui.label('ANALYSIS RESULTS (GAPS)').classes('text-[10px] text-red-500 font-bold mt-2 tracking-widest')
                for gap in gaps:
                    f_path = gap.get("file", "Unknown")
                    l_num = gap.get("line")
                    issue = gap.get("issue", "Unknown")
                    
                    # 個別の警告カード
                    with ui.element('div').classes('gap-card w-full'):
                        with ui.row().classes('items-center justify-between w-full'):
                            ui.label(f"FILE: {f_path} (Line {l_num})" if l_num else f"FILE: {f_path}").classes('gap-file')
                            with ui.row().classes('gap-1'):
                                # 修正案がある場合のボタン
                                fix_code = gap.get("corrected_code")
                                if fix_code:
                                    ui.button(icon='content_copy', on_click=lambda e, fc=fix_code: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(fc)})'))\
                                        .props('flat dense size=xs color=slate-400').classes('text-[9px]')
                                    ui.button('FIX', icon='auto_fix_high', on_click=lambda e, fp=f_path, ln=l_num, fc=fix_code: open_preview_func(fp, target_dir, ln, fc))\
                                        .props('flat dense size=xs color=green-7').classes('text-[9px]')
                                # プレビューアで該当行へジャンプするためのボタン
                                if f_path != "Unknown":
                                    ui.button('JUMP', icon='launch', on_click=lambda e, fp=f_path, ln=l_num: open_preview_func(fp, target_dir, ln))\
                                        .props('flat dense size=xs color=red-7').classes('text-[9px]')
                        ui.label(issue).classes('gap-issue')
    except Exception as e:
        print(f"Gap Parse Error: {e}")

def render_message(container, role, content, sources=None, open_preview_func=None, target_dir=None, doc_dir=None):
    """
    チャットメッセージ（ユーザーまたはAI）を描画します。
    AIの回答には、引用されたソースファイルへのリンクボタンも表示します。
    """
    with container:
        if role == 'user':
            # ユーザー質問
            ui.label(f"Q: {content}").classes('text-indigo-600 font-bold text-sm bg-indigo-50 p-2 w-full border-l-4 border-indigo-600')
        else:
            # AI回答（<gaps>タグは除外してメインテキストのみ表示）
            display_text = content.split("<gaps>")[0] if "<gaps>" in content else content
            ui.markdown(display_text).classes('text-slate-700 text-sm p-4 w-full border-b')
            
            # Gap分析の結果があれば描画
            render_gap_results(container, content, open_preview_func, target_dir)
            
            # クリップボードへのコピー機能
            ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=content: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
            
            # 参考文献ボタンのリスト
            if sources:
                with ui.row().classes('gap-2 mt-1'):
                    for p, t in sources:
                        b_dir = target_dir if t == 'code' else doc_dir
                        ui.button(p, on_click=lambda e, path=p, bd=b_dir: open_preview_func(path, bd)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')
