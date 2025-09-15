"""
Flask web server with Board-style UI for TOPIS notice crawler.
"""
import asyncio
import json
import os
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template_string, Response
from flask_cors import CORS

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.application.notice_crawler_service import NoticeCrawlerService
from src.application.word_export_service import WordExportService
from src.domain.notice import NoticeCategory
from src.domain.date_filter import DateFilter
from src.infrastructure.selenium_notice_repository import SeleniumNoticeRepository


app = Flask(__name__)
CORS(app)

# 글로벌 서비스 인스턴스
crawler_service = None
word_service = WordExportService()

# 공지사항 캐시 (메모리 기반)
notice_cache = {}  # {notice_id: notice_data}


def get_crawler_service():
    """크롤러 서비스 인스턴스 가져오기."""
    global crawler_service
    if crawler_service is None:
        repository = SeleniumNoticeRepository()
        crawler_service = NoticeCrawlerService(repository)
    return crawler_service


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


@app.route('/favicon.ico')
def favicon():
    """Favicon 핸들러 - 브라우저 404 오류 방지."""
    favicon_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    return Response(favicon_data, mimetype='image/png')


@app.route('/')
def index():
    """메인 웹 인터페이스 - 게시판 스타일 UI."""
    return render_template_string("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚗 TOPIS 공지사항 게시판</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
            background: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 10px 15px;
        }
        
        /* 헤더 - 컴팩트 */
        .header {
            background: #fff;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            color: #2c5aa0;
            font-size: 1.4rem;
            margin: 0;
            font-weight: 600;
        }
        
        .header-subtitle {
            color: #666;
            font-size: 0.8rem;
            margin-top: 2px;
        }
        
        /* 검색/필터 영역 - 헤더에 통합 */
        .search-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .form-group {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .form-group label {
            font-size: 0.8rem;
            font-weight: 500;
            color: #666;
            white-space: nowrap;
        }
        
        .form-group input {
            padding: 10px 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.9rem;
            width: 160px;
            min-width: 160px;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #2c5aa0;
        }
        
        .search-btn {
            background: #2c5aa0;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .search-btn:hover {
            background: #1e3f73;
        }
        
        /* 게시판 - 컴팩트 */
        .board-section {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .board-header {
            background: #2c5aa0;
            color: white;
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .board-title {
            font-size: 1rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .total-count {
            background: rgba(255,255,255,0.2);
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        
        /* 테이블 */
        .board-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .board-table thead {
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }
        
        .board-table th {
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            font-size: 0.85rem;
            border-right: 1px solid #dee2e6;
        }
        
        .board-table th:last-child {
            border-right: none;
        }
        
        .board-table th.col-no { width: 80px; text-align: center; }
        .board-table th.col-category { width: 100px; text-align: center; }
        .board-table th.col-title { width: auto; }
        .board-table th.col-date { width: 120px; text-align: center; }
        .board-table th.col-views { width: 80px; text-align: center; }
        .board-table th.col-attach { width: 60px; text-align: center; }
        .board-table th.col-actions { width: 120px; text-align: center; }
        
        .board-table tbody tr {
            border-bottom: 1px solid #dee2e6;
            transition: background-color 0.2s;
        }
        
        .board-table tbody tr:hover {
            background: #f8f9fa;
        }
        
        .board-table td {
            padding: 8px;
            vertical-align: middle;
            font-size: 0.85rem;
        }
        
        .board-table td.col-no {
            text-align: center;
            font-weight: 600;
            color: #666;
        }
        
        .board-table td.col-category {
            text-align: center;
        }
        
        .board-table td.col-title {
            font-weight: 500;
        }
        
        .board-table td.col-date {
            text-align: center;
            color: #666;
            font-size: 0.85rem;
        }
        
        .board-table td.col-views {
            text-align: center;
            color: #666;
            font-size: 0.85rem;
        }
        
        .board-table td.col-attach {
            text-align: center;
        }
        
        .board-table td.col-actions {
            text-align: center;
        }
        
        /* 카테고리 배지 */
        .category-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-align: center;
            white-space: nowrap;
        }
        
        .category-traffic {
            background: #fff5f5;
            color: #e53e3e;
            border: 1px solid #fed7d7;
        }
        
        .category-bus {
            background: #ebf8ff;
            color: #3182ce;
            border: 1px solid #bee3f8;
        }
        
        .category-policy {
            background: #faf5ff;
            color: #805ad5;
            border: 1px solid #e9d8fd;
        }
        
        .category-weather {
            background: #f0fff4;
            color: #38a169;
            border: 1px solid #c6f6d5;
        }
        
        .category-etc {
            background: #f7fafc;
            color: #718096;
            border: 1px solid #e2e8f0;
        }
        
        /* 아이콘 */
        .attach-icon {
            color: #666;
            font-size: 16px;
        }
        
        .attach-yes {
            color: #3182ce;
        }
        
        /* 액션 버튼 */
        .action-btn {
            background: #2c5aa0;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .action-btn:hover {
            background: #1e3f73;
        }
        
        /* 로딩 */
        .loading {
            display: none;
            text-align: center;
            padding: 60px;
            background: #fff;
            border-radius: 12px;
            margin-top: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #2c5aa0;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 초기 안내 화면 */
        .welcome-state {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
        }
        
        .welcome-icon {
            font-size: 3rem;
            margin-bottom: 20px;
        }
        
        .welcome-state h3 {
            color: #2c5aa0;
            font-size: 1.5rem;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        .welcome-state p {
            color: #666;
            font-size: 1rem;
            margin-bottom: 25px;
            line-height: 1.6;
        }
        
        .welcome-tips {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 15px;
            max-width: 800px;
            margin: 0 auto;
        }
        
        .tip-item {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 10px 15px;
            font-size: 0.85rem;
            color: #495057;
            flex: 1;
            min-width: 200px;
        }
        
        /* 빈 상태 */
        .empty-state {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
            padding: 60px;
            color: #666;
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        /* 반응형 */
        @media (max-width: 768px) {
            .container {
                padding: 5px 10px;
            }
            
            .header {
                flex-direction: column;
                gap: 10px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 1.2rem;
            }
            
            .search-form {
                flex-wrap: wrap;
                justify-content: center;
                gap: 8px;
            }
            
            .form-group input {
                width: 140px;
                min-width: 140px;
                font-size: 16px; /* iOS zoom 방지 */
            }
            
            .board-table {
                font-size: 0.8rem;
            }
            
            .board-table th,
            .board-table td {
                padding: 8px 6px;
            }
            
            /* 모바일에서 일부 컬럼 숨김 */
            .board-table th.col-views,
            .board-table td.col-views,
            .board-table th.col-attach,
            .board-table td.col-attach {
                display: none;
            }
            
            /* 환영 화면 모바일 최적화 */
            .welcome-state {
                padding: 25px 15px;
            }
            
            .welcome-state h3 {
                font-size: 1.2rem;
            }
            
            .welcome-tips {
                flex-direction: column;
                gap: 10px;
            }
            
            .tip-item {
                min-width: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 헤더 -->
        <div class="header">
            <div>
                <h1>🚌 대중교통 공지왕</h1>
                <div class="header-subtitle">TOPIS 공지사항 간편 조회</div>
            </div>
            <div class="search-form">
                <div class="form-group">
                    <label for="startDate">시작일</label>
                    <input type="date" id="startDate">
                </div>
                <div class="form-group">
                    <label for="endDate">종료일</label>
                    <input type="date" id="endDate">
                </div>
                <button class="search-btn" onclick="searchNotices()">검색</button>
            </div>
        </div>
        
        <!-- 로딩 -->
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>공지사항을 불러오는 중입니다...</p>
        </div>
        
        <!-- 초기 안내 -->
        <div class="welcome-state" id="welcomeState">
            <div class="welcome-icon">🚌</div>
            <h3>대중교통 공지왕에 오신 것을 환영합니다!</h3>
            <p>원하시는 날짜 범위를 설정하고 <strong>검색</strong> 버튼을 눌러 공지사항을 조회하세요.</p>
            <div class="welcome-tips">
                <div class="tip-item">📅 기본값은 최근 1주일로 설정되어 있습니다</div>
                <div class="tip-item">📄 Word 파일로 개별 다운로드가 가능합니다</div>
                <div class="tip-item">🔍 통제안내, 버스안내 등 모든 카테고리를 한번에 조회합니다</div>
            </div>
        </div>

        <!-- 게시판 -->
        <div class="board-section" id="boardSection" style="display: none;">
            <div class="board-header">
                <div class="board-title">📋 공지사항 목록</div>
                <div class="total-count" id="totalCount">총 0건</div>
            </div>
            
            <table class="board-table">
                <thead>
                    <tr>
                        <th class="col-no">번호</th>
                        <th class="col-category">구분</th>
                        <th class="col-title">제목</th>
                        <th class="col-date">등록일</th>
                        <th class="col-views">조회</th>
                        <th class="col-attach">첨부</th>
                        <th class="col-actions">다운로드</th>
                    </tr>
                </thead>
                <tbody id="noticeTableBody">
                    <!-- 데이터가 여기에 동적으로 삽입됩니다 -->
                </tbody>
            </table>
        </div>
        
        <!-- 빈 상태 -->
        <div class="empty-state" id="emptyState" style="display: none;">
            <div class="empty-state-icon">📭</div>
            <p>검색 조건에 맞는 공지사항이 없습니다.</p>
        </div>
    </div>

    <script>
        // 오늘 날짜로 기본값 설정
        const today = new Date().toISOString().split('T')[0];
        const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        document.getElementById('endDate').value = today;
        document.getElementById('startDate').value = lastWeek;
        
        let currentNotices = [];
        
        // 카테고리별 배지 생성
        function getCategoryBadge(category) {
            const categoryMap = {
                '통제안내': { class: 'category-traffic', text: '통제안내' },
                '버스안내': { class: 'category-bus', text: '버스안내' },
                '정책안내': { class: 'category-policy', text: '정책안내' },
                '기상안내': { class: 'category-weather', text: '기상안내' },
                '기타안내': { class: 'category-etc', text: '기타안내' }
            };
            
            const categoryInfo = categoryMap[category] || { class: 'category-etc', text: category };
            return `<span class="category-badge ${categoryInfo.class}">${categoryInfo.text}</span>`;
        }
        
        // 공지사항 검색
        async function searchNotices() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            
            // UI 상태 변경
            document.getElementById('welcomeState').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            document.getElementById('boardSection').style.display = 'none';
            document.getElementById('emptyState').style.display = 'none';
            
            try {
                const response = await fetch('/api/crawl', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        category: 'all',
                        start_date: startDate,
                        end_date: endDate,
                        max_pages: 3,
                        with_content: false
                    })
                });
                
                const result = await response.json();
                
                if (result.success && result.notices) {
                    currentNotices = result.notices;
                    displayNotices(result.notices);
                } else {
                    showEmptyState();
                }
            } catch (error) {
                alert('서버 오류: ' + error.message);
                showEmptyState();
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        // 공지사항 목록 표시
        function displayNotices(notices) {
            const tbody = document.getElementById('noticeTableBody');
            const totalCount = document.getElementById('totalCount');
            const boardSection = document.getElementById('boardSection');
            
            if (notices.length === 0) {
                showEmptyState();
                return;
            }
            
            // 총 개수 업데이트
            totalCount.textContent = `총 ${notices.length}건`;
            
            // 테이블 내용 생성
            tbody.innerHTML = notices.map((notice, index) => `
                <tr>
                    <td class="col-no">${notices.length - index}</td>
                    <td class="col-category">${getCategoryBadge(notice.category)}</td>
                    <td class="col-title">${notice.title}</td>
                    <td class="col-date">${notice.created_date.split('T')[0]}</td>
                    <td class="col-views">${notice.view_count.toLocaleString()}</td>
                    <td class="col-attach">
                        <span class="attach-icon ${notice.has_attachment ? 'attach-yes' : ''}">
                            ${notice.has_attachment ? '📎' : ''}
                        </span>
                    </td>
                    <td class="col-actions">
                        <button class="action-btn" onclick="downloadWord('${notice.id}')">
                            Word
                        </button>
                    </td>
                </tr>
            `).join('');
            
            boardSection.style.display = 'block';
        }
        
        // 빈 상태 표시
        function showEmptyState() {
            document.getElementById('welcomeState').style.display = 'none';
            document.getElementById('emptyState').style.display = 'block';
            document.getElementById('boardSection').style.display = 'none';
        }
        
        // Word 다운로드
        function downloadWord(noticeId) {
            window.open(`/api/export/word/${noticeId}`, '_blank');
        }
        
        // 엔터 키로도 검색 가능하게 설정
        document.getElementById('startDate').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') searchNotices();
        });
        
        document.getElementById('endDate').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') searchNotices();
        });
    </script>
</body>
</html>
    """)


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
        
        print(f"🔍 게시판 크롤링 시작:")
        print(f"   최대 페이지: {max_pages}")
        print(f"   시작 날짜: {start_date}")
        print(f"   종료 날짜: {end_date}")
        
        # 🚀 전체 데이터 크롤링
        from src.domain.notice import NoticeCategory
        all_notices = asyncio.run(service.crawl_category_fast(NoticeCategory.ALL, max_pages=max_pages))
        print(f"✅ 크롤링 완료: {len(all_notices)}개")
        
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
                'content': notice.content
            }
            notices.append(notice_dict)
        
        # 날짜 필터링
        if start_date or end_date:
            print(f"📅 날짜 필터링: {date_filter}")
            
            filtered_notices = []
            for notice in notices:
                notice_date = datetime.fromisoformat(notice['created_date'])
                if date_filter.is_in_range(notice_date):
                    filtered_notices.append(notice)
            
            notices = filtered_notices
            print(f"✅ 필터링 완료: {len(notices)}개")
        
        # 캐시에 저장
        global notice_cache
        for notice in notices:
            notice_cache[notice['id']] = notice
        
        # 임시 파일 저장
        temp_file = tempfile.mktemp(suffix='.json')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(notices, f, ensure_ascii=False, indent=2)
        
        app.config['LAST_CRAWL_FILE'] = temp_file
        
        return jsonify({
            'success': True,
            'count': len(notices),
            'notices': notices,
            'period': str(date_filter)
        })
        
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
            # 특정 공지사항
            global notice_cache
            notice_dict = None
            
            # 캐시에서 확인
            if notice_id in notice_cache:
                cached_notice = notice_cache[notice_id]
                print(f"⚡ 캐시에서 발견: {notice_id}")
                
                # 상세 내용이 필요하면 크롤링
                if cached_notice.get('content') and cached_notice['content'] not in [None, '', 'null']:
                    notice_dict = cached_notice
                else:
                    print(f"📄 상세 내용 크롤링 중...")
                    service = get_crawler_service()
                    notice_dict = asyncio.run(service.get_notice_with_content(notice_id))
                    
                    if notice_dict:
                        notice_cache[notice_id] = notice_dict
            else:
                print(f"🔍 새로운 크롤링: {notice_id}")
                service = get_crawler_service()
                notice_dict = asyncio.run(service.get_notice_with_content(notice_id))
                
                if notice_dict:
                    notice_cache[notice_id] = notice_dict
            
            if not notice_dict:
                return jsonify({'error': '공지사항을 찾을 수 없습니다.'}), 404
            
            # Word 문서 생성
            output_path = tempfile.mktemp(suffix='.docx')
            word_service.create_notice_document(notice_dict, output_path)
            
            # 파일명 생성
            safe_title = notice_dict['title'][:50]
            safe_title = "".join(c for c in safe_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"TOPIS_{safe_title}_{datetime.now().strftime('%Y%m%d')}.docx"
            
            return send_file(
                output_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_server(host='127.0.0.1', port=8081, debug=False):
    """게시판 웹 서버 실행."""
    print("🌐 TOPIS 게시판 크롤러 웹 서버가 시작됩니다!")
    print(f"🔗 브라우저에서 http://{host}:{port} 를 열어주세요.")
    print("🛑 서버를 중지하려면 Ctrl+C를 눌러주세요.")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
