"""
Multi-site notice crawler service implementing business logic.
"""
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from ..domain.notice import Notice, NoticeCategory, Site, SiteConfigManager
from ..infrastructure.repository_factory import RepositoryFactory
from ..infrastructure.selenium_ictr_repository import SeleniumIctrRepository


class MultiSiteCrawlerService:
    """Service for crawling notices from multiple sites."""
    
    def __init__(self, headless: bool = True):
        """Initialize the service.
        
        Args:
            headless: Whether to run browsers in headless mode
        """
        self.headless = headless
        self.repositories = {}  # Cache repositories
    
    def _get_repository(self, site: Site):
        """Get repository instance for a site (with caching)."""
        if site not in self.repositories:
            self.repositories[site] = RepositoryFactory.create_repository(site, self.headless)
        return self.repositories[site]
    
    async def crawl_site(
        self,
        site: Site,
        category: NoticeCategory = NoticeCategory.ALL,
        max_pages: int = 3,
        per_page: int = 10,
        search_params: Optional[Dict[str, str]] = None
    ) -> List[Notice]:
        """Crawl notices from a specific site.
        
        Args:
            site: Site to crawl
            category: Category to crawl (for TOPIS)
            max_pages: Maximum number of pages
            per_page: Number of notices per page
            search_params: Search parameters for ICTR
                - keyword: search keyword
                - search_type: "title", "content", "titlecontent"
        
        Returns:
            List of Notice objects
        """
        repository = self._get_repository(site)
        notices = []
        
        try:
            print(f"🌐 Crawling {site.value} site...")
            
            if site == Site.TOPIS:
                # TOPIS 사이트: 기존 방식으로 카테고리별 크롤링
                for page in range(1, max_pages + 1):
                    page_notices = await repository.get_notices_by_category(
                        category, page, per_page
                    )
                    notices.extend(page_notices)
                    
                    if not page_notices:  # No more notices
                        break
                        
                    await asyncio.sleep(0.1)  # Rate limiting
                        
            elif site == Site.ICTR:
                # ICTR 사이트: 검색 기반 크롤링
                keyword = search_params.get("keyword", "") if search_params else ""
                search_type = search_params.get("search_type", "title") if search_params else "title"
                
                for page in range(1, max_pages + 1):
                    page_notices = await repository.get_notices_by_search(
                        keyword=keyword,
                        search_type=search_type,
                        page=page,
                        per_page=per_page
                    )
                    notices.extend(page_notices)
                    
                    if not page_notices:  # No more notices
                        break
                        
                    await asyncio.sleep(0.1)  # Rate limiting
            
            print(f"✅ {site.value} crawling completed: {len(notices)} notices")
            
        except Exception as e:
            print(f"❌ Error crawling {site.value}: {str(e)}")
        
        return notices
    
    async def crawl_all_sites(
        self,
        topis_category: NoticeCategory = NoticeCategory.ALL,
        ictr_search_params: Optional[Dict[str, str]] = None,
        max_pages: int = 3,
        per_page: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Crawl notices from all supported sites.
        
        Args:
            topis_category: Category for TOPIS crawling
            ictr_search_params: Search parameters for ICTR
            max_pages: Maximum pages per site
            per_page: Number of notices per page
        
        Returns:
            Dictionary with site names as keys and notice dictionaries as values
        """
        results = {}
        supported_sites = RepositoryFactory.get_supported_sites()
        
        for site in supported_sites:
            site_config = SiteConfigManager.get_config(site)
            print(f"🌐 Starting {site_config.display_name} crawling...")
            
            try:
                if site == Site.TOPIS:
                    notices = await self.crawl_site(
                        site=site,
                        category=topis_category,
                        max_pages=max_pages,
                        per_page=per_page
                    )
                elif site == Site.ICTR:
                    notices = await self.crawl_site(
                        site=site,
                        max_pages=max_pages,
                        per_page=per_page,
                        search_params=ictr_search_params
                    )
                else:
                    notices = []
                
                # Convert notices to dictionaries
                notice_dicts = []
                for notice in notices:
                    notice_dict = asdict(notice)
                    notice_dict['created_date'] = notice.created_date.isoformat()
                    notice_dict['category'] = self._get_category_name(notice.category)
                    notice_dict['site'] = site.value
                    notice_dicts.append(notice_dict)
                
                results[site_config.display_name] = notice_dicts
                print(f"✅ {site_config.display_name}: {len(notices)} notices")
                
            except Exception as e:
                print(f"❌ Error with {site_config.display_name}: {str(e)}")
                results[site_config.display_name] = []
        
        return results
    
    async def get_notice_with_content(self, site: Site, notice_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific notice with full content from a site.
        
        Args:
            site: Site enum
            notice_id: ID of the notice
        
        Returns:
            Notice dictionary with content or None
        """
        try:
            repository = self._get_repository(site)
            notice = await repository.get_notice_detail(notice_id)
            
            if notice:
                notice_dict = asdict(notice)
                notice_dict['created_date'] = notice.created_date.isoformat()
                notice_dict['category'] = self._get_category_name(notice.category)
                notice_dict['site'] = site.value
                return notice_dict
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting notice {notice_id} from {site.value}: {str(e)}")
            return None
    
    async def search_notices(
        self,
        site: Site,
        keyword: str,
        search_type: str = "title",
        max_pages: int = 3,
        per_page: int = 10
    ) -> List[Dict[str, Any]]:
        """Search notices on a specific site.
        
        Args:
            site: Site to search
            keyword: Search keyword
            search_type: Search type ("title", "content", "titlecontent")
            max_pages: Maximum pages to search
            per_page: Results per page
        
        Returns:
            List of notice dictionaries
        """
        if site == Site.ICTR:
            notices = await self.crawl_site(
                site=site,
                max_pages=max_pages,
                per_page=per_page,
                search_params={
                    "keyword": keyword,
                    "search_type": search_type
                }
            )
        else:
            # For TOPIS, we don't have search functionality, so return empty
            notices = []
        
        # Convert to dictionaries
        notice_dicts = []
        for notice in notices:
            notice_dict = asdict(notice)
            notice_dict['created_date'] = notice.created_date.isoformat()
            notice_dict['category'] = self._get_category_name(notice.category)
            notice_dict['site'] = site.value
            notice_dicts.append(notice_dict)
        
        return notice_dicts
    
    def _get_category_name(self, category: NoticeCategory) -> str:
        """Get human-readable category name."""
        category_names = {
            NoticeCategory.ALL: "전체",
            NoticeCategory.TRAFFIC_CONTROL: "통제안내",
            NoticeCategory.BUS: "버스안내",
            NoticeCategory.POLICY: "정책안내", 
            NoticeCategory.WEATHER: "기상안내",
            NoticeCategory.ETC: "기타안내"
        }
        return category_names.get(category, "기타안내")
    
    def get_site_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for all supported sites.
        
        Returns:
            Dictionary with site configurations
        """
        configs = {}
        for site in RepositoryFactory.get_supported_sites():
            config = SiteConfigManager.get_config(site)
            configs[site.value] = {
                'name': config.name,
                'display_name': config.display_name,
                'base_url': config.base_url,
                'supports_categories': config.supports_categories,
                'supports_search': config.supports_search,
                'categories': config.categories,
                'search_types': config.search_types
            }
        return configs
    
    def cleanup(self):
        """Cleanup all repository instances."""
        for repository in self.repositories.values():
            if hasattr(repository, '_close_driver'):
                repository._close_driver()
        self.repositories.clear()
    
    def __del__(self):
        """Cleanup when service is destroyed."""
        self.cleanup()
