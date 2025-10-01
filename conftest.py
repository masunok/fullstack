import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

@pytest.fixture(scope="session")
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """테스트 환경 설정"""
    # 테스트용 환경변수 설정
    if not os.getenv("SUPABASE_URL"):
        os.environ["SUPABASE_URL"] = "https://kjkctytkgnkyzuweeyud.supabase.co"
    if not os.getenv("SUPABASE_ANON_KEY"):
        os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
    if not os.getenv("SUPABASE_JWT_SECRET"):
        os.environ["SUPABASE_JWT_SECRET"] = "test-jwt-secret"
    if not os.getenv("SESSION_SECRET"):
        os.environ["SESSION_SECRET"] = "test-session-secret"