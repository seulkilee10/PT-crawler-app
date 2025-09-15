"""
Notice crawler service implementing business logic.
"""
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from ..domain.notice import Notice, NoticeCategory
from ..domain.notice_repository import NoticeRepository


class NoticeCrawlerService:
    """Service for crawling notices with business logic."""
    
    def __init__(self, repository: NoticeRepository):
        """Initialize the service.
        
        Args:
            repository: Notice repository implementation
        """
        self.repository = repository
    
    async def crawl_all_categories(
        self, 
        max_pages_per_category: int = 5,
        per_page: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Crawl notices from all categories.
        
        Args:
            max_pages_per_category: Maximum pages to crawl per category
            per_page: Number of notices per page
            
        Returns:
            Dictionary with category names as keys and list of notice dictionaries as values
        """
        categories = [
            NoticeCategory.TRAFFIC_CONTROL,
            NoticeCategory.BUS,
            NoticeCategory.POLICY,
            NoticeCategory.WEATHER,
            NoticeCategory.ETC
        ]
        
        results = {}
        
        for category in categories:
            category_name = self._get_category_name(category)
            print(f"Crawling {category_name} notices...")
            
            try:
                notices = await self.crawl_category(
                    category, 
                    max_pages_per_category, 
                    per_page
                )
                
                # Convert notices to dictionaries for JSON serialization
                notice_dicts = [asdict(notice) for notice in notices]
                
                # Convert datetime objects to strings
                for notice_dict in notice_dicts:
                    if notice_dict['created_date']:
                        notice_dict['created_date'] = notice_dict['created_date'].isoformat()
                    notice_dict['category'] = category_name
                
                results[category_name] = notice_dicts
                print(f"Found {len(notices)} notices in {category_name}")
                
            except Exception as e:
                print(f"Error crawling {category_name}: {str(e)}")
                results[category_name] = []
        
        return results
    
    async def crawl_category_fast(
        self, 
        category: NoticeCategory, 
        max_pages: int = 5,
        per_page: int = 10
    ) -> List[Notice]:
        """🚀 Fast crawl notices from a specific category with optimizations.
        
        Args:
            category: Category to crawl
            max_pages: Maximum number of pages to crawl
            per_page: Number of notices per page
            
        Returns:
            List of Notice objects
        """
        all_notices = []
        
        try:
            print(f"🚀 Fast crawling {self._get_category_name(category)}...")
            
            # 첫 페이지로 총 페이지 수 확인 (빠르게)
            first_page_notices = await self.repository.get_notices_by_category(
                category, 1, per_page
            )
            all_notices.extend(first_page_notices)
            
            # 나머지 페이지들 처리 (최소 대기시간으로)
            if max_pages > 1:
                for page in range(2, min(max_pages + 1, 11)):  # 최대 10페이지까지만
                    print(f"⚡ Page {page}...")
                    
                    try:
                        notices = await self.repository.get_notices_by_category(
                            category, page, per_page
                        )
                        
                        if not notices:  # 더 이상 데이터가 없으면 중단
                            print(f"No more data at page {page}, stopping...")
                            break
                            
                        all_notices.extend(notices)
                        
                        # 극도로 짧은 대기 (0.05초)
                        await asyncio.sleep(0.05)
                        
                    except Exception as e:
                        print(f"⚠️  Error at page {page}: {str(e)}")
                        continue
                        
            print(f"✅ Fast crawling completed: {len(all_notices)} notices")
            
        except Exception as e:
            print(f"❌ Fast crawling failed: {str(e)}")
            
        return all_notices
    
    async def crawl_category(
        self, 
        category: NoticeCategory, 
        max_pages: int = 5,
        per_page: int = 10
    ) -> List[Notice]:
        """Crawl notices from a specific category.
        
        Args:
            category: Category to crawl
            max_pages: Maximum number of pages to crawl
            per_page: Number of notices per page
            
        Returns:
            List of Notice objects
        """
        all_notices = []
        
        try:
            total_pages = await self.repository.get_total_pages(category)
            pages_to_crawl = min(max_pages, total_pages)
            
            print(f"Total pages available: {total_pages}, crawling: {pages_to_crawl}")
            
            for page in range(1, pages_to_crawl + 1):
                print(f"Crawling page {page}/{pages_to_crawl}...")
                
                try:
                    notices = await self.repository.get_notices_by_category(
                        category, page, per_page
                    )
                    
                    all_notices.extend(notices)
                    
                    # 페이지 간 대기시간 단축 (⚡ 속도 최적화)
                    if page < pages_to_crawl:
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    print(f"Error crawling page {page}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Error getting total pages: {str(e)}")
        
        return all_notices
    
    async def get_notice_with_content(self, notice_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific notice with full content.
        
        Args:
            notice_id: ID of the notice to retrieve
            
        Returns:
            Dictionary representation of the notice with content
        """
        try:
            notice = await self.repository.get_notice_detail(notice_id)
            
            if notice:
                notice_dict = asdict(notice)
                
                # Convert datetime to string
                if notice_dict['created_date']:
                    notice_dict['created_date'] = notice_dict['created_date'].isoformat()
                
                notice_dict['category'] = self._get_category_name(notice.category)
                
                return notice_dict
            
            return None
            
        except Exception as e:
            print(f"Error getting notice {notice_id}: {str(e)}")
            return None
    
    async def crawl_with_content(
        self, 
        category: NoticeCategory,
        max_notices: int = 50
    ) -> List[Dict[str, Any]]:
        """Crawl notices with full content.
        
        Args:
            category: Category to crawl
            max_notices: Maximum number of notices to get content for
            
        Returns:
            List of notice dictionaries with content
        """
        # First get the list of notices
        notices = await self.crawl_category(category, max_pages=10)
        notices = notices[:max_notices]  # Limit the number
        
        notices_with_content = []
        
        for i, notice in enumerate(notices, 1):
            print(f"Getting content for notice {i}/{len(notices)}: {notice.id}")
            
            try:
                detailed_notice = await self.repository.get_notice_detail(notice.id)
                
                if detailed_notice:
                    notice_dict = asdict(detailed_notice)
                    
                    # Convert datetime to string
                    if notice_dict['created_date']:
                        notice_dict['created_date'] = notice_dict['created_date'].isoformat()
                    
                    notice_dict['category'] = self._get_category_name(detailed_notice.category)
                    notices_with_content.append(notice_dict)
                
                # Be respectful with delay
                if i < len(notices):
                    await asyncio.sleep(2)
                    
            except Exception as e:
                print(f"Error getting content for notice {notice.id}: {str(e)}")
                continue
        
        return notices_with_content
    
    def _get_category_name(self, category: NoticeCategory) -> str:
        """Get human-readable category name.
        
        Args:
            category: NoticeCategory enum value
            
        Returns:
            Human-readable category name
        """
        category_names = {
            NoticeCategory.ALL: "전체",
            NoticeCategory.TRAFFIC_CONTROL: "통제안내",
            NoticeCategory.BUS: "버스안내",
            NoticeCategory.POLICY: "정책안내",
            NoticeCategory.WEATHER: "기상안내",
            NoticeCategory.ETC: "기타안내"
        }
        
        return category_names.get(category, "기타안내")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about notices across categories.
        
        Returns:
            Dictionary with statistics
        """
        categories = [
            NoticeCategory.TRAFFIC_CONTROL,
            NoticeCategory.BUS,
            NoticeCategory.POLICY,
            NoticeCategory.WEATHER,
            NoticeCategory.ETC
        ]
        
        stats = {
            'total_notices': 0,
            'categories': {}
        }
        
        for category in categories:
            category_name = self._get_category_name(category)
            
            try:
                # Get first page to estimate
                notices = await self.repository.get_notices_by_category(category, 1, 10)
                total_pages = await self.repository.get_total_pages(category)
                estimated_total = total_pages * 10  # Rough estimate
                
                stats['categories'][category_name] = {
                    'estimated_total': estimated_total,
                    'total_pages': total_pages,
                    'sample_notices': len(notices)
                }
                
                stats['total_notices'] += estimated_total
                
            except Exception as e:
                print(f"Error getting stats for {category_name}: {str(e)}")
                stats['categories'][category_name] = {
                    'estimated_total': 0,
                    'total_pages': 0,
                    'sample_notices': 0,
                    'error': str(e)
                }
        
        return stats
