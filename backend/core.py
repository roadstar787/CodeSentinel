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
APP_VERSION = "0.4.0"

class RAGBackend:
    def __init__(self):
        self.target_dir = r"E:\sample\json"
        self.doc_dir = r""
        self.db_path = "faiss_index_code"
        self.lm_studio_url = "http://localhost:1234/v1"
        self.mode = "Normal"
        self.chat_dir = Path("chat_history")
        self.chat_dir.mkdir(exist_ok=True)
        self.vectorstore = None
        self.embeddings = OpenAIEmbeddings(
            base_url=self.lm_studio_url,
            api_key="lm-studio",
            check_embedding_ctx_length=False
        )
        self.stats = {
            "total_chunks": 0, 
            "is_rebuilding": False, 
            "lm_connected": False, 
            "model": "N/A",
            "revision": "v0.4.0",
            "last_rebuild": "Never"
        }

    async def check_lm_studio(self):
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
        if os.path.exists(self.db_path):
            try:
                self.vectorstore = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
                if self.vectorstore:
                    self.stats["total_chunks"] = self.vectorstore.index.ntotal
                    return True
                return False
            except: 
                return False
        return False

    def list_chats(self):
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
            except: continue
        return sorted(chats, key=lambda x: x["date"], reverse=True)

    def load_chat(self, chat_id):
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save_chat(self, chat_id, messages, title=None):
        path = self.chat_dir / f"{chat_id}.json"
        existing_title = "New Chat"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_title = old_data.get("title", existing_title)
            except: pass
        
        data = {
            "title": title if title else existing_title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_chat(self, chat_id):
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()

    def get_retriever(self):
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs={"k": 10})
        return None
    
    def rebuild_db(self):
        self.stats["is_rebuilding"] = True
        docs = []
        
        code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, chunk_overlap=200,
            separators=["\nclass ", "\ndef ", "\nvoid ", "\nint ", "\nstatic ", "\n\n", "\n", " ", ""]
        )
        doc_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

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
                
                files = [p for p in base_path.rglob('*') if p.suffix.lower() in target["exts"] and ".venv" not in p.parts and ".git" not in p.parts]
                
                for p in files:
                    try:
                        ext = p.suffix.lower()
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
                            d.metadata["source"] = str(p.relative_to(base_path))
                            d.metadata["type"] = target["type"]
                        
                        splitter = code_splitter if target["type"] == "code" else doc_splitter
                        docs.extend(splitter.split_documents(raw))
                    except Exception as e:
                        print(f"Error loading {p}: {e}")
                        continue
            
            if not docs:
                return False, "No documents found"

            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            if self.vectorstore:
                self.vectorstore.save_local(self.db_path)
                self.stats["total_chunks"] = len(docs)
                self.stats["last_rebuild"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return True, "SUCCESS"
            return False, "Failed to create vector store"
        finally: 
            self.stats["is_rebuilding"] = False
