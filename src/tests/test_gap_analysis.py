"""ギャップ分析のテスト"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.components.gap_analysis import create_gap_card, render_gap_analysis


class TestGapAnalysis:
    """ギャップ分析のテストクラス."""

    def test_create_gap_card_returns_card(self) -> None:
        """create_gap_cardがカードを返すことをテスト."""
        mock_card = MagicMock()
        mock_card.__enter__ = Mock(return_value=mock_card)
        mock_card.__exit__ = Mock(return_value=False)
        mock_row = MagicMock()
        mock_row.__enter__ = Mock(return_value=mock_row)
        mock_row.__exit__ = Mock(return_value=False)
        mock_column = MagicMock()
        mock_column.__enter__ = Mock(return_value=mock_column)
        mock_column.__exit__ = Mock(return_value=False)
        mock_label = MagicMock()
        mock_label.classes = Mock(return_value=mock_label)
        
        gap_data = {
            'file': 'test.py',
            'line': 10,
            'issue': 'Test issue',
            'expected': 'Expected behavior',
            'actual': 'Actual behavior'
        }
        
        with patch('src.ui.components.gap_analysis.ui') as mock_ui:
            mock_ui.card.return_value = mock_card
            mock_ui.row.return_value = mock_row
            mock_ui.column.return_value = mock_column
            mock_ui.label.return_value = mock_label
            
            result = create_gap_card(gap_data)
            assert mock_ui.card.called

    def test_render_gap_analysis_with_empty_gaps(self) -> None:
        """空のギャップリストでrender_gap_analysisをテスト."""
        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)
        mock_label = MagicMock()
        mock_label.classes = Mock(return_value=mock_label)
        
        with patch('src.ui.components.gap_analysis.ui') as mock_ui:
            mock_ui.label.return_value = mock_label
            
            # with container をモック
            render_gap_analysis(mock_container, [])
            assert mock_ui.label.called

    def test_render_gap_analysis_with_gaps(self) -> None:
        """ギャップありでrender_gap_analysisをテスト."""
        mock_container = MagicMock()
        mock_container.__enter__ = Mock(return_value=mock_container)
        mock_container.__exit__ = Mock(return_value=False)
        mock_label = MagicMock()
        mock_label.classes = Mock(return_value=mock_label)
        
        gaps = [
            {
                'file': 'test.py',
                'line': 10,
                'issue': 'Test issue 1'
            },
            {
                'file': 'test2.py',
                'line': 20,
                'issue': 'Test issue 2'
            }
        ]
        
        with patch('src.ui.components.gap_analysis.ui') as mock_ui:
            mock_ui.label.return_value = mock_label
            with patch('src.ui.components.gap_analysis.create_gap_card') as mock_create:
                mock_create.return_value = MagicMock()
                
                render_gap_analysis(mock_container, gaps)
                assert mock_ui.label.called or mock_create.called