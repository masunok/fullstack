import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.models.boards import BoardService, BoardRequest, BoardResponse


class TestBoardService:
    """게시판 서비스 테스트"""
    
    @pytest.fixture
    def board_service(self):
        return BoardService()
    
    @pytest.mark.asyncio
    async def test_get_all_boards(self, board_service):
        """모든 게시판 목록 조회 테스트"""
        boards = await board_service.get_all_boards()
        
        assert isinstance(boards, list)
        assert len(boards) >= 3  # 초기 3개 게시판 확인
        
        # 초기 게시판 확인
        board_slugs = [board["slug"] for board in boards]
        assert "notice" in board_slugs
        assert "newsletter" in board_slugs
        assert "free" in board_slugs
    
    @pytest.mark.asyncio
    async def test_get_board_by_slug(self, board_service):
        """slug로 게시판 조회 테스트"""
        board = await board_service.get_board_by_slug("notice")
        
        assert board is not None
        assert board["slug"] == "notice"
        assert board["name"] == "공지사항"
        assert board["write_permission"] == "admin"
        
        # 존재하지 않는 slug 테스트
        non_existent = await board_service.get_board_by_slug("nonexistent")
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_get_board_by_id(self, board_service):
        """ID로 게시판 조회 테스트"""
        boards = await board_service.get_all_boards()
        first_board = boards[0]
        board_id = first_board["id"]
        
        board = await board_service.get_board_by_id(board_id)
        
        assert board is not None
        assert board["id"] == board_id
        assert board["slug"] == first_board["slug"]
        
        # 존재하지 않는 ID 테스트
        non_existent = await board_service.get_board_by_id(99999)
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_create_board(self, board_service):
        """게시판 생성 테스트"""
        board_data = {
            "name": "테스트게시판",
            "slug": "test_board",
            "description": "테스트용 게시판입니다",
            "write_permission": "member"
        }
        
        created_board = await board_service.create_board(board_data)
        
        assert created_board is not None
        assert created_board["name"] == board_data["name"]
        assert created_board["slug"] == board_data["slug"]
        assert created_board["description"] == board_data["description"]
        assert created_board["write_permission"] == board_data["write_permission"]
        assert "created_at" in created_board
        assert "updated_at" in created_board
    
    @pytest.mark.asyncio
    async def test_create_board_duplicate_slug(self, board_service):
        """중복 slug로 게시판 생성 실패 테스트"""
        board_data = {
            "name": "중복테스트",
            "slug": "notice",  # 기존 slug
            "description": "중복 slug 테스트",
            "write_permission": "member"
        }
        
        with pytest.raises(ValueError) as exc_info:
            await board_service.create_board(board_data)
        
        assert "이미 존재하는 slug" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_board(self, board_service):
        """게시판 수정 테스트"""
        # 먼저 새 게시판 생성
        board_data = {
            "name": "수정테스트",
            "slug": "update_test",
            "description": "수정 테스트용",
            "write_permission": "member"
        }
        created_board = await board_service.create_board(board_data)
        board_id = created_board["id"]
        
        # 수정 데이터
        update_data = {
            "name": "수정완료",
            "description": "수정된 설명",
            "write_permission": "admin"
        }
        
        updated_board = await board_service.update_board(board_id, update_data)
        
        assert updated_board is not None
        assert updated_board["id"] == board_id
        assert updated_board["name"] == update_data["name"]
        assert updated_board["description"] == update_data["description"]
        assert updated_board["write_permission"] == update_data["write_permission"]
        assert updated_board["slug"] == "update_test"  # slug는 변경되지 않음
    
    @pytest.mark.asyncio
    async def test_delete_board(self, board_service):
        """게시판 삭제 테스트"""
        # 먼저 새 게시판 생성
        board_data = {
            "name": "삭제테스트",
            "slug": "delete_test",
            "description": "삭제 테스트용",
            "write_permission": "member"
        }
        created_board = await board_service.create_board(board_data)
        board_id = created_board["id"]
        
        # 삭제 실행
        result = await board_service.delete_board(board_id)
        assert result == True
        
        # 삭제 확인
        deleted_board = await board_service.get_board_by_id(board_id)
        assert deleted_board is None
        
        # 존재하지 않는 게시판 삭제 시도
        result = await board_service.delete_board(99999)
        assert result == False


