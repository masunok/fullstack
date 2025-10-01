from fastapi import APIRouter, HTTPException, Depends, Request, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
from app.models.admin import AdminService, UserUpdateRequest, UserResponse
from app.routers.auth import get_current_user
from app.dependencies import csrf_protection

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_service = AdminService()
templates = Jinja2Templates(directory="templates")


def verify_admin_permission(current_user: dict = Depends(get_current_user)):
    """관리자 권한 확인"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return current_user


# HTML 페이지 라우트들 (더 구체적인 경로를 먼저 정의)
@router.get("/users/page", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    page: int = Query(1, ge=1, description="페이지 번호"),
    q: Optional[str] = Query(None, description="검색어"),
    search_type: Optional[str] = Query("all", description="검색 범위"),
    role: Optional[str] = Query("all", description="권한 필터"),
    sort: Optional[str] = Query("created_desc", description="정렬 방식"),
    include_deleted: Optional[bool] = Query(False, description="삭제된 사용자 포함"),
    current_admin: dict = Depends(verify_admin_permission)
):
    """관리자 사용자 관리 페이지"""
    try:
        # 세션 ID 확인 및 생성
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = csrf_protection.generate_session_id()

        # CSRF 토큰 가져오기 또는 생성
        csrf_token = csrf_protection.get_or_create_csrf_token(session_id)

        # 파라미터 정규화 (빈 문자열을 기본값으로 변환)
        if not role or role.strip() == "":
            role = "all"
        if not search_type or search_type.strip() == "":
            search_type = "all"
        if not sort or sort.strip() == "":
            sort = "created_desc"

        # 사용자 목록 조회 (검색/필터 적용)
        if include_deleted:
            # 삭제된 사용자 포함하여 조회
            if q and q.strip():
                # 삭제된 사용자 포함 검색
                users_data = await admin_service.search_users_including_deleted(q.strip(), page, 20, search_type, role, sort)
            else:
                # 모든 사용자 조회 (삭제된 사용자 포함, 필터 적용)
                users_data = await admin_service.get_all_users_including_deleted(page, 20, role, sort)
        else:
            # 기존 로직 (삭제된 사용자 제외)
            if q and q.strip():
                users_data = await admin_service.search_users_with_filters(q.strip(), page, 20, search_type, role, sort)
            else:
                users_data = await admin_service.get_all_users_with_filters(page, 20, role, sort)

        # 관리자 통계 조회 (검색/필터 적용)
        stats = await admin_service.get_filtered_admin_stats(
            query=q,
            search_type=search_type,
            role=role,
            include_deleted=include_deleted
        )

        # Enhanced pagination data with Flask-style properties
        current_page = users_data.get("page", 1)
        total_pages = users_data.get("total_pages", 1)

        pagination = {
            "page": current_page,
            "total_pages": total_pages,
            "total_count": users_data.get("total_count", 0),
            "limit": users_data.get("limit", 20),
            "has_prev": current_page > 1,
            "has_next": current_page < total_pages,
            "prev_num": max(1, current_page - 1),
            "next_num": min(total_pages, current_page + 1)
        }

        # 템플릿 응답 생성
        response = templates.TemplateResponse("pages/admin_users.html", {
            "request": request,
            "current_user": current_admin,
            "users": users_data.get("users", []),
            "pagination": pagination,
            "stats": stats,
            "csrf_token": csrf_token,
            "include_deleted": include_deleted,
            "search_params": {
                "q": q or "",
                "search_type": search_type or "all",
                "role": role or "all",
                "sort": sort or "created_desc"
            }
        })

        # 세션 ID가 없었다면 쿠키 설정
        if not request.cookies.get("session_id"):
            response.set_cookie(
                "session_id",
                session_id,
                httponly=True,
                secure=False,  # 개발환경
                samesite="lax",
                max_age=24*60*60  # 24시간
            )

        return response
    except Exception as e:
        print(f"관리자 사용자 페이지 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="페이지를 불러올 수 없습니다")


@router.get("/boards/page", response_class=HTMLResponse)
async def admin_boards_page(
    request: Request,
    current_admin: dict = Depends(verify_admin_permission)
):
    """관리자 게시판 관리 페이지"""
    try:
        # 세션 ID 확인 및 생성
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = csrf_protection.generate_session_id()

        # CSRF 토큰 가져오기 또는 생성
        csrf_token = csrf_protection.get_or_create_csrf_token(session_id)

        # 게시판 목록 조회
        from app.models.boards import BoardService
        board_service = BoardService()
        boards = await board_service.get_all_boards_with_stats()

        # 관리자 통계 조회
        stats = await admin_service.get_admin_stats()

        # 템플릿 응답 생성
        response = templates.TemplateResponse("pages/admin_boards.html", {
            "request": request,
            "current_user": current_admin,
            "boards": boards,
            "stats": stats,
            "csrf_token": csrf_token
        })

        # 세션 ID가 없었다면 쿠키 설정
        if not request.cookies.get("session_id"):
            response.set_cookie(
                "session_id",
                session_id,
                httponly=True,
                secure=False,  # 개발환경
                samesite="lax",
                max_age=24*60*60  # 24시간
            )

        return response
    except Exception as e:
        print(f"관리자 게시판 페이지 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="페이지를 불러올 수 없습니다")


# API 라우트들
@router.get("/users", response_model=dict)
async def get_all_users(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 사용자 수"),
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    모든 사용자 목록 조회
    - 관리자만 접근 가능
    - 페이지네이션 지원 (기본 20개씩)
    - 각 사용자별 게시글/댓글 통계 포함
    """
    try:
        users_data = await admin_service.get_all_users(page, limit)
        return users_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}", response_model=dict)
