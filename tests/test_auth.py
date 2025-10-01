import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.models.auth import AuthService
from app.utils.password import PasswordUtils


class TestPasswordUtils:
    """비밀번호 유틸리티 테스트"""
    
    def test_validate_password_policy_valid(self):
        """유효한 비밀번호 정책 테스트"""
        valid_passwords = [
            "abcd123!@#",
            "Test123!",
            "MyPassword1$",
            "SecurePass9*"
        ]
        
        for password in valid_passwords:
            assert PasswordUtils.validate_password_policy(password) == True
    
    def test_validate_password_policy_invalid(self):
        """유효하지 않은 비밀번호 정책 테스트"""
        invalid_passwords = [
            "short1!",      # 너무 짧음
            "nouppercase1!", # 대문자 없음
            "NOLOWERCASE1!", # 소문자 없음
            "NoNumbers!",    # 숫자 없음
            "NoSpecial123",  # 특수문자 없음
            "spaces not allowed1!",  # 공백 포함
        ]
        
        for password in invalid_passwords:
            assert PasswordUtils.validate_password_policy(password) == False
    
    def test_hash_password(self):
        """비밀번호 해싱 테스트"""
        password = "testpass123!"
        hashed = PasswordUtils.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt 해시는 일반적으로 60자
    
    def test_verify_password(self):
        """비밀번호 검증 테스트"""
        password = "testpass123!"
        hashed = PasswordUtils.hash_password(password)
        
        assert PasswordUtils.verify_password(password, hashed) == True
        assert PasswordUtils.verify_password("wrongpass", hashed) == False


