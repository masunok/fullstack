import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr, validator


class AuthService:
    """인증 관련 서비스"""
    
    def __init__(self):
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "fallback-secret-key")
        self.csrf_tokens: Dict[str, str] = {}  # 메모리 기반 CSRF 토큰 저장
    
    def generate_csrf_token(self) -> str:
        """CSRF 토큰 생성"""
        return secrets.token_hex(16)
    
    def store_csrf_token(self, session_id: str, token: str) -> None:
        """CSRF 토큰 저장"""
        self.csrf_tokens[session_id] = token
    
    def validate_csrf_token(self, session_id: str, token: str) -> bool:
        """CSRF 토큰 검증"""
        stored_token = self.csrf_tokens.get(session_id)
        return stored_token == token
    
    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """JWT 토큰 생성"""
        payload = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "is_admin": user_data["is_admin"],
            "exp": datetime.utcnow() + timedelta(hours=24),  # 24시간 유효
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except JWTError:
            return None


class SignupRequest(BaseModel):
    """회원가입 요청 모델"""
    email: EmailStr
    username: str
    password: str
    password_confirm: str
    display_name: Optional[str] = None
    
    @validator('password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('비밀번호가 일치하지 않습니다.')
        return v


class LoginRequest(BaseModel):
    """로그인 요청 모델"""
    email: str
    password: str


class UserResponse(BaseModel):
    """사용자 응답 모델"""
    id: str
    email: str
    username: str
    display_name: str
    is_admin: bool
    created_at: datetime