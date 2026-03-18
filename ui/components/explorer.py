from pathlib import Path
from nicegui import ui

class Explorer:
    """
    ファイルツリーを表示・管理するクラス。
    コードディレクトリとドキュメントディレクトリの内容を階層表示し、
    RAG検索でのヒット数に応じたハイライト機能を提供します。
    """
    def __init__(self, container, on_select):
        self.container = container
        self.on_select = on_select

    def refresh(self, code_dir, doc_dir, hit_counts):
        """ツリーの内容を最新の状態に更新します。"""
        self.container.clear()
        
        def build_nodes(path: Path, relative_to: Path):
            """再帰的にディレクトリを走査し、NiceGUIのtreeノード形式に変換します。"""
            rel = str(path.relative_to(relative_to)) if path != relative_to else ""
            hits = hit_counts.get(rel, 0)
            # ヒット数に応じたラベルとスタイルの生成
            hit_label = f" • {hits}" if hits > 0 else ""
            bg_style = f"background: rgba(99, 102, 241, {min(hits * 0.15, 0.4)});" if hits > 0 else ""
            
            node = {"id": rel if path.is_file() else None, "label": path.name + hit_label, "class": "hit-file" if hits > 0 else "", "style": bg_style}
            
            if path.is_dir():
                # サポート対象の拡張子のみ表示
                supported = {".py", ".cs", ".cpp", ".h", ".hpp", ".json", ".pdf", ".md", ".xlsx", ".pptx"}
                node["children"] = [build_nodes(p, relative_to) for p in sorted(path.iterdir())
                                    if not p.name.startswith('.') and (p.is_dir() or p.suffix.lower() in supported)]
                node["icon"] = "folder"
            else:
                ext = path.suffix.lower()
                # 拡張子に応じたアイコン設定
                icon_map = {".pdf": "picture_as_pdf", ".xlsx": "table_view", ".xls": "table_view", ".pptx": "present_to_all", ".md": "article"}
                node["icon"] = icon_map.get(ext, "description")
            return node

        try:
            with self.container:
                # コード用セクション
                if code_dir and Path(code_dir).exists():
                    root = Path(code_dir)
                    ui.label('CODE').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    ui.tree(nodes=[build_nodes(root, root)], label_key='label', on_select=lambda e: self.on_select(e.value, code_dir)).props('dark dense expand-all')\
                        .add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
                
                # ドキュメント用セクション
                if doc_dir and Path(doc_dir).exists():
                    root = Path(doc_dir)
                    ui.label('DOCS').classes('text-[9px] text-slate-500 mt-2 uppercase tracking-tighter')
                    ui.tree(nodes=[build_nodes(root, root)], label_key='label', on_select=lambda e: self.on_select(e.value, doc_dir)).props('dark dense expand-all')\
                        .add_slot('default-header', '<div :class="props.node.class" :style="props.node.style" style="border-radius: 4px; padding: 2px 6px;">{{ props.node.label }}</div>')
        except Exception as e:
            print(f"Explorer Refresh Error: {e}")
