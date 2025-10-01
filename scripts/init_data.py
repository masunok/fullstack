#!/usr/bin/env python3
"""
AIZEVA 초기 데이터 생성 스크립트
- 초기 관리자 계정 생성
- 초기 게시판 생성
"""

import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# 초기 데이터
ADMIN_USER = {
    "email": "masunok@example.com",
    "password": "msk040830*",
    "username": "admin",
    "display_name": "관리자",
    "is_admin": True
}

INITIAL_BOARDS = [
    {
        "name": "공지사항",
        "slug": "notice",
        "description": "중요한 공지사항을 게시합니다",
        "write_permission": "admin"
    },
    {
        "name": "뉴스레터",
        "slug": "newsletter", 
        "description": "정기 뉴스레터를 발행합니다",
        "write_permission": "admin"
    },
    {
        "name": "자유게시판",
        "slug": "free",
        "description": "자유롭게 소통하는 공간입니다",
        "write_permission": "member"
    }
]

async def create_admin_user(supabase: Client):
    """초기 관리자 계정 생성"""
    print("관리자 계정 생성 중...")
    
    try:
        # Auth 사용자 생성
        auth_response = supabase.auth.admin.create_user({
            "email": ADMIN_USER["email"],
            "password": ADMIN_USER["password"],
            "email_confirm": True
        })
        
        if auth_response.user:
            user_id = auth_response.user.id
            print(f"Auth 사용자 생성 완료: {user_id}")
            
            # 프로필 정보 추가
            profile_response = supabase.table("users").insert({
                "id": user_id,
                "username": ADMIN_USER["username"],
                "display_name": ADMIN_USER["display_name"],
                "is_admin": ADMIN_USER["is_admin"]
            }).execute()
            
            print("관리자 프로필 생성 완료")
            return user_id
            
    except Exception as e:
        print(f"관리자 계정 생성 실패: {e}")
        return None

async def create_initial_boards(supabase: Client):
    """초기 게시판 생성"""
    print("초기 게시판 생성 중...")
    
    try:
        for board_data in INITIAL_BOARDS:
            response = supabase.table("boards").insert(board_data).execute()
            print(f"게시판 '{board_data['name']}' 생성 완료")
            
    except Exception as e:
        print(f"게시판 생성 실패: {e}")

async def main():
    """메인 함수"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("환경변수가 설정되지 않았습니다.")
        print("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 확인해주세요.")
        return
    
    # Supabase 클라이언트 생성
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    print("=== AIZEVA 초기 데이터 생성 ===")
    
    # 관리자 계정 생성
    admin_id = await create_admin_user(supabase)
    
    if admin_id:
        # 초기 게시판 생성
        await create_initial_boards(supabase)
        
        print("\n=== 초기 데이터 생성 완료 ===")
        print(f"관리자 이메일: {ADMIN_USER['email']}")
        print(f"관리자 비밀번호: {ADMIN_USER['password']}")
        print(f"생성된 게시판: {len(INITIAL_BOARDS)}개")
    else:
        print("\n=== 초기 데이터 생성 실패 ===")

if __name__ == "__main__":
    asyncio.run(main())