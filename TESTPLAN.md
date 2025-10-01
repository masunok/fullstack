# AIZEVA 테스트 계획

## 테스트 전략
- 테스트 레벨별로 각각 테스트
  1. **단위 테스트**: 개별 함수 및 메서드
  2. **통합 테스트**: API 엔드포인트
  3. **E2E 테스트**: 전체 사용자 시나리오

## 테스트 환경
- **로컬**: Python pytest + Docker Compose
- **E2E**: Puppeteer MCP
- **데이터베이스**: 실제 Supabase 환경 (.env)

## 기능별 테스트 케이스

### 1. 인증 시스템 테스트
#### 단위 테스트
- 비밀번호 정책 검증 (영문자+숫자+특수문자 10자리 이상)
- JWT 토큰 생성/검증
- CSRF 토큰 생성/검증

#### API 테스트
- POST /auth/signup (회원가입)
- POST /auth/login (로그인)  
- POST /auth/logout (로그아웃)
- GET /auth/me (현재 사용자 정보)

#### E2E 테스트
- 회원가입 플로우 (@signup.xml 기반)
- 로그인 플로우 (@login.xml 기반)
- 로그아웃 기능

### 2. 게시판 시스템 테스트
#### API 테스트
- GET /boards (게시판 목록)
- GET /boards/{slug} (게시판 상세)
- POST /boards (게시판 생성 - 관리자만)

#### E2E 테스트
- 게시판 목록 페이지 (@board_list.xml 기반)
- 게시판 상세 페이지 (@board_detail.xml 기반)
- 페이지네이션 (10개씩, 처음/이전/다음/끝 버튼)

### 3. 게시글 시스템 테스트
#### API 테스트
- GET /boards/{slug}/posts (게시글 목록)
- GET /posts/{id} (게시글 상세)
- POST /boards/{slug}/posts (게시글 작성)
- PUT /posts/{id} (게시글 수정)
- DELETE /posts/{id} (게시글 삭제)

#### E2E 테스트
- 게시글 작성 (@post_write.xml 기반)
- 게시글 상세 보기 (@post_detail.xml 기반)
- 게시글 수정/삭제 권한 확인

### 4. 댓글 시스템 테스트
#### API 테스트
- GET /posts/{post_id}/comments (댓글 목록)
- POST /posts/{post_id}/comments (댓글 작성)
- PUT /comments/{id} (댓글 수정)
- DELETE /comments/{id} (댓글 삭제)

#### E2E 테스트
- 댓글 작성/수정/삭제
- 답글 작성/수정/삭제 (2단계 계층)
- HTMX 기반 실시간 업데이트

### 5. 관리자 기능 테스트
#### API 테스트
- GET /admin/users (사용자 관리)
- PUT /admin/users/{id} (사용자 권한 변경)

#### E2E 테스트
- 사용자 관리 페이지 (@admin_users.xml 기반)
- 게시판 관리 페이지 (@admin_boards.xml 기반)
- 권한 확인 (관리자만 접근)

### 6. UI/UX 테스트 (Puppeteer MCP)
#### 반응형 디자인 테스트
- 모바일 (768px 이하): 햄버거 메뉴, 카드 레이아웃
- 태블릿 (768px-1024px): 2단 그리드
- 데스크톱 (1024px 이상): 테이블 형태

#### 공통 컴포넌트 테스트
- 헤더 (@header.xml): 로고, 네비게이션, 검색, 모바일 메뉴
- 푸터 (@footer.xml): 링크, 저작권 정보

#### 페이지별 UI 테스트
- 메인 페이지 (@main.xml): 히어로, 인기 게시판, 최신 게시글
- 로그인/회원가입 (@login.xml, @signup.xml): 폼 검증, 에러 메시지
- 게시판/게시글 페이지: 검색, 페이지네이션, CRUD 기능

### 7. 보안 테스트
#### XSS 방어 테스트
- 게시글/댓글 내용에 스크립트 삽입 시도
- HTML 태그 필터링 확인 (bleach)

#### CSRF 보호 테스트
- 토큰 없는 요청 차단 확인
- 잘못된 토큰으로 요청 시도

#### 권한 테스트
- 비로그인 사용자 접근 제한
- 일반 사용자의 관리자 기능 접근 차단
- 게시글/댓글 작성자 권한 확인

### 8. 성능 테스트
#### 페이지 로딩 테스트
- 각 페이지 로딩 시간 측정
- 이미지 최적화 확인

#### 데이터베이스 쿼리 테스트
- N+1 쿼리 문제 확인
- 페이지네이션 성능 측정
