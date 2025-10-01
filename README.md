# AIZEVA 커뮤니티 서비스

다중 게시판 기반의 현대적인 커뮤니티 플랫폼

## 🚀 주요 기능

- **다중 게시판 시스템**: 공지사항, 뉴스레터, 자유게시판 등
- **권한별 접근 제어**: 게시판별 읽기/쓰기 권한 관리 (all/member/admin)
- **계층형 댓글**: 2단계 댓글/답글 시스템
- **실시간 UI 업데이트**: HTMX 기반 부분 페이지 갱신
- **리치 에디터**: Quill.js 기반 WYSIWYG 에디터
- **관리자 대시보드**: 사용자/게시판 관리, 통계 제공
- **보안**: CSRF 보호, XSS 방어, JWT 인증

## 🛠️ 기술 스택

### Backend & Frontend
- **Python 3.12** + **FastAPI**
- **Jinja2** 템플릿 엔진
- **Tailwind CSS 3.4** + **HTMX**
- **Quill.js** (리치 텍스트 에디터)

### Database & Auth
- **Supabase** (PostgreSQL + Auth + Storage)
- JWT 기반 세션 관리

### Deployment
- **Docker** + **Docker Compose**
- **Nginx** (리버스 프록시)

## 📋 필수 요구사항

- Python 3.12+
- Docker & Docker Compose
- Supabase 계정 (무료 플랜 가능)

## 🔧 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/YOUR_USERNAME/aizeva.git
cd aizeva
```

### 2. 환경변수 설정
`.env` 파일을 생성하고 다음 내용을 입력:

```env
# Supabase 설정
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# 세션 보안
SESSION_SECRET=your-random-secret-key

# 쿠키 설정 (개발환경)
COOKIE_SECURE=False
COOKIE_SAMESITE=lax
```

### 3. Docker로 실행
```bash
docker-compose up -d
```

서비스가 `http://localhost:8000`에서 실행됩니다.

### 4. 초기 데이터 설정
```bash
# 가상환경 활성화 (로컬 실행 시)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 초기 관리자 및 게시판 생성
python scripts/init_data.py

# 테스트 데이터 생성 (선택사항)
python scripts/create_test_data.py
```

## 📁 프로젝트 구조

```
aizeva/
├── app/
│   ├── models/          # 데이터 모델
│   ├── routers/         # API 라우터
│   ├── services/        # 비즈니스 로직
│   ├── utils/           # 유틸리티 함수
│   └── main.py          # FastAPI 앱
├── templates/           # Jinja2 템플릿
│   ├── base.html
│   ├── components/
│   └── pages/
├── static/              # 정적 파일
│   ├── css/
│   └── js/
├── tests/               # 테스트 코드
├── docker-compose.yml   # Docker 구성
├── Dockerfile
├── requirements.txt     # Python 의존성
└── nginx.conf          # Nginx 설정
```

## 🔐 보안 설정

### Supabase 설정 체크리스트
- [ ] Email Confirmation **OFF** (FastAPI에서 처리)
- [ ] Row Level Security (RLS) **OFF** (서버 사이드 인증)
- [ ] Service Role Key 안전하게 보관

### 프로덕션 배포 시
```env
COOKIE_SECURE=True
COOKIE_SAMESITE=strict
```

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 특정 테스트만 실행
pytest tests/test_auth.py

# 커버리지 확인
pytest --cov=app --cov-report=html
```

## 📚 주요 문서

- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 구조 및 API 명세
- [DESIGN.md](DESIGN.md) - UI/UX 디자인 가이드
- [PROGRESS.md](PROGRESS.md) - 개발 진행 상황
- [TESTPLAN.md](TESTPLAN.md) - 테스트 계획
- [NOTE.md](NOTE.md) - 개발 노트 및 트러블슈팅

## 🎯 기본 계정

초기 관리자 계정 (scripts/init_data.py 실행 후):
- **이메일**: soma@kcc.co.kr
- **비밀번호**: msk040830*

⚠️ **프로덕션 환경에서는 반드시 비밀번호를 변경하세요!**

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이선스

This project is licensed under the MIT License.

## 👤 Contact

프로젝트 관련 문의: soma@kcc.co.kr

---

**Built with ❤️ using FastAPI and Supabase**

