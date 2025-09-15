"""
Selenium-based implementation for ICTR (Incheon Transit Corporation).
"""
import asyncio
import re
import os
from datetime import datetime
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from ..domain.notice import Notice, NoticeCategory, Site
from ..domain.notice_repository import NoticeRepository


class SeleniumIctrRepository(NoticeRepository):
    """Selenium-based ICTR Notice repository implementation."""
    
    def __init__(self, base_url: str = "https://www.ictr.or.kr", headless: bool = True):
        """Initialize the repository.
        
        Args:
            base_url: Base URL of the ICTR website
            headless: Whether to run browser in headless mode
        """
        self.base_url = base_url
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
    
    def _get_driver(self) -> webdriver.Chrome:
        """Get Chrome WebDriver instance with speed optimizations."""
        if self.driver is None:
            try:
                options = Options()
                if self.headless:
                    options.add_argument('--headless')
                
                # 속도 최적화 옵션들 (대폭 강화)
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')  # 이미지 로딩 차단
                options.add_argument('--disable-css')     # CSS 로딩 차단
                options.add_argument('--disable-web-security')
                options.add_argument('--disable-features=TranslateUI')
                options.add_argument('--disable-ipc-flooding-protection')
                options.add_argument('--disable-renderer-backgrounding')
                options.add_argument('--disable-backgrounding-occluded-windows')
                options.add_argument('--disable-client-side-phishing-detection')
                options.add_argument('--disable-sync')
                options.add_argument('--disable-default-apps')
                options.add_argument('--no-first-run')
                options.add_argument('--no-default-browser-check')
                options.add_argument('--window-size=1280,720')
                
                # 추가 속도 최적화 (더 공격적)
                options.add_argument('--disable-logging')
                options.add_argument('--disable-network-service-logging')
                options.add_argument('--aggressive-cache-discard')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-features=VizDisplayCompositor')
                options.add_argument('--disable-3d-apis')
                options.add_argument('--disable-smooth-scrolling')
                options.add_argument('--disable-threaded-scrolling')
                
                # 배포 환경 최적화 (Render, Heroku 등)
                options.add_argument('--disable-dev-tools')
                options.add_argument('--remote-debugging-port=9223')
                
                # Chrome 바이너리 경로 자동 감지 (여러 위치 확인)
                chrome_bin = os.environ.get('GOOGLE_CHROME_BIN')
                if not chrome_bin:
                    # 일반적인 Chrome 설치 위치들 확인
                    possible_paths = [
                        '/usr/bin/google-chrome',
                        '/usr/bin/google-chrome-stable', 
                        '/opt/google/chrome/chrome',
                        '/usr/bin/chromium-browser'
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            chrome_bin = path
                            print(f"🔍 ICTR Chrome 바이너리 발견: {chrome_bin}")
                            break
                
                if chrome_bin and os.path.exists(chrome_bin):
                    options.binary_location = chrome_bin
                    print(f"✅ ICTR Chrome 바이너리 설정: {chrome_bin}")
                else:
                    print("⚠️  ICTR Chrome 바이너리 경로를 찾을 수 없습니다. 시스템 기본값 사용")
                
                # 페이지 로딩 전략을 eager로 변경 (더 안정적)
                options.page_load_strategy = 'eager'
                
                # 불필요한 리소스 차단 (더 공격적)
                prefs = {
                    "profile.managed_default_content_settings.images": 2,
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.managed_default_content_settings.media_stream": 2,
                    "profile.managed_default_content_settings.plugins": 2,
                    "profile.managed_default_content_settings.popups": 2,
                    "profile.managed_default_content_settings.geolocation": 2,
                    "profile.managed_default_content_settings.automatic_downloads": 2,
                }
                options.add_experimental_option("prefs", prefs)
                
                # WebDriver Manager를 사용해서 자동으로 ChromeDriver 관리
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                
                # 속도 최적화: 타임아웃 극단적 단축
                self.driver.set_page_load_timeout(10)   # 5초 → 10초 (안정성 고려)
                self.driver.implicitly_wait(2)          # 1초 → 2초 (안정성 고려)
                
                print(f"✅ ICTR Chrome WebDriver 초기화 완료 (headless: {self.headless})")
                
            except WebDriverException as e:
                error_msg = f"ICTR WebDriver 초기화 실패: {str(e)}"
                print(f"❌ {error_msg}")
                raise RuntimeError(f"인천교통공사 사이트 크롤링을 위한 브라우저를 시작할 수 없습니다. {error_msg}")
            except Exception as e:
                error_msg = f"예상치 못한 ICTR WebDriver 오류: {str(e)}"
                print(f"❌ {error_msg}")
                raise RuntimeError(f"인천교통공사 크롤링 브라우저 설정 중 오류가 발생했습니다. {error_msg}")
            
        return self.driver
    
    def _close_driver(self) -> None:
        """Close WebDriver instance."""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object.
        
        Args:
            date_str: Date string in format 'YYYY.MM.DD'
            
        Returns:
            Parsed datetime object
        """
        try:
            return datetime.strptime(date_str, '%Y.%m.%d')
        except ValueError:
            return datetime.now()
    
    async def get_notices_by_category(
        self, 
        category: NoticeCategory, 
        page: int = 1,
        per_page: int = 10
    ) -> List[Notice]:
        """Get notices by category with pagination."""
        # ICTR은 카테고리가 없으므로 전체 공지사항을 가져옴
        return await self.get_notices_by_search(
            keyword="",
            search_type="title", 
            page=page,
            per_page=per_page
        )
    
    async def get_notices_by_search(
        self,
        keyword: str = "",
        search_type: str = "title",  # "title", "content", "titlecontent"
        page: int = 1,
        per_page: int = 10
    ) -> List[Notice]:
        """Get notices by search criteria.
        
        Args:
            keyword: Search keyword
            search_type: Search type ("title", "content", "titlecontent")
            page: Page number
            per_page: Number of notices per page (controls listsz parameter)
            
            
        Returns:
            List of Notice objects
        """
        try:
            driver = self._get_driver()
            
            # Navigate to the notice list page  
            notice_url = f"{self.base_url}/main/board/notice.jsp"
            driver.get(notice_url)
            
            # Give page time to load (극한 최적화)
            await asyncio.sleep(0.5)  # 2초 → 0.5초
            
            # Wait for the page to load with board_list element
            
            # Wait for page load
            try:
                WebDriverWait(driver, 3).until(  # 8초 → 3초 극한 최적화
                    EC.presence_of_element_located((By.CLASS_NAME, "board_list"))
                )
            except TimeoutException:
                # Try to find generalList as alternative
                WebDriverWait(driver, 2).until(  # 3초 → 2초 극한 최적화
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.generalList"))
                )
            
            # Set list size if different from default
            if per_page != 10:
                try:
                    listsz_select = Select(driver.find_element(By.NAME, "listsz"))
                    listsz_select.select_by_value(str(per_page))
                    await asyncio.sleep(0.5)  # Wait for page refresh
                except NoSuchElementException:
                    pass
            
            # Perform search if keyword is provided
            if keyword:
                try:
                    # Select search type
                    search_type_map = {
                        "title": "title",
                        "content": "content", 
                        "titlecontent": "titlecontent"
                    }
                    keyfield_select = Select(driver.find_element(By.NAME, "keyfield"))
                    keyfield_select.select_by_value(search_type_map.get(search_type, "title"))
                    
                    # Enter search keyword
                    keyword_input = driver.find_element(By.NAME, "keyword")
                    keyword_input.clear()
                    keyword_input.send_keys(keyword)
                    
                    # Submit search
                    search_btn = driver.find_element(By.CSS_SELECTOR, ".btn_search")
                    driver.execute_script("arguments[0].click();", search_btn)
                    
                    # Wait for search results
                    await asyncio.sleep(0.2)  # 1초 → 0.2초 극한 최적화
                except NoSuchElementException:
                    pass
            
            # Navigate to requested page if not page 1
            if page > 1:
                try:
                    # Find and click page link
                    page_link = driver.find_element(By.XPATH, f"//a[@title='{page} page' or text()='{page}']")
                    driver.execute_script("arguments[0].click();", page_link)
                    await asyncio.sleep(0.1)  # 0.5초 → 0.1초 극한 최적화
                except NoSuchElementException:
                    pass
            
            # Extract notices from the page
            notices = []
            try:
                # ICTR 사이트 구조: ul.generalList > li (각 li가 하나의 공지사항)
                # 중요: 직접 자식 li만 선택 (writer_info 안의 li 제외)
                print(f"🔍 DEBUG - generalList 요소 찾는 중...")
                notice_items = driver.find_elements(By.CSS_SELECTOR, "ul.generalList > li")
                
                # 추가로 다른 구조도 확인
                if len(notice_items) == 0:
                    print(f"⚠️ DEBUG - generalList에서 li 요소 없음, 다른 구조 확인 중...")
                    # board_list 구조도 확인
                    try:
                        board_list = driver.find_element(By.CLASS_NAME, "board_list")
                        notice_items = board_list.find_elements(By.TAG_NAME, "tr")[1:]  # 헤더 제외
                        print(f"🔍 DEBUG - board_list에서 {len(notice_items)}개 발견")
                    except NoSuchElementException:
                        pass
                
                print(f"🔍 DEBUG - 페이지에서 발견된 공지사항 요소: {len(notice_items)}개")
                
                for i, notice_item in enumerate(notice_items[:10]):  # 최대 10개로 제한
                    try:
                        print(f"📝 DEBUG - {i+1}번째 공지사항 처리 중...")
                        # 1. 제목과 링크 추출 (여러 선택자 시도)
                        title_elem = None
                        title = ""
                        href = ""
                        
                        # 다양한 선택자로 시도
                        selectors = [
                            "p.title a",      # 원래 선택자
                            ".title a",       # 클래스만
                            "a",              # 모든 링크
                            "p a",            # p 태그 내 링크
                        ]
                        
                        for selector in selectors:
                            try:
                                title_elem = notice_item.find_element(By.CSS_SELECTOR, selector)
                                title = title_elem.text.strip()
                                href = title_elem.get_attribute("href")
                                if title and href and "notice" in href.lower():  # 유효한 공지사항 링크인지 확인
                                    print(f"   📋 제목 (선택자: {selector}): {title[:50]}...")
                                    break
                            except NoSuchElementException:
                                continue
                        
                        if not title_elem or not title:
                            # HTML 구조 확인을 위해 전체 텍스트 출력
                            item_text = notice_item.text.strip()
                            print(f"   ❌ 제목 요소 찾기 실패. 전체 텍스트: {item_text[:100]}...")
                            continue
                        
                        # Remove "new" tag from title
                        title = re.sub(r'\s*new\s*$', '', title, flags=re.IGNORECASE).strip()
                        
                        # Extract notice ID from href
                        notice_id_match = re.search(r'msg_seq=(\d+)', href)
                        notice_id = notice_id_match.group(1) if notice_id_match else str(i + 1)
                        print(f"   🆔 ID: {notice_id}")
                        
                        # 2. writer_info에서 날짜, 작성자, 첨부파일 추출
                        try:
                            writer_info = notice_item.find_element(By.CSS_SELECTOR, "div.writer_info ul")
                            info_items = writer_info.find_elements(By.TAG_NAME, "li")
                            print(f"   📊 writer_info 항목 개수: {len(info_items)}")
                        except NoSuchElementException:
                            print(f"   ❌ writer_info 요소 찾기 실패 - 건너뛰기")
                            continue
                        
                        # 기본값 설정
                        created_date = datetime.now()
                        department = ""
                        has_attachment = False
                        
                        for info_item in info_items:
                            item_class = info_item.get_attribute("class") or ""
                            item_title = info_item.get_attribute("title") or ""
                            item_text = info_item.text.strip()
                            
                            # 날짜 추출
                            if "w80" in item_class or item_title == "작성일":
                                if re.search(r'\d{4}\.\d{2}\.\d{2}', item_text):
                                    created_date = self._parse_date(item_text)
                            
                            # 작성자 추출
                            elif "writer" in item_class or item_title == "작성자":
                                department = item_text
                            
                            # 첨부파일 확인
                            elif "file" in item_class:
                                file_links = info_item.find_elements(By.TAG_NAME, "a")
                                if file_links:
                                    has_attachment = True
                        
                        # 공지사항 객체 생성
                        notice = Notice(
                            id=notice_id,
                            title=title,
                            category=NoticeCategory.ETC,
                            created_date=created_date,
                            view_count=0,
                            has_attachment=has_attachment,
                            site=Site.ICTR,
                            department=department
                        )
                        notices.append(notice)
                        print(f"   ✅ {i+1}번째 공지사항 처리 완료")
                        
                    except Exception as e:
                        print(f"   💥 {i+1}번째 공지사항 처리 중 오류: {str(e)}")
                        # Skip items that don't have the expected structure
                        continue
            
            except Exception as e:
                print(f"ICTR 공지사항 추출 중 오류: {str(e)}")
            
            return notices
            
        except Exception as e:
            raise Exception(f"Failed to get ICTR notices: {str(e)}")
    
    async def get_notice_detail(self, notice_id: str) -> Optional[Notice]:
        """Get notice detail by ID."""
        try:
            driver = self._get_driver()
            
            # First get basic info from list (needed for title, date, etc.)
            base_notice = None
            try:
                notices = await self.get_notices_by_search("", "title", 1, 50)
                for notice in notices:
                    if notice.id == notice_id:
                        base_notice = notice
                        break
                        
                # Search more pages if not found
                if not base_notice:
                    for page in range(2, 6):
                        notices = await self.get_notices_by_search("", "title", page, 50)
                        if not notices:
                            break
                        for notice in notices:
                            if notice.id == notice_id:
                                base_notice = notice
                                break
                        if base_notice:
                            break
            except Exception:
                pass
            
            if not base_notice:
                # Create minimal notice if not found in list
                base_notice = Notice(
                    id=notice_id,
                    title=f"공지사항 {notice_id}",
                    category=NoticeCategory.ETC,
                    created_date=datetime.now(),
                    view_count=0,
                    has_attachment=False,
                    site=Site.ICTR
                )
            
            # Navigate to detail page
            detail_url = f"{self.base_url}/main/bbs/bbsMsgDetail.do?msg_seq={notice_id}&bcd=notice"
            driver.get(detail_url)
            
            # Wait for page load (극한 최적화)
            await asyncio.sleep(0.2)  # 1초 → 0.2초
            
            # Extract content
            content = ""
            try:
                # ICTR 사이트 구조에 맞는 content selector 시도
                content_selectors = [
                    ".board_view .content",
                    ".view_content", 
                    ".board_content",
                    "#detail_con .board_view",
                    "article .content",
                    ".detail_content"
                ]
                
                for selector in content_selectors:
                    try:
                        content_elem = driver.find_element(By.CSS_SELECTOR, selector)
                        content = content_elem.text.strip()
                        if content and len(content) > 10:
                            break
                    except NoSuchElementException:
                        continue
                
                # 내용이 없으면 페이지 전체에서 추출 시도
                if not content or len(content) < 10:
                    try:
                        # 본문을 포함할 수 있는 div들 탐색
                        body_divs = driver.find_elements(By.CSS_SELECTOR, 
                            "div[class*='content'], div[class*='view'], div[class*='detail']")
                        for div in body_divs:
                            div_text = div.text.strip()
                            if len(div_text) > 50:
                                content = div_text
                                break
                    except:
                        pass
                
                if not content:
                    content = "상세 내용을 가져올 수 없습니다."
                        
            except Exception as e:
                content = f"Content extraction error: {str(e)}"
            
            # Create notice with content
            return Notice(
                id=base_notice.id,
                title=base_notice.title,
                category=base_notice.category,
                created_date=base_notice.created_date,
                view_count=base_notice.view_count,
                has_attachment=base_notice.has_attachment,
                site=Site.ICTR,
                department=base_notice.department,
                content=content
            )
            
        except Exception as e:
            raise Exception(f"Failed to get ICTR notice detail: {str(e)}")
    
    async def get_total_pages(self, category: NoticeCategory) -> int:
        """Get total number of pages."""
        try:
            driver = self._get_driver()
            
            # Navigate to notice list page
            notice_url = f"{self.base_url}/main/board/notice.jsp"
            driver.get(notice_url)
            
            # Wait for page load
            WebDriverWait(driver, 2).until(  # 5초 → 2초 극한 최적화
                EC.presence_of_element_located((By.CLASS_NAME, "board_list"))
            )
            
            # Extract total pages from pagination
            try:
                # Look for pagination info like "전체 852건, 현재페이지 1/86"
                written_elem = driver.find_element(By.CSS_SELECTOR, ".written")
                written_text = written_elem.text
                
                # Extract total pages from text like "현재페이지 1/86"
                pages_match = re.search(r'현재페이지\s+\d+/(\d+)', written_text)
                if pages_match:
                    return int(pages_match.group(1))
                
                # Fallback: look for last page in pagination links
                page_links = driver.find_elements(By.CSS_SELECTOR, ".paging a.num")
                if page_links:
                    page_numbers = []
                    for link in page_links:
                        try:
                            page_num = int(link.text.strip())
                            page_numbers.append(page_num)
                        except ValueError:
                            continue
                    if page_numbers:
                        return max(page_numbers)
                
                return 1
                
            except NoSuchElementException:
                return 1
                
        except Exception as e:
            raise Exception(f"Failed to get total pages: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self._close_driver()
