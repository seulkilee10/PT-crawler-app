"""
Unit tests for Notice domain entity.
"""
import pytest
from datetime import datetime
from src.domain.notice import Notice, NoticeCategory


class TestNotice:
    """Test cases for Notice entity."""
    
    def test_create_valid_notice(self):
        """Test creating a valid notice."""
        # Given
        notice_data = {
            'id': '5284',
            'title': '9/15(월)~9/27(토) 북한남삼거리 보도육교 철거공사에 따른 교통통제 안내',
            'category': NoticeCategory.TRAFFIC_CONTROL,
            'created_date': datetime(2025, 9, 15),
            'view_count': 28,
            'has_attachment': True
        }
        
        # When
        notice = Notice(**notice_data)
        
        # Then
        assert notice.id == '5284'
        assert notice.title == '9/15(월)~9/27(토) 북한남삼거리 보도육교 철거공사에 따른 교통통제 안내'
        assert notice.category == NoticeCategory.TRAFFIC_CONTROL
        assert notice.created_date == datetime(2025, 9, 15)
        assert notice.view_count == 28
        assert notice.has_attachment is True
        assert notice.content is None
        assert notice.attachment_url is None
    
    def test_create_notice_with_content(self):
        """Test creating notice with content."""
        # Given
        notice_data = {
            'id': '5284',
            'title': 'Test Notice',
            'category': NoticeCategory.BUS,
            'created_date': datetime(2025, 9, 15),
            'view_count': 10,
            'has_attachment': False,
            'content': 'This is test content'
        }
        
        # When
        notice = Notice(**notice_data)
        
        # Then
        assert notice.content == 'This is test content'
    
    def test_create_notice_with_empty_id_raises_error(self):
        """Test that empty ID raises ValueError."""
        # Given
        notice_data = {
            'id': '',
            'title': 'Test Notice',
            'category': NoticeCategory.BUS,
            'created_date': datetime(2025, 9, 15),
            'view_count': 10,
            'has_attachment': False
        }
        
        # When & Then
        with pytest.raises(ValueError, match="Notice ID cannot be empty"):
            Notice(**notice_data)
    
    def test_create_notice_with_empty_title_raises_error(self):
        """Test that empty title raises ValueError."""
        # Given
        notice_data = {
            'id': '123',
            'title': '',
            'category': NoticeCategory.BUS,
            'created_date': datetime(2025, 9, 15),
            'view_count': 10,
            'has_attachment': False
        }
        
        # When & Then
        with pytest.raises(ValueError, match="Notice title cannot be empty"):
            Notice(**notice_data)
    
    def test_create_notice_with_negative_view_count_raises_error(self):
        """Test that negative view count raises ValueError."""
        # Given
        notice_data = {
            'id': '123',
            'title': 'Test Notice',
            'category': NoticeCategory.BUS,
            'created_date': datetime(2025, 9, 15),
            'view_count': -1,
            'has_attachment': False
        }
        
        # When & Then
        with pytest.raises(ValueError, match="View count cannot be negative"):
            Notice(**notice_data)
    
    def test_notice_immutability(self):
        """Test that Notice is immutable (frozen dataclass)."""
        # Given
        notice = Notice(
            id='123',
            title='Test Notice',
            category=NoticeCategory.BUS,
            created_date=datetime(2025, 9, 15),
            view_count=10,
            has_attachment=False
        )
        
        # When & Then
        with pytest.raises(AttributeError):
            notice.title = 'Modified Title'
