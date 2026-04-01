"""
ドキュメントプロセッサーのテスト
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.services.document_processor import DocumentProcessor, ProcessedDocument
from src.config.settings import Settings


class TestDocumentProcessor:
    """DocumentProcessorクラスのテスト"""

    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリの作成"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def settings(self, temp_dir):
        """設定オブジェクトの作成"""
        settings = Settings()
        settings.paths.target_dir = str(temp_dir)
        settings.paths.doc_dir = str(temp_dir)
        return settings

    @pytest.fixture
    def processor(self, settings):
        """DocumentProcessorのインスタンス作成"""
        return DocumentProcessor(settings)

    @pytest.fixture
    def sample_text_file(self, temp_dir):
        """サンプルテキストファイルの作成"""
        file_path = temp_dir / "test.py"
        file_path.write_text("""
def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def method(self):
        pass
""")
        return file_path

    @pytest.fixture
    def sample_markdown_file(self, temp_dir):
        """サンプルMarkdownファイルの作成"""
        file_path = temp_dir / "test.md"
        file_path.write_text("# タイトル\n\nこれはテストです。\n\n## サブタイトル\n\n詳細説明。")
        return file_path

    def test_init(self, processor, settings):
        """初期化のテスト"""
        assert processor.config == settings
        assert processor.processed_documents == []
        assert processor.code_splitter is not None
        assert processor.doc_splitter is not None

    def test_get_document_loader_text(self, processor, temp_dir):
        """テキストファイルローダーの取得テスト"""
        file_path = temp_dir / "test.py"
        file_path.write_text("print('hello')")
        
        loader = processor.get_document_loader(file_path)
        assert loader is not None
        assert hasattr(loader, 'load')

    def test_get_document_loader_pdf(self, processor, temp_dir):
        """PDFファイルローダーの取得テスト"""
        file_path = temp_dir / "test.pdf"
        file_path.write_text("dummy pdf content")
        
        with patch('src.services.document_processor.PyPDFLoader') as mock_pdf_loader:
            processor.get_document_loader(file_path)
            mock_pdf_loader.assert_called_once_with(str(file_path))

    def test_get_document_loader_unsupported(self, processor, temp_dir):
        """非対応ファイル拡張子のテスト"""
        file_path = temp_dir / "test.xyz"
        
        with pytest.raises(ValueError, match="Unsupported file extension"):
            processor.get_document_loader(file_path)

    def test_split_documents_code(self, processor, temp_dir):
        """コードドキュメントの分割テスト"""
        from unittest.mock import Mock
        
        # モックドキュメントの作成
        mock_doc1 = Mock()
        mock_doc1.page_content = "def func1():\n    pass"
        mock_doc1.metadata = {"source": "test.py"}
        
        mock_doc2 = Mock()
        mock_doc2.page_content = "def func2():\n    pass"
        mock_doc2.metadata = {"source": "test.py"}
        
        # モックのsplit_documentsメソッドを設定
        processor.code_splitter.split_documents = Mock(return_value=[
            Mock(page_content="def func1():", metadata={"source": "test.py"}),
            Mock(page_content="    pass", metadata={"source": "test.py"}),
            Mock(page_content="def func2():", metadata={"source": "test.py"}),
            Mock(page_content="    pass", metadata={"source": "test.py"}),
        ])
        
        result = processor.split_documents([mock_doc1, mock_doc2], "code")
        
        # 各ドキュメントが分割されるので、元のドキュメント数 × 分割数になる
        assert len(result) == 8  # 2ドキュメント × 4チャンク
        assert all(isinstance(doc, ProcessedDocument) for doc in result)
        assert all(doc.metadata["type"] == "code" for doc in result)

    def test_split_documents_document(self, processor, temp_dir):
        """ドキュメントの分割テスト"""
        from unittest.mock import Mock
        
        # モックドキュメントの作成
        mock_doc = Mock()
        mock_doc.page_content = "これはテストドキュメントです。"
        mock_doc.metadata = {"source": "test.md"}
        
        # モックのsplit_documentsメソッドを設定
        processor.doc_splitter.split_documents = Mock(return_value=[
            Mock(page_content="これはテストドキュメントです。", metadata={"source": "test.md"}),
        ])
        
        result = processor.split_documents([mock_doc], "document")
        
        assert len(result) == 1
        assert isinstance(result[0], ProcessedDocument)
        # ドキュメントタイプはsplit_documents内で設定される
        assert result[0].metadata["type"] == "document"

    def test_process_file_text_utf8(self, processor, sample_text_file):
        """UTF-8テキストファイルの処理テスト"""
        result = processor.process_file(sample_text_file, sample_text_file.parent, "code")
        
        assert len(result) > 0
        assert all(isinstance(doc, ProcessedDocument) for doc in result)
        assert all(doc.metadata["source"] == "test.py" for doc in result)
        assert all(doc.metadata["type"] == "code" for doc in result)

    def test_process_file_text_cp932_fallback(self, processor, temp_dir):
        """CP932フォールバックのテスト"""
        file_path = temp_dir / "test.txt"
        # CP932でエンコードされた文字列
        test_text = "テスト文字列"
        file_path.write_text(test_text, encoding="cp932")
        
        with patch('src.services.document_processor.TextLoader') as mock_loader:
            # UTF-8で失敗し、CP932で成功するモック
            mock_instance = Mock()
            mock_instance.load.return_value = [
                Mock(page_content=test_text, metadata={})
            ]
            mock_loader.return_value = mock_instance
            
            # UTF-8で例外が発生するように設定
            with patch('builtins.open', side_effect=[UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"), None]):
                result = processor.process_file(file_path, temp_dir, "code")
                
                assert len(result) == 1
                assert result[0].content == test_text

    def test_process_file_unsupported_extension(self, processor, temp_dir):
        """非対応ファイル拡張子の処理テスト"""
        file_path = temp_dir / "test.xyz"
        file_path.write_text("test content")
        
        result = processor.process_file(file_path, temp_dir, "code")
        assert result == []

    def test_process_file_error_handling(self, processor, temp_dir):
        """ファイル処理エラーのハンドリングテスト"""
        # 存在しないファイル
        file_path = temp_dir / "nonexistent.py"
        
        result = processor.process_file(file_path, temp_dir, "code")
        assert result == []

    @pytest.mark.asyncio
    async def test_process_directory_empty(self, processor, temp_dir):
        """空ディレクトリの処理テスト"""
        result = await processor.process_directory(temp_dir, temp_dir, "code")
        assert result == []

    @pytest.mark.asyncio
    async def test_process_directory_with_files(self, processor, temp_dir):
        """ファイルを含むディレクトリの処理テスト"""
        # テストファイルの作成
        (temp_dir / "test1.py").write_text("def test1(): pass")
        (temp_dir / "test2.py").write_text("def test2(): pass")
        
        # モックでファイル処理をシミュレート
        processor.process_file = Mock(return_value=[
            ProcessedDocument("content1", {"source": "test1.py", "type": "code"})
        ])
        
        result = await processor.process_directory(temp_dir, temp_dir, "code")
        
        # process_fileが2回呼び出されることを確認
        assert processor.process_file.call_count == 2
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_process_directory_too_many_files(self, processor, temp_dir):
        """ファイル数が多すぎる場合のテスト"""
        # max_file_displayより多いファイルを作成
        processor.config.ui.max_file_display = 10
        for i in range(11):  # max_file_displayより多い
            (temp_dir / f"test{i}.py").write_text(f"def test{i}(): pass")
        
        # ファイル数チェックをテストするために、process_directoryを直接呼び出す
        with pytest.raises(ValueError, match="Too many files"):
            await processor.process_directory(temp_dir, temp_dir, "code")

    @pytest.mark.asyncio
    async def test_process_directory_file_error_handling(self, processor, temp_dir):
        """ファイル処理エラー時の継続処理テスト"""
        # テストファイルの作成
        (temp_dir / "good.py").write_text("def good(): pass")
        (temp_dir / "bad.py").write_text("bad content")
        
        # モックでエラーをシミュレート
        processor.process_file = Mock(side_effect=[
            [ProcessedDocument("good", {"source": "good.py", "type": "code"})],
            Exception("Processing error"),
            [ProcessedDocument("good2", {"source": "good2.py", "type": "code"})]
        ])
        
        # 3つのファイルを作成
        (temp_dir / "good2.py").write_text("def good2(): pass")
        
        result = await processor.process_directory(temp_dir, temp_dir, "code")
        
        # エラーが発生しても処理は継続される
        assert len(result) == 2  # goodとgood2のみ処理される

    @pytest.mark.asyncio
    async def test_process_all_documents_no_target(self, processor):
        """ターゲットディレクトリがない場合のテスト"""
        processor.config.paths.target_dir = None
        processor.config.paths.doc_dir = None
        
        success, message = await processor.process_all_documents()
        
        assert success is False
        assert message == "No documents found"

    @pytest.mark.asyncio
    async def test_process_all_documents_target_only(self, processor, temp_dir):
        """ターゲットディレクトリのみの場合のテスト"""
        processor.config.paths.target_dir = str(temp_dir)
        processor.config.paths.doc_dir = None
        
        # テストファイルの作成
        (temp_dir / "test.py").write_text("def test(): pass")
        
        # モックでディレクトリ処理をシミュレート
        processor.process_directory = AsyncMock(return_value=[
            ProcessedDocument("content", {"source": "test.py", "type": "code"})
        ])
        
        success, message = await processor.process_all_documents()
        
        assert success is True
        assert "Processed 1 documents" in message
        assert len(processor.processed_documents) == 1

    @pytest.mark.asyncio
    async def test_process_all_documents_both_dirs(self, processor, temp_dir):
        """両方のディレクトリがある場合のテスト"""
        # 2つの異なるディレクトリを作成
        target_dir = temp_dir / "target"
        doc_dir = temp_dir / "doc"
        target_dir.mkdir()
        doc_dir.mkdir()
        
        processor.config.paths.target_dir = str(target_dir)
        processor.config.paths.doc_dir = str(doc_dir)
        
        # テストファイルの作成
        (target_dir / "code.py").write_text("def code(): pass")
        (doc_dir / "doc.md").write_text("# ドキュメント")
        
        # モックでディレクトリ処理をシミュレート
        processor.process_directory = AsyncMock(side_effect=[
            [ProcessedDocument("code_content", {"source": "code.py", "type": "code"})],
            [ProcessedDocument("doc_content", {"source": "doc.md", "type": "document"})]
        ])
        
        success, message = await processor.process_all_documents()
        
        assert success is True
        assert "Processed 2 documents" in message
        assert len(processor.processed_documents) == 2

    @pytest.mark.asyncio
    async def test_process_all_documents_duplicate_dirs(self, processor, temp_dir):
        """重複ディレクトリのテスト"""
        processor.config.paths.target_dir = str(temp_dir)
        processor.config.paths.doc_dir = str(temp_dir)  # 同じディレクトリ
        
        # テストファイルの作成
        (temp_dir / "test.py").write_text("def test(): pass")
        
        # モックでディレクトリ処理をシミュレート
        processor.process_directory = AsyncMock(return_value=[
            ProcessedDocument("content", {"source": "test.py", "type": "code"})
        ])
        
        success, message = await processor.process_all_documents()
        
        assert success is True
        # ディレクトリが重複している場合、1回のみ処理される
        assert processor.process_directory.call_count == 1
        assert "Processed 1 documents" in message

    @pytest.mark.asyncio
    async def test_process_all_documents_too_many_chunks(self, processor, temp_dir):
        """チャンク数が多すぎる場合のテスト"""
        processor.config.paths.target_dir = str(temp_dir)
        processor.config.paths.doc_dir = None
        processor.config.ui.max_document_chunks = 1
        
        # 多数のチャンクを返すモック
        processor.process_directory = AsyncMock(return_value=[
            ProcessedDocument("content1", {"source": "test1.py", "type": "code"}),
            ProcessedDocument("content2", {"source": "test2.py", "type": "code"}),
        ])
        
        success, message = await processor.process_all_documents()
        
        assert success is False
        assert "Too many document chunks" in message

    def test_get_processed_documents(self, processor):
        """処理済みドキュメントの取得テスト"""
        # テストデータの追加
        processor.processed_documents = [
            ProcessedDocument("content1", {"source": "test1.py", "type": "code"}),
            ProcessedDocument("content2", {"source": "test2.py", "type": "code"}),
        ]
        
        result = processor.get_processed_documents()
        
        assert len(result) == 2
        assert result == processor.processed_documents

    def test_clear_processed_documents(self, processor):
        """処理済みドキュメントのクリアテスト"""
        # テストデータの追加
        processor.processed_documents = [
            ProcessedDocument("content1", {"source": "test1.py", "type": "code"}),
        ]
        
        processor.clear_processed_documents()
        
        assert processor.processed_documents == []

    @pytest.mark.asyncio
    async def test_heartbeat_maintenance(self, processor, temp_dir):
        """Heartbeat維持のテスト"""
        # 多数のファイルを作成
        for i in range(10):
            (temp_dir / f"test{i}.py").write_text(f"def test{i}(): pass")
        
        # process_fileが呼び出されることを確認
        call_count = 0
        def mock_process_file(*args):
            nonlocal call_count
            call_count += 1
            return [ProcessedDocument(f"content{call_count}", {"source": f"test{call_count}.py", "type": "code"})]
        
        processor.process_file = Mock(side_effect=mock_process_file)
        
        await processor.process_directory(temp_dir, temp_dir, "code")
        
        # 各ファイルごとにprocess_fileが呼び出される
        assert processor.process_file.call_count == 10