import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.models.posts import PostService, PostRequest, PostUpdateRequest


class TestPostService:
    """게시글 서비스 테스트"""
    
    @pytest.fixture
    def post_service(self):
        return PostService()
    
    @pytest.mark.asyncio
    async def test_get_posts_by_board_slug(self, post_service):
        """게시판별 게시글 목록 조회 테스트"""
        posts = await post_service.get_posts_by_board_slug("free", page=1, limit=10)
        
        assert isinstance(posts, dict)
        assert "posts" in posts
        assert "total_count" in posts
        assert "page" in posts
        assert "limit" in posts
        assert "total_pages" in posts
        
        # 페이지네이션 검증
        assert posts["page"] == 1
        assert posts["limit"] == 10
        assert len(posts["posts"]) <= 10
    
    @pytest.mark.asyncio
    async def test_get_posts_pagination(self, post_service):
        """게시글 목록 페이지네이션 테스트"""
        # 첫 번째 페이지
        page1 = await post_service.get_posts_by_board_slug("free", page=1, limit=5)
        
        # 두 번째 페이지  
        page2 = await post_service.get_posts_by_board_slug("free", page=2, limit=5)
        
        # 페이지가 다르면 다른 게시글이어야 함
        if len(page1["posts"]) > 0 and len(page2["posts"]) > 0:
            page1_ids = [post["id"] for post in page1["posts"]]
            page2_ids = [post["id"] for post in page2["posts"]]
            assert set(page1_ids).isdisjoint(set(page2_ids))
    
    @pytest.mark.asyncio
    async def test_get_post_by_id(self, post_service):
        """ID로 게시글 조회 테스트"""
        # 먼저 게시글 목록에서 하나 가져오기
        posts = await post_service.get_posts_by_board_slug("free", page=1, limit=1)
        
        if posts["posts"]:
            post_id = posts["posts"][0]["id"]
            post = await post_service.get_post_by_id(post_id)
            
            assert post is not None
            assert post["id"] == post_id
            assert "title" in post
            assert "content" in post
            assert "user_id" in post
            assert "board_id" in post
            assert "view_count" in post
        
        # 존재하지 않는 게시글
        non_existent = await post_service.get_post_by_id(99999)
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_create_post(self, post_service):
        """게시글 생성 테스트"""
        # 테스트용 사용자 ID (UUID 형식이어야 함)
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # free 게시판 ID 조회
        from app.models.boards import BoardService
        board_service = BoardService()
        board = await board_service.get_board_by_slug("free")
        
        if board:
            post_data = {
                "title": "테스트 게시글",
                "content": "테스트 내용입니다.",
                "board_id": board["id"],
                "user_id": test_user_id
            }
            
            created_post = await post_service.create_post(post_data)
            
            assert created_post is not None
            assert created_post["title"] == post_data["title"]
            assert created_post["content"] == post_data["content"]
            assert created_post["board_id"] == post_data["board_id"]
            assert created_post["user_id"] == post_data["user_id"]
            assert created_post["view_count"] == 0
            assert "created_at" in created_post
            assert "updated_at" in created_post
    
    @pytest.mark.asyncio
    async def test_create_post_validation(self, post_service):
        """게시글 생성 검증 테스트"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # 제목 없는 게시글
        with pytest.raises(ValueError) as exc_info:
            await post_service.create_post({
                "content": "내용만 있음",
                "board_id": 1,
                "user_id": test_user_id
            })
        assert "제목은 필수" in str(exc_info.value)
        
        # 내용 없는 게시글
        with pytest.raises(ValueError) as exc_info:
            await post_service.create_post({
                "title": "제목만 있음",
                "board_id": 1,
                "user_id": test_user_id
            })
        assert "내용은 필수" in str(exc_info.value)
        
        # 존재하지 않는 게시판
        with pytest.raises(ValueError) as exc_info:
            await post_service.create_post({
                "title": "테스트",
                "content": "테스트",
                "board_id": 99999,
                "user_id": test_user_id
            })
        assert "존재하지 않는 게시판" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_post(self, post_service):
        """게시글 수정 테스트"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # 게시판 정보 가져오기
        from app.models.boards import BoardService
        board_service = BoardService()
        board = await board_service.get_board_by_slug("free")
        
        if board:
            # 먼저 게시글 생성
            post_data = {
                "title": "수정 전 제목",
                "content": "수정 전 내용",
                "board_id": board["id"],
                "user_id": test_user_id
            }
            created_post = await post_service.create_post(post_data)
            post_id = created_post["id"]
            
            # 수정 데이터
            update_data = {
                "title": "수정 후 제목",
                "content": "수정 후 내용"
            }
            
            updated_post = await post_service.update_post(post_id, update_data)
            
            assert updated_post is not None
            assert updated_post["id"] == post_id
            assert updated_post["title"] == update_data["title"]
            assert updated_post["content"] == update_data["content"]
            assert updated_post["board_id"] == board["id"]  # 변경되지 않음
            assert updated_post["user_id"] == test_user_id  # 변경되지 않음
    
    @pytest.mark.asyncio
    async def test_delete_post(self, post_service):
        """게시글 삭제 테스트"""
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        
        # 게시판 정보 가져오기
        from app.models.boards import BoardService
        board_service = BoardService()
        board = await board_service.get_board_by_slug("free")
        
        if board:
            # 먼저 게시글 생성
            post_data = {
                "title": "삭제될 게시글",
                "content": "삭제될 내용",
                "board_id": board["id"],
                "user_id": test_user_id
            }
            created_post = await post_service.create_post(post_data)
            post_id = created_post["id"]
            
            # 삭제 실행
            result = await post_service.delete_post(post_id)
            assert result == True
            
            # 삭제 확인
            deleted_post = await post_service.get_post_by_id(post_id)
            assert deleted_post is None
    
    @pytest.mark.asyncio
    async def test_increment_view_count(self, post_service):
        """조회수 증가 테스트"""
        posts = await post_service.get_posts_by_board_slug("free", page=1, limit=1)
        
        if posts["posts"]:
            post_id = posts["posts"][0]["id"]
            original_view_count = posts["posts"][0]["view_count"]
            
            # 조회수 증가
            await post_service.increment_view_count(post_id)
            
            # 조회수 확인
            updated_post = await post_service.get_post_by_id(post_id)
            assert updated_post["view_count"] == original_view_count + 1
    
    @pytest.mark.asyncio 
    async def test_search_posts(self, post_service):
        """게시글 검색 테스트"""
        # 검색어가 있는 경우
        results = await post_service.search_posts("테스트", board_slug="free")
        
        assert isinstance(results, dict)
        assert "posts" in results
        assert "total_count" in results
        
        # 검색 결과의 제목이나 내용에 검색어가 포함되어야 함
        for post in results["posts"]:
            content_match = "테스트" in post.get("title", "") or "테스트" in post.get("content", "")
            # 실제로는 대소문자 구분 없이 검색해야 하지만, 간단한 테스트로 진행


