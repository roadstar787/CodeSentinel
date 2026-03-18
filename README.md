# CodeSentinel (v0.4.0)

## 概要
CodeSentinel は、Retrieval-Augmented Generation (RAG) を活用した、エンジニアのための高度なコード分析・質問応答システムです。
ローカルのコードベースと仕様書（PDF, Markdown, Excel 等）を横断的に検索し、実装と仕様の乖離を特定する「ギャップ分析」や、詳細なコードプレビュー機能を提供します。
オフライン環境（LM Studio 互換サーバー）での動作を前提としており、機密性の高いプロジェクトでも安心して利用できます。

## 主な機能

### 1. ギャップ分析 (Gap Analysis) ✨ New in v0.4.0
- **仕様と実装の比較**: 仕様書（DOCS）とソースコード（CODE）の内容を比較し、矛盾点や未実装項目を自動的に抽出します。
- **構造化された可視化**: 分析結果を視覚的な「ギャップカード」として表示し、問題の詳細を一目で確認できます。
- **ダイレクトジャンプ**: カード内のボタンから、指摘された具体的なファイルと行番号へ即座に移動できます。

### 2. 高度なコードプレビュー
- **2カラム表示**: 行番号とコードを分離して表示し、大規模ファイルでも高い視認性を維持します。
- **シンタックスハイライト**: 言語ごとの色付けにより、構造を直感的に把握できます。
- **ファイル内検索**: プレビュー内でワード検索が可能。ヒット件数の表示や、Enter キーによる巡回機能を搭載しています。

### 3. ハイブリッド RAG 検索
- **マルチドキュメント対応**: `.py`, `.cpp`, `.cs`, `.h`, `.json` などのコードだけでなく、`.pdf`, `.md`, `.xlsx`, `.pptx` などのドキュメントもインデックス対象です。
- **FAISS ベクトルストア**: 高速かつ精度の高いセマンティック検索を実現します。

### 4. システム監視と管理
- **リアルタイムステータス**: CPU/RAM 使用率、LM Studio 接続状態、ロード中のモデル名をリアルタイムに表示。
- **チャット履歴管理**: 過去の質問や分析結果を保存・再開できます。
- **インデックス再構築**: UI からワンクリックでベクトル DB の構築・更新が可能。

## インストール方法

1. **Python 環境の構築**
   ```bash
   pip install -r requirements.txt
   ```
   ※主な依存: `nicegui`, `langchain`, `faiss-cpu`, `psutil`, `httpx`, `unstructured` (ドキュメント解析用)

2. **LM Studio の準備**
   - [LM Studio](https://lmstudio.ai/) をインストール。
   - モデルをダウンロードし、Local Server を起動（デフォルト: Port 1234）。

## 使い方

1. **起動**
   ```bash
   python CodeSentinel.py
   ```
2. **初期設定**
   - ブラウザで `http://localhost:8080` にアクセス。
   - サイドバーの「SET」タブで、解析対象の「Code Path」と「Doc Path」を入力。
   - 「REBUILD」をクリックしてインデックスを構築します。
3. **分析**
   - 画面上部のトグルで「Q&A (Normal)」または「GAP (Gap Analysis)」を選択。
   - 質問を入力すると、関連するコード・仕様書に基づいた回答が生成されます。

## 技術スタック
- **UI**: NiceGUI (Python-based Web UI)
- **RAG**: LangChain, FAISS
- **Backend Content**: OpenAI Embeddings API (LM Studio Compatible)
- **Monitoring**: psutil

## ライセンス
MIT License
