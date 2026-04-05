# サイドバー機能修正計画

## 概要

old_src/CodeSentinel.py と src/ のUI実装を比較し、13項目の差異を特定しました。
本計画書に基づき、テストファーストで修正を実施します。

---

## 修正リスト（優先度順）

### Phase 1: クリティカル修正（機能しない部分）

#### 1. チャット履歴の表示・ロード機能
- **問題**: サイドバーのチャット一覧でクリックしてもチャットがロードできない
- **原因**: `create_sidebar()` が `session`/`chat_results` を受け取っていない
- **対象ファイル**: 
  - `src/ui/components/sidebar.py`
  - `src/ui/main_page.py`
- **テストファイル**: `src/tests/test_sidebar.py`（新規作成）

#### 2. ToDoリストの削除機能
- **問題**: ToDoアイテムの削除ボタンが機能しない
- **原因**: `_delete_todo()` で `import src.app` による循環インポートの危険性
- **対象ファイル**: `src/ui/components/todo_manager.py`
- **テストファイル**: `src/tests/test_todo_manager.py`（新規作成）

#### 3. 設定保存機能
- **問題**: 設定入力フィールドの値が正しく保存されない
- **原因**: `.on('blur')` イベントの不安定さ、selectのblur未対応
- **対象ファイル**: `src/ui/components/sidebar.py`
- **テストファイル**: 上記#1に統合

#### 4. ステータス更新機能
- **問題**: STSタブのステータスが更新されない
- **原因**: `setup_status_tab()` が定義されているが未呼び出し
- **対象ファイル**: `src/ui/main_page.py`
- **テストファイル**: `src/tests/test_status_updater.py`（既存）

#### 5. app.storage.user の未使用
- **問題**: チャットセッションや設定が永続化されない
- **原因**: `app.storage.user` を使用していない
- **対象ファイル**: `src/app.py`, `src/ui/main_page.py`
- **テストファイル**: `src/tests/test_app.py`（新規作成）

---

### Phase 2: 重要修正（UX改善）

#### 6. ファイルエクスプローラーのツリー表示
- **問題**: ファイル一覧がフラット表示でフォルダ展開不可
- **原因**: `ui.tree` を使用していない
- **対象ファイル**: `src/ui/components/file_explorer.py`
- **テストファイル**: `src/tests/test_file_explorer.py`（新規作成）

#### 7. フォルダ展開機能
- **問題**: フォルダをクリックしても展開しない
- **原因**: 同上（ui.tree で解決）
- **対象ファイル**: 同上

#### 8. ハンバーガーメニューボタン
- **問題**: サイドバーの開閉ボタンがない
- **原因**: `header.py` に未実装
- **対象ファイル**: `src/ui/components/header.py`
- **テストファイル**: `src/tests/test_header.py`（既存・更新必要）

#### 9. クエリ処理の非同期化
- **問題**: 検索が同期的に実行されUIがフリーズ
- **原因**: `asyncio.get_event_loop()` の誤った使用
- **対象ファイル**: `src/ui/components/chat_interface.py`
- **テストファイル**: `src/tests/test_chat_interface.py`（新規作成）

#### 10. ギャップ分析の統合
- **問題**: Gap モードで分析結果が表示されない
- **原因**: `chat_interface.py` から `gap_analysis.py` が呼ばれていない
- **対象ファイル**: `src/ui/components/chat_interface.py`
- **テストファイル**: 上記#9に統合

#### 11. フッター固定入力エリア
- **問題**: 入力エリアがスクロールしてしまう
- **原因**: `ui.footer()` を使用していない
- **対象ファイル**: `src/ui/components/chat_interface.py`, `src/ui/main_page.py`
- **テストファイル**: 上記#9に統合

---

## 実施順序

```
Phase 1:
  Step 1: チャット履歴の表示・ロード機能 (#1)
  Step 2: ToDoリストの削除機能 (#2)
  Step 3: 設定保存機能 (#3)
  Step 4: ステータス更新機能 (#4)
  Step 5: app.storage.user の統合 (#5)

Phase 2:
  Step 6: ファイルエクスプローラーのツリー表示 (#6, #7)
  Step 7: ハンバーガーメニューボタン (#8)
  Step 8: クエリ処理の非同期化 (#9)
  Step 9: ギャップ分析の統合 (#10)
  Step 10: フッター固定入力エリア (#11)
```

---

## テスト方針

各修正ごとに以下のサイクルで実施：

1. **テストコード作成** - 期待される動作をテストとして定義
2. **実装** - テストがパスするようにコードを修正
3. **mypy確認** - 型チェックを実行
4. **pytest実行** - 全テストがパスすることを確認

---

## 注意事項

- `old_src/` は参考資料のみ。直接統合は禁止
- 各修正後は既存テストが壊れていないか確認
- NiceGUI コンポーネントのテストはモックを活用

---

## 改修履歴

### 2026-04-05: サイドバーのリファクタリング

#### 実施内容
- `src/ui/components/sidebar.py`をシンプルにリファクタリング
- `create_sidebar()`内で`register_sidebar_elements()`を呼び出すように変更
- `main_page.py`からの二重呼び出しを削除
- `set_sidebar_tabs_enabled()`は`tab.set_enabled()`を使用

#### 変更ファイル
- `src/ui/components/sidebar.py`
- `src/ui/main_page.py`

#### テスト結果
- 全18テストがパス