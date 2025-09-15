# TOPIS 서울시 교통정보 공지사항 크롤러

서울시 교통정보센터(TOPIS) 공지사항을 크롤링하는 Python 프로그램입니다.

## 🏗️ 아키텍처

Clean Architecture 원칙에 따라 설계되었습니다:

- **Domain Layer**: 핵심 비즈니스 엔티티와 인터페이스
- **Application Layer**: 비즈니스 로직과 유스케이스
- **Infrastructure Layer**: 외부 시스템 연동 (Selenium 웹 드라이버)
- **Interface Layer**: CLI 인터페이스

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. Chrome 드라이버 설치

Selenium을 사용하므로 Chrome 브라우저와 ChromeDriver가 필요합니다.

macOS:
```bash
brew install --cask google-chrome
brew install chromedriver
```

### 3. 실행

#### 모든 카테고리 크롤링
```bash
python main.py crawl-all -o results/all_notices.json
```

#### 특정 카테고리 크롤링
```bash
# 버스 안내 크롤링
python main.py crawl-category 버스안내 -o results/bus_notices.json

# 통제 안내 크롤링 (영문으로도 가능)
python main.py crawl-category traffic -o results/traffic_notices.json
```

#### 상세 내용까지 크롤링 (느림)
```bash
python main.py crawl-category 통제안내 -o results/traffic_content.json --with-content
```

#### 특정 공지사항 상세보기
```bash
python main.py get-detail 5284 -o results/notice_5284.json
```

#### 통계 정보 확인
```bash
python main.py stats
```

## 📝 사용 가능한 카테고리

| 한국어 | 영어 | 설명 |
|--------|------|------|
| 전체 | all | 모든 공지사항 |
| 통제안내 | traffic | 교통 통제 관련 |
| 버스안내 | bus | 버스 운행 관련 |
| 정책안내 | policy | 교통 정책 관련 |
| 기상안내 | weather | 기상 관련 |
| 기타안내 | etc | 기타 공지사항 |

## 🎛️ 명령어 옵션

### 공통 옵션
- `--no-headless`: 브라우저 창을 표시하며 실행 (디버깅용)

### crawl-all 옵션
- `-o, --output`: 결과를 저장할 JSON 파일 경로 (필수)
- `--max-pages`: 카테고리별 최대 크롤링 페이지 수 (기본값: 5)

### crawl-category 옵션
- `-o, --output`: 결과를 저장할 JSON 파일 경로 (필수)
- `--max-pages`: 최대 크롤링 페이지 수 (기본값: 5)
- `--with-content`: 전체 내용까지 크롤링 (느림)

## 📊 출력 형식

크롤링 결과는 JSON 형식으로 저장됩니다:

```json
{
  "id": "5284",
  "title": "9/15(월)~9/27(토) 북한남삼거리 보도육교 철거공사에 따른 교통통제 안내",
  "category": "통제안내",
  "created_date": "2025-09-15T00:00:00",
  "view_count": 28,
  "has_attachment": true,
  "content": "상세 내용..."
}
```

## 🧪 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/unit/ -v

# 모든 테스트 실행
python -m pytest -v
```

## 🏗️ 프로젝트 구조

```
crowling/
├── src/
│   ├── domain/              # 도메인 레이어
│   │   ├── notice.py        # Notice 엔티티
│   │   └── notice_repository.py  # Repository 인터페이스
│   ├── infrastructure/      # 인프라 레이어
│   │   └── selenium_notice_repository.py  # Selenium 구현체
│   ├── application/         # 애플리케이션 레이어
│   │   └── notice_crawler_service.py      # 비즈니스 로직
│   └── interface_adapters/  # 인터페이스 레이어
│       └── cli.py          # CLI 인터페이스
├── tests/
│   ├── unit/               # 단위 테스트
│   └── integration/        # 통합 테스트
├── main.py                 # 메인 실행 파일
├── requirements.txt        # 의존성 목록
└── README.md              # 이 파일
```

## ⚠️ 주의사항

1. **웹사이트 부하**: 크롤링 간격을 두어 서버에 부하를 주지 않도록 합니다.
2. **ChromeDriver**: Chrome 브라우저와 ChromeDriver 버전이 호환되어야 합니다.
3. **네트워크**: 안정적인 인터넷 연결이 필요합니다.
4. **사이트 변경**: 웹사이트 구조가 변경되면 코드 수정이 필요할 수 있습니다.

## 🐛 문제 해결

### ChromeDriver 오류
```bash
# ChromeDriver 재설치
brew uninstall chromedriver
brew install chromedriver
```

### 권한 오류 (macOS)
```bash
# ChromeDriver 권한 허용
xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver
```

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
