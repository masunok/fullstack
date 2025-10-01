from fastapi import APIRouter, HTTPException, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from app.models.comments import CommentService, CommentRequest, CommentUpdateRequest, CommentResponse
from app.routers.auth import get_current_user, get_current_user_optional
from app.dependencies import csrf_protection

router = APIRouter(tags=["Comments"])
comment_service = CommentService()
templates = Jinja2Templates(directory="templates")


@router.get("/posts/{post_id}/comments", response_model=List[dict])
async def get_comments_by_post(
    post_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    게시글의 댓글 목록 조회
    - 모든 사용자 접근 가능
    - 계층 구조로 반환 (부모 댓글 + 답글들)
    """
    try:
        comments = await comment_service.get_comments_by_post_id(post_id)
        
        # 각 댓글에 사용자별 권한 정보 추가
        if current_user:
            for comment in comments:
                permissions = await comment_service.check_comment_permission(
                    comment["id"],
                    current_user["id"],
                    current_user.get("is_admin", False)
                )
                comment["permissions"] = permissions
                
                # 답글들에도 권한 정보 추가
                for reply in comment.get("replies", []):
                    reply_permissions = await comment_service.check_comment_permission(
                        reply["id"],
                        current_user["id"],
                        current_user.get("is_admin", False)
                    )
                    reply["permissions"] = reply_permissions
        else:
            # 비로그인 사용자는 읽기만 가능
            for comment in comments:
                comment["permissions"] = {
                    "read": True,
                    "update": False,
                    "delete": False,
                    "is_owner": False
                }
                for reply in comment.get("replies", []):
                    reply["permissions"] = {
                        "read": True,
                        "update": False,
                        "delete": False,
                        "is_owner": False
                    }
        
        return comments
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/posts/{post_id}/comments")
async def create_comment(
    post_id: int,
    request: Request,
    content: str = Form(...),
    parent_id: Optional[int] = Form(None),
    csrf_token: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    댓글 작성
    - 로그인 사용자만 가능
    - CSRF 보호 적용
    - 답글 작성도 지원 (parent_id 제공시)
    """
    try:
        print(f"댓글 작성 시작 - post_id: {post_id}, content: {content[:50]}..., parent_id: {parent_id}")

        # CSRF 토큰 검증
        session_id = request.cookies.get("session_id")
        if not session_id:
            print("CSRF 에러: 세션 ID 없음")
            raise HTTPException(status_code=403, detail="CSRF: Missing session")

        stored_token = csrf_protection.csrf_tokens.get(session_id)
        if not stored_token or stored_token != csrf_token:
            print(f"CSRF 에러: 토큰 불일치 - stored: {stored_token}, received: {csrf_token}")
            raise HTTPException(status_code=403, detail="CSRF: Invalid token")

        print("CSRF 토큰 검증 성공")

        # 댓글 데이터 준비
        create_data = {
            "post_id": post_id,
            "user_id": current_user["id"],
            "content": content.strip(),
            "parent_id": parent_id
        }

        # 유효성 검증
        if not create_data["content"]:
            raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요")

        created_comment = await comment_service.create_comment(create_data)

        # HTML 폼에서 온 요청인지 확인하고 적절히 응답
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            # HTML 폼 요청: 게시글 상세 페이지로 리다이렉트
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=f"/posts/{post_id}?from=comment#comments", status_code=302)
        else:
            # JSON API 요청: JSON 응답
            return created_comment

    except HTTPException:
        raise
    except ValueError as e:
        print(f"댓글 작성 ValueError: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"댓글 작성 Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/comments/{comment_id}", response_model=dict)
async def update_comment(
    comment_id: int,
    request: Request,
    update_data: CommentUpdateRequest,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    댓글 수정
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    """
    try:
        # 권한 확인
        permissions = await comment_service.check_comment_permission(
            comment_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )
        
        if not permissions["update"]:
            raise HTTPException(status_code=403, detail="댓글 수정 권한이 없습니다")
        
        updated_comment = await comment_service.update_comment(
            comment_id,
            {"content": update_data.content}
        )
        
        if not updated_comment:
            raise HTTPException(status_code=404, detail="수정할 댓글을 찾을 수 없습니다")
        
        return updated_comment
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
    csrf_token: str = Depends(csrf_protection.verify_csrf_token)
):
    """
    댓글 삭제
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    - 답글이 있는 댓글은 삭제 불가
    """
    try:
        # 권한 확인
        permissions = await comment_service.check_comment_permission(
            comment_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )
        
        if not permissions["delete"]:
            raise HTTPException(status_code=403, detail="댓글 삭제 권한이 없습니다")
        
        success = await comment_service.delete_comment(comment_id)
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 댓글을 찾을 수 없습니다")
        
        # 204 No Content - 성공했지만 반환할 데이터 없음
        return
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/comments/{comment_id}", response_model=dict)
async def get_comment_detail(
    comment_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    댓글 상세 조회
    - 모든 사용자 접근 가능
    - 사용자별 권한 정보 포함
    """
    try:
        comment = await comment_service.get_comment_by_id(comment_id)
        if not comment:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")
        
        # 사용자 권한 정보 추가
        if current_user:
            permissions = await comment_service.check_comment_permission(
                comment_id,
                current_user["id"],
                current_user.get("is_admin", False)
            )
            comment["permissions"] = permissions
        else:
            comment["permissions"] = {
                "read": True,
                "update": False,
                "delete": False,
                "is_owner": False
            }
        
        return comment
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/comments/{comment_id}/permissions")
async def get_comment_permissions(
    comment_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    댓글 권한 확인
    - 현재 사용자의 댓글 권한 반환
    - 비로그인 사용자도 확인 가능
    """
    try:
        if current_user:
            permissions = await comment_service.check_comment_permission(
                comment_id,
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
            "comment_id": comment_id,
            "permissions": permissions,
            "user_id": current_user["id"] if current_user else None,
            "is_admin": current_user.get("is_admin", False) if current_user else False
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/posts/{post_id}/comments/stats", response_model=dict)
async def get_comments_stats(
    post_id: int
):
    """
    특정 게시글의 댓글 통계 조회
    - 모든 사용자 접근 가능
    """
    try:
        stats = await comment_service.get_comment_stats(post_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/comments/stats", response_model=dict)
async def get_all_comments_stats():
    """
    전체 댓글 통계 조회
    - 모든 사용자 접근 가능
    """
    try:
        stats = await comment_service.get_comment_stats()
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# HTMX 지원을 위한 HTML 응답 라우터들

@router.get("/posts/{post_id}/comments/html", response_class=HTMLResponse)
async def get_comments_html(
    request: Request,
    post_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    HTMX용 댓글 목록 HTML 조회
    """
    try:
        comments = await comment_service.get_comments_by_post_id(post_id)

        # 권한 정보 추가 (기존 로직과 동일)
        if current_user:
            for comment in comments:
                permissions = await comment_service.check_comment_permission(
                    comment["id"],
                    current_user["id"],
                    current_user.get("is_admin", False)
                )
                comment["permissions"] = permissions

                for reply in comment.get("replies", []):
                    reply_permissions = await comment_service.check_comment_permission(
                        reply["id"],
                        current_user["id"],
                        current_user.get("is_admin", False)
                    )
                    reply["permissions"] = reply_permissions
        else:
            for comment in comments:
                comment["permissions"] = {
                    "read": True,
                    "update": False,
                    "delete": False,
                    "is_owner": False
                }
                for reply in comment.get("replies", []):
                    reply["permissions"] = {
                        "read": True,
                        "update": False,
                        "delete": False,
                        "is_owner": False
                    }

        return templates.TemplateResponse("components/comments_list.html", {
            "request": request,
            "comments": comments,
            "current_user": current_user,
            "post_id": post_id
        })

    except Exception as e:
        # 에러 시 기본 에러 메시지 HTML 반환
        return templates.TemplateResponse("components/comments_list.html", {
            "request": request,
            "comments": [],
            "current_user": current_user,
            "post_id": post_id,
            "error": "댓글을 불러올 수 없습니다."
        })


@router.post("/posts/{post_id}/comments/html", response_class=HTMLResponse)
async def create_comment_html(
    request: Request,
    post_id: int,
    content: str = Form(...),
    parent_id: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user)
    # csrf_token: str = Depends(csrf_protection.verify_csrf_token)  # 임시 비활성화
):
    """
    HTMX용 댓글 작성 후 HTML 응답
    """
    try:
        print(f"댓글 작성 요청 - post_id: {post_id}, content: {content}, parent_id: {parent_id}, user_id: {current_user.get('id')}")
        # 댓글 데이터 준비
        create_data = {
            "post_id": post_id,
            "user_id": current_user["id"],
            "content": content,
            "parent_id": parent_id
        }

        await comment_service.create_comment(create_data)

        # 댓글 작성 후 전체 댓글 목록을 다시 조회하여 반환
        comments = await comment_service.get_comments_by_post_id(post_id)

        # 권한 정보 추가
        for comment in comments:
            permissions = await comment_service.check_comment_permission(
                comment["id"],
                current_user["id"],
                current_user.get("is_admin", False)
            )
            comment["permissions"] = permissions

            for reply in comment.get("replies", []):
                reply_permissions = await comment_service.check_comment_permission(
                    reply["id"],
                    current_user["id"],
                    current_user.get("is_admin", False)
                )
                reply["permissions"] = reply_permissions

        return templates.TemplateResponse("components/comments_list.html", {
            "request": request,
            "comments": comments,
            "current_user": current_user,
            "post_id": post_id
        })

    except ValueError as e:
        # 에러 시 현재 댓글 목록 반환 (에러 메시지 포함)
        comments = await comment_service.get_comments_by_post_id(post_id)
        return templates.TemplateResponse("components/comments_list.html", {
            "request": request,
            "comments": comments,
            "current_user": current_user,
            "post_id": post_id,
            "error": str(e)
        })


# 간단한 폼 기반 댓글 작성 (HTMX 대신)
@router.post("/posts/{post_id}/comments/simple")
async def create_comment_simple(
    post_id: int,
    request: Request,
    content: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    간단한 폼 기반 댓글 작성 (리다이렉트 방식)
    """
    try:
        print(f"간단 댓글 작성 - post_id: {post_id}, content: {content[:50]}..., user_id: {current_user.get('id')}")

        # 댓글 데이터 준비
        create_data = {
            "post_id": post_id,
            "user_id": current_user["id"],
            "content": content.strip(),
            "parent_id": None  # 간단 버전에서는 답글 지원하지 않음
        }

        # 유효성 검증
        if not create_data["content"]:
            raise HTTPException(status_code=400, detail="댓글 내용을 입력해주세요")

        created_comment = await comment_service.create_comment(create_data)
        print(f"댓글 생성 성공: {created_comment}")

        # 성공 시 게시글 상세 페이지로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"/posts/{post_id}#comments",
            status_code=302
        )

    except Exception as e:
        print(f"간단 댓글 작성 실패: {str(e)}")
        # 에러 발생 시에도 게시글 상세로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"/posts/{post_id}",
            status_code=302
        )


@router.delete("/comments/{comment_id}/html", response_class=HTMLResponse)
async def delete_comment_html(
    request: Request,
    comment_id: int,
    current_user: dict = Depends(get_current_user)
    # csrf_token: str = Depends(csrf_protection.verify_csrf_token)  # 임시 비활성화
):
    """
    HTMX용 댓글 삭제 후 빈 응답 (해당 요소 제거)
    """
    try:
        # 댓글 삭제 전에 post_id 저장
        comment_data = await comment_service.get_comment_by_id(comment_id)
        if not comment_data:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")

        # 권한 확인
        permissions = await comment_service.check_comment_permission(
            comment_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )

        if not permissions["delete"]:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다")

        await comment_service.delete_comment(comment_id)

        # 빈 응답 반환 (해당 댓글 요소가 DOM에서 제거됨)
        return HTMLResponse(content="", status_code=200)

    except Exception as e:
        # 에러 시 에러 메시지 반환
        return HTMLResponse(
            content=f'<div class="text-red-500 text-sm">삭제 실패: {str(e)}</div>',
            status_code=400
        )


@router.post("/comments/{comment_id}/delete")
async def delete_comment_html_form(
    comment_id: int,
    request: Request,
    csrf_token: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    HTML 폼으로 댓글 삭제
    - 작성자 또는 관리자만 가능
    - CSRF 보호 적용
    - 성공 시 게시글 상세 페이지로 리다이렉트
    """
    try:
        # CSRF 토큰 검증
        await csrf_protection.verify_csrf_token(request)

        # 댓글 정보 조회 (삭제 전에 post_id 필요)
        comment_data = await comment_service.get_comment_by_id(comment_id)
        if not comment_data:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다")

        post_id = comment_data["post_id"]

        # 권한 확인
        permissions = await comment_service.check_comment_permission(
            comment_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )

        if not permissions["delete"]:
            raise HTTPException(status_code=403, detail="댓글 삭제 권한이 없습니다")

        # 댓글 삭제
        success = await comment_service.delete_comment(comment_id)
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 댓글을 찾을 수 없습니다")

        # 성공 시 게시글 상세 페이지로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"/posts/{post_id}#comments",
            status_code=302
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"HTML 댓글 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="댓글 삭제 중 오류가 발생했습니다")