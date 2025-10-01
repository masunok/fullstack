"""
FastAPI 전역 의존성 관리
"""
from app.utils.csrf import CSRFProtection

# 전역 CSRF 보호 인스턴스
csrf_protection = CSRFProtection()