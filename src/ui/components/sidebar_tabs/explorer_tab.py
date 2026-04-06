"""エクスプローラータブUIコンポーネント"""

from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set

from nicegui import ui


def create_explorer_tab(
    backend: Any,
    state: Dict[str, Any],
    preview_open: Optional[Callable] = None,
) -> ui.column:
    # ツリー表示用コンテナ
    tree_container = ui.column().classes('w-full gap-0')

    @ui.refreshable
    def render_explorer():
        _refresh_explorer(tree_container, backend, state, preview_open)

    render_explorer()

    # ヒット数や再構築状態を監視して再描画する
    last_hits_sum = [sum(state.get('hit_counts', {}).values())]
    last_rebuilding = [backend.stats.get('is_rebuilding', False) if backend else False]

    def check_explorer_state():
        current_hits_sum = sum(state.get('hit_counts', {}).values())
        current_rebuilding = backend.stats.get('is_rebuilding', False) if backend else False
        
        if current_hits_sum != last_hits_sum[0] or current_rebuilding != last_rebuilding[0]:
            last_hits_sum[0] = current_hits_sum
            last_rebuilding[0] = current_rebuilding
            render_explorer.refresh()
    
    ui.timer(1.0, check_explorer_state)

    return tree_container


def _refresh_explorer(
    tree_container: ui.column,
    backend: Any,
    state: Dict[str, Any],
    preview_open: Optional[Callable] = None,
) -> None:
    """エクスプローラーを更新."""
    if tree_container is None:
        return

    try:
        tree_container.clear()
    except RuntimeError:
        return
    except Exception:
        pass

    def _on_select(path: str, base_dir: str) -> None:
        if preview_open:
            preview_open(path, base_dir)

    try:
        CODE_EXTS: Set[str] = {".py", ".cs", ".cpp", ".h", ".hpp", ".json"}
        DOCS_EXTS: Set[str] = {".pdf", ".md", ".xlsx", ".pptx"}

        settings = backend.get_user_settings()
        target_dir = Path(settings.get('target_dir', ''))
        doc_dir_str = settings.get('doc_dir', '')

        # Code Directory
        if target_dir.exists():
            tree_data = [_build_nodes(target_dir, target_dir, state, CODE_EXTS)]
            if tree_data[0]["children"] or tree_data[0].get("id"):
                with tree_container:
                    ui.label('CODE').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    t = ui.tree(
                        nodes=tree_data,
                        label_key='label',
                        on_select=lambda e, base=str(target_dir): _on_select(e.value, base)
                    ).props('dark dense expand-all')
                    t.add_slot(
                        'default-header',
                        '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>'
                    )

        # Document Directory
        if doc_dir_str:
            doc_dir = Path(doc_dir_str)
            if doc_dir.exists():
                doc_tree_data = [_build_nodes(doc_dir, doc_dir, state, DOCS_EXTS)]
                if doc_tree_data[0]["children"] or doc_tree_data[0].get("id"):
                    with tree_container:
                        ui.label('DOCS').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                        t_doc = ui.tree(
                            nodes=doc_tree_data,
                            label_key='label',
                            on_select=lambda e, base=str(doc_dir): _on_select(e.value, base)
                        ).props('dark dense expand-all')
                        t_doc.add_slot(
                            'default-header',
                            '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>'
                        )
    except Exception as e:
        print(f"Explorer Refresh Error: {e}")


def _build_nodes(
    path: Path,
    relative_to: Path,
    state: Dict[str, Any],
    supported_exts: Set[str],
) -> dict:
    """ツリーノードを構築.

    Args:
        path: 現在のパス
        relative_to: ルートパス
        state: 状態（ヒットカウント含む）
        supported_exts: サポートする拡張子セット

    Returns:
        ツリーノード辞書

    """
    rel = str(path.relative_to(relative_to)) if path != relative_to else ""
    hits = state.get('hit_counts', Counter()).get(rel, 0)
    hit_label = f" • {hits}" if hits > 0 else ""
    bg_style = f"background: rgba(99, 102, 241, {min(hits * 0.15, 0.4)});" if hits > 0 else ""

    node: Dict[str, Any] = {
        "id": rel if path.is_file() else None,
        "label": path.name + hit_label,
        "class": "hit-file" if hits > 0 else "",
        "style": bg_style,
    }

    if path.is_dir():
        children = []
        try:
            for p in sorted(path.iterdir()):
                if p.name.startswith('.'):
                    continue
                if p.is_dir():
                    child_node = _build_nodes(p, relative_to, state, supported_exts)
                    if child_node["children"] or child_node.get("id"):
                        children.append(child_node)
                elif p.suffix.lower() in supported_exts:
                    children.append(_build_nodes(p, relative_to, state, supported_exts))
        except PermissionError:
            pass

        node["children"] = children
        node["icon"] = "folder"
    else:
        ext = path.suffix.lower()
        icon_map = {
            ".pdf": "picture_as_pdf",
            ".xlsx": "table_view",
            ".xls": "table_view",
            ".pptx": "present_to_all",
            ".md": "article",
        }
        node["icon"] = icon_map.get(ext, "description")

    return node