async def get_user_detail(
    user_id: str,
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    특정 사용자 상세 정보 조회
    - 관리자만 접근 가능
    - 사용자 통계 포함
    """
    try:
        user = await admin_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
        
        return user
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{user_id}", response_model=dict)
async def update_user_permissions(
    user_id: str,
    request: Request,
    update_data: UserUpdateRequest,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    사용자 권한 변경
    - 관리자만 가능
    - CSRF 보호 적용
    - 마지막 관리자의 권한 해제 방지
    """
    try:
        updated_user = await admin_service.update_user_permissions(
            user_id,
            {"is_admin": update_data.is_admin}
        )
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="수정할 사용자를 찾을 수 없습니다")
        
        return updated_user
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    사용자 삭제 (비활성화)
    - 관리자만 가능
    - CSRF 보호 적용
    - 마지막 관리자는 삭제 불가
    - 게시글/댓글이 있는 사용자는 비활성화만 수행
    """
    try:
        # 자기 자신 삭제 방지
        if user_id == current_admin["id"]:
            raise HTTPException(status_code=400, detail="자기 자신은 삭제할 수 없습니다")
        
        success = await admin_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 사용자를 찾을 수 없습니다")
        
        # 204 No Content - 성공했지만 반환할 데이터 없음
        return
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/users/{user_id}/restore", status_code=204)
async def restore_user(
    user_id: str,
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    사용자 복원 (Soft Delete된 사용자 활성화)
    - 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        success = await admin_service.restore_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="복원할 사용자를 찾을 수 없습니다")
        
        # 204 No Content - 성공했지만 반환할 데이터 없음
        return
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/search", response_model=dict)
async def search_users(
    q: str = Query(..., description="검색어"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 결과 수"),
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    사용자 검색
    - 관리자만 접근 가능
    - 사용자명과 표시이름에서 검색
    """
    try:
        search_results = await admin_service.search_users(q, page, limit)
        return search_results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=dict)
