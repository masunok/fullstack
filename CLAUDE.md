# AIZEVA 커뮤니티 서비스

## 프로젝트 개요
- **서비스명**: AIZEVA (아이제바) - 다중 게시판 서비스

## 기술 스택 
- **백엔드 & SSR 프론트**  
  - Python 3.12 + FastAPI
  - 템플릿: **Jinja2**  
  - UI: Tailwind CSS 3.4 + **HTMX**(부분 갱신)  
- **인증·DB·파일 저장**: **Supabase**  
  - Auth·Storage·SQL은 Supabase API를 *서버 측(FastAPI)* 에서만 호출
  - **브라우저에는 Supabase JS SDK·키를 포함하지 않음**  
- **배포**: 도커컴포즈 (uvicorn 기반 실행 FastAPI 도커, nginx 도커로 구성)
  - 로컬에서도 도커컴포즈 명령으로 테스트 가능토록 구성

## 핵심 문서
- **@ARCHITECTURE.md**: 시스템 구조, DB 스키마, API 명세
- **@PROGRESS.md**: 개발 진행 상황, 완료/미완료 작업 (작업 후 반드시 기억해야할 사항)
- **@DESIGN.md**: UI/UX 디자인 가이드
- **@TESTPLAN.md**: 테스트 전략
- **@TESTDATA.md**: 테스트 데이터

## 공통 작업 가이드
- 모든 작업은 ultra think 해서 작업해주세요.
- 모든 작업은 
  1. 먼저 현재 상태를 철저히 분석하고, 
  2. 철저하게 계획을 세우고, 
  3. sub agents 로 분리하지 말고, 순차적인 작업 계획을 작성한 후, 
  4. API 는 모두 TDD 기반으로 테스트 코드 및 실제 코드를 구현하고, 
  5. API 는 예외 케이스까지 완벽히 테스트하고, 
  6. 코드 완성 후에는 바로 종료하지 말고, 전체 코드를 코드 레벨로 확인하여, 확실한 버그가 발견되면, 수정해주세요
- 작업이 완료되면 꼭 기억해야할 내용에 대해서는 PROGRESS.md 파일에 기록해주고, 
- 필요시 CLAUDE.md 와 ARCHITECTURE.md 등의 다음 주요 파일들도 개선해주세요
- 모든 작업은 다음 주요 파일을 확인하여 작업해주세요
  - **@CLAUDE.md**: 전체 프로젝트 개요 및 기술스택과 작업 가이드
  - **@ARCHITECTURE.md**: 시스템 구조, DB 스키마, API 명세
  - **@PROGRESS.md**: 개발 진행 상황, 완료/미완료 작업 (작업 후 반드시 기억해야할 내용)
  - **@DESIGN.md**: UI/UX 디자인 가이드
    - wireframes 하위폴더에 UI 구현이 필요한 모든 화면은 xml 포멧으로 UI 화면 표현
  - **@TESTPLAN.md**: 테스트 항목
  - **@TESTDATA.md**: 테스트시 필요한 데이터
  - **@NOTE.md**: 빈번한 실수와 해결 방법 기억
- 작업 완료 후에는 테스트 항목을 @TESTPLAN.md 파일에 작성하고, 직접 docker 를 실행하고, puppeteer MCP 로 테스트하여, 모든 버그를 side effect 를 고려하여 신중하게 수정한 후, @TESTPLAN.md 에 기재된 모든 테스트 항목이 PASS 할 때까지 작업을 반복합니다
  - 주로 실수하는 항목은 @NOTE.md 파일에 이후 실수를 반복하지 않기 위해 기재합니다.

## MCP 사용 설정
- 다음 MCP 가 연결되어 있으므로, 관련 작업은 해당 MCP 를 직접 사용해서 작업해주세요
  - supabase MCP (supabase 제어)
  - puppeteer MCP (브라우저 제어)

## Supabase 설정
- **프로젝트 ID**: kjkctytkgnkyzuweeyud
- **초기 관리자**: masunok@example.com / msk040830*
- **중요**: Email confirmation OFF, RLS OFF
  - FastAPI 내부에서만 supabase 에 엑세스하므로 RLS 불필요

## 주요 기능
1. **게시판**: 다중 게시판, 권한 관리 (all/member/admin)
2. **인증**: JWT 쿠키 방식, 세션별 CSRF 보호
3. **게시글**: Quill.js 에디터, Base64 이미지 (1MB 제한)
4. **댓글**: 2단계 계층, HTMX 실시간 업데이트
5. **관리자**: 게시판/사용자 관리
6. **세션**: 메모리 기반 세션 저장

## 필수 환경변수 (.env)
```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SESSION_SECRET=your-session-secret
COOKIE_SECURE=False  # True for production
COOKIE_SAMESITE=lax
```

## 보안 체크리스트
- XSS 방어 (bleach)
- CSRF 보호 (Double Submit Cookie)
- Rate Limiting (Nginx)
- HttpOnly·Secure 쿠키

## 초기 데이터 셋업
- **초기 관리자**: soma@kcc.co.kr / msk040830* (자동 생성 스크립트)
- **초기 게시판**: 
  - notice (공지사항) - 관리자만 글쓰기 허용
  - newsletter (뉴스레터) - 관리자만 글쓰기 허용  
  - free (자유게시판) - 로그인 사용자 모두 글쓰기 허용