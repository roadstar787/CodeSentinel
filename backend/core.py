import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
import httpx
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    UnstructuredMarkdownLoader, 
    UnstructuredExcelLoader, 
    UnstructuredPowerPointLoader
)

# --- システム設定 ---
APP_NAME = "CodeSentinel"
APP_VERSION = "1.5.0"

class RAGBackend:
    """
    RAG(Retrieval-Augmented Generation)のバックエンド処理を管理するクラス。
    ベクターストアの構築、検索、チャット履歴の永続化などを担当します。
    """
    def __init__(self):
        # デフォルトのパス設定
        self.target_dir = r"E:\sample\json"
        self.doc_dir = r""
        self.db_path = "faiss_index_code"
        self.lm_studio_url = "http://localhost:1234/v1"
        self.mode = "Normal"
        
        # チャット履歴用ディレクトリの確保
        self.chat_dir = Path("chat_history")
        self.chat_dir.mkdir(exist_ok=True)
        
        self.vectorstore = None
        # LM Studio互換のエンドポイントを使用した埋め込みモデルの設定
        self.embeddings = OpenAIEmbeddings(
            base_url=self.lm_studio_url,
            api_key="lm-studio",
            check_embedding_ctx_length=False
        )
        # システム統計情報
        self.stats = {
            "total_chunks": 0, 
            "is_rebuilding": False, 
            "lm_connected": False, 
            "model": "N/A",
            "revision": f"v{APP_VERSION}",
            "last_rebuild": "Never"
        }

    async def check_lm_studio(self):
        """LM Studioのエンドポイントに接続可能か確認し、モデル情報を取得します。"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.lm_studio_url}/models", timeout=30.0)
                if resp.status_code == 200:
                    self.stats["lm_connected"] = True
                    data = resp.json()
                    if data.get('data'):
                        self.stats["model"] = data['data'][0]['id']
                    return True
        except Exception as e:
            print(f"Connection Error Detail: {e}")
        self.stats["lm_connected"] = False
        return False
    
    def load_db(self):
        """ローカルに保存されたFAISSインデックスを読み込みます。"""
        if os.path.exists(self.db_path):
            try:
                print(f"Loading DB from {self.db_path}...")
                self.vectorstore = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
                if self.vectorstore:
                    self.stats["total_chunks"] = self.vectorstore.index.ntotal
                    print(f"DB loaded: {self.stats['total_chunks']} chunks found.")
                    return True
                print("FAISS load_local returned None.")
                return False
            except Exception as e:
                print(f"Error loading FAISS index: {e}")
                return False
        print(f"DB path {self.db_path} does not exist.")
        return False

    def list_chats(self):
        """保存されているチャットセッションの一覧を取得します。"""
        chats = []
        for f in self.chat_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as j:
                    data = json.load(j)
                    chats.append({
                        "id": f.stem,
                        "title": data.get("title", "Untitled Chat"),
                        "date": data.get("date", "")
                    })
            except Exception as e: 
                print(f"Error reading chat file {f}: {e}")
                continue
        return sorted(chats, key=lambda x: x["date"], reverse=True)

    def load_chat(self, chat_id):
        """特定のチャット履歴をロードします。"""
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading chat {chat_id}: {e}")
        return None

    def save_chat(self, chat_id, messages, title=None):
        """チャット履歴をJSONファイルとして保存します。"""
        path = self.chat_dir / f"{chat_id}.json"
        existing_title = "New Chat"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_title = old_data.get("title", existing_title)
            except: pass
        
        try:
            data = {
                "title": title if title else existing_title,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messages": messages
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Chat saved: {path}")
        except Exception as e:
            print(f"Error saving chat {chat_id}: {e}")

    def delete_chat(self, chat_id):
        """チャット履歴ファイルを削除します。"""
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()

    def get_retriever(self):
        """LangChainのリトリーバーオブジェクトを返します。"""
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs={"k": 10})
        return None
    
    def rebuild_db(self):
        """
        指定されたディレクトリからファイルを読み込み、ベクターストアを再構築します。
        コード用とドキュメント用で異なるチャンク分割ルールを適用します。
        """
        self.stats["is_rebuilding"] = True
        docs = []
        
        # コード用のスプリッター
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]
        )
        # 一般ドキュメント用のスプリッター
        doc_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

        # 走査対象の設定
        targets = [
            {"path": self.target_dir, "type": "code", "exts": {".hpp", ".h", ".cpp", ".py", ".json", ".cs"}},
            {"path": self.doc_dir, "type": "document", "exts": {".pdf", ".md", ".xlsx", ".pptx"}}
        ]

        try:
            for target in targets:
                path_str = str(target["path"])
                if not path_str: continue
                base_path = Path(path_str)
                if not base_path.exists(): continue
                
                # 拡張子と除外パス（.venv, .git）を考慮してファイル収集
                files = [p for p in base_path.rglob('*') if p.suffix.lower() in target["exts"] and ".venv" not in p.parts and ".git" not in p.parts]
                
                for p in files:
                    try:
                        ext = p.suffix.lower()
                        # ファイル形式に応じたローダーの選択
                        if ext in {".py", ".cpp", ".h", ".hpp", ".cs", ".json"}:
                            loader = TextLoader(str(p), encoding="utf-8")
                        elif ext == ".pdf":
                            loader = PyPDFLoader(str(p))
                        elif ext == ".md":
                            loader = UnstructuredMarkdownLoader(str(p))
                        elif ext == ".xlsx":
                            loader = UnstructuredExcelLoader(str(p))
                        elif ext == ".pptx":
                            loader = UnstructuredPowerPointLoader(str(p))
                        else:
                            continue

                        raw = loader.load()
                        for d in raw:
                            # メタデータに相対パスと種別(code/doc)を付与
                            d.metadata["source"] = str(p.relative_to(base_path))
                            d.metadata["type"] = target["type"]
                        
                        splitter = code_splitter if target["type"] == "code" else doc_splitter
                        docs.extend(splitter.split_documents(raw))
                    except Exception as e:
                        print(f"Error loading {p}: {e}")
                        continue
            
            if not docs:
                return False, "No documents found"

            # ベクターストアの生成と保存
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            if self.vectorstore:
                self.vectorstore.save_local(self.db_path)
                self.stats["total_chunks"] = len(docs)
                self.stats["last_rebuild"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return True, "SUCCESS"
            return False, "Failed to create vector store"
        finally: 
            self.stats["is_rebuilding"] = False
