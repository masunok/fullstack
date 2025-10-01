import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from supabase import create_client, Client


class CommentRequest(BaseModel):
    """댓글 생성 요청 모델"""
    content: str
    parent_id: Optional[int] = None  # 답글인 경우 부모 댓글 ID


class CommentUpdateRequest(BaseModel):
    """댓글 수정 요청 모델"""
    content: str


class CommentResponse(BaseModel):
    """댓글 응답 모델"""
    id: int
    post_id: int
    user_id: str
    parent_id: Optional[int]
    content: str
    created_at: datetime
    updated_at: datetime


class CommentService:
    """댓글 관련 비즈니스 로직"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
        )
    
    async def get_comments_by_post_id(self, post_id: int) -> List[Dict[str, Any]]:
        """게시글의 댓글 목록 조회 (계층 구조)"""
        try:
            # 게시글 존재 확인
            post_response = self.supabase.table("posts").select("id").eq("id", post_id).execute()
            if not post_response.data:
                raise ValueError("존재하지 않는 게시글입니다")
            
            # 댓글 조회 (사용자 정보 포함)
            comments_response = self.supabase.table("comments")\
                .select("""
                    *,
                    users!comments_user_id_fkey(username, display_name)
                """)\
                .eq("post_id", post_id)\
                .order("created_at", desc=False)\
                .execute()
            
            comments = comments_response.data if comments_response.data else []
            
            # 계층 구조로 정리
            return self._organize_comments_hierarchy(comments)
            
        except Exception as e:
            if "존재하지 않는 게시글" in str(e):
                raise e
            raise ValueError(f"댓글 목록 조회 실패: {str(e)}")
    
    def _organize_comments_hierarchy(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """댓글을 계층 구조로 정리 (부모-자식 관계)"""
        # 부모 댓글들 (parent_id가 None인 것들)
        parent_comments = [c for c in comments if c["parent_id"] is None]
        
        # 각 부모 댓글에 대해 자식 댓글들 찾기
        for parent in parent_comments:
            parent["replies"] = [
                c for c in comments 
                if c["parent_id"] == parent["id"]
            ]
        
        return parent_comments
    
    async def create_comment(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """댓글 작성"""
        try:
            # 필수 필드 검증
            if not comment_data.get("content"):
                raise ValueError("댓글 내용은 필수입니다")
            
            if not comment_data.get("post_id"):
                raise ValueError("게시글 ID는 필수입니다")
            
            if not comment_data.get("user_id"):
                raise ValueError("사용자 ID는 필수입니다")
            
            # 게시글 존재 확인
            post_response = self.supabase.table("posts").select("id").eq("id", comment_data["post_id"]).execute()
            if not post_response.data:
                raise ValueError("존재하지 않는 게시글입니다")
            
            # 부모 댓글 존재 확인 (답글인 경우)
            if comment_data.get("parent_id"):
                parent_response = self.supabase.table("comments")\
                    .select("id, post_id")\
                    .eq("id", comment_data["parent_id"])\
                    .execute()
                
                if not parent_response.data:
                    raise ValueError("존재하지 않는 부모 댓글입니다")
                
                # 부모 댓글과 같은 게시글인지 확인
                if parent_response.data[0]["post_id"] != comment_data["post_id"]:
                    raise ValueError("부모 댓글과 다른 게시글에는 답글을 작성할 수 없습니다")
            
            # 사용자 존재 확인
            user_response = self.supabase.table("users").select("id").eq("id", comment_data["user_id"]).execute()
            if not user_response.data:
                raise ValueError("존재하지 않는 사용자입니다")
            
            # XSS 방어를 위한 HTML 태그 필터링
            import bleach
            clean_content = bleach.clean(
                comment_data["content"], 
                tags=['p', 'br', 'strong', 'em'],
                strip=True
            )
            
            # 댓글 데이터 준비
            insert_data = {
                "post_id": comment_data["post_id"],
                "user_id": comment_data["user_id"],
                "content": clean_content,
                "parent_id": comment_data.get("parent_id")
            }
            
            response = self.supabase.table("comments").insert(insert_data).execute()
            
            if response.data:
                return response.data[0]
            else:
                raise ValueError("댓글 작성에 실패했습니다")
                
        except Exception as e:
            if any(msg in str(e) for msg in ["필수", "존재하지 않는", "작성할 수 없습니다"]):
                raise e
            raise ValueError(f"댓글 작성 실패: {str(e)}")
    
    async def get_comment_by_id(self, comment_id: int) -> Optional[Dict[str, Any]]:
        """ID로 댓글 조회"""
        try:
            response = self.supabase.table("comments")\
                .select("""
                    *,
                    users!comments_user_id_fkey(username, display_name)
                """)\
                .eq("id", comment_id)\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            raise ValueError(f"댓글 조회 실패: {str(e)}")
    
    async def update_comment(self, comment_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """댓글 수정"""
        try:
            # 존재 확인
            existing_comment = await self.get_comment_by_id(comment_id)
            if not existing_comment:
                raise ValueError("수정할 댓글을 찾을 수 없습니다")
            
            # 내용 검증
            if not update_data.get("content"):
                raise ValueError("댓글 내용은 빈 값일 수 없습니다")
            
            # XSS 방어를 위한 HTML 태그 필터링
            import bleach
            clean_content = bleach.clean(
                update_data["content"],
                tags=['p', 'br', 'strong', 'em'],
                strip=True
            )
            
            response = self.supabase.table("comments")\
                .update({"content": clean_content})\
                .eq("id", comment_id)\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            if any(msg in str(e) for msg in ["찾을 수 없습니다", "빈 값일 수 없습니다"]):
                raise e
            raise ValueError(f"댓글 수정 실패: {str(e)}")
    
    async def delete_comment(self, comment_id: int) -> bool:
        """댓글 삭제"""
        try:
            # 존재 확인
            existing_comment = await self.get_comment_by_id(comment_id)
            if not existing_comment:
                return False
            
            # 답글이 있는지 확인
            replies_response = self.supabase.table("comments")\
                .select("id")\
                .eq("parent_id", comment_id)\
                .limit(1)\
                .execute()
            
            if replies_response.data:
                raise ValueError("답글이 있는 댓글은 삭제할 수 없습니다")
            
            response = self.supabase.table("comments").delete().eq("id", comment_id).execute()
            
            # 삭제 성공 확인
            return len(response.data) > 0 if response.data else True
            
        except Exception as e:
            if "답글이 있는 댓글" in str(e):
                raise e
            raise ValueError(f"댓글 삭제 실패: {str(e)}")
    
    async def check_comment_permission(self, comment_id: int, user_id: str, is_admin: bool = False) -> Dict[str, bool]:
        """댓글 권한 확인 (수정/삭제)"""
        try:
            comment = await self.get_comment_by_id(comment_id)
            if not comment:
                return {"read": False, "update": False, "delete": False}
            
            # 읽기 권한: 모든 사용자
            can_read = True
            
            # 수정/삭제 권한: 작성자 또는 관리자
            is_owner = comment["user_id"] == user_id
            can_update = is_owner or is_admin
            can_delete = is_owner or is_admin
            
            return {
                "read": can_read,
                "update": can_update,
                "delete": can_delete,
                "is_owner": is_owner
            }
            
        except Exception as e:
            raise ValueError(f"권한 확인 실패: {str(e)}")
    
    async def get_comment_stats(self, post_id: Optional[int] = None) -> Dict[str, Any]:
        """댓글 통계 조회"""
        try:
            stats_query = self.supabase.table("comments")
            
            if post_id:
                # 게시글 존재 확인
                post_response = self.supabase.table("posts").select("id").eq("id", post_id).execute()
                if not post_response.data:
                    raise ValueError("존재하지 않는 게시글입니다")
                
                stats_query = stats_query.eq("post_id", post_id)
            
            # 전체 댓글 수
            total_response = stats_query.select("*", count="exact").execute()
            total_comments = total_response.count if total_response.count else 0
            
            # 오늘 댓글 수
            today = datetime.now().strftime("%Y-%m-%d")
            today_response = stats_query.select("*", count="exact").gte("created_at", today).execute()
            today_comments = today_response.count if today_response.count else 0
            
            return {
                "total_comments": total_comments,
                "today_comments": today_comments,
                "post_id": post_id
            }
            
        except Exception as e:
            if "존재하지 않는 게시글" in str(e):
                raise e
            raise ValueError(f"댓글 통계 조회 실패: {str(e)}")