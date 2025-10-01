# AIZEVA 아키텍처 문서

## 페이지 플로우 다이어그램
```
[비로그인 사용자]
/ (메인페이지) → /login (로그인) → /signup (회원가입)
                ↓
                /boards (게시판목록) → /boards/{slug} (게시글목록) → /posts/{id} (게시글상세)

[로그인 사용자] 
/ (메인페이지) → /boards (게시판목록) → /boards/{slug} (게시글목록) → /posts/{id} (게시글상세)
                                     ↓                              ↓
                                     /boards/{slug}/write (글쓰기)    댓글 작성/수정/삭제
                                     /posts/{id}/edit (글수정)

[관리자]
/admin/users (사용자관리) → /admin/boards (게시판관리)
```

## 시스템 구조
```
Nginx (Reverse Proxy) → FastAPI (Backend) → Supabase (Auth/DB)
```

## 프로젝트 파일 구조
```
/
├── app/                    # FastAPI 애플리케이션
│   ├── main.py            # FastAPI 메인 앱
│   ├── models/            # 데이터 모델
│   ├── routers/           # API 라우터
│   ├── services/          # 비즈니스 로직
│   ├── utils/             # 유틸리티 함수
│   └── dependencies.py    # 의존성 주입
├── templates/             # Jinja2 템플릿
│   ├── base.html
│   ├── components/
│   └── pages/
├── static/                # 정적 파일 (CSS, JS)
│   ├── css/
│   ├── js/
│   └── images/
├── tests/                 # 테스트 파일
├── docker-compose.yml     # Docker 구성
├── Dockerfile            # FastAPI 컨테이너
├── requirements.txt      # Python 의존성
├── nginx.conf           # Nginx 설정
└── .env                 # 환경변수
```

## UI 디자인 (wireframes/)
- **인증**: @login.xml, @signup.xml
- **메인**: @main.xml (최신 게시글 포함)
- **게시판**: @board_list.xml, @board_detail.xml
- **게시글**: @post_list.xml, @post_detail.xml, @post_write.xml
- **공통**: @header.xml, @footer.xml (모바일 햄버거 메뉴)

## DB 스키마

### 1. 사용자 프로필 테이블 (users)
- Supabase Auth와 연동하는 추가 프로필 정보
```sql
CREATE TABLE users (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  display_name VARCHAR(100),
  is_admin BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. 게시판 테이블 (boards)
```sql
CREATE TABLE boards (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  write_permission VARCHAR(20) DEFAULT 'member', -- 'all', 'member', 'admin'
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3. 게시글 테이블 (posts)
```sql
CREATE TABLE posts (
  id SERIAL PRIMARY KEY,
  board_id INTEGER REFERENCES boards(id),
  user_id UUID REFERENCES users(id),
  title VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  view_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4. 댓글 테이블 (comments)
```sql
CREATE TABLE comments (
  id SERIAL PRIMARY KEY,
  post_id INTEGER REFERENCES posts(id),
  user_id UUID REFERENCES users(id),
  parent_id INTEGER REFERENCES comments(id),
  content TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## 주요 API

### 인증 API
- POST /auth/signup - 회원가입
- POST /auth/login - 로그인  
- POST /auth/logout - 로그아웃
- GET /auth/me - 현재 사용자 정보

### 게시판 API
- GET /boards - 게시판 목록
- GET /boards/{slug} - 게시판 상세
- POST /boards - 게시판 생성 (관리자)
- PUT /boards/{id} - 게시판 수정 (관리자)
- DELETE /boards/{id} - 게시판 삭제 (관리자)

### 게시글 API  
- GET /boards/{slug}/posts - 게시글 목록 (페이지네이션: 10개씩)
- GET /posts/{id} - 게시글 상세
- POST /boards/{slug}/posts - 게시글 작성
- PUT /posts/{id} - 게시글 수정
- DELETE /posts/{id} - 게시글 삭제

### 댓글 API
- GET /posts/{post_id}/comments - 댓글 목록
- POST /posts/{post_id}/comments - 댓글 작성
- PUT /comments/{id} - 댓글 수정
- DELETE /comments/{id} - 댓글 삭제

### 검색 API
- GET /search?q={query}&board={board_slug} - 게시글 검색

### 관리자 API
- GET /admin/users - 사용자 관리
- PUT /admin/users/{id} - 사용자 권한 변경
