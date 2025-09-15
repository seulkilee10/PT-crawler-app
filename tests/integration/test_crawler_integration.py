"""
Integration tests for the entire crawler system.
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.domain.notice import Notice, NoticeCategory
from src.application.notice_crawler_service import NoticeCrawlerService
from src.interface_adapters.cli import NoticeCrawlerCLI


class MockNoticeRepository:
    """Mock repository for integration testing."""
    
    def __init__(self):
        self.sample_notices = [
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
            ),
            Notice(
                id='5268',
                title='광명-서울 고속도로 직결 < 방화터널 > 일체화구간 구조물공사로 인한 전면통제 안내',
                category=NoticeCategory.TRAFFIC_CONTROL,
                created_date=datetime(2025, 9, 5),
                view_count=252,
                has_attachment=True
            ),
        ]
    
    async def get_notices_by_category(
        self, 
        category: NoticeCategory, 
        page: int = 1,
        per_page: int = 10
    ) -> list[Notice]:
        """Mock implementation."""
        if category == NoticeCategory.ALL:
            filtered = self.sample_notices
        else:
            filtered = [n for n in self.sample_notices if n.category == category]
        
        start = (page - 1) * per_page
        end = start + per_page
        return filtered[start:end]
    
    async def get_notice_detail(self, notice_id: str) -> Notice | None:
        """Mock implementation."""
        for notice in self.sample_notices:
            if notice.id == notice_id:
                return Notice(
                    id=notice.id,
                    title=notice.title,
                    category=notice.category,
                    created_date=notice.created_date,
                    view_count=notice.view_count,
                    has_attachment=notice.has_attachment,
                    content=f"Detailed content for notice {notice_id}. This is a mock content for testing purposes."
                )
        return None
    
    async def get_total_pages(self, category: NoticeCategory) -> int:
        """Mock implementation."""
        if category == NoticeCategory.ALL:
            total_notices = len(self.sample_notices)
        else:
            total_notices = len([n for n in self.sample_notices if n.category == category])
        
        return (total_notices + 9) // 10  # Round up division


class TestCrawlerIntegration:
    """Integration tests for the crawler system."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a crawler service with mock repository."""
        mock_repo = MockNoticeRepository()
        return NoticeCrawlerService(mock_repo)
    
    @pytest.mark.asyncio
    async def test_service_crawl_all_categories(self, mock_service):
        """Test crawling all categories through service."""
        # When
        results = await mock_service.crawl_all_categories(max_pages_per_category=1)
        
        # Then
        assert isinstance(results, dict)
        assert '통제안내' in results
        assert '버스안내' in results
        
        # Check traffic control notices
        traffic_notices = results['통제안내']
        assert len(traffic_notices) == 2  # Two traffic control notices
        
        # Check bus notices
        bus_notices = results['버스안내']
        assert len(bus_notices) == 1  # One bus notice
        
        # Check data structure
        for category_notices in results.values():
            for notice in category_notices:
                assert 'id' in notice
                assert 'title' in notice
                assert 'category' in notice
                assert 'created_date' in notice
                assert 'view_count' in notice
                assert 'has_attachment' in notice
    
    @pytest.mark.asyncio
    async def test_service_crawl_specific_category(self, mock_service):
        """Test crawling specific category through service."""
        # When
        notices = await mock_service.crawl_category(NoticeCategory.TRAFFIC_CONTROL, max_pages=1)
        
        # Then
        assert len(notices) == 2  # Two traffic control notices
        assert all(n.category == NoticeCategory.TRAFFIC_CONTROL for n in notices)
        assert notices[0].id == '5284'
        assert notices[1].id == '5268'
    
    @pytest.mark.asyncio
    async def test_service_get_notice_with_content(self, mock_service):
        """Test getting notice with content through service."""
        # When
        result = await mock_service.get_notice_with_content('5284')
        
        # Then
        assert result is not None
        assert result['id'] == '5284'
        assert result['content'] is not None
        assert 'Detailed content for notice 5284' in result['content']
        assert result['category'] == '통제안내'
        assert isinstance(result['created_date'], str)  # Should be ISO formatted
    
    @pytest.mark.asyncio
    async def test_service_get_statistics(self, mock_service):
        """Test getting statistics through service."""
        # When
        stats = await mock_service.get_statistics()
        
        # Then
        assert isinstance(stats, dict)
        assert 'total_notices' in stats
        assert 'categories' in stats
        assert stats['total_notices'] > 0
        
        categories = stats['categories']
        assert '통제안내' in categories
        assert '버스안내' in categories
        
        # Check category stats structure
        traffic_stats = categories['통제안내']
        assert 'estimated_total' in traffic_stats
        assert 'total_pages' in traffic_stats
        assert 'sample_notices' in traffic_stats
    
    @pytest.mark.asyncio
    async def test_service_crawl_with_content(self, mock_service):
        """Test crawling with full content through service."""
        # When
        results = await mock_service.crawl_with_content(NoticeCategory.TRAFFIC_CONTROL, max_notices=5)
        
        # Then
        assert len(results) == 2  # Two traffic control notices
        
        for result in results:
            assert 'id' in result
            assert 'title' in result
            assert 'content' in result
            assert result['content'] is not None
            assert 'Detailed content for notice' in result['content']
    
    def test_cli_initialization(self):
        """Test CLI initialization."""
        # When
        cli = NoticeCrawlerCLI()
        
        # Then
        assert cli.repository is None
        assert cli.service is None
    
    @pytest.mark.asyncio
    async def test_end_to_end_crawl_with_file_output(self):
        """Test end-to-end crawling with file output."""
        # Given
        mock_repo = MockNoticeRepository()
        service = NoticeCrawlerService(mock_repo)
        
        # When
        results = await service.crawl_all_categories(max_pages_per_category=1)
        
        # Create temporary file to test file output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Then
        assert temp_path.exists()
        
        # Read and verify the file
        with open(temp_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        assert isinstance(saved_data, dict)
        assert '통제안내' in saved_data
        assert '버스안내' in saved_data
        
        # Cleanup
        temp_path.unlink()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_service(self):
        """Test error handling in service layer."""
        # Given - Create a repository that raises errors
        class ErrorRepository:
            async def get_notices_by_category(self, category, page=1, per_page=10):
                raise Exception("Network error")
            
            async def get_total_pages(self, category):
                raise Exception("Network error")
            
            async def get_notice_detail(self, notice_id):
                raise Exception("Network error")
        
        error_repo = ErrorRepository()
        service = NoticeCrawlerService(error_repo)
        
        # When & Then - Should handle errors gracefully
        try:
            result = await service.get_notice_with_content('5284')
            assert result is None
        except Exception:
            pytest.fail("Service should handle repository errors gracefully")
        
        try:
            notices = await service.crawl_category(NoticeCategory.ALL, max_pages=1)
            assert notices == []  # Should return empty list on error
        except Exception:
            pytest.fail("Service should handle repository errors gracefully")
    
    def test_category_name_mapping(self):
        """Test category name mapping in service."""
        # Given
        mock_repo = MockNoticeRepository()
        service = NoticeCrawlerService(mock_repo)
        
        # When & Then
        assert service._get_category_name(NoticeCategory.TRAFFIC_CONTROL) == "통제안내"
        assert service._get_category_name(NoticeCategory.BUS) == "버스안내"
        assert service._get_category_name(NoticeCategory.POLICY) == "정책안내"
        assert service._get_category_name(NoticeCategory.WEATHER) == "기상안내"
        assert service._get_category_name(NoticeCategory.ETC) == "기타안내"
        assert service._get_category_name(NoticeCategory.ALL) == "전체"
