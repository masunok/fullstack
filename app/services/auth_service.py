import os
from typing import Optional, Dict, Any
from supabase import create_client, Client
from app.utils.password import PasswordUtils
from app.models.auth import AuthService as AuthModel, SignupRequest, LoginRequest


class AuthenticationService:
    """인증 관련 비즈니스 로직"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
        )
        self.auth_model = AuthModel()
    
    async def signup_user(self, signup_data: SignupRequest) -> Dict[str, Any]:
        """사용자 회원가입"""
        # 비밀번호 정책 검증
        if not PasswordUtils.validate_password_policy(signup_data.password):
            raise ValueError("비밀번호는 10자리 이상, 영문자, 숫자, 특수문자를 포함해야 합니다.")
        
        try:
            # 이메일 중복 확인
            print(f"[DEBUG] Checking if email exists in users table: {signup_data.email}")
            existing_user = self.supabase.table("users").select("email").eq("email", signup_data.email).execute()
            print(f"[DEBUG] Users table check result: {len(existing_user.data) if existing_user.data else 0} records found")
            if existing_user.data:
                print(f"[DEBUG] Email already exists in users table")
                raise ValueError("이미 존재하는 이메일입니다.")
            
            # 사용자명 중복 확인
            print(f"[DEBUG] Checking if username exists: {signup_data.username}")
            existing_username = self.supabase.table("users").select("username").eq("username", signup_data.username).execute()
            print(f"[DEBUG] Username check result: {len(existing_username.data) if existing_username.data else 0} records found")
            if existing_username.data:
                print(f"[DEBUG] Username already exists")
                raise ValueError("이미 존재하는 사용자명입니다.")
            
            # Supabase Auth에 사용자 생성
            print(f"[DEBUG] Attempting to sign up user: {signup_data.email}")
            auth_response = self.supabase.auth.sign_up({
                "email": signup_data.email,
                "password": signup_data.password
            })
            
            print(f"[DEBUG] Auth response: user={auth_response.user is not None}")
            print(f"[DEBUG] Auth response type: {type(auth_response)}")
            print(f"[DEBUG] Auth response attributes: {dir(auth_response)}")
            if hasattr(auth_response, 'error') and auth_response.error:
                print(f"[DEBUG] Auth error object: {auth_response.error}")
                print(f"[DEBUG] Auth error message: {getattr(auth_response.error, 'message', 'No message')}")
                print(f"[DEBUG] Auth error code: {getattr(auth_response.error, 'code', 'No code')}")

            if not auth_response.user:
                # Supabase Auth 오류 처리
                if hasattr(auth_response, 'error') and auth_response.error:
                    error_msg = auth_response.error.message
                    print(f"[ERROR] Supabase Auth error: {error_msg}")
                    
                    if "User already registered" in error_msg:
                        raise ValueError("이미 가입된 이메일입니다.")
                    elif "Invalid email" in error_msg or "email" in error_msg.lower():
                        raise ValueError("올바른 이메일 주소를 입력해주세요.")
                    elif "password" in error_msg.lower():
                        raise ValueError("비밀번호가 정책에 맞지 않습니다.")
                    else:
                        raise ValueError(f"회원가입 실패: {error_msg}")
                else:
                    print(f"[ERROR] No user created but no error message")
                    raise ValueError("사용자 생성에 실패했습니다.")

            # 프로필 정보 저장
            user_id = auth_response.user.id
            profile_data = {
                "id": user_id,
                "email": signup_data.email,
                "username": signup_data.username,
                "display_name": signup_data.display_name,
                "is_admin": False
            }
            
            profile_response = self.supabase.table("users").insert(profile_data).execute()
            
            return {
                "success": True,
                "message": "회원가입이 완료되었습니다.",
                "user_id": user_id
            }
            
        except ValueError:
            # ValueError는 그대로 전달 (이미 사용자 친화적 메시지)
            raise
        except Exception as e:
            print(f"[ERROR] Unexpected signup error: {str(e)}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            print(f"[ERROR] Exception details: {e}")
            
            # AuthApiError인 경우 특별 처리
            if hasattr(e, 'message'):
                error_msg = e.message
                print(f"[ERROR] Auth API error message: {error_msg}")
                
                if "User already registered" in error_msg:
                    # Supabase Auth에만 존재하는 경우
                    print(f"[WARNING] User exists in Auth but not in users table. This is an inconsistent state.")
                    raise ValueError("이미 가입된 이메일입니다. 로그인을 시도하거나 다른 이메일을 사용해주세요.")
                elif "Invalid email" in error_msg or "email" in error_msg.lower():
                    raise ValueError("올바른 이메일 주소를 입력해주세요.")
                elif "password" in error_msg.lower():
                    raise ValueError("비밀번호가 정책에 맞지 않습니다.")
                else:
                    raise ValueError(f"회원가입 실패: {error_msg}")
            
            raise ValueError(f"회원가입 중 오류가 발생했습니다: {str(e)}")
    
    async def login_user(self, login_data: LoginRequest) -> Dict[str, Any]:
        """사용자 로그인"""
        try:
            # 1. 기본 이메일 형식 검증
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, login_data.email):
                raise ValueError("정상적인 이메일 규칙이 아닙니다.")

            # 2. 이메일이 등록되어 있는지 먼저 확인
            user_check_response = self.supabase.table("users").select("id, email, deleted_at").eq("email", login_data.email).execute()
            
            if not user_check_response.data or len(user_check_response.data) == 0:
                print(f"[WARNING] Login attempt with non-existent email: {login_data.email}")
                raise ValueError("입력한 이메일이 존재하지 않습니다.")
            
            # 3. 사용자가 삭제된 상태인지 확인
            user_data = user_check_response.data[0]
            if user_data.get("deleted_at") is not None:
                print(f"[WARNING] Login attempt by deleted user: {login_data.email}")
                raise ValueError("계정이 비활성화되었습니다. 관리자에게 문의하세요.")

            # 4. Supabase Auth로 로그인 시도
            try:
                auth_response = self.supabase.auth.sign_in_with_password({
                    "email": login_data.email,
                    "password": login_data.password
                })
                
                print(f"[DEBUG] Auth response for {login_data.email}: user={auth_response.user is not None}")
                if hasattr(auth_response, 'error') and auth_response.error:
                    print(f"[DEBUG] Auth response error: {auth_response.error}")

                if not auth_response.user:
                    # Supabase Auth 오류 분석
                    if hasattr(auth_response, 'error') and auth_response.error:
                        error_msg = str(auth_response.error.message) if hasattr(auth_response.error, 'message') else str(auth_response.error)
                        print(f"[WARNING] Supabase Auth error for {login_data.email}: {error_msg}")
                        
                        if "Invalid login credentials" in error_msg or "invalid" in error_msg.lower():
                            raise ValueError("비밀번호가 올바르지 않습니다.")
                        elif "Email not confirmed" in error_msg:
                            raise ValueError("이메일 인증이 완료되지 않았습니다.")
                        elif "Account locked" in error_msg:
                            raise ValueError("계정이 잠겨있습니다. 관리자에게 문의하세요.")
                        else:
                            raise ValueError("로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.")
                    else:
                        raise ValueError("비밀번호가 올바르지 않습니다.")
                        
            except Exception as auth_error:
                print(f"[ERROR] Auth API exception for {login_data.email}: {auth_error}")
                print(f"[ERROR] Auth exception type: {type(auth_error).__name__}")
                
                # Supabase Auth 예외 분석
                error_str = str(auth_error)
                if "Invalid login credentials" in error_str or "400" in error_str:
                    raise ValueError("비밀번호가 올바르지 않습니다.")
                elif "Email not confirmed" in error_str:
                    raise ValueError("이메일 인증이 완료되지 않았습니다.")
                elif "Too many requests" in error_str or "429" in error_str:
                    raise ValueError("너무 많은 로그인 시도입니다. 잠시 후 다시 시도해주세요.")
                elif "Network" in error_str or "timeout" in error_str.lower():
                    raise ValueError("네트워크 오류입니다. 잠시 후 다시 시도해주세요.")
                else:
                    # 다시 던져서 외부 예외 처리에서 처리하도록
                    raise auth_error

            user_id = auth_response.user.id

            # 5. 사용자 프로필 정보 조회 (이미 위에서 확인했지만 최신 정보로 재확인)
            profile_response = self.supabase.table("users").select("*").eq("id", user_id).execute()

            if not profile_response.data or len(profile_response.data) == 0:
                print(f"[ERROR] User profile missing after successful auth for: {login_data.email}")
                raise ValueError("사용자 프로필을 찾을 수 없습니다. 관리자에게 문의하세요.")

            user_profile = profile_response.data[0]
            
            # 6. 최종 삭제 상태 재확인 (데이터 정합성 체크)
            if user_profile.get("deleted_at") is not None:
                print(f"[WARNING] User deleted after auth success: {login_data.email}")
                raise ValueError("계정이 비활성화되었습니다. 관리자에게 문의하세요.")

            # 7. auth.users 메타데이터에서도 삭제 상태 확인
            try:
                auth_user = auth_response.user
                if auth_user and auth_user.app_metadata and auth_user.app_metadata.get("deleted_at"):
                    print(f"[WARNING] User has deleted_at in auth metadata: {login_data.email}")
                    raise ValueError("계정이 비활성화되었습니다. 관리자에게 문의하세요.")
            except Exception as metadata_error:
                # 메타데이터 체크 실패는 로그만 남기고 계속 진행
                print(f"[INFO] Could not check auth metadata for {login_data.email}: {metadata_error}")

            # JWT 토큰 생성
            jwt_token = self.auth_model.create_jwt_token({
                "user_id": user_id,
                "email": user_profile["email"] if "email" in user_profile else login_data.email,
                "is_admin": user_profile["is_admin"]
            })

            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": {
                    "id": user_id,
                    "email": login_data.email,
                    "username": user_profile["username"],
                    "display_name": user_profile["display_name"],
                    "is_admin": user_profile["is_admin"]
                }
            }

        except ValueError as ve:
            # ValueError는 사용자 친화적 메시지이므로 그대로 전달
            raise ve
        except Exception as e:
            print(f"[ERROR] Unexpected login error for {login_data.email}: {str(e)}")
            print(f"[ERROR] Exception type: {type(e).__name__}")
            
            # Supabase Auth API 오류 분석
            if hasattr(e, 'message'):
                error_msg = str(e.message)
                if "Invalid login credentials" in error_msg:
                    raise ValueError("비밀번호가 올바르지 않습니다.")
                elif "Email not confirmed" in error_msg:
                    raise ValueError("이메일 인증이 완료되지 않았습니다.")
                elif "Too many requests" in error_msg:
                    raise ValueError("너무 많은 로그인 시도입니다. 잠시 후 다시 시도해주세요.")
                elif "Network" in error_msg or "timeout" in error_msg.lower():
                    raise ValueError("네트워크 오류입니다. 잠시 후 다시 시도해주세요.")
            
            # 일반적인 오류
            raise ValueError("로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """사용자 ID로 사용자 정보 조회 (삭제되지 않은 사용자만)"""
        try:
            response = self.supabase.table("users").select("*").eq("id", user_id).is_("deleted_at", "null").execute()

            if response.data and len(response.data) > 0:
                # 이메일 정보가 이미 users 테이블에 있으므로 추가 조회 불필요
                user_data = response.data[0].copy()
                
                # 삭제된 사용자 체크 (추가 안전장치)
                if user_data.get("deleted_at") is not None:
                    print(f"[WARNING] Attempt to access soft-deleted user: {user_id}")
                    return None
                    
                return user_data

            return None

        except Exception:
            return None
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        return self.auth_model.verify_jwt_token(token)