@pytest.mark.asyncio
class TestBoardAPI:
    """게시판 API 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_get_boards_list(self, client):
        """게시판 목록 조회 API 테스트"""
        response = client.get("/boards")
        
        assert response.status_code == 200
        boards = response.json()
        assert isinstance(boards, list)
        assert len(boards) >= 3
        
        # 필수 필드 확인
        for board in boards:
            assert "id" in board
            assert "name" in board
            assert "slug" in board
            assert "description" in board
            assert "write_permission" in board
            assert "created_at" in board
    
    def test_get_board_by_slug(self, client):
        """slug로 게시판 조회 API 테스트"""
        response = client.get("/boards/notice")
        
        assert response.status_code == 200
        board = response.json()
        assert board["slug"] == "notice"
        assert board["name"] == "공지사항"
        assert board["write_permission"] == "admin"
    
    def test_get_board_by_slug_not_found(self, client):
        """존재하지 않는 slug로 게시판 조회 테스트"""
        response = client.get("/boards/nonexistent")
        
        assert response.status_code == 404
        assert "게시판을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_create_board_admin_required(self, client):
        """관리자 권한 없이 게시판 생성 시도 테스트"""
        board_data = {
            "name": "테스트게시판",
            "slug": "test_board",
            "description": "테스트용",
            "write_permission": "member"
        }
        
        # 인증 없이 요청
        response = client.post("/boards", json=board_data)
        assert response.status_code == 401
    
    def test_create_board_with_admin(self, client):
        """관리자 권한으로 게시판 생성 테스트"""
        # 관리자로 로그인 (실제 테스트에서는 관리자 토큰 필요)
        # 이 테스트는 인증 시스템과 통합하여 구현
        pass
    
    def test_create_board_validation_error(self, client):
        """잘못된 데이터로 게시판 생성 테스트"""
        # 필수 필드 누락
        invalid_data = {
            "description": "설명만 있음"
        }
        
        response = client.post("/boards", json=invalid_data)
        assert response.status_code == 422  # Validation Error
    
    def test_update_board_admin_required(self, client):
        """관리자 권한 없이 게시판 수정 시도 테스트"""
        update_data = {
            "name": "수정된 이름",
            "description": "수정된 설명"
        }
        
        response = client.put("/boards/1", json=update_data)
        assert response.status_code == 401
    
    def test_delete_board_admin_required(self, client):
        """관리자 권한 없이 게시판 삭제 시도 테스트"""
        response = client.delete("/boards/1")
        assert response.status_code == 401


class TestBoardPermissions:
    """게시판 권한 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_board_write_permissions(self, client):
        """게시판별 작성 권한 확인 테스트"""
        # notice: admin만 작성 가능
        response = client.get("/boards/notice")
        assert response.status_code == 200
        board = response.json()
        assert board["write_permission"] == "admin"
        
        # free: member 작성 가능
        response = client.get("/boards/free")
        assert response.status_code == 200
        board = response.json()
        assert board["write_permission"] == "member"
    
    def test_validate_write_permission_values(self, client):
        """write_permission 유효값 확인"""
        valid_permissions = ["all", "member", "admin"]
        
        for permission in valid_permissions:
            board_data = {
                "name": f"테스트_{permission}",
                "slug": f"test_{permission}",
                "description": f"{permission} 권한 테스트",
                "write_permission": permission
            }
            
            # 실제로는 관리자 인증이 필요하지만, 데이터 검증만 테스트
            response = client.post("/boards", json=board_data)
            # 인증 오류는 401, 데이터 검증 오류는 422
            assert response.status_code in [401, 201]  # 인증은 실패하지만 데이터 검증은 통과