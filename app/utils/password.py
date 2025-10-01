import re
import bcrypt


class PasswordUtils:
    """비밀번호 관련 유틸리티"""
    
    @staticmethod
    def validate_password_policy(password: str) -> bool:
        """
        비밀번호 정책 검증
        - 10자리 이상
        - 영문자 포함
        - 숫자 포함
        - 특수문자 포함
        - 공백 불허
        """
        if len(password) < 10:
            return False

        # 공백 확인
        if ' ' in password:
            return False

        # 영문자 확인 (대소문자 구분 없음)
        if not re.search(r'[a-zA-Z]', password):
            return False

        # 숫자 확인
        if not re.search(r'[0-9]', password):
            return False

        # 특수문자 확인
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\?]', password):
            return False

        return True
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해싱"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))