"""
Flask web server with Apple-style UI for TOPIS notice crawler.
Refactored version with separated templates and static files.
"""
import asyncio
import json
import os
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template, Response
from flask_cors import CORS

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.application.notice_crawler_service import NoticeCrawlerService
from src.application.multi_site_crawler_service import MultiSiteCrawlerService
from src.application.word_export_service import WordExportService
from src.domain.notice import NoticeCategory, Site, SiteConfigManager
from src.domain.date_filter import DateFilter
from src.infrastructure.selenium_notice_repository import SeleniumNoticeRepository

# Flask 앱 설정 - 템플릿과 정적 파일 경로 지정
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
CORS(app)

# 글로벌 서비스 인스턴스
multi_site_service = None
legacy_crawler_service = None  # 기존 호환성용
word_service = WordExportService()

# 공지사항 캐시 (메모리 기반) - 사이트별로 관리
notice_cache = {}  # {site_notice_id: notice_data}


def get_multi_site_service():
    """다중 사이트 크롤러 서비스 인스턴스 가져오기."""
    global multi_site_service
    if multi_site_service is None:
        multi_site_service = MultiSiteCrawlerService()
    return multi_site_service


def get_crawler_service():
    """크롤러 서비스 인스턴스 가져오기 (기존 호환성)."""
    global legacy_crawler_service
    if legacy_crawler_service is None:
        repository = SeleniumNoticeRepository()
        legacy_crawler_service = NoticeCrawlerService(repository)
    return legacy_crawler_service


def parse_category(category_str: str) -> NoticeCategory:
    """문자열을 카테고리 enum으로 변환."""
    category_map = {
        'traffic': NoticeCategory.TRAFFIC_CONTROL,
        'bus': NoticeCategory.BUS,
        'policy': NoticeCategory.POLICY, 
        'weather': NoticeCategory.WEATHER,
        'etc': NoticeCategory.ETC,
        'all': NoticeCategory.ALL
    }
    return category_map.get(category_str, NoticeCategory.ALL)


def parse_site(site_str: str) -> Site:
    """문자열을 사이트 enum으로 변환."""
    site_map = {
        'topis': Site.TOPIS,
        'ictr': Site.ICTR
    }
    return site_map.get(site_str, Site.TOPIS)


@app.route('/favicon.ico')
def favicon():
    """Favicon 핸들러 - 브라우저 404 오류 방지."""
    favicon_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(favicon_data, mimetype='image/png')


