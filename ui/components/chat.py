import json
from nicegui import ui

def parse_gap_content(content):
    """
    AIの回答から<gaps>タグ内の内容を抽出し、正規表現を用いてJSON部分を特定・解析します。
    トークン切れ等で不完全なJSONの場合も、可能な限り自動修復を試みます。
    """
    import re
    if "<gaps>" not in content:
        return []

    # 閉じタグがない場合（トークン切れで途切れた場合）も考慮
    parts = content.split("<gaps>")
    raw_content = parts[-1].split("</gaps>")[0].strip()
    if not raw_content:
        return []
    
    # JSON部分の開始位置を特定
    json_start = re.search(r'[\[\{]', raw_content)
    if not json_start:
        return []
    json_str = raw_content[json_start.start():].strip()
    
    # トークン切れ等でJSONが不完全な場合、閉じ括弧を順次補完してパースを試みる
    def try_repair_and_load(s):
        s = s.strip()
        # 閉じ括弧の不足を補完（単純なカウンターではなく、試行錯誤的に追加）
        attempts = [s]
        base = s
        for _ in range(10): # 最大10回試行
            try:
                return json.loads(base)
            except Exception:
                # 最後に開いた括弧を閉じる（スタックを厳密に管理する代わりに、両方を試す）
                # 辞書の閉じ忘れが多いと仮定して } を優先
                if base.count('{') > base.count('}'):
                    base += '}'
                elif base.count('[') > base.count(']'):
                    base += ']'
                else:
                    break
        return json.loads(s) # 最後は元ので投げる（例外をキャッチするため）

    try:
        gaps_data = try_repair_and_load(json_str)
    except:
        # 読み込みに失敗した場合は、最後の方の不完全な要素を削ってみる
        idx = max(json_str.rfind('}'), json_str.rfind(']'))
        if idx > 0:
            try:
                gaps_data = try_repair_and_load(json_str[:idx+1])
            except:
                return []
        else:
            return []

    # データの正規化
    if isinstance(gaps_data, dict) and "gaps" in gaps_data:
        gaps_data = gaps_data["gaps"]
    if not isinstance(gaps_data, list):
        gaps_data = [gaps_data]
    
    return gaps_data

def render_gap_results(container, content, open_preview_func, target_dir, sources=None):
    """AIの回答から乖離項目を表示します。"""
    from pathlib import Path
    try:
        gaps_data = parse_gap_content(content)
        if not gaps_data:
            return

        with container:
            ui.label('ANALYSIS RESULTS (GAPS)').classes('text-[10px] text-red-500 font-bold mt-2 tracking-widest')
            for gap in gaps_data:
                f_path = gap.get("file", "Unknown")
                l_num = gap.get("line")
                issue = gap.get("issue", "Unknown")
                
                # パス解決の試行
                resolved_path = f_path
                # f_path がそのままでは存在しない場合、sources からマッチするものを探す
                if sources and not (Path(target_dir) / f_path).exists():
                    for s_path, s_type in sources:
                        if Path(s_path).name == Path(f_path).name:
                            resolved_path = s_path
                            break
                
                # 個別の警告カード
                with ui.element('div').classes('gap-card w-full'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f"FILE: {resolved_path} (Line {l_num})" if l_num else f"FILE: {resolved_path}").classes('gap-file')
                        with ui.row().classes('gap-1'):
                            fix_code = gap.get("corrected_code")
                            if fix_code:
                                ui.button(icon='content_copy', on_click=lambda e, fc=fix_code: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(fc)})'))\
                                    .props('flat dense size=xs color=slate-400').classes('text-[9px]')
                                ui.button('FIX', icon='auto_fix_high', on_click=lambda e, fp=resolved_path, ln=l_num, fc=fix_code: open_preview_func(fp, target_dir, ln, fc))\
                                    .props('flat dense size=xs color=green-7').classes('text-[9px]')
                            if resolved_path != "Unknown":
                                ui.button('JUMP', icon='launch', on_click=lambda e, fp=resolved_path, ln=l_num: open_preview_func(fp, target_dir, ln))\
                                    .props('flat dense size=xs color=red-7').classes('text-[9px]')
                    ui.label(issue).classes('gap-issue')
    except Exception as e:
        print(f"Gap Render Error: {e}")

def render_message(container, role, content, sources=None, open_preview_func=None, target_dir=None, doc_dir=None):
    """
    チャットメッセージ（ユーザーまたはAI）を描画します。
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
            render_gap_results(container, content, open_preview_func, target_dir, sources=sources)
            
            # クリップボードへのコピー機能
            ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=content: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
            
            # 参考文献ボタンのリスト
            if sources:
                with ui.row().classes('gap-2 mt-1'):
                    for p, t in sources:
                        b_dir = target_dir if t == 'code' else doc_dir
                        ui.button(p, on_click=lambda e, path=p, bd=b_dir: open_preview_func(path, bd)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')
