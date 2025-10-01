## 빈번한 실수와 해결 방법

### 2025-09-19 - viewport meta 태그 경고 관련

#### 문제 상황
- 브라우저 개발자 도구에서 "A 'viewport' meta element was not specified" 경고 발생
- 실제로는 base.html에 `<meta name="viewport" content="width=device-width, initial-scale=1.0">` 태그가 올바르게 설정되어 있음

#### 원인 분석
1. **False Positive**: 브라우저 개발자 도구의 잘못된 경고
2. **캐시 문제**: 브라우저 캐시로 인한 이전 버전 페이지 표시
3. **네트워크 지연**: 페이지 로딩 중 일시적인 meta 태그 인식 실패

#### 해결 방법
1. **하드 새로고침**: Ctrl+Shift+R (또는 Cmd+Shift+R)로 캐시 무시 새로고침
2. **개발자 도구 네트워크 탭**: Disable cache 옵션 활성화
3. **실제 동작 확인**: 모바일 반응형이 정상 작동하는지 확인

#### 재발 방지책
1. **정기적인 확인**: viewport meta 태그가 base.html의 head 섹션 상단에 위치하는지 확인
2. **테스트 자동화**: Puppeteer MCP로 모바일/데스크톱 반응형 테스트 수행
3. **브라우저 다양성**: Chrome, Firefox, Safari 등 다양한 브라우저에서 확인
4. **실제 기능 우선**: 경고보다는 실제 반응형 동작이 정상적인지 확인

### 2025-09-19 - CSRF 토큰 세션 누락 오류 해결

#### 문제 상황
- 회원가입/로그인 시 `{"detail":"CSRF: Missing session"}` 403 오류 발생
- 브라우저 개발자도구에서 `POST http://localhost:8000/auth/signup 403 (Forbidden)` 확인

#### 원인 분석
1. **CSRF 인스턴스 분리**: main.py와 auth.py에서 각각 별도의 CSRFProtection 인스턴스 생성
   - 토큰 저장 인스턴스 ≠ 토큰 검증 인스턴스 → 토큰 불일치
2. **쿠키 설정 실패**: FastAPI TemplateResponse에서 set_cookie()가 무시됨
   - Response 객체로 쿠키 설정 → 실제 응답에 반영 안됨
3. **폼 데이터 파싱 오류**: HTML 폼을 Pydantic 모델로 직접 파싱
   - `signup_data: SignupRequest` → Form 데이터를 JSON으로 파싱 시도

#### 해결 방법
1. **전역 CSRF 인스턴스**: `app/dependencies.py` 생성하여 단일 인스턴스 관리
   ```python
   from app.utils.csrf import CSRFProtection
   csrf_protection = CSRFProtection()  # 전역 인스턴스
   ```

2. **TemplateResponse 쿠키 설정**: 응답 객체에서 직접 쿠키 설정
   ```python
   response = templates.TemplateResponse("pages/signup.html", {...})
   response.set_cookie("session_id", session_id, ...)  # 올바른 방법
   ```

3. **Form 의존성 사용**: HTML 폼 데이터를 개별 파라미터로 수신
   ```python
   async def signup(
       email: str = Form(...),
       username: str = Form(...),
       ...
   ):
   ```

#### 재발 방지책
1. **의존성 주입 일관성**: 모든 모듈에서 동일한 인스턴스 사용 확인
2. **쿠키 설정 검증**: `curl -D` 명령으로 Set-Cookie 헤더 확인
3. **폼 처리 표준화**: HTML 폼은 항상 Form() 의존성 사용
4. **통합 테스트**: Puppeteer MCP로 실제 브라우저 동작 확인

### 2025-09-19 - Pydantic display_name 검증 오류 해결

#### 문제 상황
- 회원가입 시 `{"detail":"1 validation error for SignupRequest\ndisplay_name\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]"}` 오류 발생

#### 근본 원인 분석
1. **모델 불일치**: SignupRequest에서 `display_name: str` (필수 필드)
2. **로직 모순**: `display_name if display_name else None` (빈 문자열 → None 변환)
3. **필드 누락**: `password_confirm` 필드가 모델에 없음

#### 해결 방법
1. **모델 수정**: `display_name: Optional[str] = None`으로 선택적 필드 변경
2. **필드 추가**: `password_confirm: str` 모델에 추가
3. **로직 개선**: `display_name.strip()` 후 빈 문자열 체크로 안전성 향상

