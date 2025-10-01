from fastapi import APIRouter, HTTPException, Depends, Response, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import quote, unquote
from app.models.auth import SignupRequest, LoginRequest, UserResponse, AuthService
from app.services.auth_service import AuthenticationService
from app.dependencies import csrf_protection

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
auth_service = AuthenticationService()
auth_model = AuthService()


async def get_current_user(request: Request) -> dict:
    """현재 로그인한 사용자 정보 반환"""
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided")

    payload = auth_model.verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")

    user_data = await auth_service.get_user_by_id(payload["user_id"])
    if not user_data:
        raise HTTPException(status_code=401, detail="Unauthorized: User not found")

    return user_data


async def get_current_user_optional(request: Request) -> Optional[dict]:
    """현재 로그인한 사용자 정보 반환 (선택적)"""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


@router.get("/csrf-token")
async def get_csrf_token(request: Request, response: Response):
    """CSRF 토큰 발급"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = csrf_protection.generate_session_id()
        response.set_cookie("session_id", session_id, httponly=True, secure=False, samesite="lax")
    
    csrf_token = auth_model.generate_csrf_token()
    auth_model.store_csrf_token(session_id, csrf_token)
    
    return {"csrf_token": csrf_token}


@router.post("/signup", status_code=201)
async def signup(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    display_name: str = Form(""),
    password: str = Form(...),
    password_confirm: str = Form(...),
    agree_terms: str = Form(""),
    # csrf_token: str = Depends(csrf_protection.verify_csrf_token)  # 임시 비활성화
):
    """회원가입"""
    try:
        # 약관 동의 확인 - 더 명확한 에러 메시지
        if not agree_terms or agree_terms.strip() != "on":
            raise HTTPException(
                status_code=400,
                detail="이용약관 및 개인정보처리방침에 동의해야 회원가입 가능합니다."
            )

        # 폼 데이터를 SignupRequest 모델로 변환
        try:
            signup_data = SignupRequest(
                email=email,
                username=username,
                password=password,
                password_confirm=password_confirm,
                display_name=display_name if display_name.strip() else None
            )
        except Exception as validation_error:
            # Pydantic 검증 오류를 사용자 친화적 메시지로 변환
            error_msg = "입력값을 확인해주세요."
            error_str = str(validation_error).lower()
            
            if "password" in error_str and "match" in error_str:
                error_msg = "비밀번호가 일치하지 않습니다."
            elif "password" in error_str:
                error_msg = "비밀번호는 10자리 이상, 영문 대소문자, 숫자, 특수문자를 포함해야 합니다."
            elif "email" in error_str or "value is not a valid email" in error_str:
                error_msg = "올바른 이메일 주소를 입력해주세요."
            elif "username" in error_str:
                error_msg = "사용자명을 입력해주세요."

            raise HTTPException(status_code=400, detail=error_msg)

        result = await auth_service.signup_user(signup_data)
        # 회원가입 성공 후 로그인 페이지로 리다이렉트
        return RedirectResponse(url="/auth/login", status_code=302)
    except HTTPException:
        # 이미 처리된 HTTP 예외는 그대로 전달
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"회원가입 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...)
    # csrf_token: str = Depends(csrf_protection.verify_csrf_token)  # 임시 비활성화
):
    """로그인"""
    try:
        # 폼 데이터를 LoginRequest 모델로 변환
        login_data = LoginRequest(email=email, password=password)

        result = await auth_service.login_user(login_data)

        # JWT를 HttpOnly 쿠키에 저장하고 메인 페이지로 리다이렉트
        redirect_response = RedirectResponse(url="/", status_code=302)
        redirect_response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=False,  # 개발환경에서는 False
            samesite="lax",
            max_age=24*60*60  # 24시간
        )

        return redirect_response
    except ValueError as e:
        # 로그인 실패 시 로그인 페이지로 리다이렉트하면서 오류 메시지 전달
        redirect_response = RedirectResponse(url="/auth/login", status_code=302)
        # 오류 메시지를 URL 인코딩하여 쿠키로 임시 저장 (한글 지원)
        error_message = quote(str(e), safe='')
        redirect_response.set_cookie(
            key="login_error",
            value=error_message,
            httponly=False,  # JavaScript에서 읽을 수 있도록
            max_age=10,  # 10초 후 자동 삭제
            samesite="lax"
        )
        return redirect_response
    except Exception as e:
        # 서버 오류 시에도 로그인 페이지로 리다이렉트
        redirect_response = RedirectResponse(url="/auth/login", status_code=302)
        error_message = quote("서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", safe='')
        redirect_response.set_cookie(
            key="login_error",
            value=error_message,
            httponly=False,
            max_age=10,
            samesite="lax"
        )
        return redirect_response


@router.post("/logout")
async def logout():
    """로그아웃"""
    redirect_response = RedirectResponse(url="/", status_code=302)
    redirect_response.delete_cookie("access_token")
    redirect_response.delete_cookie("session_id")
    return redirect_response


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """현재 사용자 정보 조회"""
    return current_user