import json
import logging
from nicegui import ui

logger = logging.getLogger(__name__)

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
    json_start = re.search(r'[\w\W]', raw_content)
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
        logger.error(f"Gap Render Error: {e}")

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
            
            # メッセージをテキスト部分とMermaid部分に分割して描画
            import re
            # 閉じタグがない場合（ストリーミング中）も考慮
            # 改良版正規表現: 大文字小文字を区別せず、タグの後の任意の文字列を許容し、非最短一致で抽出
            parts = re.split(r'(```\s*mermaid[^\n]*\n[\s\S]*?(?:```|$))', display_text, flags=re.IGNORECASE)
            
            for part in parts:
                if part.startswith('```') and 'mermaid' in part.lower():
                    # Mermaidブロックを抽出（タグを除去）
                    # 最初の行を除去（大文字小文字不問）
                    code = re.sub(r'^```\s*mermaid[^\n]*\n', '', part, flags=re.IGNORECASE)
                    # 最後の ``` を除去
                    code = re.sub(r'```$', '', code).strip()
                    
                    # ストリーミング時: 閉じタグがない不完全なブロックをスキップ
                    if not part.rstrip().endswith('```'):
                        logger.debug(f"Skipping incomplete mermaid block (no closing tag)")
                        continue
                    
                    if code:
                        # デバッグ用: 抽出されたコードをコンソールに出力
                        logger.debug(f"Mermaid block detected: {code[:100]}...")
                        
                        # mermaidのsyntax制限に対応するため、<>を~にエスケープ
                        # 主にclassDiagramでGenericsを使用する場合に必要
                        escaped_code = code.replace('<', '~').replace('>', '~')
                        
                        # NiceGUIのmermaidコンポーネントを使用
                        with ui.card().classes('w-full items-center justify-center p-4 bg-white border border-slate-200 shadow-sm'):
                            try:
                                ui.mermaid(escaped_code)
                            except Exception as e:
                                error_msg = f"Mermaid Rendering Error: {str(e)}"
                                logger.error(error_msg)
                                ui.label(error_msg).classes('text-red-500 text-sm p-2')
                                ui.label("Check browser console for details").classes('text-gray-400 text-xs p-1')
                                # エラー時はコードを表示
                                ui.code(code).classes('w-full mt-2 text-xs')
                            else:
                                # 成功時も控えめにコードの一部を表示
                                ui.label("Mermaid Diagram").classes('text-[8px] text-slate-300 pointer-events-none mt-2')
                                ui.label(code[:50] + "..." if len(code) > 50 else code).classes('text-[8px] text-slate-400')
                else:
                    # 通常のテキスト部分
                    clean_part = part.strip()
                    if clean_part:
                        ui.markdown(clean_part).classes('text-slate-700 text-sm p-4 w-full border-b')
            
            # Gap分析の結果があれば描画
            render_gap_results(container, content, open_preview_func, target_dir, sources=sources)
            
            # クリップボードへのコピー機能
            ui.button('COPY MARKDOWN', icon='content_copy', on_click=lambda f=content: ui.run_javascript(f'navigator.clipboard.writeText({json.dumps(f)})')) \
                .props('flat dense color=slate-400 size=sm').classes('self-end mt-[-10px] mb-4 opacity-50 hover:opacity-100')
            
            # 参考文献ボタンのリスト
            if sources and open_preview_func:
                with ui.row().classes('gap-2 mt-1'):
                    for p, t in sources:
                        b_dir = target_dir if t == 'code' else doc_dir
                        ui.button(p, on_click=lambda e, path=p, bd=b_dir: open_preview_func(path, bd)).props('outline dense size=xs').classes('text-[10px] text-indigo-500 border-indigo-200 bg-indigo-50')