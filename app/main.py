from fastapi import FastAPI, Request, HTTPException, Response, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from urllib.parse import unquote
import os

# 환경변수 로드
load_dotenv()

app = FastAPI(title="AIZEVA", description="다중 게시판 커뮤니티 서비스")

# Templates
templates = Jinja2Templates(directory="templates")

# 전역 CSRF 보호 인스턴스 가져오기
from app.dependencies import csrf_protection


# HTML 페이지 라우터 (API 라우터보다 먼저 등록)
@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # 세션 ID 확인 및 생성
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = csrf_protection.generate_session_id()

    # CSRF 토큰 가져오기 또는 생성
    csrf_token = csrf_protection.get_or_create_csrf_token(session_id)

    # 로그인 오류 메시지 확인 (쿠키)
    login_error = request.cookies.get("login_error")
    messages = []
    if login_error:
        # URL 인코딩된 오류 메시지 디코딩
        try:
            decoded_error = unquote(login_error)
        except Exception:
            decoded_error = "로그인 중 오류가 발생했습니다."
        
        messages.append({
            "category": "error",
            "content": decoded_error
        })

    # 성공 메시지 확인 (URL 파라미터)
    success_message = request.query_params.get("message")
    if success_message:
        try:
            decoded_message = unquote(success_message)
        except Exception:
            decoded_message = success_message
        
        messages.append({
            "category": "success",
            "content": decoded_message
        })

    # 템플릿 응답 생성
    response = templates.TemplateResponse("pages/login.html", {
        "request": request,
        "csrf_token": csrf_token,
        "current_user": None,
        "messages": messages
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

    # 로그인 오류 쿠키 삭제 (한 번만 표시)
    if login_error:
        response.delete_cookie("login_error")

    return response

@app.get("/auth/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    # 세션 ID 확인 및 생성
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = csrf_protection.generate_session_id()

    # CSRF 토큰 가져오기 또는 생성
    csrf_token = csrf_protection.get_or_create_csrf_token(session_id)

    # 템플릿 응답 생성
    response = templates.TemplateResponse("pages/signup.html", {
        "request": request,
        "csrf_token": csrf_token,
        "current_user": None
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

@app.get("/boards", response_class=HTMLResponse)
async def boards_page(request: Request):
    # CSRF 토큰 생성
    csrf_token = csrf_protection.generate_csrf_token()

    # 현재 사용자 정보 확인
    from app.routers.auth import get_current_user_optional
    try:
        current_user = await get_current_user_optional(request)
    except Exception:
        current_user = None

    # 게시판 목록 조회 (통계 포함)
    from app.models.boards import BoardService
    from app.models.posts import PostService

    board_service = BoardService()
    post_service = PostService()

    try:
        # 모든 게시판의 통계를 포함하여 조회
        boards = await board_service.get_popular_boards_with_stats(limit=100)  # 모든 게시판을 가져오기 위해 충분히 큰 limit 설정
        # ID 순으로 다시 정렬 (생성 순서대로)
        boards.sort(key=lambda x: x['id'])
    except Exception as e:
        print(f"게시판 목록 조회 실패: {str(e)}")
        boards = []

    # 최신 게시글 목록 조회
    try:
        latest_posts = await post_service.get_latest_posts_for_main(limit=15)  # 더 많은 게시글 표시
    except Exception as e:
        print(f"최신 게시글 조회 실패: {str(e)}")
        latest_posts = []

    return templates.TemplateResponse("pages/boards.html", {
        "request": request,
        "csrf_token": csrf_token,
        "current_user": current_user,
        "boards": boards,
        "latest_posts": latest_posts
    })

@app.get("/boards/{slug}", response_class=HTMLResponse)
async def board_detail_page(request: Request, slug: str):
    # CSRF 토큰 생성
    csrf_token = csrf_protection.generate_csrf_token()

    # 현재 사용자 정보 확인
    from app.routers.auth import get_current_user_optional
    try:
        current_user = await get_current_user_optional(request)
    except Exception:
        current_user = None

    # 게시판 및 게시글 조회
    from app.models.boards import BoardService
    from app.models.posts import PostService

    board_service = BoardService()
    post_service = PostService()

    try:
        # 게시판 정보 조회
        board = await board_service.get_board_by_slug(slug)
        if not board:
            raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다")

        # 게시글 목록 조회 (페이지네이션: 기본 1페이지, 10개씩)
        try:
            page = int(request.query_params.get("page", "1"))
        except (ValueError, TypeError):
            page = 1
        search = request.query_params.get("search", "")

        posts_data = await post_service.get_posts_by_board_slug(
            board_slug=slug,
            page=page,
            limit=10
        )

        return templates.TemplateResponse("pages/board_detail.html", {
            "request": request,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "board": board,
            "posts": posts_data['posts'],
            "pagination": {
                "page": posts_data['page'],
                "limit": posts_data['limit'],
                "total_count": posts_data['total_count'],
                "total_pages": posts_data['total_pages']
            },
            "search": search
        })

    except Exception as e:
        print(f"게시판 상세 조회 실패: {str(e)}")
        # 에러 발생 시 게시판 목록으로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/boards", status_code=302)

@app.get("/posts/{post_id}", response_class=HTMLResponse)
async def post_detail_page(request: Request, post_id: int, from_param: str = Query(None, alias="from")):
    # 세션 ID 확인 및 생성
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = csrf_protection.generate_session_id()

    # CSRF 토큰 가져오기 또는 생성
    csrf_token = csrf_protection.get_or_create_csrf_token(session_id)

    # 현재 사용자 정보 확인
    from app.routers.auth import get_current_user_optional
    try:
        current_user = await get_current_user_optional(request)
    except Exception:
        current_user = None

    # 게시글 및 댓글 조회
    from app.models.posts import PostService
    from app.models.comments import CommentService

    post_service = PostService()
    comment_service = CommentService()

    try:
        # 댓글 작성 후 리다이렉트인지 확인하여 조회수 증가 여부 결정
        increment_view = from_param != "comment"
        post = await post_service.get_post_by_id(post_id, increment_view=increment_view)
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

        # 게시판 정보 조회
        from app.models.boards import BoardService
        board_service = BoardService()
        board = await board_service.get_board_by_id(post['board_id'])
        if not board:
            raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다")

        # 댓글 목록 조회
        comments = await comment_service.get_comments_by_post_id(post_id)

        # 템플릿 응답 생성
        response = templates.TemplateResponse("pages/post_detail.html", {
            "request": request,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "post": post,
            "board": board,
            "comments": comments
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
        print(f"게시글 상세 조회 실패: {str(e)}")
        # 에러 발생 시 게시판 목록으로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/boards", status_code=302)

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    # CSRF 토큰 생성
    csrf_token = csrf_protection.generate_csrf_token()

    # 현재 사용자 정보 확인
    from app.routers.auth import get_current_user_optional
    try:
        current_user = await get_current_user_optional(request)
    except Exception:
        current_user = None

    # 검색 파라미터 추출
    query = request.query_params.get("q", "")
    board = request.query_params.get("board", "")
    try:
        page = int(request.query_params.get("page", "1"))
    except (ValueError, TypeError):
        page = 1

    # 검색 결과 조회
    from app.models.posts import PostService
    from app.models.boards import BoardService

    post_service = PostService()
    board_service = BoardService()

    try:
        search_results = None
        boards = []

        # 게시판 목록 조회 (검색 필터용)
        boards = await board_service.get_all_boards()

        # 검색 수행 (빈 검색어는 전체 게시글 조회)
        search_results = await post_service.search_posts(
            query=query.strip(),
            board_slug=board if board else None,
            page=page,
            limit=10
        )

        return templates.TemplateResponse("pages/search.html", {
            "request": request,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "query": query,
            "board": board,
            "boards": boards,
            "search_results": search_results
        })

    except Exception as e:
        print(f"검색 실패: {str(e)}")
        # 에러 발생 시 빈 결과로 표시
        return templates.TemplateResponse("pages/search.html", {
            "request": request,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "query": query,
            "board": board,
            "boards": [],
            "search_results": None
        })

@app.get("/boards/{slug}/write", response_class=HTMLResponse)
async def post_write_page(request: Request, slug: str):
    # CSRF 토큰 생성
    csrf_token = csrf_protection.generate_csrf_token()

    # 현재 사용자 정보 확인 (로그인 필수)
    from app.routers.auth import get_current_user
    try:
        current_user = await get_current_user(request)
    except HTTPException:
        # 로그인하지 않은 사용자는 로그인 페이지로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)

    # 게시판 조회 및 작성 권한 확인
    from app.models.boards import BoardService
    board_service = BoardService()

    try:
        # 게시판 정보 조회
        board = await board_service.get_board_by_slug(slug)
        if not board:
            raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다")

        # 작성 권한 확인
        has_permission = await board_service.check_write_permission(
            slug,
            "member" if current_user else None,
            current_user.get("is_admin", False)
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="게시글 작성 권한이 없습니다")

        return templates.TemplateResponse("pages/post_write.html", {
            "request": request,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "board": board,
            "mode": "create"
        })

    except Exception as e:
        print(f"게시글 작성 페이지 조회 실패: {str(e)}")
        # 에러 발생 시 게시판 목록으로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/boards", status_code=302)

@app.get("/posts/{post_id}/edit", response_class=HTMLResponse)
async def post_edit_page(request: Request, post_id: int):
    # CSRF 토큰 생성
    csrf_token = csrf_protection.generate_csrf_token()

    # 현재 사용자 정보 확인 (로그인 필수)
    from app.routers.auth import get_current_user
    try:
        current_user = await get_current_user(request)
    except HTTPException:
        # 로그인하지 않은 사용자는 로그인 페이지로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login", status_code=302)

    # 게시글 및 게시판 조회
    from app.models.posts import PostService
    from app.models.boards import BoardService

    post_service = PostService()
    board_service = BoardService()

    try:
        # 게시글 조회
        post = await post_service.get_post_by_id(post_id, increment_view=False)
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다")

        # 수정 권한 확인
        permissions = await post_service.check_post_permission(
            post_id,
            current_user["id"],
            current_user.get("is_admin", False)
        )

        if not permissions["update"]:
            raise HTTPException(status_code=403, detail="게시글 수정 권한이 없습니다")

        # 게시판 정보 조회
        board = await board_service.get_board_by_id(post['board_id'])
        if not board:
            raise HTTPException(status_code=404, detail="게시판을 찾을 수 없습니다")

        return templates.TemplateResponse("pages/post_write.html", {
            "request": request,
            "csrf_token": csrf_token,
            "current_user": current_user,
            "board": board,
            "post": post,
            "mode": "edit"
        })

    except Exception as e:
        print(f"게시글 수정 페이지 조회 실패: {str(e)}")
        # 에러 발생 시 게시글 상세로 리다이렉트
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"/posts/{post_id}", status_code=302)

# API 라우터 등록
from app.routers import auth, boards, posts, comments, admin
app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(posts.router)
app.include_router(comments.router)
app.include_router(admin.router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 세션 ID 확인 및 생성
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = csrf_protection.generate_session_id()

    # CSRF 토큰 가져오기 또는 생성
    csrf_token = csrf_protection.get_or_create_csrf_token(session_id)

    # 서비스 인스턴스 생성
    from app.models.boards import BoardService
    from app.models.posts import PostService

    board_service = BoardService()
    post_service = PostService()

    # 인기 게시판 조회 (에러 시 빈 리스트)
    try:
        popular_boards = await board_service.get_popular_boards_with_stats(limit=3)
    except Exception as e:
        print(f"인기 게시판 조회 실패: {str(e)}")
        popular_boards = []

    # 최신 게시글 조회 (에러 시 빈 리스트)
    try:
        latest_posts = await post_service.get_latest_posts_for_main(limit=5)
    except Exception as e:
        print(f"최신 게시글 조회 실패: {str(e)}")
        latest_posts = []

    # 현재 사용자 정보 확인
    from app.routers.auth import get_current_user_optional
    try:
        current_user = await get_current_user_optional(request)
    except Exception:
        current_user = None

    # 템플릿 응답 생성
    response = templates.TemplateResponse("pages/main.html", {
        "request": request,
        "csrf_token": csrf_token,
        "current_user": current_user,
        "popular_boards": popular_boards,
        "latest_posts": latest_posts
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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)