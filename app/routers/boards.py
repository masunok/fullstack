from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from app.models.boards import BoardService, BoardRequest, BoardUpdateRequest, BoardResponse
from app.routers.auth import get_current_user, get_current_user_optional
from app.utils.csrf import CSRFProtection

router = APIRouter(prefix="/boards", tags=["Boards"])
board_service = BoardService()
csrf_protection = CSRFProtection()


@router.get("/", response_model=List[dict])
async def get_boards():
    """
    게시판 목록 조회
    - 모든 사용자 접근 가능
    - 게시판 기본 정보 반환
    """
    try:
        boards = await board_service.get_all_boards()
        return boards
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{slug}", response_model=dict)
async def get_board_by_slug(slug: str):
    """
    slug로 게시판 상세 조회
    - 모든 사용자 접근 가능
    - 존재하지 않는 게시판은 404 반환
    """
    try:
        board = await board_service.get_board_by_slug(slug)
        if not board:
            raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다")
        return board
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{board_id}/stats", response_model=dict)
async def get_board_stats(board_id: int):
    """
    게시판 통계 조회 (게시글 수, 최근 게시글)
    - 모든 사용자 접근 가능
    """
    try:
        stats = await board_service.get_board_stats(board_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=dict, status_code=201)
async def create_board(
    request: Request,
    board_data: BoardRequest,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 생성
    - 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        # 관리자 권한 확인
        if not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
        # write_permission 값 검증
        valid_permissions = ["all", "member", "admin"]
        if board_data.write_permission not in valid_permissions:
            raise HTTPException(
                status_code=400, 
                detail=f"write_permission은 {', '.join(valid_permissions)} 중 하나여야 합니다"
            )
        
        created_board = await board_service.create_board(board_data.dict())
        return created_board
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{board_id}", response_model=dict)
async def update_board(
    board_id: int,
    request: Request,
    update_data: BoardUpdateRequest,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 수정
    - 관리자만 가능
    - CSRF 보호 적용
    - slug는 수정 불가
    """
    try:
        # 관리자 권한 확인
        if not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
        # write_permission 값 검증
        if update_data.write_permission:
            valid_permissions = ["all", "member", "admin"]
            if update_data.write_permission not in valid_permissions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"write_permission은 {', '.join(valid_permissions)} 중 하나여야 합니다"
                )
        
        # 수정할 데이터만 추출 (None 값 제거)
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="수정할 데이터가 없습니다")
        
        updated_board = await board_service.update_board(board_id, update_dict)
        if not updated_board:
            raise HTTPException(status_code=404, detail="수정할 게시판을 찾을 수 없습니다")
        
        return updated_board
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{board_id}", status_code=204)
async def delete_board(
    board_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 삭제
    - 관리자만 가능
    - CSRF 보호 적용
    - 게시글이 있는 게시판은 삭제 불가
    """
    try:
        # 관리자 권한 확인
        if not current_user.get("is_admin", False):
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
        
        success = await board_service.delete_board(board_id)
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 게시판을 찾을 수 없습니다")
        
        # 204 No Content - 성공했지만 반환할 데이터 없음
        return
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{slug}/write-permission")
async def check_write_permission(
    slug: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    게시판 작성 권한 확인
    - 로그인하지 않은 사용자도 확인 가능
    - 권한 여부를 boolean으로 반환
    """
    try:
        user_role = "member" if current_user else None
        is_admin = current_user.get("is_admin", False) if current_user else False
        
        has_permission = await board_service.check_write_permission(slug, user_role, is_admin)
        
        return {
            "board_slug": slug,
            "has_write_permission": has_permission,
            "user_role": user_role,
            "is_admin": is_admin
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")