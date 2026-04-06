"""ギャップ分析UIコンポーネント"""

from typing import Any, Dict, List, Optional, Callable

from nicegui import ui


def create_gap_card(gap_data: Dict[str, Any]) -> ui.card:
    """ギャップカードを作成する.

    Args:
        gap_data: ギャップデータ（file, line, issue, expected, actual）

    Returns:
        ギャップカードコンポーネント

    """
    with ui.card().classes('w-full gap-card bg-red-50 border-l-4 border-red-400 p-3') as card:
        with ui.row().classes('w-full items-center justify-between'):
            # ファイル名と行番号
            file_info = f"{gap_data.get('file', 'Unknown')}"
            line_num = gap_data.get('line', '')
            if line_num:
                file_info += f":{line_num}"
            
            ui.label(file_info).classes('text-[10px] font-bold text-red-600')
        
        # 問題の説明
        issue = gap_data.get('issue', 'No description')
        ui.label(issue).classes('text-xs text-red-800 leading-relaxed')
        
        # 期待値と実際の値
        with ui.row().classes('w-full gap-4'):
            expected = gap_data.get('expected', '')
            actual = gap_data.get('actual', '')
            
            if expected:
                with ui.column().classes('flex-1'):
                    ui.label('期待値').classes('text-[9px] text-slate-500 font-bold uppercase')
                    ui.label(expected).classes('text-[10px] text-green-700 bg-green-50 p-2 rounded')
            
            if actual:
                with ui.column().classes('flex-1'):
                    ui.label('現状').classes('text-[9px] text-slate-500 font-bold uppercase')
                    ui.label(actual).classes('text-[10px] text-orange-700 bg-orange-50 p-2 rounded')

        # コード比較
        current_code = gap_data.get('current_code', '')
        proposed_code = gap_data.get('proposed_code', '')

        if current_code:
            with ui.column().classes('w-full mt-2'):
                ui.label('現在のコード').classes('text-[9px] text-slate-500 font-bold uppercase opacity-60')
                ui.code(current_code).classes('text-[10px] w-full bg-slate-900 text-slate-300 p-2 rounded border border-slate-700 overflow-x-auto')

        if proposed_code:
            with ui.column().classes('w-full mt-2'):
                ui.label('改修提案のコード').classes('text-[9px] text-indigo-500 font-bold uppercase')
                ui.code(proposed_code).classes('text-[10px] w-full bg-slate-900 text-indigo-100 p-2 rounded border border-indigo-400/50 overflow-x-auto shadow-sm')
    
    return card


def render_gap_analysis(container: ui.column, gaps: List[Dict[str, Any]], on_navigate: Optional[Callable] = None) -> None:
    """ギャップ分析結果を表示する.

    Args:
        container: 表示先コンテナ
        gaps: ギャップデータのリスト
        on_navigate: ファイルへのナビゲーションコールバック

    """
    with container:
        if not gaps:
            ui.label('No gaps found.').classes('text-slate-400 text-sm italic p-4')
            return
        
        ui.label(f'Found {len(gaps)} gap(s)').classes('text-[10px] text-slate-500 font-bold uppercase mb-2')
        
        for i, gap in enumerate(gaps):
            with ui.column().classes('w-full gap-2'):
                create_gap_card(gap)
                
                # ナビゲーションボタン
                if on_navigate:
                    file_path = gap.get('file', '')
                    line_num = gap.get('line')
                    with ui.row().classes('w-full justify-end'):
                        ui.button(
                            'View File',
                            icon='open_in_new',
                            on_click=lambda f=file_path, l=line_num: on_navigate(f, l)
                        ).props('flat dense size=sm color=indigo-400')