@app.route('/api/sites')
def get_sites():
    """지원하는 사이트 목록과 설정 조회 API."""
    try:
        service = get_multi_site_service()
        configs = service.get_site_configs()
        
        return jsonify({
            'success': True,
            'sites': configs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/')
def index():
    """메인 웹 인터페이스 - 다중 사이트 크롤러 UI."""
    return render_template('index.html')


@app.route('/api/crawl', methods=['POST'])
def crawl_notices():
    """공지사항 크롤링 API."""
    try:
        data = request.get_json()
        
        category_str = data.get('category', 'all')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        max_pages = data.get('max_pages', 3)
        with_content = data.get('with_content', True)
        
        # 카테고리 변환
        category = parse_category(category_str)
        
        # 날짜 필터 생성
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
        date_filter = DateFilter(start_date=start_date, end_date=end_date)
        
        # 크롤링 실행
        service = get_crawler_service()
        
        print(f"🔍 DEBUG - 전체 공지사항 크롤링:")
        print(f"   최대 페이지: {max_pages}")
        print(f"   시작 날짜: {start_date}")
        print(f"   종료 날짜: {end_date}")
        
        # 🚀 항상 전체 데이터 크롤링 (카테고리 구분은 UI에서만)
        from src.domain.notice import NoticeCategory
        all_notices = asyncio.run(service.crawl_category_fast(NoticeCategory.ALL, max_pages=max_pages))
        print(f"🔍 DEBUG - 빠른 크롤링 완료: {len(all_notices)}개")
        
        # Notice 객체를 딕셔너리로 변환
        notices = []
        for notice in all_notices:
            notice_dict = {
                'id': notice.id,
                'title': notice.title,
                'category': service._get_category_name(notice.category),
                'created_date': notice.created_date.isoformat(),
                'view_count': notice.view_count,
                'has_attachment': notice.has_attachment,
                'content': notice.content  # 빠른 크롤링이므로 null
            }
            notices.append(notice_dict)
        
        print(f"🔍 DEBUG - 딕셔너리 변환 완료: {len(notices)}개 (content는 Word 다운로드 시 자동 추가됨)")
        
        # 날짜 필터링
        if start_date or end_date:
            print(f"🔍 DEBUG - 날짜 필터링 시작:")
            print(f"   필터 범위: {date_filter}")
            print(f"   필터링 전: {len(notices)}개")
            
            filtered_notices = []
            for notice in notices:
                # ISO 형태 직접 파싱
                notice_date = datetime.fromisoformat(notice['created_date'])
                is_valid = date_filter.is_in_range(notice_date)
                status = "✅ 포함" if is_valid else "❌ 제외"
                print(f"   {notice['id']} | {notice_date.strftime('%Y-%m-%d')} | {status}")
                
                if is_valid:
                    filtered_notices.append(notice)
            
            notices = filtered_notices
            print(f"🔍 DEBUG - 필터링 완료: {len(notices)}개")
        else:
            print(f"🔍 DEBUG - 날짜 필터링 없음: {len(notices)}개 그대로 사용")
        
        # ⚡ 공지사항 데이터를 캐시에 저장 (빠른 Word 다운로드를 위해)
        global notice_cache
        for notice in notices:
            notice_cache[notice['id']] = notice
        
        print(f"🔍 DEBUG - 최종 결과: {len(notices)}개 공지사항을 클라이언트에게 전송")
        
        # 임시로 notices 저장 (Word 내보내기에서 사용)
        temp_file = tempfile.mktemp(suffix='.json')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(notices, f, ensure_ascii=False, indent=2)
        
        # 세션에 임시 파일 경로 저장 (실제로는 Redis나 DB 사용 권장)
        app.config['LAST_CRAWL_FILE'] = temp_file
        
        response = jsonify({
            'success': True,
            'count': len(notices),
            'notices': notices,
            'period': str(date_filter)
        })
        
        # 캐시 방지 헤더 추가
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/crawl-multi', methods=['POST'])
def crawl_multi_site():
    """다중 사이트 공지사항 크롤링 API."""
    try:
        data = request.get_json()
        
        site_str = data.get('site', 'topis')
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        max_pages = data.get('max_pages', 3)
        with_content = data.get('with_content', False)
        
        # 사이트 변환
        site = parse_site(site_str)
        
        # 날짜 필터 생성
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
        date_filter = DateFilter(start_date=start_date, end_date=end_date)
        
        # 다중 사이트 서비스 사용
        service = get_multi_site_service()
        
        print(f"🌐 DEBUG - 다중 사이트 크롤링:")
        print(f"   사이트: {site.value}")
        print(f"   최대 페이지: {max_pages}")
        print(f"   시작 날짜: {start_date}")
        print(f"   종료 날짜: {end_date}")
        
        notices = []
        
        if site == Site.TOPIS:
            # TOPIS 크롤링
            category_str = data.get('category', 'all')
            category = parse_category(category_str)
            notices = asyncio.run(service.crawl_site(
                site=site,
                category=category,
                max_pages=max_pages,
                per_page=10
            ))
        elif site == Site.ICTR:
            # ICTR 크롤링 (검색 기능 포함)
            keyword = data.get('keyword', '')
            search_type = data.get('search_type', 'title')
            search_params = {
                'keyword': keyword,
                'search_type': search_type
            } if keyword else None
            
            notices = asyncio.run(service.crawl_site(
                site=site,
                max_pages=max_pages,
                per_page=10,
                search_params=search_params
            ))
            
        print(f"🌐 DEBUG - 크롤링 완료: {len(notices)}개")
        
        # Notice 객체를 딕셔너리로 변환
        notices_dicts = []
        for notice in notices:
            notice_dict = {
                'id': notice.id,
                'title': notice.title,
                'category': service._get_category_name(notice.category),
                'created_date': notice.created_date.isoformat(),
                'view_count': notice.view_count,
                'has_attachment': notice.has_attachment,
                'site': notice.site.value,
                'department': notice.department,
                'content': notice.content
            }
            notices_dicts.append(notice_dict)
        
        print(f"🌐 DEBUG - 딕셔너리 변환 완료: {len(notices_dicts)}개")
        
        # 날짜 필터링
        if start_date or end_date:
            print(f"🌐 DEBUG - 날짜 필터링 시작:")
            print(f"   필터 범위: {date_filter}")
            print(f"   필터링 전: {len(notices_dicts)}개")
            
            filtered_notices = []
            for notice in notices_dicts:
                notice_date = datetime.fromisoformat(notice['created_date'])
                is_valid = date_filter.is_in_range(notice_date)
                status = "✅ 포함" if is_valid else "❌ 제외"
                print(f"   {notice['id']} | {notice_date.strftime('%Y-%m-%d')} | {status}")
                
                if is_valid:
                    filtered_notices.append(notice)
            
            notices_dicts = filtered_notices
            print(f"🌐 DEBUG - 필터링 완료: {len(notices_dicts)}개")
        else:
            print(f"🌐 DEBUG - 날짜 필터링 없음: {len(notices_dicts)}개 그대로 사용")
        
        # 공지사항 데이터를 캐시에 저장 (사이트 정보 포함)
        global notice_cache
        for notice in notices_dicts:
            cache_key = f"{notice['site']}_{notice['id']}"
            notice_cache[cache_key] = notice
        
        print(f"🌐 DEBUG - 최종 결과: {len(notices_dicts)}개 공지사항을 클라이언트에게 전송")
        
        # 임시로 notices 저장 (Word 내보내기에서 사용)
        temp_file = tempfile.mktemp(suffix='.json')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(notices_dicts, f, ensure_ascii=False, indent=2)
        
        # 세션에 임시 파일 경로 저장
        app.config['LAST_CRAWL_FILE'] = temp_file
        
        response = jsonify({
            'success': True,
            'count': len(notices_dicts),
            'notices': notices_dicts,
            'period': str(date_filter),
            'site': site.value
        })
        
        # 캐시 방지 헤더 추가
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/export/word/<notice_id>')
def export_word(notice_id):
    """Word 문서 다운로드 API."""
    try:
        if notice_id == 'all':
            # 전체 공지사항을 하나의 문서로
            temp_file = app.config.get('LAST_CRAWL_FILE')
            if not temp_file or not os.path.exists(temp_file):
                return jsonify({'error': '먼저 크롤링을 수행해주세요.'}), 400
            
            with open(temp_file, 'r', encoding='utf-8') as f:
                notices = json.load(f)
            
            if not notices:
                return jsonify({'error': '공지사항이 없습니다.'}), 400
            
            # Word 문서 생성
            output_path = tempfile.mktemp(suffix='.docx')
            word_service.create_multiple_notices_document(notices, output_path)
            
            return send_file(
                output_path,
                as_attachment=True,
                download_name=f"TOPIS_공지사항_모음_{datetime.now().strftime('%Y%m%d')}.docx",
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        else:
            # ⚡ 특정 공지사항 - 캐시 먼저 확인
            global notice_cache
            notice_dict = None
            
            # notice_id 형식: "site_id" (예: "topis_5284", "ictr_1392")
            if '_' in notice_id:
                site_str, actual_id = notice_id.split('_', 1)
                site = parse_site(site_str)
            else:
                # 기존 호환성을 위해 기본값은 TOPIS
                site = Site.TOPIS
                actual_id = notice_id
            
            # 1단계: 캐시에서 확인 (즉시)
            cache_key = f"{site.value}_{actual_id}"
            if cache_key in notice_cache:
                cached_notice = notice_cache[cache_key]
                print(f"⚡ CACHE HIT: Found cached data for notice {cache_key}")
                
                # 캐시된 데이터에 content가 있는지 확인
                if cached_notice.get('content') and cached_notice['content'] not in [None, '', 'null']:
                    print(f"📄 CONTENT AVAILABLE: Using cached content")
                    notice_dict = cached_notice
                else:
                    print(f"📄 CONTENT MISSING: Fetching detailed content for Word export")
                    service = get_multi_site_service()
                    notice_dict = asyncio.run(service.get_notice_with_content(site, actual_id))
                    
                    # 상세 내용을 캐시에 업데이트
                    if notice_dict and notice_dict.get('content'):
                        notice_cache[cache_key] = notice_dict
                        print(f"💾 CACHE UPDATED: Content added to cache")
            
            # 2단계: 캐시에 없으면 크롤링 (느림)
            if not notice_dict:
                print(f"🔍 CACHE MISS: Crawling notice {cache_key}")
                service = get_multi_site_service()
                notice_dict = asyncio.run(service.get_notice_with_content(site, actual_id))
                
                # 크롤링 결과를 캐시에 저장
                if notice_dict:
                    notice_cache[cache_key] = notice_dict
            
            if not notice_dict:
                return jsonify({'error': '공지사항을 찾을 수 없습니다.'}), 404
            
            # Word 문서 생성
            output_path = tempfile.mktemp(suffix='.docx')
            word_service.create_notice_document(notice_dict, output_path)
            
            # 파일명 생성 (사이트별)
            safe_title = notice_dict['title'][:50]  # 제목 길이 제한
            safe_title = "".join(c for c in safe_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            site_name = "인천교통공사" if site == Site.ICTR else "TOPIS"
            filename = f"{site_name}_{safe_title}_{datetime.now().strftime('%Y%m%d')}.docx"
            
            return send_file(
                output_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_server(host='127.0.0.1', port=8080, debug=False):
    """웹 서버 실행."""
    print("🌐 TOPIS 크롤러 웹 서버가 시작됩니다!")
    print(f"🔗 브라우저에서 http://{host}:{port} 를 열어주세요.")
    print("🛑 서버를 중지하려면 Ctrl+C를 눌러주세요.")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