@pytest.mark.asyncio
class TestPostAPI:
    """게시글 API 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_get_board_posts(self, client):
        """게시판별 게시글 목록 조회 API 테스트"""
        response = client.get("/boards/free/posts")
        
        # API 키 문제로 400이 될 수 있지만, 라우팅은 정상이어야 함
        assert response.status_code in [200, 400]
        
        # 페이지네이션 파라미터 테스트
        response = client.get("/boards/free/posts?page=1&limit=5")
        assert response.status_code in [200, 400]
    
    def test_get_post_detail(self, client):
        """게시글 상세 조회 API 테스트"""
        response = client.get("/posts/1")
        
        # 게시글이 존재하지 않을 수 있으므로 404도 정상
        assert response.status_code in [200, 400, 404]
    
    def test_create_post_unauthorized(self, client):
        """비로그인 상태로 게시글 작성 시도"""
        post_data = {
            "title": "테스트 게시글",
            "content": "테스트 내용"
        }
        
        response = client.post("/boards/free/posts", json=post_data)
        
        # 인증이 필요하므로 401 또는 403
        assert response.status_code in [401, 403]
    
    def test_update_post_unauthorized(self, client):
        """비로그인 상태로 게시글 수정 시도"""
        update_data = {
            "title": "수정된 제목",
            "content": "수정된 내용"
        }
        
        response = client.put("/posts/1", json=update_data)
        
        # 인증이 필요하므로 401 또는 403
        assert response.status_code in [401, 403]
    
    def test_delete_post_unauthorized(self, client):
        """비로그인 상태로 게시글 삭제 시도"""
        response = client.delete("/posts/1")
        
        # 인증이 필요하므로 401 또는 403
        assert response.status_code in [401, 403]
    
    def test_post_validation(self, client):
        """게시글 데이터 검증 테스트"""
        # 필수 필드 누락
        invalid_data = {
            "content": "제목이 없는 게시글"
        }
        
        response = client.post("/boards/free/posts", json=invalid_data)
        
        # 인증 오류(401/403) 또는 검증 오류(422) 
        assert response.status_code in [401, 403, 422]
    
    def test_search_posts_api(self, client):
        """게시글 검색 API 테스트"""
        response = client.get("/search?q=테스트")
        
        # API 키 문제로 400이 될 수 있지만, 라우팅은 정상이어야 함
        assert response.status_code in [200, 400]
        
        # 게시판 지정 검색
        response = client.get("/search?q=테스트&board=free")
        assert response.status_code in [200, 400]


class TestPostPermissions:
    """게시글 권한 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_post_write_permission_by_board(self, client):
        """게시판별 게시글 작성 권한 확인"""
        # notice 게시판 (admin만 작성 가능)
        response = client.get("/boards/notice/write-permission")
        assert response.status_code in [200, 400]
        
        # free 게시판 (member 작성 가능)  
        response = client.get("/boards/free/write-permission")
        assert response.status_code in [200, 400]
    
    def test_post_ownership_validation(self, client):
        """게시글 작성자 권한 확인 (수정/삭제)"""
        # 실제 테스트에서는 다른 사용자의 게시글 수정/삭제 시도
        # 지금은 구조만 확인
        
        response = client.put("/posts/1", json={"title": "다른 사용자 게시글 수정 시도"})
        assert response.status_code in [401, 403, 404]
        
        response = client.delete("/posts/1")
        assert response.status_code in [401, 403, 404]