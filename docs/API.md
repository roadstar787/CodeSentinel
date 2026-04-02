# CodeSentinel v2.0 APIドキュメント

## 目次

- [CodeSentinel v2.0 APIドキュメント](#codesentinel-v20-apiドキュメント)
  - [目次](#目次)
  - [RAGBackend](#ragbackend)
    - [メソッド](#メソッド)
  - [DocumentService](#documentservice)
    - [メソッド](#メソッド-1)
  - [ChatService](#chatservice)
    - [メソッド](#メソッド-2)
  - [TodoService](#todoservice)
    - [メソッド](#メソッド-3)
  - [DocumentProcessor](#documentprocessor)
    - [メソッド](#メソッド-4)
  - [リポジトリ層](#リポジトリ層)
    - [FileStorageRepository](#filestoragerepository)
    - [JsonRepository](#jsonrepository)
    - [VectorStoreRepository](#vectorstorerepository)

---

## RAGBackend

アプリケーションの中心的なバックエンドクラス。すべてのサービスを統合管理します。

### メソッド

| メソッド | 説明 |
|---------|------|
| `get_user_settings() -> Dict[str, Any]` | ユーザー設定を取得 |
| `update_user_settings(settings: Dict[str, Any]) -> None` | ユーザー設定を更新 |
| `get_document_service() -> DocumentService` | ドキュメントサービスを取得 |
| `get_chat_service() -> ChatService` | チャットサービスを取得 |
| `get_todo_service() -> TodoService` | ToDoサービスを取得 |
| `get_retriever() -> Optional[BaseRetriever]` | ベクトルストアリトリーバーを取得 |
| `list_chats() -> List[Dict[str, Any]]` | チャット履歴一覧を取得 |
| `load_chat(chat_id: str) -> Optional[Dict[str, Any]]` | 指定したチャットを読み込み |
| `save_chat(chat_id: str, history: List[Dict], title: Optional[str] = None) -> None` | チャットを保存 |
| `delete_chat(chat_id: str) -> None` | チャットを削除 |
| `rebuild_db() -> Tuple[bool, str]` | データベースを再構築 |

---

## DocumentService

ドキュメントのインデックス管理と検索を担当します。

### メソッド

| メソッド | 説明 |
|---------|------|
| `load_database() -> bool` | ベクトルデータベースをロード |
| `get_retriever() -> Optional[BaseRetriever]` | リトリーバーを取得 |
| `check_lm_studio() -> bool` | LM Studioの接続を確認 |
| `get_statistics() -> Dict[str, Any]` | 統計情報を取得 |
| `update_statistics(stats: Dict[str, Any]) -> None` | 統計情報を更新 |
| `rebuild_database() -> Tuple[bool, str]` | データベースを再構築 |

---

## ChatService

チャット機能とLLMとの連携を担当します。

### メソッド

| メソッド | 説明 |
|---------|------|
| `generate_response(query: str, context: str, mode: str) -> Dict[str, Any]` | LLMに応答を生成させる |
| `process_search_results(docs: List[Document]) -> List[Tuple[str, str]]` | 検索結果を処理 |
| `format_context(docs: List[Document]) -> str` | コンテキストをフォーマット |
| `save_chat_history(chat_id: str, history: List[Dict]) -> None` | チャット履歴を保存 |
| `load_chat_history(chat_id: str) -> Optional[Dict]` | チャット履歴を読み込み |
| `delete_chat_history(chat_id: str) -> None` | チャット履歴を削除 |
| `list_chat_histories() -> List[Dict]` | チャット履歴一覧を取得 |
| `create_prompt(query: str, context: str) -> str` | プロンプトを作成 |
| `generate_chat_id() -> str` | チャットIDを生成 |

---

## TodoService

ToDo管理機能を担当します。

### メソッド

| メソッド | 説明 |
|---------|------|
| `add_todo(title: str, description: str = '', priority: str = 'medium', due_date: Optional[str] = None) -> bool` | ToDoを追加 |
| `update_todo(todo_id: str, **kwargs) -> bool` | ToDoを更新 |
| `delete_todo(todo_id: str) -> bool` | ToDoを削除 |
| `load_todo(todo_id: str) -> Optional[Dict]` | ToDoを読み込み |
| `list_todos(show_completed: bool = True, sort_by: str = 'created_at', sort_order: str = 'desc') -> List[Dict]` | ToDo一覧を取得 |
| `toggle_todo_completion(todo_id: str) -> bool` | 完了状態を切り替え |
| `get_todo_statistics() -> Dict[str, Any]` | 統計情報を取得 |
| `generate_todo_id() -> str` | ToDo IDを生成 |

---

## DocumentProcessor

ドキュメントの読み込みとチャンク分割を担当します。

### メソッド

| メソッド | 説明 |
|---------|------|
| `get_document_loader(file_path: Path) -> Optional[BaseLoader]` | ドキュメントローダーを取得 |
| `split_documents(documents: List[Document], file_type: str) -> List[Document]` | ドキュメントを分割 |
| `process_file(file_path: Path) -> List[Document]` | ファイルを処理 |
| `process_directory(directory: Path) -> List[Document]` | ディレクトリを処理 |
| `process_all_documents() -> List[Document]` | すべてのドキュメントを処理 |
| `get_processed_documents() -> List[Dict]` | 処理済みドキュメントを取得 |
| `clear_processed_documents() -> None` | 処理済みドキュメントをクリア |

---

## リポジトリ層

### FileStorageRepository

ファイルI/O操作を担当します。

| メソッド | 説明 |
|---------|------|
| `exists(path: Path) -> bool` | ファイルの存在を確認 |
| `read_text(path: Path, encoding: str = 'utf-8') -> str` | テキストを読み込み |
| `write_text(path: Path, content: str, encoding: str = 'utf-8') -> None` | テキストを書き込み |
| `delete(path: Path) -> bool` | ファイルを削除 |
| `list_files(directory: Path, pattern: str = '*') -> List[Path]` | ファイル一覧を取得 |
| `mkdir(path: Path, parents: bool = True, exist_ok: bool = True) -> None` | ディレクトリを作成 |

### JsonRepository

JSONデータの永続化を担当します。

| メソッド | 説明 |
|---------|------|
| `save(key: str, data: Any) -> None` | データを保存 |
| `load(key: str, default: Any = None) -> Any` | データを読み込み |
| `delete(key: str) -> bool` | データを削除 |
| `exists(key: str) -> bool` | データの存在を確認 |

### VectorStoreRepository

FAISSベクトルストアの管理を担当します。

| メソッド | 説明 |
|---------|------|
| `load_local(db_path: str, config: Settings) -> VectorStoreRepository` | ローカルからロード |
| `save_local(db_path: str) -> None` | ローカルに保存 |
| `as_retriever(**kwargs) -> Optional[BaseRetriever]` | リトリーバーを取得 |
| `index() -> Optional[faiss.Index]` | インデックスを取得 |
| `from_documents(documents: List[Document], config: Settings) -> VectorStoreRepository` | ドキュメントから作成 |