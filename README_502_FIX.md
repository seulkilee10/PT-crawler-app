# 502 Bad Gateway 오류 해결 방법

## 문제 원인
Render.com 배포 환경에서 Selenium WebDriver가 Chrome 브라우저를 찾을 수 없어서 502 오류가 발생했습니다.

## 해결한 내용

### 1. WebDriver Manager 적용
- `SeleniumNoticeRepository`와 `SeleniumIctrRepository`에서 `webdriver-manager` 사용
- Chrome Driver를 자동으로 관리하도록 변경
- Chrome 바이너리 경로를 자동으로 감지하도록 개선

### 2. Chrome 설치 스크립트 추가
- `render_install.sh`: Render.com에서 Chrome과 필요한 의존성 설치
- Chrome 바이너리 자동 탐지 로직 추가

### 3. 배포 설정 개선
- `render.yaml`: Chrome 설치 빌드 명령어 추가
- 환경 변수로 Chrome 바이너리 경로 설정
- Gunicorn 타임아웃 300초로 증가

### 4. 에러 핸들링 개선
- WebDriver 초기화 실패시 적절한 502 에러 반환
- 사용자에게 명확한 에러 메시지 제공

## 배포 후 확인사항

1. **Chrome 설치 확인**:
   - Render 배포 로그에서 Chrome 설치 성공 확인
   - `✅ Chrome 설치 완료` 메시지 확인

2. **WebDriver 초기화 확인**:
   - 크롤링 시도시 `✅ Chrome WebDriver 초기화 완료` 메시지 확인
   - 502 대신 정상 응답 또는 다른 구체적인 에러 메시지

3. **메모리 사용량**:
   - 무료 플랜 메모리 제한(512MB) 고려
   - 필요시 유료 플랜으로 업그레이드

## 추가 문제 해결

만약 여전히 문제가 발생한다면:

1. **Chrome 설치 실패**:
   ```bash
   # render_install.sh의 Chrome 설치 부분 수정 필요
   # 수동으로 설치 명령어 확인
   ```

2. **메모리 부족**:
   - Chrome 옵션을 더 공격적으로 설정
   - `--memory-pressure-off` 옵션 추가 고려

3. **권한 문제**:
   - `--no-sandbox` 옵션이 적용되었는지 확인
   - Render의 컨테이너 권한 제한 고려

## 변경된 주요 파일
- `src/infrastructure/selenium_notice_repository.py`
- `src/infrastructure/selenium_ictr_repository.py`
- `src/interface_adapters/web_server.py`
- `render.yaml`
- `render_install.sh` (새로 추가)

이제 재배포 후 크롤링이 정상적으로 작동해야 합니다.
