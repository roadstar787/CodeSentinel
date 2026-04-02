# CodeSentinel v2.0 - 実装TODOリスト

## 現在の状態

### ✅ 実装済み（スケルトンレベル）
| サービス | 関数名 | 状態 |
|---------|--------|------|
| DocumentProcessor | get_document_loader | ✅ 実装完了 |
| DocumentProcessor | split_documents | ✅ 実装済み |
| DocumentProcessor | process_file | ✅ 実装済み |
| DocumentProcessor | process_directory | ✅ 実装済み |
| DocumentProcessor | process_all_documents | ✅ 実装済み |
| DocumentService | 全メソッド | 🟡 スケルトンのみ |
| ChatService | 全メソッド | 🟡 スケルトンのみ |
| TodoService | 全メソッド | 🟡 スケルトンのみ |

---

## 未実装関数リスト（優先度順）

### 🔴 優先度1: 高（コア機能）

- [ ] **#1 DocumentService `rebuild_database()`** - FAISSベクトルストアの再構築
  - 参考: `old_src/rag/base.py`
- [ ] **#2 DocumentService `load_database()`** - FAISSベクトルストアのロード
  - 参考: `old_src/rag/base.py`
- [ ] **#3 DocumentService `get_retriever()`** - ドキュメントリトリーバーの取得
  - 参考: `old_src/rag/base.py`
- [ ] **#4 DocumentService `check_lm_studio()`** - LM Studio接続確認
  - 参考: `old_src/rag/base.py`
- [ ] **#5 ChatService `generate_response()`** - チャット応答生成（LLM連携）
  - 参考: `old_src/rag/chat_service.py`
- [ ] **#6 ChatService `process_search_results()`** - 検索結果の処理
  - 参考: `old_src/rag/chat_service.py`
- [ ] **#7 ChatService `format_context()`** - コンテキストフォーマット
  - 参考: `old_src/rag/chat_service.py`

### 🟡 優先度2: 中（データ永続化）

- [ ] **#8 ChatService `save_chat_history()`** - チャット履歴保存
  - 参考: `old_src/rag/chat_service.py`
- [ ] **#9 ChatService `load_chat_history()`** - チャット履歴ロード
  - 参考: `old_src/rag/chat_service.py`
- [ ] **#10 ChatService `delete_chat_history()`** - チャット履歴削除
  - 参考: `old_src/rag/chat_service.py`
- [ ] **#11 ChatService `list_chat_histories()`** - チャット履歴一覧
  - 参考: `old_src/rag/chat_service.py`
- [ ] **#12 TodoService `add_todo()`** - ToDo追加
  - 参考: `old_src/rag/todo_service.py`
- [ ] **#13 TodoService `update_todo()`** - ToDo更新
  - 参考: `old_src/rag/todo_service.py`
- [ ] **#14 TodoService `delete_todo()`** - ToDo削除
  - 参考: `old_src/rag/todo_service.py`
- [ ] **#15 TodoService `list_todos()`** - ToDo一覧取得
  - 参考: `old_src/rag/todo_service.py`

### 🟢 優先度3: 低（ユーティリティ）

- [ ] **#16 TodoService `toggle_todo_completion()`** - 完了状態切り替え
  - 参考: `old_src/rag/todo_service.py`
- [ ] **#17 TodoService `get_todo_statistics()`** - ToDo統計情報
  - 参考: `old_src/rag/todo_service.py`
- [ ] **#18 DocumentService `get_statistics()`** - 統計情報取得
  - 参考: `old_src/rag/base.py`
- [ ] **#19 DocumentService `update_statistics()`** - 統計情報更新
  - 参考: `old_src/rag/base.py`

---

## 必要なリポジトリ層（未実装）

- [ ] **FileStorageRepository** - ファイルI/O操作
  - 参考: `old_src/rag/repositories.py`
- [ ] **JsonRepository** - JSONデータ操作
  - 参考: `old_src/rag/repositories.py`
- [ ] **VectorStoreRepository** - FAISSベクトルストア
  - 参考: `old_src/rag/repositories.py`

---

## 実装計画（推奨順序）

### フェーズ1: 基盤構築（優先度1 - 高）
- [ ] Step 1: FileStorageRepository, JsonRepositoryの実装
- [ ] Step 2: VectorStoreRepositoryの実装
- [ ] Step 3: DocumentServiceの実装（rebuild_database, load_database等）
- [ ] Step 4: ChatServiceのgenerate_response実装（LLM連携）

### フェーズ2: データ永続化（優先度2 - 中）
- [ ] Step 5: ChatServiceのチャット履歴機能実装
- [ ] Step 6: TodoServiceのCRUD機能実装
- [ ] Step 7: テスト追加・修正

### フェーズ3: 仕上げ（優先度3 - 低）
- [ ] Step 8: ユーティリティ関数の実装
- [ ] Step 9: 統合テスト
- [ ] Step 10: mypy + pytestの最終確認

---

## 注意事項

1. **old_src/との統合は禁止** - 既存コードは参考資料としてのみ使用
2. **テストファースト** - テストコードを先に書き、その後実装
3. **mypyチェック** - 実装後は必ず`mypy`で型検査
4. **pytest** - テストが全てパスすることを確認