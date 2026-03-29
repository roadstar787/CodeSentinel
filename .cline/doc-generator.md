---
name: doc-generator
description: ソースコードから技術ドキュメントやREADME、CHANGELOGを生成・更新します。
---

# doc-generator

## Usage
- 新しいプロジェクトの初期READMEを作成するとき。
- Gitの差分から更新内容をまとめる（CHANGELOG）とき。
- コード内のDocstringやコメントを整理するとき。

## Steps
1. **構造解析**: クラス・関数の役割と引数を抽出し、Markdown形式で整理します。
2. **セットアップガイド**: 依存ライブラリや環境構築手順を `README.md` に自動反映します。
3. **視覚化**: Mermaid.js 等を用いて、クラス図やシーケンス図を作成します。