#### 수정된 코드
```python
# app/models/auth.py
class SignupRequest(BaseModel):
    email: str
    username: str
    password: str
    password_confirm: str
    display_name: Optional[str] = None

# app/routers/auth.py
display_name=display_name if display_name.strip() else None
```

#### 재발 방지책
1. **선택적 필드 원칙**: 비필수 필드는 항상 Optional 타입 사용
2. **모델 완전성**: 폼 필드와 Pydantic 모델 필드 일치 확인
3. **안전한 변환**: 빈 문자열 처리 시 `.strip()` 후 검증
4. **타입 일관성**: None과 문자열 타입 혼용 금지

### 2025-09-19 - 회원가입 "비밀번호 정책" 오류 잘못된 진단 해결

#### 문제 상황
- 사용자가 `Test123456!` 입력 후 "비밀번호는 10자리 이상, 영문 대소문자, 숫자, 특수문자를 포함해야 합니다" 오류 보고

#### 잘못된 진단 과정
1. **비밀번호 정책 검증 의심**: 사용자 보고로 비밀번호 검증 로직 문제로 판단
2. **불필요한 디버깅**: 정상 작동하는 PasswordUtils에 디버깅 코드 추가
3. **실제 검증 결과**: 비밀번호 정책은 완벽하게 통과

#### 실제 원인
- **데이터베이스 스키마 문제**: `column users.email does not exist`
- **오류 메시지 혼동**: 이전 캐시된 오류와 현재 오류 혼동

#### 회원가입 프로세스 전체 검증 결과
```
✅ CSRF 토큰 검증: 정상
✅ 폼 데이터 파싱: 정상
✅ 약관 동의 확인: 정상
✅ 비밀번호 정책 검증: 정상 (Test123456! 모든 조건 만족)
❌ 데이터베이스 처리: 실패 (스키마 문제)
```

#### 올바른 진단 방법
1. **서버 로그 우선 확인**: 실제 오류 위치 파악
2. **단계별 검증**: 각 검증 단계별로 성공/실패 확인
3. **브라우저 캐시 고려**: 이전 오류 메시지와 현재 오류 구분

#### 재발 방지책
1. **로그 기반 진단**: 사용자 보고보다 서버 로그 우선 확인
2. **단계별 분석**: 회원가입 프로세스를 단계별로 체계적 분석
3. **캐시 클리어**: 브라우저 하드 새로고침으로 최신 오류 확인

### 2025-09-24 - 로그인 버튼 404 오류 (템플릿 URL 불일치) 해결

#### 문제 상황
- 게시판 페이지(`/boards/notice`, `/boards/newsletter`, `/boards/free`)에서 로그인 버튼 클릭 시 `{"detail":"Not Found"}` 404 오류 발생
- 모든 게시판 상세 페이지에서 동일한 문제 재현

#### 원인 분석
- **URL 불일치**: 템플릿에서 로그인 버튼이 `/login`으로 링크되어 있으나, 실제 라우트는 `/auth/login`
- **affected files**: board_detail.html, post_detail.html, login.html, signup.html
- **FastAPI 라우터**: main.py에서 `/auth/login`, `/auth/signup` 경로로 등록되어 있음

#### 수정 내용
1. **board_detail.html**: 2군데 수정 (74행, 181행)
   - `href="/login"` → `href="/auth/login"`
2. **post_detail.html**: 1군데 수정 (196행)
   - `href="/login"` → `href="/auth/login"`
   - `href="/signup"` → `href="/auth/signup"`
3. **login.html**: 1군데 수정 (118행)
   - `href="/signup"` → `href="/auth/signup"`
4. **signup.html**: 1군데 수정 (216행)
   - `href="/login"` → `href="/auth/login"`

#### 검증 결과
```
✅ notice 게시판: HTTP 200 응답, 로그인 링크 정상
✅ newsletter 게시판: HTTP 200 응답
✅ free 게시판: HTTP 200 응답
✅ /auth/login 접근: HTTP 200 응답
✅ Docker 재시작: 정상 완료
```

#### 재발 방지책
1. **URL 일관성 확인**: 템플릿의 모든 인증 관련 링크는 `/auth/` 프리픽스 사용
2. **라우트 검증**: 새로운 템플릿 생성 시 실제 라우트 경로와 일치 확인
3. **통합 테스트**: 모든 버튼과 링크에 대한 404 오류 체크
4. **문서화**: ARCHITECTURE.md에 정확한 API 경로 명시