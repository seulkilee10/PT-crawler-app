// 다중 사이트 크롤러 JavaScript

// 전역 변수
let currentSite = 'topis';

// DOM이 로드되면 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeDatePickers();
    changeSite(); // 초기 상태 설정
});

// 오늘 날짜로 기본값 설정 (범위를 6개월로 확장)
function initializeDatePickers() {
    const today = new Date().toISOString().split('T')[0];
    const sixMonthsAgo = new Date(Date.now() - 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    document.getElementById('endDate').value = today;
    document.getElementById('startDate').value = sixMonthsAgo;
}

// 사이트 변경 함수 (드롭다운)
function changeSite() {
    const selectedSite = document.getElementById('siteSelect').value;
    currentSite = selectedSite;
    
    // 사이트별 안내 메시지 변경
    const siteInfo = document.getElementById('siteInfo');
    
    if (selectedSite === 'ictr') {
        siteInfo.textContent = '🚇 인천교통공사: 최신 공지사항 수집';
    } else {
        siteInfo.textContent = '📊 TOPIS: 모든 카테고리 공지사항 수집';
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

// 크롤링 시작 함수
async function startCrawling() {
    console.log('🚀 startCrawling 시작');
    
    // 공통 설정 값들 가져오기
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const maxPages = parseInt(document.getElementById('maxPages').value);
    
    console.log('📋 크롤링 설정:', { currentSite, startDate, endDate, maxPages });
    
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
        requestData.keyword = '';
        requestData.search_type = 'title';  // 기본값으로 제목 검색
        
        loadingMessage = `🚇 인천교통공사 크롤링 중... ${maxPages}페이지 처리`;
    }
    
    console.log('📤 요청 데이터:', requestData);
    
    // UI 상태 변경
    document.querySelector('.primary-btn').disabled = true;
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    
    // 로딩 메시지 업데이트
    const loadingMsg = document.getElementById('loadingMessage');
    loadingMsg.textContent = loadingMessage + ' (Word 다운로드 시 상세 내용 자동 추가)';
    
    try {
        console.log('📡 서버에 요청 전송 중...');
        
        // AbortController로 타임아웃 설정 (2분)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        
        const response = await fetch('/api/crawl-multi', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify(requestData),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        console.log('📡 서버 응답 상태:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        console.log('🔄 JSON 파싱 중...');
        const result = await response.json();
        console.log('📦 서버 응답 데이터:', result);
        
        if (result.success) {
            console.log('✅ 크롤링 성공, 결과 표시 중...');
            displayResults(result);
        } else {
            console.error('❌ 크롤링 실패:', result.message);
            alert('크롤링 중 오류가 발생했습니다: ' + result.message);
        }
    } catch (error) {
        console.error('💥 크롤링 오류:', error);
        console.error('오류 상세:', error.stack);
        
        if (error.name === 'AbortError') {
            alert('서버 응답 시간이 초과되었습니다 (2분). 페이지 수를 줄이거나 다시 시도해주세요.');
        } else if (error instanceof TypeError && error.message.includes('fetch')) {
            alert('네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인하고 다시 시도해주세요.');
        } else {
            alert('서버와 통신 중 오류가 발생했습니다: ' + error.message);
        }
    } finally {
        console.log('🔄 UI 상태 복원 중...');
        // UI 상태 복원
        document.querySelector('.primary-btn').disabled = false;
        document.getElementById('loading').style.display = 'none';
    }
}

// 결과 표시 함수
function displayResults(result) {
    console.log('🎨 displayResults 시작, 데이터:', result);
    
    try {
        const resultsDiv = document.getElementById('results');
        const contentDiv = document.getElementById('resultContent');
        
        console.log('🔍 DOM 요소 확인:', { resultsDiv: !!resultsDiv, contentDiv: !!contentDiv });
    
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
    
        console.log('✏️ HTML 생성 완료, DOM 업데이트 중...');
        contentDiv.innerHTML = html;
        resultsDiv.style.display = 'block';
        
        console.log('📜 화면에 결과 표시 완료, 스크롤 이동 중...');
        // 결과로 스무스 스크롤
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        console.log('✅ displayResults 완료');
        
    } catch (error) {
        console.error('💥 displayResults 오류:', error);
        console.error('오류 상세:', error.stack);
        alert('결과 표시 중 오류가 발생했습니다: ' + error.message);
    }
}

// Word 다운로드 함수들
function downloadWord(siteNoticeId) {
    // siteNoticeId 형식: "site_id" (예: "topis_5284", "ictr_1392")  
    window.open(`/api/export/word/${siteNoticeId}`, '_blank');
}

function downloadAllWord() {
    window.open('/api/export/word/all', '_blank');
}
