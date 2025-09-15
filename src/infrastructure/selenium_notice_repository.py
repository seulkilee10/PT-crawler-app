"""
Selenium-based implementation of NoticeRepository.
"""
import asyncio
import re
import os
from datetime import datetime
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from ..domain.notice import Notice, NoticeCategory
from ..domain.notice_repository import NoticeRepository


class SeleniumNoticeRepository(NoticeRepository):
    """Selenium-based Notice repository implementation."""
    
    def __init__(self, base_url: str = "https://topis.seoul.go.kr", headless: bool = True):
        """Initialize the repository.
        
        Args:
            base_url: Base URL of the TOPIS website
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
                
                # 🚀 속도 최적화 옵션들
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')  # 이미지 로딩 차단
                options.add_argument('--disable-css')  # CSS 차단 
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
                options.add_argument('--window-size=1280,720')  # 더 작은 창 크기
                
                # 배포 환경 최적화 (Render, Heroku 등)
                options.add_argument('--disable-logging')
                options.add_argument('--disable-dev-tools')
                options.add_argument('--remote-debugging-port=9222')
                
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
                            print(f"🔍 Chrome 바이너리 발견: {chrome_bin}")
                            break
                
                if chrome_bin and os.path.exists(chrome_bin):
                    options.binary_location = chrome_bin
                    print(f"✅ Chrome 바이너리 설정: {chrome_bin}")
                else:
                    print("⚠️  Chrome 바이너리 경로를 찾을 수 없습니다. 시스템 기본값 사용")
                
                # 페이지 로딩 전략 (빠른 로딩)
                options.page_load_strategy = 'eager'  # DOM 준비되면 바로 진행
                
                # 불필요한 리소스 차단
                prefs = {
                    "profile.managed_default_content_settings.images": 2,  # 이미지 차단
                    "profile.default_content_setting_values.notifications": 2,  # 알림 차단
                    "profile.managed_default_content_settings.media_stream": 2,  # 미디어 차단
                }
                options.add_experimental_option("prefs", prefs)
                
                # WebDriver Manager를 사용해서 자동으로 ChromeDriver 관리
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
                
                # 타임아웃 설정 (더 짧게)
                self.driver.set_page_load_timeout(10)  # 10초로 단축
                self.driver.implicitly_wait(3)  # 3초로 단축
                
                print(f"✅ Chrome WebDriver 초기화 완료 (headless: {self.headless})")
                
            except WebDriverException as e:
                error_msg = f"WebDriver 초기화 실패: {str(e)}"
                print(f"❌ {error_msg}")
                raise RuntimeError(f"크롤링을 위한 브라우저를 시작할 수 없습니다. {error_msg}")
            except Exception as e:
                error_msg = f"예상치 못한 WebDriver 오류: {str(e)}"
                print(f"❌ {error_msg}")
                raise RuntimeError(f"브라우저 설정 중 오류가 발생했습니다. {error_msg}")
            
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
            # Fallback to current date if parsing fails
            return datetime.now()
    
    def _extract_category_from_label(self, label_text: str) -> NoticeCategory:
        """Extract category from label text.
        
        Args:
            label_text: Label text from the notice
            
        Returns:
            Corresponding NoticeCategory
        """
        category_mapping = {
            '통제안내': NoticeCategory.TRAFFIC_CONTROL,
            '버스안내': NoticeCategory.BUS,
            '정책안내': NoticeCategory.POLICY,
            '기상안내': NoticeCategory.WEATHER,
            '기타안내': NoticeCategory.ETC
        }
        
        for key, category in category_mapping.items():
            if key in label_text:
                return category
        
        return NoticeCategory.ETC
    
    async def get_notices_by_category(
        self, 
        category: NoticeCategory, 
        page: int = 1,
        per_page: int = 10
    ) -> List[Notice]:
        """Get notices by category with pagination."""
        try:
            # 크롤링 시작
            driver = self._get_driver()
            
            # Navigate to the notice list page
            notice_url = f"{self.base_url}/notice/openNoticeList.do"
            # 페이지 로드
            driver.get(notice_url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "notiList"))
            )
            # 페이지 로드 완료
            
            # Click on the appropriate tab if not ALL
            if category != NoticeCategory.ALL:
                tab_id = f"tab-{category.value}"
                try:
                    # 탭은 <li> 요소이므로 JavaScript 함수를 직접 호출
                    js_script = f"fn_getNoticeTabList('{category.value}', 1);"
                    driver.execute_script(js_script)
                    print(f"🎯 탭 전환: {category.value}")
                    
                    # Wait for the content to refresh
                    await asyncio.sleep(1.0)  # 탭 전환 후 데이터 로딩 대기
                except Exception as e:
                    print(f"⚠️  탭 전환 실패: {str(e)}, 전체 데이터로 진행")
                    pass  # Continue with ALL category
            
            # Navigate to the requested page if not page 1
            if page > 1:
                try:
                    # Find and click the pagination link
                    pagination_link = driver.find_element(By.XPATH, f"//a[text()='{page}']")
                    driver.execute_script("arguments[0].click();", pagination_link)
                    
                    # Wait for the content to refresh
                    await asyncio.sleep(0.5)  # ⚡ 2초 → 0.5초로 단축
                except NoSuchElementException:
                    pass  # Return empty if page doesn't exist
            
            # Extract notices from the table
            notices = []
            try:
                notice_rows = driver.find_elements(By.CSS_SELECTOR, "#notiList tr")
                
                for i, row in enumerate(notice_rows):
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 5:
                            continue
                        
                        # Extract data from cells
                        notice_id = cells[0].text.strip()
                        title_cell = cells[1]
                        attachment_cell = cells[2]
                        date_str = cells[3].text.strip()
                        view_count_str = cells[4].text.strip()
                        
                        # Extract title and category
                        title_link = title_cell.find_element(By.TAG_NAME, "a")
                        full_title = title_link.text.strip()
                        
                        # Extract category from label if exists
                        notice_category = NoticeCategory.ETC
                        try:
                            label_element = title_cell.find_element(By.CSS_SELECTOR, ".label")
                            label_text = label_element.text.strip()
                            notice_category = self._extract_category_from_label(label_text)
                            
                            # Remove category label from title
                            full_title = re.sub(r'^[^\n]*\n', '', full_title).strip()
                        except NoSuchElementException:
                            pass
                        
                        # Check for attachment
                        has_attachment = False
                        try:
                            attachment_cell.find_element(By.CSS_SELECTOR, "img[alt*='첨부파일']")
                            has_attachment = True
                        except NoSuchElementException:
                            pass
                        
                        # Parse date and view count
                        created_date = self._parse_date(date_str)
                        try:
                            view_count = int(view_count_str.replace(',', ''))
                        except ValueError:
                            view_count = 0
                        
                        notice = Notice(
                            id=notice_id,
                            title=full_title,
                            category=notice_category,
                            created_date=created_date,
                            view_count=view_count,
                            has_attachment=has_attachment
                        )
                        notices.append(notice)
                        
                        # Limit results according to per_page
                        if len(notices) >= per_page:
                            break
                            
                    except Exception as e:
                        # Skip problematic rows
                        continue
                        
            except NoSuchElementException:
                pass  # No notices found
            
            return notices
            
        except Exception as e:
            raise Exception(f"Failed to get notices: {str(e)}")
    
    async def get_notice_detail(self, notice_id: str) -> Optional[Notice]:
        """Get notice detail by ID."""
        try:
            driver = self._get_driver()
            
            # Try to find the notice in different categories
            base_notice = None
            categories_to_try = [
                NoticeCategory.TRAFFIC_CONTROL,
                NoticeCategory.BUS,
                NoticeCategory.POLICY,
                NoticeCategory.WEATHER,
                NoticeCategory.ETC
            ]
            
            for category in categories_to_try:
                try:
                    notices = await self.get_notices_by_category(category, page=1, per_page=20)
                    for notice in notices:
                        if notice.id == notice_id:
                            base_notice = notice
                            break
                    if base_notice:
                        break
                except Exception:
                    continue
            
            # If still not found, try more pages in traffic control (most common)
            if not base_notice:
                try:
                    for page in range(2, 6):  # Search up to page 5 in traffic control
                        notices = await self.get_notices_by_category(NoticeCategory.TRAFFIC_CONTROL, page=page, per_page=20)
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
                # Create a minimal notice object if we can't find it in the list
                # We'll get the content anyway
                from datetime import datetime
                base_notice = Notice(
                    id=notice_id,
                    title=f"공지사항 {notice_id}",  # Placeholder title
                    category=NoticeCategory.ETC,  # Default category
                    created_date=datetime.now(),  # Current date as fallback
                    view_count=0,
                    has_attachment=False
                )
            
            # Navigate to notice list page first (where the JavaScript function is defined)
            list_url = f"{self.base_url}/notice/openNoticeList.do"
            driver.get(list_url)
            
            # Wait for page to load (reduced to 0.3s)
            await asyncio.sleep(0.3)
            
            # Now try to execute the JavaScript function
            js_script = f"fn_goNotiView('02', '{notice_id}');"
            try:
                driver.execute_script(js_script)
                
                # Wait for navigation to detail page (reduced from 5s to 2s)
                await asyncio.sleep(2)
                
            except Exception as js_error:
                # Alternative approach: Direct URL construction
                possible_urls = [
                    f"{self.base_url}/notice/openNoticeView.do?bdwrSeq={notice_id}&blbdDivCd=02",
                    f"{self.base_url}/notice/openNoticeView.do?bdwrSeq={notice_id}",
                    f"{self.base_url}/notice/openNoticeView.do?seq={notice_id}&divCd=02",
                    f"{self.base_url}/notice/openNoticeView.do?noticeId={notice_id}"
                ]
                
                for url in possible_urls:
                    try:
                        driver.get(url)
                        await asyncio.sleep(0.2)  # ⚡ 극도로 단축
                        
                        # Check if we got valid content
                        if "공지사항" in driver.title or notice_id in driver.page_source:
                            break
                    except Exception:
                        continue
            
            # Extract content
            content = ""
            
            try:
                # TOPIS 사이트 구조에 맞는 셀렉터들
                content_selectors = [
                    "#brdContents",  # 메인 콘텐츠 ID
                    ".dtl-body",     # 상세 내용 클래스
                    ".col-xs-12.dtl-body.clearb",  # 전체 클래스 구조
                    ".board-content",
                    ".content-area"
                ]
                
                for selector in content_selectors:
                    try:
                        content_element = driver.find_element(By.CSS_SELECTOR, selector)
                        content = content_element.text.strip()
                        if content and len(content) > 10:  # 의미있는 내용이 있는지 확인
                            break
                    except NoSuchElementException:
                        continue
                
                # 여전히 내용이 없다면 HTML을 가져와서 정리
                if not content or len(content) < 10:
                    try:
                        content_element = driver.find_element(By.CSS_SELECTOR, "#brdContents")
                        # HTML 태그 제거하고 텍스트만 추출
                        content = content_element.get_attribute('innerText') or content_element.text
                        if not content:
                            content = content_element.get_attribute('innerHTML')
                            # 간단한 HTML 태그 제거
                            import re
                            content = re.sub(r'<[^>]+>', '', content)
                            content = re.sub(r'\s+', ' ', content).strip()
                    except NoSuchElementException:
                        pass
                    
                # 최후의 수단: 페이지 전체에서 본문 추출 시도
                if not content or len(content) < 10:
                    try:
                        # 페이지 제목 근처에서 본문 찾기
                        body_elements = driver.find_elements(By.CSS_SELECTOR, "div[class*='content'], div[class*='body'], div[id*='content']")
                        for elem in body_elements:
                            elem_text = elem.text.strip()
                            if len(elem_text) > 50:  # 충분한 내용이 있는 요소
                                content = elem_text
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
                content=content
            )
                
        except Exception as e:
            print(f"❌ DEBUG: Outer exception: {str(e)}")
            raise Exception(f"Failed to get notice detail: {str(e)}")
    
    async def get_total_pages(self, category: NoticeCategory) -> int:
        """Get total number of pages for a category."""
        try:
            driver = self._get_driver()
            
            # Navigate to the notice list page
            notice_url = f"{self.base_url}/notice/openNoticeList.do"
            driver.get(notice_url)
            
            # Wait for the page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "notiList"))
            )
            
            # Click on the appropriate tab if not ALL
            if category != NoticeCategory.ALL:
                try:
                    # 탭은 <li> 요소이므로 JavaScript 함수를 직접 호출
                    js_script = f"fn_getNoticeTabList('{category.value}', 1);"
                    driver.execute_script(js_script)
                    print(f"🎯 총 페이지 확인을 위한 탭 전환: {category.value}")
                    
                    # Wait for the content to refresh
                    await asyncio.sleep(1.0)  # 탭 전환 후 데이터 로딩 대기
                except Exception as e:
                    print(f"⚠️  탭 전환 실패: {str(e)}, 전체 데이터로 진행")
                    pass
            
            # Extract total pages from pagination
            try:
                # Look for the "끝" (End) button which contains the total pages
                end_link = driver.find_element(By.XPATH, "//a[contains(@onclick, 'fn_getNoticeList') and span[text()='끝']]")
                onclick_value = end_link.get_attribute('onclick')
                
                # Extract page number from onclick function
                match = re.search(r'fn_getNoticeList\((\d+)\)', onclick_value)
                if match:
                    return int(match.group(1))
                
                # Fallback: count pagination links
                page_links = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'fn_getNoticeList') and not(span)]")
                page_numbers = []
                
                for link in page_links:
                    try:
                        page_num = int(link.text.strip())
                        page_numbers.append(page_num)
                    except ValueError:
                        continue
                
                return max(page_numbers) if page_numbers else 1
                
            except NoSuchElementException:
                return 1
                
        except Exception as e:
            raise Exception(f"Failed to get total pages: {str(e)}")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self._close_driver()
