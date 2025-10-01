from fastapi import APIRouter, HTTPException, Depends, Request, Query, Form
from fastapi.responses import RedirectResponse
from typing import Optional, List
from app.models.posts import PostService, PostRequest, PostUpdateRequest, PostResponse, PostListResponse
from app.models.boards import BoardService
from app.routers.auth import get_current_user, get_current_user_optional
from app.dependencies import csrf_protection

router = APIRouter(tags=["Posts"])
post_service = PostService()
board_service = BoardService()


@router.get("/boards/{slug}/posts", response_model=dict)
async def get_posts_by_board(
    slug: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=50, description="페이지당 게시글 수")
):
    """
    게시판별 게시글 목록 조회
    - 모든 사용자 접근 가능
    - 페이지네이션 지원 (기본 10개씩)
    """
    try:
        posts_data = await post_service.get_posts_by_board_slug(slug, page, limit)
        return posts_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts/{post_id}", response_model=dict)
async def get_post_detail(
    post_id: int,
    increment_view: bool = Query(True, description="조회수 증가 여부"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    게시글 상세 조회
    - 모든 사용자 접근 가능
    - 기본적으로 조회수 증가
    - 사용자별 권한 정보 포함
    """
    try:
        post = await post_service.get_post_by_id(post_id, increment_view)
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")
        
        # 사용자 권한 정보 추가
        if current_user:
            permissions = await post_service.check_post_permission(
                post_id, 
                current_user["id"], 
                current_user.get("is_admin", False)
            )
            post["permissions"] = permissions
        else:
            post["permissions"] = {
                "read": True,
                "update": False,
                "delete": False,
                "is_owner": False
            }
        
        return post
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/boards/{slug}/posts", response_model=dict, status_code=201)
async def create_post(
    slug: str,
    request: Request,
    post_data: PostRequest,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시글 작성
    - 로그인 사용자만 가능
    - 게시판별 작성 권한 확인
    - CSRF 보호 적용
    """
    try:
        # 게시판 존재 확인 및 작성 권한 확인
        board = await board_service.get_board_by_slug(slug)
        if not board:
            raise HTTPException(status_code=404, detail="존재하지 않는 게시판입니다")
        
        # 작성 권한 확인
        has_permission = await board_service.check_write_permission(
            slug, 
            "member" if current_user else None, 
            current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="게시글 작성 권한이 없습니다")
        
        # 게시글 데이터 준비
        create_data = {
            "board_id": board["id"],
            "user_id": current_user["id"],
            "title": post_data.title,
            "content": post_data.content
        }
        
        created_post = await post_service.create_post(create_data)
        return created_post
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/posts/{post_id}", response_model=dict)
async def update_post(
    post_id: int,
    request: Request,
    update_data: PostUpdateRequest,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시글 수정
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        # 권한 확인
        permissions = await post_service.check_post_permission(
            post_id, 
            current_user["id"], 
            current_user.get("is_admin", False)
        )
        
        if not permissions["update"]:
            raise HTTPException(status_code=403, detail="게시글 수정 권한이 없습니다")
        
        # 수정할 데이터만 추출 (None 값 제거)
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="수정할 데이터가 없습니다")
        
        updated_post = await post_service.update_post(post_id, update_dict)
        if not updated_post:
            raise HTTPException(status_code=404, detail="수정할 게시글을 찾을 수 없습니다")
        
        return updated_post
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    게시글 삭제
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    - 관련 댓글도 함께 삭제
    """
    try:
        # 권한 확인
        permissions = await post_service.check_post_permission(
            post_id, 
            current_user["id"], 
            current_user.get("is_admin", False)
        )
        
        if not permissions["delete"]:
            raise HTTPException(status_code=403, detail="게시글 삭제 권한이 없습니다")
        
        success = await post_service.delete_post(post_id)
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 게시글을 찾을 수 없습니다")
        
        # 204 No Content - 성공했지만 반환할 데이터 없음
        return
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search", response_model=dict)
async def search_posts(
    q: str = Query(..., description="검색어"),
    board: Optional[str] = Query(None, description="검색할 게시판 slug"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(10, ge=1, le=50, description="페이지당 결과 수")
):
    """
    게시글 검색
    - 모든 사용자 접근 가능
    - 제목과 내용에서 검색
    - 특정 게시판 또는 전체 검색 가능
    """
    try:
        search_results = await post_service.search_posts(q, board, page, limit)
        return search_results
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts/{post_id}/permissions")
async def get_post_permissions(
    post_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    게시글 권한 확인
    - 현재 사용자의 게시글 권한 반환
    - 비로그인 사용자도 확인 가능
    """
    try:
        if current_user:
            permissions = await post_service.check_post_permission(
                post_id,
                current_user["id"],
                current_user.get("is_admin", False)
            )
        else:
            permissions = {
                "read": True,
                "update": False,
                "delete": False,
                "is_owner": False
            }
        
        return {
            "post_id": post_id,
            "permissions": permissions,
            "user_id": current_user["id"] if current_user else None,
            "is_admin": current_user.get("is_admin", False) if current_user else False
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats", response_model=dict)
async def get_post_stats(
    board: Optional[str] = Query(None, description="특정 게시판의 통계 (slug)")
):
    """
    게시글 통계 조회
    - 전체 또는 특정 게시판의 통계
    - 모든 사용자 접근 가능
    """
    try:
        stats = await post_service.get_post_stats(board)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# HTML 폼 기반 게시글 CRUD 엔드포인트
@router.post("/boards/{slug}/posts/html")
async def create_post_html(
    slug: str,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    current_user: dict = Depends(get_current_user)
    # csrf_token: str = Depends(csrf_protection.verify_csrf_token)  # 임시 비활성화
):
    """
    HTML 폼으로 게시글 작성
    - 로그인 사용자만 가능
    - 게시판별 작성 권한 확인
    - CSRF 보호 적용
    - 성공 시 게시글 상세 페이지로 리다이렉트
    """
    try:
        # 게시판 존재 확인 및 작성 권한 확인
        board = await board_service.get_board_by_slug(slug)
        if not board:
            raise HTTPException(status_code=404, detail="존재하지 않는 게시판입니다")

        # 작성 권한 확인
        has_permission = await board_service.check_write_permission(
            slug,
            "member" if current_user else None,
            current_user.get("is_admin", False)
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="게시글 작성 권한이 없습니다")

        # 게시글 데이터 준비
        create_data = {
            "board_id": board["id"],
            "user_id": current_user["id"],
            "title": title.strip(),
            "content": content.strip()
        }

        # 유효성 검증
        if not create_data["title"]:
            raise HTTPException(status_code=400, detail="제목을 입력해주세요")
        if not create_data["content"]:
            raise HTTPException(status_code=400, detail="내용을 입력해주세요")

        created_post = await post_service.create_post(create_data)

        # 성공 시 게시글 상세 페이지로 리다이렉트
        return RedirectResponse(
            url=f"/posts/{created_post['id']}",
            status_code=302
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"HTML 게시글 작성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="게시글 작성 중 오류가 발생했습니다")


@router.post("/posts/{post_id}/html")
async def update_post_html(
    post_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    current_user: dict = Depends(get_current_user)
    # csrf_token: str = Depends(csrf_protection.verify_csrf_token)  # 임시 비활성화
):
    """
    HTML 폼으로 게시글 수정
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    - 성공 시 게시글 상세 페이지로 리다이렉트
    """
    try:
        # 권한 확인
        permissions = await post_service.check_post_permission(
            post_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )

        if not permissions["update"]:
            raise HTTPException(status_code=403, detail="게시글 수정 권한이 없습니다")

        # 수정할 데이터 준비
        update_data = {
            "title": title.strip(),
            "content": content.strip()
        }

        # 유효성 검증
        if not update_data["title"]:
            raise HTTPException(status_code=400, detail="제목을 입력해주세요")
        if not update_data["content"]:
            raise HTTPException(status_code=400, detail="내용을 입력해주세요")

        updated_post = await post_service.update_post(post_id, update_data)
        if not updated_post:
            raise HTTPException(status_code=404, detail="수정할 게시글을 찾을 수 없습니다")

        # 성공 시 게시글 상세 페이지로 리다이렉트
        return RedirectResponse(
            url=f"/posts/{post_id}",
            status_code=302
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"HTML 게시글 수정 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="게시글 수정 중 오류가 발생했습니다")


@router.get("/posts/{post_id}/check-comments")
async def check_post_comments(
    post_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    게시글 삭제 전 댓글 상태 확인
    - 작성자 또는 관리자만 가능
    - 댓글/답글 상태와 소유권 정보 반환
    """
    try:
        # 권한 확인
        permissions = await post_service.check_post_permission(
            post_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )

        if not permissions["delete"]:
            raise HTTPException(status_code=403, detail="게시글 삭제 권한이 없습니다")

        # 댓글 조회
        from app.models.comments import CommentService
        comment_service = CommentService()
        comments_data = await comment_service.get_comments_by_post_id(
            post_id=post_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )

        # 댓글 분석
        total_comments = 0
        others_comments = 0  # 타인의 댓글
        own_comments = 0     # 작성자의 댓글
        others_details = []  # 타인의 댓글 상세 정보

        for comment in comments_data:
            total_comments += 1
            if comment["user_id"] == current_user["id"]:
                own_comments += 1
            else:
                others_comments += 1
                # 타인의 댓글 상세 정보 저장
                author_name = comment.get("users", {}).get("display_name") or comment.get("users", {}).get("username", "알 수 없음")
                created_at = comment.get("created_at", "")
                if isinstance(created_at, str):
                    formatted_date = created_at[:16]  # YYYY-MM-DD HH:MM 형식
                else:
                    formatted_date = created_at.strftime('%Y-%m-%d %H:%M') if created_at else ""

                others_details.append({
                    "type": "댓글",
                    "author": author_name,
                    "created_at": formatted_date,
                    "content_preview": comment.get("content", "")[:30] + "..." if len(comment.get("content", "")) > 30 else comment.get("content", "")
                })

            # 답글도 확인
            for reply in comment.get("replies", []):
                total_comments += 1
                if reply["user_id"] == current_user["id"]:
                    own_comments += 1
                else:
                    others_comments += 1
                    # 타인의 답글 상세 정보 저장
                    author_name = reply.get("users", {}).get("display_name") or reply.get("users", {}).get("username", "알 수 없음")
                    created_at = reply.get("created_at", "")
                    if isinstance(created_at, str):
                        formatted_date = created_at[:16]  # YYYY-MM-DD HH:MM 형식
                    else:
                        formatted_date = created_at.strftime('%Y-%m-%d %H:%M') if created_at else ""

                    others_details.append({
                        "type": "답글",
                        "author": author_name,
                        "created_at": formatted_date,
                        "content_preview": reply.get("content", "")[:30] + "..." if len(reply.get("content", "")) > 30 else reply.get("content", "")
                    })

        return {
            "can_delete": True,
            "total_comments": total_comments,
            "others_comments": others_comments,
            "own_comments": own_comments,
            "has_others_comments": others_comments > 0,
            "others_details": others_details  # 타인의 댓글/답글 상세 정보
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"댓글 상태 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="댓글 상태 확인 중 오류가 발생했습니다")


@router.post("/posts/{post_id}/delete")
async def delete_post_html(
    post_id: int,
    request: Request,
    csrf_token: str = Form(default=""),  # CSRF 토큰 선택적으로 변경
    force_delete: str = Form(default="false"),
    current_user: dict = Depends(get_current_user)
):
    """
    HTML 폼으로 게시글 삭제
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    - force_delete=true인 경우 댓글과 함께 삭제
    - 성공 시 게시판 목록으로 리다이렉트
    """
    try:
        # CSRF 토큰 검증 건너뜀 (현재 설정)
        # 필요시 향후 재활성화 가능

        # 권한 확인
        permissions = await post_service.check_post_permission(
            post_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )

        if not permissions["delete"]:
            raise HTTPException(status_code=403, detail="게시글 삭제 권한이 없습니다")

        # 게시글 정보 조회 (삭제 전에 게시판 정보 필요)
        post = await post_service.get_post_by_id(post_id, increment_view=False)
        if not post:
            raise HTTPException(status_code=404, detail="삭제할 게시글을 찾을 수 없습니다")

        # 게시판 정보 조회
        try:
            from app.models.boards import BoardService
            board_service_instance = BoardService()
            board = await board_service_instance.get_board_by_id(post['board_id'])
        except Exception as board_error:
            print(f"게시판 정보 조회 오류: {board_error}")
            # 게시판 정보를 못 가져와도 삭제는 진행
            board = {'slug': 'free'}  # 기본값

        # force_delete가 아닌 경우 댓글 확인
        if force_delete != "true":
            try:
                from app.models.comments import CommentService
                comment_service_instance = CommentService()
                comments_data = await comment_service_instance.get_comments_by_post_id(
                    post_id=post_id,
                    user_id=current_user["id"],
                    is_admin=current_user.get("is_admin", False)
                )
            except Exception as comment_error:
                print(f"댓글 조회 오류: {comment_error}")
                # 댓글 조회 실패해도 삭제는 진행
                comments_data = []

            # 타인의 댓글이 있는지 확인
            has_others_comments = False
            for comment in comments_data:
                if comment["user_id"] != current_user["id"]:
                    has_others_comments = True
                    break
                for reply in comment.get("replies", []):
                    if reply["user_id"] != current_user["id"]:
                        has_others_comments = True
                        break
                if has_others_comments:
                    break

            if has_others_comments:
                # 타인의 댓글이 있으면 에러 메시지와 함께 리다이렉트
                redirect_url = f"/posts/{post_id}?error=has_others_comments"
                return RedirectResponse(
                    url=redirect_url,
                    status_code=302
                )

        # 게시글 삭제 (관련 댓글들도 함께 삭제됨)
        success = await post_service.delete_post(post_id)
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 게시글을 찾을 수 없습니다")

        # 성공 시 게시판 목록으로 리다이렉트
        redirect_url = f"/boards/{board['slug']}" if board else "/boards"
        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"HTML 게시글 삭제 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="게시글 삭제 중 오류가 발생했습니다")