async def get_admin_dashboard_stats(
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    관리자 대시보드 통계
    - 관리자만 접근 가능
    - 전체 사용자/게시글/댓글 수
    - 오늘 가입자/게시글 수 등
    """
    try:
        stats = await admin_service.get_admin_stats()
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/logs", response_model=dict)
async def get_admin_logs(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(50, ge=1, le=200, description="페이지당 로그 수"),
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    관리자 활동 로그 조회
    - 관리자만 접근 가능
    - 향후 확장을 위한 placeholder
    """
    # 현재는 기본적인 구조만 제공
    # 실제 로그 테이블이 있다면 여기서 조회
    return {
        "logs": [],
        "total_count": 0,
        "page": page,
        "limit": limit,
        "total_pages": 1,
        "message": "로그 시스템은 향후 구현 예정입니다"
    }


@router.get("/system/health", response_model=dict)
async def get_system_health(
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    시스템 상태 확인
    - 관리자만 접근 가능
    - 데이터베이스 연결 상태 등 확인
    """
    try:
        # 데이터베이스 연결 테스트
        test_response = admin_service.supabase.table("users").select("id").limit(1).execute()
        
        db_status = "healthy" if test_response else "error"
        
        return {
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }


@router.get("/users/{user_id}/content-check", response_model=dict)
async def check_user_content(
    user_id: str,
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    사용자가 작성한 게시글/댓글 존재 여부 확인
    - 관리자만 접근 가능
    - 사용자 삭제 전 확인용
    """
    try:
        content_info = await admin_service.check_user_content(user_id)
        return content_info
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/users/bulk-delete")
async def bulk_delete_users(
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    사용자 일괄 삭제
    - 관리자만 가능
    - CSRF 보호 적용
    - Form 데이터로 user_ids 배열 수신
    """
    try:
        # Form 데이터에서 user_ids 추출
        form_data = await request.form()
        user_ids = form_data.getlist("user_ids")

        if not user_ids:
            raise HTTPException(status_code=400, detail="삭제할 사용자를 선택해주세요")

        # AdminService의 일괄 삭제 메서드 호출
        result = await admin_service.bulk_delete_users(user_ids, current_admin["id"])

        # 결과 반환
        return {
            "success": True,
            "message": f"{result['success']}명 삭제 완료",
            "details": {
                "success_count": result["success"],
                "failed_count": result["failed"],
                "errors": result["errors"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/users/bulk-promote")
async def bulk_promote_users(
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    사용자 일괄 승급 (관리자 권한 부여)
    - 관리자만 가능
    - CSRF 보호 적용
    - Form 데이터로 user_ids 배열 수신
    """
    try:
        # Form 데이터에서 user_ids 추출
        form_data = await request.form()
        user_ids = form_data.getlist("user_ids")

        if not user_ids:
            raise HTTPException(status_code=400, detail="승급할 사용자를 선택해주세요")

        # AdminService의 일괄 승급 메서드 호출
        result = await admin_service.bulk_promote_users(user_ids)

        # 결과 반환
        return {
            "success": True,
            "message": f"{result['success']}명 승급 완료",
            "details": {
                "success_count": result["success"],
                "failed_count": result["failed"],
                "errors": result["errors"]
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{user_id}/demote", response_model=dict)
async def demote_user(
    user_id: str,
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    단일 사용자 강등 (관리자 권한 제거)
    - 관리자만 가능
    - CSRF 보호 적용
    - 마지막 관리자 보호
    """
    try:
        # 자기 자신 강등 방지
        if user_id == current_admin["id"]:
            raise HTTPException(status_code=400, detail="자기 자신은 강등할 수 없습니다")

        # 강등 실행
        updated_user = await admin_service.update_user_permissions(
            user_id,
            {"is_admin": False}
        )

        if not updated_user:
            raise HTTPException(status_code=404, detail="강등할 사용자를 찾을 수 없습니다")

        return {
            "success": True,
            "message": f"{updated_user['username']} 사용자를 일반 사용자로 강등했습니다",
            "user": updated_user
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/users/bulk-demote")
async def bulk_demote_users(
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    사용자 일괄 강등 (관리자 권한 제거)
    - 관리자만 가능
    - CSRF 보호 적용
    - Form 데이터로 user_ids 배열 수신
    """
    try:
        # Form 데이터에서 user_ids 추출
        form_data = await request.form()
        user_ids = form_data.getlist("user_ids")

        if not user_ids:
            raise HTTPException(status_code=400, detail="강등할 사용자를 선택해주세요")

        # AdminService의 일괄 강등 메서드 호출
        result = await admin_service.bulk_demote_users(user_ids, current_admin["id"])

        # 결과 반환
        return {
            "success": True,
            "message": f"{result['success']}명 강등 완료",
            "details": {
                "success_count": result["success"],
                "failed_count": result["failed"],
                "errors": result["errors"]
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# 게시판 관리 엔드포인트
# ============================================================================

@router.post("/boards", status_code=201)
async def create_board(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: Optional[str] = Form(None),
    write_permission: str = Form("member"),
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    새 게시판 생성
    - 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        from app.models.boards import BoardService, BoardRequest
        
        board_service = BoardService()
        board_data = BoardRequest(
            name=name,
            slug=slug,
            description=description,
            write_permission=write_permission
        )
        
        # 게시판 생성
        new_board = await board_service.create_board(board_data.dict())
        
        # 성공 시 게시판 관리 페이지로 리다이렉트
        return RedirectResponse(
            url="/admin/boards/page?message=게시판이 성공적으로 생성되었습니다",
            status_code=303
        )
        
    except ValueError as e:
        # 실패 시 에러 메시지와 함께 리다이렉트
        return RedirectResponse(
            url=f"/admin/boards/page?error={str(e)}",
            status_code=303
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="게시판 생성 중 오류가 발생했습니다")


@router.get("/boards/{board_id}", status_code=200)
async def get_board(
    board_id: int,
    request: Request,
    current_admin: dict = Depends(verify_admin_permission)
):
    """
    게시판 개별 조회
    - 관리자만 가능
    - 편집 폼에서 사용
    """
    try:
        from app.models.boards import BoardService
        
        board_service = BoardService()
        board = await board_service.get_board_by_id(board_id)
        
        if not board:
            raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다")
        
        # 편집용 새로운 CSRF 토큰 생성
        session_id = request.cookies.get("session_id")
        new_csrf_token = None
        
        if session_id:
            new_csrf_token = csrf_protection.get_or_create_csrf_token(session_id)
        
        return {
            "success": True,
            "board": board,
            "csrf_token": new_csrf_token
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="게시판 조회 중 오류가 발생했습니다")


@router.put("/boards/{board_id}", status_code=200)
async def update_board(
    board_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    write_permission: str = Form("member"),
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 수정 (REST API)
    - 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        from app.models.boards import BoardService, BoardUpdateRequest
        
        board_service = BoardService()
        update_data = BoardUpdateRequest(
            name=name,
            description=description,
            write_permission=write_permission
        )
        
        # 게시판 수정
        updated_board = await board_service.update_board(board_id, update_data.dict(exclude_unset=True))
        
        return RedirectResponse(
            url="/admin/boards/page?message=게시판이 성공적으로 수정되었습니다",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/boards/page?error={str(e)}",
            status_code=303
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="게시판 수정 중 오류가 발생했습니다")


@router.post("/boards/{board_id}", status_code=200)
async def update_board_form(
    board_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    write_permission: str = Form("member"),
    method_override: Optional[str] = Form(None, alias="_method"),  # HTTP Method Override
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 수정 (Form 요청)
    - 관리자만 가능
    - CSRF 보호 적용
    - HTTP Method Override 지원 (_method=PUT)
    """
    # PUT 메서드가 아니면 에러
    if method_override != "PUT":
        raise HTTPException(status_code=405, detail="PUT 메서드만 지원됩니다")
    
    try:
        from app.models.boards import BoardService, BoardUpdateRequest
        
        board_service = BoardService()
        update_data = BoardUpdateRequest(
            name=name,
            description=description,
            write_permission=write_permission
        )
        
        # 게시판 수정
        updated_board = await board_service.update_board(board_id, update_data.dict(exclude_unset=True))
        
        return RedirectResponse(
            url="/admin/boards/page?message=게시판이 성공적으로 수정되었습니다",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/boards/page?error={str(e)}",
            status_code=303
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="게시판 수정 중 오류가 발생했습니다")


@router.delete("/boards/{board_id}", status_code=200)
async def delete_board(
    board_id: int,
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 삭제 (REST API)
    - 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        from app.models.boards import BoardService
        
        board_service = BoardService()
        
        # 게시판에 게시글이 있는지 확인
        board_stats = await board_service.get_board_stats(board_id)
        if board_stats and board_stats.get("posts_count", 0) > 0:
            return {
                "success": False,
                "message": "게시글이 있는 게시판은 삭제할 수 없습니다. 게시글을 먼저 삭제해주세요."
            }
        
        # 게시판 삭제
        await board_service.delete_board(board_id)
        
        return {
            "success": True,
            "message": "게시판이 성공적으로 삭제되었습니다."
        }
        
    except ValueError as e:
        return {
            "success": False,
            "message": str(e)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="게시판 삭제 중 오류가 발생했습니다")


@router.post("/boards/{board_id}/delete", status_code=200)
async def delete_board_form(
    board_id: int,
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시판 삭제 (Form 요청)
    - 관리자만 가능
    - CSRF 보호 적용
    - 프론트엔드 폼에서 사용
    """
    try:
        from app.models.boards import BoardService
        
        board_service = BoardService()
        
        # 게시판에 게시글이 있는지 확인
        board_stats = await board_service.get_board_stats(board_id)
        if board_stats and board_stats.get("posts_count", 0) > 0:
            error_message = "게시글이 있는 게시판은 삭제할 수 없습니다. 게시글을 먼저 삭제해주세요."
            return RedirectResponse(
                url=f"/admin/boards/page?error={error_message}",
                status_code=303
            )
        
        # 게시판 삭제
        await board_service.delete_board(board_id)
        
        success_message = "게시판이 성공적으로 삭제되었습니다."
        return RedirectResponse(
            url=f"/admin/boards/page?message={success_message}",
            status_code=303
        )
        
    except ValueError as e:
        return RedirectResponse(
            url=f"/admin/boards/page?error={str(e)}",
            status_code=303
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="게시판 삭제 중 오류가 발생했습니다")


# ============================================================================
# 시퀀스 수정 엔드포인트 (디버깅용)
# ============================================================================

@router.post("/fix-sequences", status_code=200)
async def fix_sequences(
    request: Request,
    current_admin: dict = Depends(verify_admin_permission),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    테이블 시퀀스 수정 (관리자 전용)
    - 게시판 테이블의 ID 시퀀스를 올바르게 재설정
    """
    try:
        from app.models.boards import BoardService
        
        board_service = BoardService()
        
        # 현재 최대 ID 조회
        max_id_result = board_service.supabase.table('boards').select('id').order('id', desc=True).limit(1).execute()
        max_id = max_id_result.data[0]['id'] if max_id_result.data else 0
        
        return {
            "success": False,
            "message": f"PostgreSQL 함수가 생성되지 않았습니다. Supabase SQL Editor에서 다음 함수를 먼저 생성하세요.",
            "details": {
                "current_max_id": max_id,
                "required_next_id": max_id + 1,
                "instruction": "Supabase Dashboard → SQL Editor에서 fix_boards_sequence() 함수를 생성하고 다시 시도하세요."
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"시퀀스 수정 중 오류 발생: {str(e)}"
        }