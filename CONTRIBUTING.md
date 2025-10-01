# Contributing to AIZEVA

AIZEVA 프로젝트에 기여해주셔서 감사합니다! 🎉

## 🚀 시작하기

### 1. Fork & Clone

```bash
# 1. GitHub에서 Fork 버튼 클릭
# 2. 본인 계정의 fork를 클론
git clone https://github.com/masunok/fullstack.git
cd aizeva

# 3. Upstream 설정
git remote add upstream https://github.com/masunok/fullstack.git
```

### 2. 개발 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp env.example .env
# .env 파일 수정 (Supabase 키 입력)

# Docker로 실행
docker-compose up -d
```

### 3. 브랜치 생성

```bash
# 최신 코드 가져오기
git checkout main
git pull upstream main

# 기능 브랜치 생성
git checkout -b feature/amazing-feature
```

## 📝 코딩 가이드

### Python 스타일

- **PEP 8** 준수
- **Type Hints** 사용 권장
- **Docstring** 작성 (Google Style)

```python
async def create_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """게시글을 생성합니다.
    
    Args:
        post_data: 게시글 데이터 딕셔너리
        
    Returns:
        생성된 게시글 정보
        
    Raises:
        ValueError: 필수 필드 누락 시
    """
    pass
```

### 커밋 메시지

```bash
# 형식: <type>: <subject>

feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 수정
style: 코드 포맷팅 (기능 변경 없음)
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드/설정 관련

# 예시
feat: Add user profile page
fix: Fix CSRF token validation error
docs: Update API documentation
```

## 🧪 테스트

### 테스트 실행

```bash
# 전체 테스트
pytest

# 특정 파일
pytest tests/test_auth.py

# 커버리지 확인
pytest --cov=app --cov-report=html
```

### 새로운 기능 추가 시

1. **테스트 코드 먼저 작성** (TDD)
2. **기능 구현**
3. **테스트 통과 확인**
4. **문서 업데이트**

## 📤 Pull Request 절차

### 1. 코드 푸시

```bash
# 변경사항 커밋
git add .
git commit -m "feat: Add amazing feature"

# Fork에 푸시
git push origin feature/amazing-feature
```

### 2. PR 생성

1. GitHub에서 **Compare & pull request** 클릭
2. **제목**: 명확하고 간결하게
3. **설명**: 
   - 변경 사항 설명
   - 관련 이슈 링크 (`Closes #123`)
   - 스크린샷 (UI 변경 시)

### 3. PR 체크리스트

- [ ] 코드가 PEP 8을 준수하는가?
- [ ] 모든 테스트를 통과하는가?
- [ ] 새로운 기능에 테스트를 추가했는가?
- [ ] 문서를 업데이트했는가?
- [ ] CHANGELOG를 업데이트했는가? (주요 변경사항)

### 4. 리뷰 대응

- 리뷰어의 피드백에 성실히 답변
- 요청사항 반영 후 **다시 푸시**
- 승인 후 **Squash and merge**

## 🐛 버그 리포트

### Issue 템플릿

```markdown
## 버그 설명
명확하고 간결한 버그 설명

## 재현 방법
1. '...' 페이지로 이동
2. '...' 클릭
3. '...' 입력
4. 에러 발생

## 예상 동작
정상적으로 작동해야 하는 동작

## 실제 동작
실제로 발생한 동작 (스크린샷 첨부)

## 환경
- OS: [예: Windows 11]
- Browser: [예: Chrome 120]
- Python: [예: 3.12]
```

## 💡 기능 제안

### Feature Request 템플릿

```markdown
## 기능 설명
제안하는 기능에 대한 명확한 설명

## 해결하려는 문제
이 기능이 해결할 문제점

## 대안 검토
고려한 다른 해결 방법들

## 추가 정보
참고 자료, 예시 등
```

## 📚 문서 기여

- **오타 수정**: 바로 PR
- **내용 추가/수정**: Issue 먼저 생성
- **번역**: i18n 폴더에 언어별 파일 추가

## ❓ 질문하기

- **Slack/Discord**: 실시간 논의
- **GitHub Discussions**: 일반적인 질문
- **GitHub Issues**: 버그/기능 관련

## 🙏 기여자 행동 강령

- **존중**: 모든 기여자를 존중합니다
- **건설적**: 건설적인 피드백을 제공합니다
- **협력**: 함께 더 나은 프로젝트를 만듭니다

---

다시 한번 기여해주셔서 감사합니다! 🚀

