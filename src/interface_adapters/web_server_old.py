"""
Flask web server with Apple-style UI for TOPIS notice crawler.
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
from src.application.multi_site_crawler_service import MultiSiteCrawlerService
from src.application.word_export_service import WordExportService
from src.domain.notice import NoticeCategory, Site, SiteConfigManager
from src.domain.date_filter import DateFilter
from src.infrastructure.selenium_notice_repository import SeleniumNoticeRepository


app = Flask(__name__)
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
    return render_template_string("""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌐 다중 사이트 교통정보 크롤러</title>
    <style>
        /* Apple Style UI */
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f7;
            min-height: 100vh;
            color: #1d1d1f;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px 16px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        
        .header h1 { 
            font-size: 1.5rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
        }
        
        .header p { 
            font-size: 0.9rem;
            color: #666;
            font-weight: 400;
        }
        
        .main-card {
            background: #ffffff;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid #e1e5e9;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        /* 컴팩트 설정 스타일 */
        .compact-settings {
            margin-bottom: 20px;
        }
        
        .setting-row {
            display: flex;
            gap: 20px;
            align-items: end;
            flex-wrap: wrap;
        }
        
        .setting-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
            min-width: 120px;
        }
        
        .setting-group label {
            font-size: 0.85rem;
            font-weight: 500;
            color: #333;
            white-space: nowrap;
        }
        
        .setting-group input,
        .setting-group select {
            padding: 8px 12px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            font-size: 13px;
            font-family: inherit;
            background: #ffffff;
            outline: none;
        }
        
        .setting-group input:focus,
        .setting-group select:focus {
            border-color: #007AFF;
            box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2);
        }
        
        .setting-group input[type="text"] {
            min-width: 150px;
        }
        
        .setting-group .primary-btn {
            margin-top: 22px; /* 라벨 높이 보정 */
            min-width: 100px;
        }
        
        .ictr-only {
            display: none;
        }
        
        .ictr-only.show {
            display: flex;
        }
        
        /* 정보 메시지 */
        .info-message {
            background: #f0f9ff;
            border: 1px solid #bfdbfe;
            border-radius: 6px;
            padding: 12px 16px;
            margin-bottom: 20px;
            font-size: 0.9rem;
            color: #1e40af;
        }
        
        .form-group {
            margin-bottom: 16px;
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: #333;
            font-size: 0.85rem;
        }
        
        input, select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            font-size: 13px;
            font-family: inherit;
            background: #ffffff;
            outline: none;
        }
        
        input:focus, select:focus {
            border-color: #007AFF;
            box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2);
        }
        
        .primary-btn {
            background: #007AFF;
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
        }
        
        .primary-btn:hover {
            background: #0051D0;
        }
        
        .primary-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .secondary-btn {
            background: #f8f9fa;
            color: #007AFF;
            border: 1px solid #d1d5db;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
        }
        
        .secondary-btn:hover {
            background: #e9ecef;
            border-color: #007AFF;
        }
        
        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e1e5e9;
        }
        
        .checkbox-wrapper:hover {
            background: #e9ecef;
        }
        
        input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: #34C759;
            cursor: pointer;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 60px 40px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            border: 1px solid rgba(0, 0, 0, 0.06);
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 3px solid rgba(0, 122, 255, 0.1);
            border-radius: 50%;
            border-top-color: #007AFF;
            margin: 0 auto 24px;
            /* 애니메이션은 아래 전역 설정에서 정의됨 */
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg) !important; }
            100% { transform: rotate(360deg) !important; }
        }
        
        .loading-message {
            color: #86868b;
            font-size: 1.1rem;
            font-weight: 500;
        }
        
        .results {
            display: none;
        }
        
        .stats-container {
            margin-bottom: 32px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background: #ffffff;
            border: 1px solid #e1e5e9;
            padding: 16px;
            border-radius: 4px;
            text-align: center;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        .stat-number {
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 4px;
            color: #1d1d1f;
            letter-spacing: -0.01em;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #86868b;
            font-weight: 500;
        }
        
        .notices-section {
            margin-top: 32px;
        }
        
        .notices-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid #e5e5e7;
        }
        
        .notices-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1d1d1f;
            margin: 0;
        }
        
        .notices-count {
            background: #f2f2f7;
            color: #86868b;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        /* 게시판 테이블 스타일 */
        .notices-table {
            width: 100%;
            border-collapse: collapse;
            background: #ffffff;
            border: 1px solid #e1e5e9;
        }
        
        .notices-table th {
            background: #f8f9fa;
            padding: 12px 8px;
            text-align: left;
            border-bottom: 2px solid #e1e5e9;
            font-size: 0.85rem;
            font-weight: 600;
            color: #495057;
        }
        
        .notices-table td {
            padding: 10px 8px;
            border-bottom: 1px solid #e9ecef;
            font-size: 0.85rem;
            vertical-align: middle;
        }
        
        .notices-table tr:hover {
            background: #f8f9fa;
        }
        
        .notices-table .title-cell {
            max-width: 400px;
        }
        
        .notices-table .title-link {
            color: #333;
            text-decoration: none;
            font-weight: 500;
        }
        
        .notices-table .title-link:hover {
            color: #007AFF;
            text-decoration: underline;
        }
        
        .notices-table .badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.7rem;
            font-weight: 500;
        }
        
        .notices-table .category-badge {
            background: #e3f2fd;
            color: #1976d2;
        }
        
        .notices-table .site-badge {
            background: #f3e5f5;
            color: #7b1fa2;
        }
        
        .notices-table .date-cell {
            white-space: nowrap;
            width: 100px;
        }
        
        .notices-table .meta-cell {
            white-space: nowrap;
            width: 120px;
        }
        
        .notices-table .action-cell {
            width: 100px;
            text-align: center;
        }
        
        .notice-header {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 10px;
        }
        
        .notice-title {
            font-weight: 600;
            font-size: 1.05rem;
            color: #1d1d1f;
            line-height: 1.4;
            flex: 1;
        }
        
        .category-chip {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
        }
        
        .category-traffic {
            background: #fee2e2;
            color: #dc2626;
        }
        
        .category-bus {
            background: #dbeafe;
            color: #2563eb;
        }
        
        .category-policy {
            background: #f3e8ff;
            color: #7c3aed;
        }
        
        .category-weather {
            background: #ecfdf5;
            color: #059669;
        }
        
        .category-etc {
            background: #f1f5f9;
            color: #64748b;
        }
        
        /* 사이트 배지 스타일 */
        .site-badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
        }
        
        .site-badge.topis {
            background: #eff6ff;
            color: #1d4ed8;
        }
        
        .site-badge.ictr {
            background: #f0fdf4;
            color: #16a34a;
        }
        
        .notice-meta {
            display: flex;
            align-items: center;
            gap: 16px;
            color: #86868b;
            font-size: 0.85rem;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        
        .meta-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .notice-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }
        
        .bulk-actions {
            text-align: center;
            margin-top: 30px;
            padding: 24px;
            background: #f9f9f9;
            border-radius: 12px;
            border: 1px solid #e5e5e5;
        }
        
        .empty-state {
            text-align: center;
            padding: 48px 32px;
            background: #fafafa;
            border: 1px solid #f0f0f0;
            border-radius: 12px;
            color: #86868b;
            font-size: 1rem;
            margin-top: 24px;
        }
        
        .empty-state-icon {
            font-size: 2.5rem;
            margin-bottom: 12px;
            opacity: 0.6;
        }
        
        .empty-state p {
            margin: 0;
            font-weight: 500;
        }
        
        @media (max-width: 768px) {
            .container { 
                padding: 20px 16px; 
            }
            
            .main-card {
                padding: 20px;
                border-radius: 12px;
            }
            
            /* 컴팩트 설정 모바일 대응 */
            .setting-row {
                flex-direction: column;
                gap: 16px;
                align-items: stretch;
            }
            
            .setting-group {
                min-width: 100%;
            }
            
            .setting-group input,
            .setting-group select {
                width: 100%;
            }
            
            .setting-group .primary-btn {
                margin-top: 16px;
                width: 100%;
                padding: 12px;
            }
            
            .stats-grid { 
                grid-template-columns: 1fr; 
                gap: 12px;
            }
            
            .stat-card {
                padding: 20px 16px;
            }
            
            .stat-number {
                font-size: 2rem;
            }
            
            .header h1 { 
                font-size: 1.3rem; 
            }
            
            .notices-header {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
            
            .notice-item {
                padding: 16px;
            }
            
            .notice-header {
                flex-direction: column;
                gap: 8px;
            }
            
            .category-chip {
                align-self: flex-start;
            }
            
            .notice-meta {
                flex-direction: column;
                gap: 8px;
                align-items: flex-start;
            }
            
            .notice-actions {
                justify-content: stretch;
            }
            
            .secondary-btn {
                width: 100%;
                padding: 12px 20px;
            }
            
            .empty-state {
                padding: 32px 24px;
            }
        }
        
        /* 모든 불필요한 애니메이션 제거 (스피너 제외) */
        *:not(.spinner) {
            transition: none !important;
            animation: none !important;
            transform: none !important;
        }
        
        /* 스피너는 예외적으로 애니메이션 허용 */
        .spinner {
            animation: spin 1s linear infinite !important;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg) !important; }
            100% { transform: rotate(360deg) !important; }
        }
        
        /* 기본적인 호버 효과는 색상 변경만 유지 */
        input:focus, select:focus {
            transition: border-color 0.15s ease !important;
        }
        
        .primary-btn:hover, .secondary-btn:hover {
            transition: background-color 0.15s ease !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 다중 사이트 크롤러</h1>
            <p>TOPIS와 인천교통공사 공지사항을 통합 수집하고 Word로 다운로드하세요</p>
        </div>
        
        <div class="main-card">
            <h2 class="section-title">🔍 크롤링 설정</h2>
            
            <!-- 한 줄 설정 -->
            <div class="compact-settings">
                <div class="setting-row">
                    <div class="setting-group">
                        <label>🌐 사이트</label>
                        <select id="siteSelect" onchange="changeSite()">
                            <option value="topis">🚗 TOPIS</option>
                            <option value="ictr">🚇 인천교통공사</option>
                        </select>
                    </div>
                    
                    <div class="setting-group">
                        <label>📅 시작일</label>
                        <input type="date" id="startDate">
                    </div>
                    
                    <div class="setting-group">
                        <label>📅 종료일</label>
                        <input type="date" id="endDate">
                    </div>
                    
                    <div class="setting-group">
                        <label>📄 페이지</label>
                        <select id="maxPages">
                            <option value="1" selected>1페이지</option>
                            <option value="2">2페이지</option>
                            <option value="3">3페이지</option>
                            <option value="5">5페이지</option>
                        </select>
                    </div>
                    
                    <div class="setting-group ictr-only" id="searchGroup" style="display: none;">
                        <label>🔍 검색어</label>
                        <input type="text" id="searchKeyword" placeholder="키워드">
                    </div>
                    
                    <div class="setting-group">
                        <button class="primary-btn" onclick="startCrawling()">🚀 크롤링</button>
                    </div>
                </div>
            </div>
            
            <!-- 간단한 안내 -->
            <div class="info-message">
                <span id="siteInfo">📊 TOPIS: 모든 카테고리 공지사항 수집</span>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-message" id="loadingMessage">공지사항을 수집하고 있습니다...</p>
        </div>
        
        <div class="results" id="results">
            <div class="main-card">
                <h2 class="section-title">📊 크롤링 결과</h2>
                <div id="resultContent"></div>
            </div>
        </div>
    </div>

    <script>
        // 전역 변수
        let currentSite = 'topis';
        
        // 오늘 날짜로 기본값 설정
        const today = new Date().toISOString().split('T')[0];
        const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        
        // 날짜 필드에 기본값 설정
        document.getElementById('endDate').value = today;
        document.getElementById('startDate').value = lastWeek;
        
        // 사이트 변경 함수 (드롭다운)
        function changeSite() {
            const selectedSite = document.getElementById('siteSelect').value;
            currentSite = selectedSite;
            
            // 사이트별 안내 메시지 변경
            const siteInfo = document.getElementById('siteInfo');
            const searchGroup = document.getElementById('searchGroup');
            
            if (selectedSite === 'ictr') {
                siteInfo.textContent = '🔍 인천교통공사: 검색어로 원하는 공지사항 수집';
                searchGroup.style.display = 'flex';
            } else {
                siteInfo.textContent = '📊 TOPIS: 모든 카테고리 공지사항 수집';
                searchGroup.style.display = 'none';
            }
        }
        
        // 카테고리별 chip 생성 함수
        function getCategoryChip(category) {
            const categoryMap = {
                '통제안내': { class: 'category-traffic', icon: '🚦', text: '통제안내' },
                '버스안내': { class: 'category-bus', icon: '🚌', text: '버스안내' },
                '정책안내': { class: 'category-policy', icon: '📋', text: '정책안내' },
                '기상안내': { class: 'category-weather', icon: '☁️', text: '기상안내' },
                '기타안내': { class: 'category-etc', icon: '📌', text: '기타안내' }
            };
            
            const categoryInfo = categoryMap[category] || { class: 'category-etc', icon: '📌', text: category };
            return `<span class="category-chip ${categoryInfo.class}">${categoryInfo.icon} ${categoryInfo.text}</span>`;
        }
        
        async function startCrawling() {
            // 공통 설정 값들 가져오기
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const maxPages = parseInt(document.getElementById('maxPages').value);
            
            // 현재 선택된 사이트에 따라 다른 파라미터 수집
            let requestData = {
                site: currentSite,
                with_content: false,  // 항상 빠른 크롤링 사용
                start_date: startDate,
                end_date: endDate,
                max_pages: maxPages
            };
            
            let loadingMessage;
            
            if (currentSite === 'topis') {
                requestData.category = 'all';  // 항상 전체 데이터
                loadingMessage = `🚗 TOPIS 크롤링 중... ${maxPages}페이지 처리`;
                
            } else if (currentSite === 'ictr') {
                const keyword = document.getElementById('searchKeyword').value;
                requestData.keyword = keyword;
                requestData.search_type = 'title';  // 기본값으로 제목 검색
                
                const keywordText = keyword ? ` "${keyword}"` : '';
                loadingMessage = `🚇 인천교통공사 크롤링 중...${keywordText} ${maxPages}페이지 처리`;
            }
            
            // UI 상태 변경
            document.querySelector('.primary-btn').disabled = true;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            // 로딩 메시지 업데이트
            const loadingMsg = document.getElementById('loadingMessage');
            loadingMsg.textContent = loadingMessage + ' (Word 다운로드 시 상세 내용 자동 추가)';
            
            try {
                const response = await fetch('/api/crawl-multi', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    displayResults(result);
                } else {
                    alert('크롤링 중 오류가 발생했습니다: ' + result.message);
                }
            } catch (error) {
                alert('서버와 통신 중 오류가 발생했습니다: ' + error.message);
            } finally {
                // UI 상태 복원
                document.querySelector('.primary-btn').disabled = false;
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        function displayResults(result) {
            const resultsDiv = document.getElementById('results');
            const contentDiv = document.getElementById('resultContent');
            
            let html = `
                <div class="stats-container">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">${result.count}</div>
                            <div class="stat-label">수집된 공지사항</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">${result.period}</div>
                            <div class="stat-label">검색 기간</div>
                        </div>
                    </div>
                </div>
            `;
            
            if (result.notices && result.notices.length > 0) {
                html += `
                    <div class="notices-section">
                        <div class="notices-header">
                            <h3 class="notices-title">📋 공지사항 목록</h3>
                            <span class="notices-count">${result.count}개</span>
                        </div>
                        <table class="notices-table">
                            <thead>
                                <tr>
                                    <th>사이트</th>
                                    <th>제목</th>
                                    <th>카테고리</th>
                                    <th>작성일</th>
                                    <th>메타정보</th>
                                    <th>첨부</th>
                                    <th>다운로드</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                result.notices.forEach(notice => {
                    // 사이트별 메타 정보
                    let metaInfo = '';
                    if (notice.site === 'ictr') {
                        metaInfo = notice.department || '작성부서 미상';
                    } else {
                        metaInfo = `${notice.view_count}회`;
                    }
                    
                    // 사이트 배지
                    const siteBadge = notice.site === 'ictr' ? 
                        '<span class="badge site-badge">🚇 인천교통공사</span>' : 
                        '<span class="badge site-badge">🚗 TOPIS</span>';
                    
                    // 카테고리 배지 (기존 함수 재활용하되 간단하게)
                    const categoryBadge = `<span class="badge category-badge">${notice.category}</span>`;
                    
                    html += `
                        <tr>
                            <td class="site-cell">${siteBadge}</td>
                            <td class="title-cell">
                                <a href="#" class="title-link" title="${notice.title}">
                                    ${notice.title.length > 60 ? notice.title.substring(0, 60) + '...' : notice.title}
                                </a>
                            </td>
                            <td class="category-cell">${categoryBadge}</td>
                            <td class="date-cell">${notice.created_date.split('T')[0]}</td>
                            <td class="meta-cell">${metaInfo}</td>
                            <td class="attachment-cell">
                                ${notice.has_attachment ? '📎' : ''}
                            </td>
                            <td class="action-cell">
                                <button class="secondary-btn" onclick="downloadWord('${notice.site}_${notice.id}')">
                                    다운로드
                                </button>
                            </td>
                        </tr>
                    `;
                });
                
                html += `
                            </tbody>
                        </table>
                    </div>
                `;
                
                // 전체 다운로드 버튼
                html += `
                    <div class="bulk-actions">
                        <button class="primary-btn" onclick="downloadAllWord()">
                            📑 전체를 하나의 Word 파일로 다운로드
                        </button>
                    </div>
                `;
            } else {
                html += `
                    <div class="empty-state">
                        <div class="empty-state-icon">😔</div>
                        <p>해당 조건에 맞는 공지사항이 없습니다.</p>
                    </div>
                `;
            }
            
            contentDiv.innerHTML = html;
            resultsDiv.style.display = 'block';
            
            // 결과로 스무스 스크롤
            resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        function downloadWord(siteNoticeId) {
            // siteNoticeId 형식: "site_id" (예: "topis_5284", "ictr_1392")  
            window.open(`/api/export/word/${siteNoticeId}`, '_blank');
        }
        
        function downloadAllWord() {
            window.open('/api/export/word/all', '_blank');
        }
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
