# AIZEVA 테스트 데이터

## 사용자 계정

### 관리자 계정
```
이메일: masunok@example.com
비밀번호: msk040830*
사용자명: admin
표시이름: 관리자
권한: is_admin = true
설명: 초기 관리자 계정 (자동 생성 스크립트로 생성됨)
```

### 테스트 사용자 (2025-09-22 정리 완료)
#### 기존 사용자 (완전 삭제됨)
```
❌ 기존 테스트 사용자들 (auth.users에서 완전 삭제됨)
- alice@example.com (ID: 550e8400-e29b-41d4-a716-446655440002)
- bob@example.com (ID: 550e8400-e29b-41d4-a716-446655440003)
- charlie@example.com (ID: 550e8400-e29b-41d4-a716-446655440004)
- diana@example.com (ID: 550e8400-e29b-41d4-a716-446655440005)

삭제 사유:
- public.users 프로필 정보 누락으로 로그인 불가능
- 게시글/댓글 데이터 없어서 삭제 시 손실 없음
- 데이터 일관성 확보를 위해 정리
```

#### 현재 사용 가능한 테스트 사용자
```
1. 새 앨리스 (alice.new@example.com / alice123!@#)
   - 사용자명: alice_new
   - 표시이름: New Alice
   - 권한: 일반 사용자
   - 상태: 로그인 테스트 완료 ✅

2. 새 밥 (bob.new@example.com / bob123!@#$)
   - 사용자명: bob_new
   - 표시이름: New Bob
   - 권한: 일반 사용자
   - 상태: 계정 생성 완료 ✅

3. 새 찰리 (charlie.new@example.com / charlie123!)
   - 사용자명: charlie_new
   - 표시이름: New Charlie
   - 권한: 일반 사용자
   - 상태: 계정 생성 완료 ✅

4. 새 다이애나 (diana.new@example.com / diana123!@)
   - 사용자명: diana_new
   - 표시이름: New Diana
   - 권한: 일반 사용자
   - 상태: 계정 생성 완료 ✅
```

### 초기 게시판
```
1. 공지사항 (notice)
   - 이름: 공지사항  
   - Slug: notice
   - 설명: 중요한 공지사항을 게시합니다
   - 작성권한: admin (관리자만)

2. 뉴스레터 (newsletter) 
   - 이름: 뉴스레터
   - Slug: newsletter
   - 설명: 정기 뉴스레터를 발행합니다
   - 작성권한: admin (관리자만)

3. 자유게시판 (free)
   - 이름: 자유게시판
   - Slug: free  
   - 설명: 자유롭게 소통하는 공간입니다
   - 작성권한: member (로그인 사용자)
```

## 테스트 데이터 (2025-09-17 현재 DB 상태)

### 게시글 현황
```
공지사항 게시판 (notice) - 2개 게시글
1. "🎉 AIZEVA 커뮤니티 오픈 안내" (관리자 작성)
2. "📋 커뮤니티 이용 규칙 안내" (관리자 작성)

뉴스레터 게시판 (newsletter) - 2개 게시글
1. "📰 AIZEVA 뉴스레터 #1 - 2024년 9월" (관리자 작성)
2. "🎯 10월 커뮤니티 이벤트 안내" (관리자 작성)

자유게시판 (free) - 5개 게시글
1. "💭 웹 개발 트렌드에 대한 생각" (앨리스 작성, 조회수: 46)
2. "🍕 오늘 점심 추천좀 해주세요!" (밥 작성, 조회수: 23)
3. "📚 프로그래밍 공부 방법 공유" (찰리 작성, 조회수: 67)
4. "🎮 요즘 하고 있는 게임 있나요?" (다이애나 작성, 조회수: 32)
5. "☕ 카페에서 작업하기 좋은 곳" (앨리스 작성, 조회수: 58)
```

### 댓글 현황
```
총 27개 댓글 (부모댓글 + 답글 계층 구조)
- 각 게시글마다 2-8개의 댓글
- 30% 확률로 답글 생성
- 모든 사용자가 다양한 댓글 참여
```

### 로그인 테스트 계정 정보
```
관리자 로그인:
- 이메일: soma@kcc.co.kr
- 비밀번호: msk040830*

일반 사용자 로그인 (2025-09-22 정리 완료):
- 앨리스: alice.new@example.com / alice123!@#
- 밥: bob.new@example.com / bob123!@#$
- 찰리: charlie.new@example.com / charlie123!
- 다이애나: diana.new@example.com / diana123!@

기존 사용자 (완전 삭제됨):
- alice@example.com, bob@example.com, charlie@example.com, diana@example.com
- 모두 auth.users 테이블에서 영구 삭제됨 (2025-09-22)
```
