"""
Repository Factory for creating site-specific repositories.
"""
from typing import Dict, Type
from ..domain.notice import Site
from ..domain.notice_repository import NoticeRepository
from .selenium_notice_repository import SeleniumNoticeRepository
from .selenium_ictr_repository import SeleniumIctrRepository


class RepositoryFactory:
    """Factory for creating site-specific notice repositories."""
    
    _repositories: Dict[Site, Type[NoticeRepository]] = {
        Site.TOPIS: SeleniumNoticeRepository,
        Site.ICTR: SeleniumIctrRepository
    }
    
    @classmethod
    def create_repository(cls, site: Site, headless: bool = True) -> NoticeRepository:
        """Create repository instance for the specified site.
        
        Args:
            site: Site enum value
            headless: Whether to run browser in headless mode
            
        Returns:
            NoticeRepository instance for the site
            
        Raises:
            ValueError: If site is not supported
        """
        if site not in cls._repositories:
            raise ValueError(f"Site {site.value} is not supported")
        
        repository_class = cls._repositories[site]
        
        # Create instance with appropriate configuration
        if site == Site.TOPIS:
            return repository_class(
                base_url="https://topis.seoul.go.kr", 
                headless=headless
            )
        elif site == Site.ICTR:
            return repository_class(
                base_url="https://www.ictr.or.kr", 
                headless=headless
            )
        else:
            raise ValueError(f"Unknown site configuration: {site.value}")
    
    @classmethod
    def get_supported_sites(cls) -> list[Site]:
        """Get list of supported sites.
        
        Returns:
            List of supported Site enum values
        """
        return list(cls._repositories.keys())
    
    @classmethod
    def register_repository(cls, site: Site, repository_class: Type[NoticeRepository]) -> None:
        """Register a new repository class for a site.
        
        Args:
            site: Site enum value
            repository_class: Repository class to register
        """
        cls._repositories[site] = repository_class
