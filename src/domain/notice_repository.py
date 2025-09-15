"""
Notice repository interface following Repository pattern.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from .notice import Notice, NoticeCategory


class NoticeRepository(ABC):
    """Notice repository interface."""
    
    @abstractmethod
    async def get_notices_by_category(
        self, 
        category: NoticeCategory, 
        page: int = 1,
        per_page: int = 10
    ) -> List[Notice]:
        """Get notices by category with pagination.
        
        Args:
            category: Notice category to filter by
            page: Page number (1-based)
            per_page: Number of notices per page
            
        Returns:
            List of Notice objects
        """
        pass
    
    @abstractmethod
    async def get_notice_detail(self, notice_id: str) -> Optional[Notice]:
        """Get notice detail by ID.
        
        Args:
            notice_id: Notice ID
            
        Returns:
            Notice object with full content or None if not found
        """
        pass
    
    @abstractmethod
    async def get_total_pages(self, category: NoticeCategory) -> int:
        """Get total number of pages for a category.
        
        Args:
            category: Notice category
            
        Returns:
            Total number of pages
        """
        pass
