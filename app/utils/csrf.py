import secrets
from typing import Dict
from fastapi import HTTPException, Request


class CSRFProtection:
    """CSRF 보호 유틸리티"""
    
    def __init__(self):
        self.csrf_tokens: Dict[str, str] = {}
    
    def generate_session_id(self) -> str:
        """세션 ID 생성"""
        return secrets.token_urlsafe(32)
    
    def generate_csrf_token(self) -> str:
        """CSRF 토큰 생성"""
        return secrets.token_hex(16)
    
    def store_csrf_token(self, session_id: str, token: str) -> None:
        """CSRF 토큰 저장"""
        self.csrf_tokens[session_id] = token

    def get_or_create_csrf_token(self, session_id: str) -> str:
        """세션에 대한 CSRF 토큰 가져오기 또는 생성"""
        if session_id in self.csrf_tokens:
            return self.csrf_tokens[session_id]
        else:
            token = self.generate_csrf_token()
            self.store_csrf_token(session_id, token)
            return token
    
    async def verify_csrf_token(self, request: Request) -> str:
        """CSRF 토큰 검증 (의존성 주입용)"""
        session_id = request.cookies.get("session_id")

        if not session_id:
            raise HTTPException(status_code=403, detail="CSRF: Missing session")

        # 헤더에서 토큰 확인
        csrf_token = request.headers.get("X-CSRF-Token")

        # 헤더에 없으면 폼 데이터에서 확인
        if not csrf_token:
            try:
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")
            except:
                pass

        if not csrf_token:
            raise HTTPException(status_code=403, detail="CSRF: Missing token")

        stored_token = self.csrf_tokens.get(session_id)
        if not stored_token or stored_token != csrf_token:
            raise HTTPException(status_code=403, detail="CSRF: Invalid token")

        return csrf_token