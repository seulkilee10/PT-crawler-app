"""
Unit tests for NoticeRepository interface.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from src.domain.notice import Notice, NoticeCategory
from src.domain.notice_repository import NoticeRepository


class MockNoticeRepository(NoticeRepository):
    """Mock implementation of NoticeRepository for testing."""
    
    def __init__(self):
        self.notices = [
            Notice(
                id='5284',
                title='9/15(월)~9/27(토) 북한남삼거리 보도육교 철거공사에 따른 교통통제 안내',
                category=NoticeCategory.TRAFFIC_CONTROL,
                created_date=datetime(2025, 9, 15),
                view_count=28,
                has_attachment=True
            ),
            Notice(
                id='5273',
                title='★ 서울 도심 << 서소문로 >> 가로변버스전용차로 지정 알림(9/21 부터)',
                category=NoticeCategory.BUS,
                created_date=datetime(2025, 9, 9),
                view_count=187,
                has_attachment=True
            )
        ]
    
    async def get_notices_by_category(
        self, 
        category: NoticeCategory, 
        page: int = 1,
        per_page: int = 10
    ) -> list[Notice]:
        """Mock implementation."""
        filtered_notices = [n for n in self.notices if category == NoticeCategory.ALL or n.category == category]
        start = (page - 1) * per_page
        end = start + per_page
        return filtered_notices[start:end]
    
    async def get_notice_detail(self, notice_id: str) -> Notice | None:
        """Mock implementation."""
        for notice in self.notices:
            if notice.id == notice_id:
                return Notice(
                    id=notice.id,
                    title=notice.title,
                    category=notice.category,
                    created_date=notice.created_date,
                    view_count=notice.view_count,
                    has_attachment=notice.has_attachment,
                    content=f"Detailed content for notice {notice_id}"
                )
        return None
    
    async def get_total_pages(self, category: NoticeCategory) -> int:
        """Mock implementation."""
        filtered_notices = [n for n in self.notices if category == NoticeCategory.ALL or n.category == category]
        return (len(filtered_notices) + 9) // 10  # Round up division


class TestNoticeRepository:
    """Test cases for NoticeRepository interface."""
    
    @pytest.fixture
    def repository(self):
        """Create mock repository for testing."""
        return MockNoticeRepository()
    
    @pytest.mark.asyncio
    async def test_get_notices_by_category_all(self, repository):
        """Test getting all notices."""
        # When
        notices = await repository.get_notices_by_category(NoticeCategory.ALL)
        
        # Then
        assert len(notices) == 2
        assert notices[0].id == '5284'
        assert notices[1].id == '5273'
    
    @pytest.mark.asyncio
    async def test_get_notices_by_category_traffic_control(self, repository):
        """Test getting traffic control notices."""
        # When
        notices = await repository.get_notices_by_category(NoticeCategory.TRAFFIC_CONTROL)
        
        # Then
        assert len(notices) == 1
        assert notices[0].id == '5284'
        assert notices[0].category == NoticeCategory.TRAFFIC_CONTROL
    
    @pytest.mark.asyncio
    async def test_get_notices_by_category_bus(self, repository):
        """Test getting bus notices."""
        # When
        notices = await repository.get_notices_by_category(NoticeCategory.BUS)
        
        # Then
        assert len(notices) == 1
        assert notices[0].id == '5273'
        assert notices[0].category == NoticeCategory.BUS
    
    @pytest.mark.asyncio
    async def test_get_notice_detail_existing(self, repository):
        """Test getting detail of existing notice."""
        # When
        notice = await repository.get_notice_detail('5284')
        
        # Then
        assert notice is not None
        assert notice.id == '5284'
        assert notice.content == "Detailed content for notice 5284"
    
    @pytest.mark.asyncio
    async def test_get_notice_detail_nonexisting(self, repository):
        """Test getting detail of non-existing notice."""
        # When
        notice = await repository.get_notice_detail('nonexistent')
        
        # Then
        assert notice is None
    
    @pytest.mark.asyncio
    async def test_get_total_pages(self, repository):
        """Test getting total pages count."""
        # When
        total_pages_all = await repository.get_total_pages(NoticeCategory.ALL)
        total_pages_traffic = await repository.get_total_pages(NoticeCategory.TRAFFIC_CONTROL)
        
        # Then
        assert total_pages_all == 1  # 2 notices, 10 per page = 1 page
        assert total_pages_traffic == 1  # 1 notice, 10 per page = 1 page
