"""
チャットサービスモジュール
チャット関連のビジネスロジックを管理します。
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from ..config import Settings


class ChatService:
    """チャットサービスを提供するクラス"""
    
    def __init__(self, config: Settings):
        """
        初期化
        
        Args:
            config: 設定オブジェクト
        """
        self.config = config
        self.chat_dir = config.paths.chat_dir
        
        # LLM初期化
        self.llm = ChatOpenAI(
            base_url=config.lm_studio.url,
            api_key=config.lm_studio.api_key,
            temperature=config.rag.temperature,
            streaming=True
        )
    
    def generate_chat_id(self) -> str:
        """
        チャットIDを生成
        
        Returns:
            チャットID
        """
        return str(uuid.uuid4())
    
    def create_prompt(self, query: str, context: str, mode: str = "Normal") -> ChatPromptTemplate:
        """
        プロンプトテンプレートを作成
        
        Args:
            query: ユーザークエリ
            context: コンテキスト
            mode: モード ('Normal' または 'Gap')
            
        Returns:
            プロンプトテンプレート
        """
        if mode == 'Gap':
            prompt = """あなたは優秀なソフトウェアエンジニア兼テクニカルドキュメントアナリストです。
提供されたコンテキストに基づいて、仕様書(document)とソースコード(code)を比較分析してください。

Q: {query}

【回答ガイドライン】
1. 仕様書(document)に記載されている内容と、実際のソースコード(code)を詳細に比較してください。
2. 仕様にあるが実装されていない項目、または仕様と実装が矛盾している箇所を特定してください。
3. 回答は日本語で、具体的なファイル名や仕様を引用して説明してください。

【重要：構造化データの出力】
回答の最後に、以下の形式で分析結果の要約を **必ず** 含めてください。
各項目は JSON 形式で `<gaps>` タグで囲んでください。
例:
<gaps>
[
  {{"file": "main.py", "line": 42, "issue": "仕様ではAとされていますが、実装はBになっています"}},
  {{"file": "utils.py", "line": 10, "issue": "仕様にある例外処理が実装されていません"}}
]
</gaps>

Context:
{context}
"""
        else:
            prompt = "回答は日本語で行ってください。\n\nContext:\n{context}\n\nQ: {query}"
        
        return ChatPromptTemplate.from_template(prompt)
    
    async def generate_response(
        self, 
        query: str, 
        context: str, 
        mode: str = "Normal"
    ) -> Dict[str, Any]:
        """
        チャット応答を生成
        
        Args:
            query: ユーザークエリ
            context: コンテキスト
            mode: モード
            
        Returns:
            応答情報
        """
        try:
            # プロンプトテンプレートの作成
            prompt_template = self.create_prompt(query, context, mode)
            
            # チェーンの構築
            chain = prompt_template | self.llm | StrOutputParser()
            
            # ストリーミング応答の生成
            full_response = ""
            async for chunk in chain.astream({"query": query, "context": context}):
                full_response += chunk
            
            # ギャップ解析（Gapモードの場合）
            gaps = []
            if mode == 'Gap' and "<gaps>" in full_response:
                try:
                    gap_json_str = full_response.split("<gaps>")[1].split("</gaps>")[0].strip()
                    gaps = json.loads(gap_json_str)
                except Exception as e:
                    print(f"Gap Parse Error: {e}")
            
            return {
                "content": full_response,
                "gaps": gaps,
                "success": True
            }
            
        except Exception as e:
            return {
                "content": f"Error: {str(e)}",
                "gaps": [],
                "success": False
            }
    
    def process_search_results(self, docs: List) -> List[tuple]:
        """
        検索結果を処理
        
        Args:
            docs: 検索結果ドキュメントリスト
            
        Returns:
            (ファイルパス, タイプ)のタプルリスト
        """
        hits = [d.metadata['source'] for d in docs]
        unique_hits = []
        seen = set()
        
        for d in docs:
            pair = (d.metadata['source'], d.metadata.get('type', 'code'))
            if pair not in seen:
                unique_hits.append(pair)
                seen.add(pair)
        
        return unique_hits
    
    def format_context(self, docs: List) -> str:
        """
        コンテキストをフォーマット
        
        Args:
            docs: 検索結果ドキュメントリスト
            
        Returns:
            フォーマットされたコンテキスト
        """
        return "\n".join([
            f"TYPE: {d.metadata.get('type', 'unknown')}\n"
            f"FILE: {d.metadata['source']}\n"
            f"{d.page_content}"
            for d in docs
        ])
    
    def save_chat_history(
        self, 
        chat_id: str, 
        messages: List[Dict[str, Any]], 
        title: Optional[str] = None
    ):
        """
        チャット履歴を保存
        
        Args:
            chat_id: チャットID
            messages: メッセージリスト
            title: タイトル
        """
        path = self.chat_dir / f"{chat_id}.json"
        
        # 既存データの読み込み
        existing_title = "New Chat"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    existing_title = old_data.get("title", existing_title)
            except Exception:
                pass
        
        data = {
            "title": title if title else existing_title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_chat_history(self, chat_id: str) -> Optional[Dict]:
        """
        チャット履歴をロード
        
        Args:
            chat_id: チャットID
            
        Returns:
            チャットデータ
        """
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def delete_chat_history(self, chat_id: str):
        """
        チャット履歴を削除
        
        Args:
            chat_id: チャットID
        """
        path = self.chat_dir / f"{chat_id}.json"
        if path.exists():
            path.unlink()
    
    def list_chat_histories(self) -> List[Dict[str, str]]:
        """
        保存されたチャット履歴の一覧を取得
        
        Returns:
            チャット履歴リスト
        """
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
            except Exception:
                continue
        return sorted(chats, key=lambda x: x["date"], reverse=True)