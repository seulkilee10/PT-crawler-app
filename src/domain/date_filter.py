"""
Date filter domain value object.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DateFilter:
    """날짜 필터 값 객체."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def is_in_range(self, target_date: datetime) -> bool:
        """주어진 날짜가 필터 범위에 포함되는지 확인.
        
        Args:
            target_date: 확인할 날짜
            
        Returns:
            범위에 포함되면 True, 아니면 False
        """
        if self.start_date and target_date < self.start_date:
            return False
        if self.end_date and target_date > self.end_date:
            return False
        return True
    
    def __str__(self) -> str:
        """문자열 표현."""
        if self.start_date and self.end_date:
            return f"{self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}"
        elif self.start_date:
            return f"{self.start_date.strftime('%Y-%m-%d')} 이후"
        elif self.end_date:
            return f"{self.end_date.strftime('%Y-%m-%d')} 이전"
        else:
            return "전체 기간"