class TestAuthService:
    """인증 서비스 테스트"""
    
    @pytest.fixture
    def auth_service(self):
        return AuthService()
    
    def test_generate_csrf_token(self, auth_service):
        """CSRF 토큰 생성 테스트"""
        token1 = auth_service.generate_csrf_token()
        token2 = auth_service.generate_csrf_token()
        
        assert token1 != token2
        assert len(token1) == 32  # 16바이트를 hex로 인코딩하면 32자
        assert len(token2) == 32
    
    def test_validate_csrf_token(self, auth_service):
        """CSRF 토큰 검증 테스트"""
        token = auth_service.generate_csrf_token()
        session_id = "test_session_123"
        
        # 세션에 토큰 저장
        auth_service.store_csrf_token(session_id, token)
        
        # 검증 테스트
        assert auth_service.validate_csrf_token(session_id, token) == True
        assert auth_service.validate_csrf_token(session_id, "invalid_token") == False
        assert auth_service.validate_csrf_token("invalid_session", token) == False
    
    def test_create_jwt_token(self, auth_service):
        """JWT 토큰 생성 테스트"""
        user_data = {
            "user_id": "12345",
            "email": "test@example.com",
            "is_admin": False
        }
        
        token = auth_service.create_jwt_token(user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT는 일반적으로 길다
        assert token.count('.') == 2  # JWT는 3개 부분으로 구성
    
    def test_verify_jwt_token(self, auth_service):
        """JWT 토큰 검증 테스트"""
        user_data = {
            "user_id": "12345",
            "email": "test@example.com", 
            "is_admin": False
        }
        
        token = auth_service.create_jwt_token(user_data)
        decoded = auth_service.verify_jwt_token(token)
        
        assert decoded is not None
        assert decoded["user_id"] == user_data["user_id"]
        assert decoded["email"] == user_data["email"]
        assert decoded["is_admin"] == user_data["is_admin"]
        
        # 잘못된 토큰 테스트
        invalid_decoded = auth_service.verify_jwt_token("invalid.token.here")
        assert invalid_decoded is None


@pytest.mark.asyncio
class TestAuthAPI:
    """인증 API 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_signup_valid_data(self, client):
        """회원가입 - 유효한 데이터"""
        signup_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "NewPass123!",
            "display_name": "새로운 사용자"
        }
        
        response = client.post("/auth/signup", json=signup_data)
        
        assert response.status_code == 201
        assert "success" in response.json()
    
    def test_signup_invalid_password(self, client):
        """회원가입 - 유효하지 않은 비밀번호"""
        signup_data = {
            "email": "newuser2@example.com",
            "username": "newuser2",
            "password": "weak",  # 약한 비밀번호
            "display_name": "새로운 사용자2"
        }
        
        response = client.post("/auth/signup", json=signup_data)
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    def test_signup_duplicate_email(self, client):
        """회원가입 - 중복 이메일"""
        signup_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "ValidPass123!",
            "display_name": "사용자1"
        }
        
        # 첫 번째 회원가입
        client.post("/auth/signup", json=signup_data)
        
        # 두 번째 회원가입 (같은 이메일)
        signup_data["username"] = "user2"
        response = client.post("/auth/signup", json=signup_data)
        
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()
    
    def test_login_valid_credentials(self, client):
        """로그인 - 유효한 자격증명"""
        # 먼저 회원가입
        signup_data = {
            "email": "logintest@example.com",
            "username": "logintest",
            "password": "LoginTest123!",
            "display_name": "로그인 테스트"
        }
        client.post("/auth/signup", json=signup_data)
        
        # 로그인 시도
        login_data = {
            "email": "logintest@example.com",
            "password": "LoginTest123!"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        
        # 쿠키 확인
        assert "session" in response.cookies
    
    def test_login_invalid_credentials(self, client):
        """로그인 - 유효하지 않은 자격증명"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPass123!"
        }
        
        response = client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "credentials" in response.json()["detail"].lower()
    
    def test_logout(self, client):
        """로그아웃 테스트"""
        # 로그인 후 로그아웃
        signup_data = {
            "email": "logouttest@example.com",
            "username": "logouttest", 
            "password": "LogoutTest123!",
            "display_name": "로그아웃 테스트"
        }
        client.post("/auth/signup", json=signup_data)
        
        login_response = client.post("/auth/login", json={
            "email": "logouttest@example.com",
            "password": "LogoutTest123!"
        })
        
        # 로그아웃
        logout_response = client.post("/auth/logout")
        
        assert logout_response.status_code == 200
        assert "success" in logout_response.json()
    
    def test_get_current_user(self, client):
        """현재 사용자 정보 조회"""
        # 로그인
        signup_data = {
            "email": "currentuser@example.com",
            "username": "currentuser",
            "password": "CurrentUser123!",
            "display_name": "현재 사용자"
        }
        client.post("/auth/signup", json=signup_data)
        
        login_response = client.post("/auth/login", json={
            "email": "currentuser@example.com",
            "password": "CurrentUser123!"
        })
        
        # 현재 사용자 정보 조회
        me_response = client.get("/auth/me")
        
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == "currentuser@example.com"
        assert user_data["username"] == "currentuser"
        assert user_data["display_name"] == "현재 사용자"
        assert user_data["is_admin"] == False
    
    def test_get_current_user_unauthorized(self, client):
        """인증되지 않은 사용자의 정보 조회"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
        assert "unauthorized" in response.json()["detail"].lower()


class TestCSRFProtection:
    """CSRF 보호 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_csrf_token_required(self, client):
        """CSRF 토큰이 필요한 요청 테스트"""
        # CSRF 토큰 없이 POST 요청
        response = client.post("/auth/signup", json={
            "email": "csrf@example.com",
            "username": "csrf",
            "password": "CsrfTest123!",
            "display_name": "CSRF 테스트"
        })
        
        # CSRF 토큰이 없으면 403 Forbidden
        assert response.status_code == 403
        assert "csrf" in response.json()["detail"].lower()
    
    def test_csrf_token_valid(self, client):
        """유효한 CSRF 토큰으로 요청 테스트"""
        # 먼저 CSRF 토큰 획득
        csrf_response = client.get("/auth/csrf-token")
        csrf_token = csrf_response.json()["csrf_token"]
        
        # CSRF 토큰과 함께 POST 요청
        response = client.post("/auth/signup", 
            json={
                "email": "csrf2@example.com",
                "username": "csrf2",
                "password": "CsrfTest123!",
                "display_name": "CSRF 테스트2"
            },
            headers={"X-CSRF-Token": csrf_token}
        )
        
        assert response.status_code == 201