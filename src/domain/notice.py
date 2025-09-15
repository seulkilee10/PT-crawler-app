"""
Notice domain entity and value objects.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class Site(Enum):
    """Supported sites enumeration."""
    TOPIS = "topis"  # 서울시 교통정보센터
    ICTR = "ictr"    # 인천교통공사


@dataclass(frozen=True) 
class SiteConfig:
    """Site configuration."""
    name: str
    display_name: str
    base_url: str
    supports_categories: bool
    supports_search: bool
    categories: List[str]
    search_types: List[str]


class NoticeCategory(Enum):
    """Notice category enumeration."""
    ALL = "A"  # 전체
    TRAFFIC_CONTROL = "T"  # 통제안내
    BUS = "B"  # 버스안내
    POLICY = "J"  # 정책안내
    WEATHER = "W"  # 기상안내
    ETC = "E"  # 기타안내


@dataclass(frozen=True)
class Notice:
    """Notice domain entity."""
    id: str
    title: str
    category: NoticeCategory
    created_date: datetime
    view_count: int
    has_attachment: bool
    site: Site = Site.TOPIS  # 기본값은 TOPIS
    content: Optional[str] = None
    attachment_url: Optional[str] = None
    department: Optional[str] = None  # 인천교통공사용 작성부서
    
    def __post_init__(self):
        if not self.id:
            raise ValueError("Notice ID cannot be empty")
        if not self.title:
            raise ValueError("Notice title cannot be empty")
        if self.view_count < 0:
            raise ValueError("View count cannot be negative")


class SiteConfigManager:
    """Manages site configurations."""
    
    @staticmethod
    def get_config(site: Site) -> SiteConfig:
        """Get configuration for a site."""
        configs = {
            Site.TOPIS: SiteConfig(
                name="topis",
                display_name="TOPIS (서울시 교통정보센터)",
                base_url="https://topis.seoul.go.kr",
                supports_categories=True,
                supports_search=False,
                categories=["통제안내", "버스안내", "정책안내", "기상안내", "기타안내"],
                search_types=[]
            ),
            Site.ICTR: SiteConfig(
                name="ictr", 
                display_name="인천교통공사",
                base_url="https://www.ictr.or.kr",
                supports_categories=False,
                supports_search=True,
                categories=["전체"],
                search_types=["제목", "내용", "제목+내용"]
            )
        }
        return configs[site]
    
    @staticmethod
    def get_all_configs() -> Dict[Site, SiteConfig]:
        """Get all site configurations."""
        return {
            site: SiteConfigManager.get_config(site) 
            for site in Site
        }
