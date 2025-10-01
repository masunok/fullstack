import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from supabase import create_client, Client


class BoardRequest(BaseModel):
    """게시판 생성/수정 요청 모델"""
    name: str
    slug: str
    description: Optional[str] = None
    write_permission: str = "member"  # "all", "member", "admin"


class BoardUpdateRequest(BaseModel):
    """게시판 수정 요청 모델"""
    name: Optional[str] = None
    description: Optional[str] = None
    write_permission: Optional[str] = None


class BoardResponse(BaseModel):
    """게시판 응답 모델"""
    id: int
    name: str
    slug: str
    description: Optional[str]
    write_permission: str
    created_at: datetime
    updated_at: datetime


class BoardService:
    """게시판 관련 비즈니스 로직"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
        )
    
    async def get_all_boards(self) -> List[Dict[str, Any]]:
        """모든 게시판 목록 조회"""
        try:
            response = self.supabase.table("boards").select("*").order("id").execute()
            return response.data
        except Exception as e:
            raise ValueError(f"게시판 목록 조회 실패: {str(e)}")
    
    async def get_board_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """slug로 게시판 조회"""
        try:
            response = self.supabase.table("boards").select("*").eq("slug", slug).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            raise ValueError(f"게시판 조회 실패: {str(e)}")
    
    async def get_board_by_id(self, board_id: int) -> Optional[Dict[str, Any]]:
        """ID로 게시판 조회"""
        try:
            response = self.supabase.table("boards").select("*").eq("id", board_id).execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            raise ValueError(f"게시판 조회 실패: {str(e)}")
    
    async def create_board(self, board_data: Dict[str, Any]) -> Dict[str, Any]:
        """게시판 생성"""
        try:
            # write_permission 값 검증
            valid_permissions = ["all", "member", "admin"]
            if board_data.get("write_permission") not in valid_permissions:
                raise ValueError(f"write_permission은 {', '.join(valid_permissions)} 중 하나여야 합니다")
            
            # slug 중복 확인
            existing_board = await self.get_board_by_slug(board_data["slug"])
            if existing_board:
                raise ValueError("이미 존재하는 slug입니다")
            
            response = self.supabase.table("boards").insert(board_data).execute()
            
            if response.data:
                return response.data[0]
            else:
                raise ValueError("게시판 생성에 실패했습니다")
                
        except Exception as e:
            if "이미 존재하는 slug" in str(e):
                raise e
            raise ValueError(f"게시판 생성 실패: {str(e)}")
    
    async def update_board(self, board_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """게시판 수정"""
        try:
            # 존재 확인
            existing_board = await self.get_board_by_id(board_id)
            if not existing_board:
                raise ValueError("수정할 게시판을 찾을 수 없습니다")
            
            # write_permission 값 검증
            if "write_permission" in update_data:
                valid_permissions = ["all", "member", "admin"]
                if update_data["write_permission"] not in valid_permissions:
                    raise ValueError(f"write_permission은 {', '.join(valid_permissions)} 중 하나여야 합니다")
            
            # slug는 수정 불가 (제거)
            if "slug" in update_data:
                del update_data["slug"]
            
            response = self.supabase.table("boards").update(update_data).eq("id", board_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            raise ValueError(f"게시판 수정 실패: {str(e)}")
    
    async def delete_board(self, board_id: int) -> bool:
        """게시판 삭제"""
        try:
            # 존재 확인
            existing_board = await self.get_board_by_id(board_id)
            if not existing_board:
                return False
            
            # 게시글이 있는지 확인 (외래키 제약 조건으로 인해 삭제 불가할 수 있음)
            posts_response = self.supabase.table("posts").select("id").eq("board_id", board_id).limit(1).execute()
            if posts_response.data:
                raise ValueError("게시글이 있는 게시판은 삭제할 수 없습니다")
            
            response = self.supabase.table("boards").delete().eq("id", board_id).execute()
            
            # 삭제 성공 확인 (응답에 데이터가 있으면 삭제됨)
            return len(response.data) > 0 if response.data else True
            
        except Exception as e:
            if "게시글이 있는 게시판" in str(e):
                raise e
            raise ValueError(f"게시판 삭제 실패: {str(e)}")
    
    async def check_write_permission(self, board_slug: str, user_role: Optional[str] = None, is_admin: bool = False) -> bool:
        """게시판 작성 권한 확인"""
        try:
            board = await self.get_board_by_slug(board_slug)
            if not board:
                return False
            
            write_permission = board["write_permission"]
            
            if write_permission == "all":
                return True
            elif write_permission == "member":
                return user_role is not None  # 로그인한 사용자
            elif write_permission == "admin":
                return is_admin
            
            return False
            
        except Exception as e:
            raise ValueError(f"권한 확인 실패: {str(e)}")
    
    async def get_board_stats(self, board_id: int) -> Dict[str, Any]:
        """게시판 통계 조회 (게시글 수, 최근 게시글 등)"""
        try:
            board = await self.get_board_by_id(board_id)
            if not board:
                raise ValueError("게시판을 찾을 수 없습니다")
            
            # 게시글 수
            posts_count_response = self.supabase.table("posts").select("id", count="exact").eq("board_id", board_id).execute()
            posts_count = posts_count_response.count if posts_count_response.count else 0
            
            # 최근 게시글
            recent_posts_response = self.supabase.table("posts")\
                .select("id, title, created_at")\
                .eq("board_id", board_id)\
                .order("created_at", desc=True)\
                .limit(5)\
                .execute()
            
            return {
                "board_id": board_id,
                "posts_count": posts_count,
                "recent_posts": recent_posts_response.data
            }
            
        except Exception as e:
            raise ValueError(f"게시판 통계 조회 실패: {str(e)}")

    async def get_popular_boards_with_stats(self, limit: int = 3) -> List[Dict[str, Any]]:
        """인기 게시판 목록 조회 (게시글 수 기준, 통계 포함)"""
        try:
            # 모든 게시판을 가져오고 게시글 수와 댓글 수를 계산
            boards_response = self.supabase.table("boards").select("*").order("id").execute()

            if not boards_response.data:
                return []

            boards_with_stats = []

            for board in boards_response.data:
                # 게시글 수 조회
                posts_response = self.supabase.table("posts")\
                    .select("id", count="exact")\
                    .eq("board_id", board["id"])\
                    .execute()

                post_count = posts_response.count or 0

                # 댓글 수 조회 (해당 게시판의 모든 게시글의 댓글)
                # 먼저 해당 게시판의 모든 게시글 ID를 조회
                posts_ids_response = self.supabase.table("posts")\
                    .select("id")\
                    .eq("board_id", board["id"])\
                    .execute()

                # 게시글 ID 리스트 생성
                post_ids = [post["id"] for post in posts_ids_response.data] if posts_ids_response.data else []

                # 댓글 수 조회 (게시글 ID가 있는 경우에만)
                if post_ids:
                    comments_response = self.supabase.table("comments")\
                        .select("id", count="exact")\
                        .in_("post_id", post_ids)\
                        .execute()
                    comment_count = comments_response.count or 0
                else:
                    comment_count = 0

                # 통계 정보 추가
                board_with_stats = {
                    **board,
                    "post_count": post_count,
                    "comment_count": comment_count
                }

                boards_with_stats.append(board_with_stats)

            # ID 순서로 정렬 (공지사항, 뉴스레터, 자유게시판 순)
            boards_with_stats.sort(key=lambda x: x["id"])

            # 상위 limit개만 반환
            return boards_with_stats[:limit]

        except Exception as e:
            # 에러 발생 시 빈 리스트 반환하여 서비스 중단 방지
            print(f"인기 게시판 조회 오류: {str(e)}")
            return []

    async def get_all_boards_with_stats(self) -> List[Dict[str, Any]]:
        """모든 게시판과 통계 정보 조회 (관리자용)"""
        try:
            # 모든 게시판 조회
            boards_response = self.supabase.table("boards").select("*").order("id").execute()

            if not boards_response.data:
                return []

            boards_with_stats = []

            for board in boards_response.data:
                # 게시판별 게시글 수 조회
                posts_response = self.supabase.table("posts")\
                    .select("*", count="exact")\
                    .eq("board_id", board["id"])\
                    .execute()
                post_count = posts_response.count if posts_response.count else 0

                # 게시판별 댓글 수 조회 (게시글의 댓글들)
                comments_response = self.supabase.table("comments")\
                    .select("*, posts!inner(board_id)", count="exact")\
                    .eq("posts.board_id", board["id"])\
                    .execute()
                comment_count = comments_response.count if comments_response.count else 0

                # 최신 게시글 조회
                latest_post_response = self.supabase.table("posts")\
                    .select("id, title, created_at, users!inner(display_name, username)")\
                    .eq("board_id", board["id"])\
                    .order("created_at", desc=True)\
                    .limit(1)\
                    .execute()

                latest_post = None
                if latest_post_response.data:
                    post = latest_post_response.data[0]
                    latest_post = {
                        "id": post["id"],
                        "title": post["title"],
                        "created_at": post["created_at"],
                        "author_name": post["users"]["display_name"] or post["users"]["username"]
                    }

                # 통계 정보가 포함된 게시판 데이터
                board_with_stats = {
                    **board,
                    "post_count": post_count,
                    "comment_count": comment_count,
                    "latest_post": latest_post
                }

                boards_with_stats.append(board_with_stats)

            return boards_with_stats

        except Exception as e:
            print(f"게시판 통계 조회 오류: {str(e)}")
            # 에러 발생 시 기본 게시판 목록 반환
            try:
                return await self.get_all_boards()
            except:
                return []