import os
import math
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from supabase import create_client, Client


class PostRequest(BaseModel):
    """게시글 생성 요청 모델"""
    title: str
    content: str


class PostUpdateRequest(BaseModel):
    """게시글 수정 요청 모델"""
    title: Optional[str] = None
    content: Optional[str] = None


class PostResponse(BaseModel):
    """게시글 응답 모델"""
    id: int
    board_id: int
    user_id: str
    title: str
    content: str
    view_count: int
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    """게시글 목록 응답 모델"""
    posts: List[Dict[str, Any]]
    total_count: int
    page: int
    limit: int
    total_pages: int


class PostService:
    """게시글 관련 비즈니스 로직"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
        )
    
    async def get_posts_by_board_slug(self, board_slug: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """게시판별 게시글 목록 조회 (페이지네이션)"""
        try:
            # 게시판 ID 조회
            board_response = self.supabase.table("boards").select("id").eq("slug", board_slug).execute()
            if not board_response.data:
                raise ValueError("존재하지 않는 게시판입니다")
            
            board_id = board_response.data[0]["id"]
            
            # 전체 게시글 수 조회
            count_response = self.supabase.table("posts").select("*", count="exact").eq("board_id", board_id).execute()
            total_count = count_response.count if count_response.count else 0
            
            # 페이지네이션 계산
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            
            # 게시글 목록 조회 (사용자 정보 조인)
            posts_response = self.supabase.table("posts")\
                .select("""
                    *,
                    users!posts_user_id_fkey(username, display_name)
                """)\
                .eq("board_id", board_id)\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()

            # 성능 최적화: 모든 게시글의 댓글 수를 한 번에 조회
            if posts_response.data:
                post_ids = [post["id"] for post in posts_response.data]
                
                # 한 번의 쿼리로 모든 댓글 수 집계
                comment_counts = {}
                if post_ids:
                    # 각 post_id별로 댓글 수를 조회 (더 안전한 방식)
                    for post_id in post_ids:
                        try:
                            comment_count_response = self.supabase.table("comments")\
                                .select("*", count="exact")\
                                .eq("post_id", post_id)\
                                .execute()
                            comment_counts[post_id] = comment_count_response.count or 0
                        except Exception as e:
                            print(f"댓글 수 조회 오류 (post_id: {post_id}): {e}")
                            comment_counts[post_id] = 0
                
                # 각 게시글에 댓글 수 추가
                for post in posts_response.data:
                    post['comment_count'] = comment_counts.get(post["id"], 0)
            
            return {
                "posts": posts_response.data,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages
            }
            
        except Exception as e:
            if "존재하지 않는 게시판" in str(e):
                raise e
            raise ValueError(f"게시글 목록 조회 실패: {str(e)}")
    
    async def get_post_by_id(self, post_id: int, increment_view: bool = False) -> Optional[Dict[str, Any]]:
        """ID로 게시글 조회"""
        try:
            # 게시글 조회 (사용자 및 게시판 정보 조인)
            response = self.supabase.table("posts")\
                .select("""
                    *,
                    users!posts_user_id_fkey(username, display_name),
                    boards!posts_board_id_fkey(name, slug, write_permission)
                """)\
                .eq("id", post_id)\
                .execute()
            
            if not response.data:
                return None
            
            post = response.data[0]
            
            # 조회수 증가 (선택적)
            if increment_view:
                await self.increment_view_count(post_id)
                post["view_count"] += 1
            
            return post
            
        except Exception as e:
            raise ValueError(f"게시글 조회 실패: {str(e)}")
    
    async def create_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """게시글 생성"""
        try:
            # 필수 필드 검증
            if not post_data.get("title"):
                raise ValueError("제목은 필수 입력 사항입니다")
            
            if not post_data.get("content"):
                raise ValueError("내용은 필수 입력 사항입니다")
            
            if not post_data.get("board_id"):
                raise ValueError("게시판 ID는 필수입니다")
            
            if not post_data.get("user_id"):
                raise ValueError("사용자 ID는 필수입니다")
            
            # 게시판 존재 확인
            board_response = self.supabase.table("boards").select("id").eq("id", post_data["board_id"]).execute()
            if not board_response.data:
                raise ValueError("존재하지 않는 게시판입니다")
            
            # 사용자 존재 확인
            user_response = self.supabase.table("users").select("id").eq("id", post_data["user_id"]).execute()
            if not user_response.data:
                raise ValueError("존재하지 않는 사용자입니다")
            
            # 제목 길이 검증
            if len(post_data["title"]) > 200:
                raise ValueError("제목은 200자를 초과할 수 없습니다")
            
            # XSS 방어를 위한 HTML 태그 필터링 (Quill.js 에디터 호환)
            import bleach
            clean_title = bleach.clean(post_data["title"], tags=[], strip=True)
            clean_content = bleach.clean(
                post_data["content"],
                tags=['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote', 'img'],
                attributes={
                    '*': [],
                    'img': ['src', 'alt', 'width', 'height']
                },
                protocols=['data'],
                strip=True
            )
            
            # 게시글 데이터 준비
            insert_data = {
                "board_id": post_data["board_id"],
                "user_id": post_data["user_id"],
                "title": clean_title,
                "content": clean_content,
                "view_count": 0
            }
            
            response = self.supabase.table("posts").insert(insert_data).execute()
            
            if response.data:
                return response.data[0]
            else:
                raise ValueError("게시글 생성에 실패했습니다")
                
        except Exception as e:
            if any(msg in str(e) for msg in ["필수", "존재하지 않는", "초과할 수 없습니다"]):
                raise e
            raise ValueError(f"게시글 생성 실패: {str(e)}")
    
    async def update_post(self, post_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """게시글 수정"""
        try:
            # 존재 확인
            existing_post = await self.get_post_by_id(post_id)
            if not existing_post:
                raise ValueError("수정할 게시글을 찾을 수 없습니다")
            
            # 수정 가능한 필드만 필터링
            allowed_fields = ["title", "content"]
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields and v is not None}
            
            if not filtered_data:
                raise ValueError("수정할 데이터가 없습니다")
            
            # 제목 검증
            if "title" in filtered_data:
                if not filtered_data["title"].strip():
                    raise ValueError("제목은 빈 값일 수 없습니다")
                if len(filtered_data["title"]) > 200:
                    raise ValueError("제목은 200자를 초과할 수 없습니다")
            
            # 내용 검증
            if "content" in filtered_data:
                if not filtered_data["content"].strip():
                    raise ValueError("내용은 빈 값일 수 없습니다")
            
            # XSS 방어를 위한 HTML 태그 필터링 (Quill.js 에디터 호환)
            import bleach
            if "title" in filtered_data:
                filtered_data["title"] = bleach.clean(filtered_data["title"], tags=[], strip=True)
            if "content" in filtered_data:
                filtered_data["content"] = bleach.clean(
                    filtered_data["content"],
                    tags=['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote', 'img'],
                    attributes={
                        '*': [],
                        'img': ['src', 'alt', 'width', 'height']
                    },
                    protocols=['data'],
                    strip=True
                )
            
            response = self.supabase.table("posts").update(filtered_data).eq("id", post_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            if any(msg in str(e) for msg in ["찾을 수 없습니다", "빈 값일 수 없습니다", "수정할 데이터가 없습니다", "초과할 수 없습니다"]):
                raise e
            raise ValueError(f"게시글 수정 실패: {str(e)}")
    
    async def delete_post(self, post_id: int) -> bool:
        """게시글 삭제"""
        try:
            # 존재 확인
            existing_post = await self.get_post_by_id(post_id)
            if not existing_post:
                return False
            
            # 댓글 존재 확인 (댓글이 있으면 삭제 불가 또는 함께 삭제)
            comments_response = self.supabase.table("comments").select("id").eq("post_id", post_id).limit(1).execute()
            if comments_response.data:
                # 댓글이 있는 경우 - 여기서는 함께 삭제
                self.supabase.table("comments").delete().eq("post_id", post_id).execute()
            
            response = self.supabase.table("posts").delete().eq("id", post_id).execute()
            
            # 삭제 성공 확인
            return len(response.data) > 0 if response.data else True
            
        except Exception as e:
            raise ValueError(f"게시글 삭제 실패: {str(e)}")
    
    async def increment_view_count(self, post_id: int) -> bool:
        """조회수 증가"""
        try:
            # 현재 조회수 조회
            response = self.supabase.table("posts").select("view_count").eq("id", post_id).execute()
            if not response.data:
                return False
            
            current_count = response.data[0]["view_count"]
            new_count = current_count + 1
            
            # 조회수 업데이트
            update_response = self.supabase.table("posts").update({"view_count": new_count}).eq("id", post_id).execute()
            
            return len(update_response.data) > 0 if update_response.data else True
            
        except Exception as e:
            raise ValueError(f"조회수 증가 실패: {str(e)}")
    
    async def search_posts(self, query: str, board_slug: Optional[str] = None, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """게시글 검색"""
        try:
            # 검색 쿼리 구성
            search_query = self.supabase.table("posts").select("""
                *,
                users!posts_user_id_fkey(username, display_name),
                boards!posts_board_id_fkey(name, slug)
            """)

            # 게시판 필터링
            board_ids = []
            if board_slug:
                # 여러 게시판 처리 (콤마로 구분된 값)
                board_slugs = [slug.strip() for slug in board_slug.split(",")]
                for slug in board_slugs:
                    board_response = self.supabase.table("boards").select("id").eq("slug", slug).execute()
                    if board_response.data:
                        board_ids.append(board_response.data[0]["id"])

                if not board_ids:
                    raise ValueError("존재하지 않는 게시판입니다")

                if len(board_ids) == 1:
                    search_query = search_query.eq("board_id", board_ids[0])
                else:
                    # 여러 게시판의 경우 in_ 사용
                    search_query = search_query.in_("board_id", board_ids)

            # 전체 개수 조회
            count_query = self.supabase.table("posts").select("*", count="exact")
            if board_ids:
                if len(board_ids) == 1:
                    count_query = count_query.eq("board_id", board_ids[0])
                else:
                    count_query = count_query.in_("board_id", board_ids)

            # 검색어가 있으면 검색 조건 추가, 없으면 전체 조회
            if query.strip():
                search_pattern = f"%{query}%"
                count_response = count_query.or_(f"title.ilike.{search_pattern},content.ilike.{search_pattern}").execute()
                search_query = search_query.or_(f"title.ilike.{search_pattern},content.ilike.{search_pattern}")
            else:
                count_response = count_query.execute()

            total_count = count_response.count if count_response.count else 0

            # 페이지네이션 계산
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 검색 실행
            search_response = search_query\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return {
                "posts": search_response.data,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "query": query,
                "board_slug": board_slug
            }
            
        except Exception as e:
            if "검색어를 입력" in str(e) or "존재하지 않는 게시판" in str(e):
                raise e
            raise ValueError(f"게시글 검색 실패: {str(e)}")
    
    async def check_post_permission(self, post_id: int, user_id: str, is_admin: bool = False) -> Dict[str, bool]:
        """게시글 권한 확인 (읽기/수정/삭제)"""
        try:
            post = await self.get_post_by_id(post_id)
            if not post:
                return {"read": False, "update": False, "delete": False}
            
            # 읽기 권한: 모든 사용자
            can_read = True
            
            # 수정/삭제 권한: 작성자 또는 관리자
            is_owner = post["user_id"] == user_id
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
    
    async def get_post_stats(self, board_slug: Optional[str] = None) -> Dict[str, Any]:
        """게시글 통계 조회"""
        try:
            stats_query = self.supabase.table("posts")
            
            if board_slug:
                board_response = self.supabase.table("boards").select("id").eq("slug", board_slug).execute()
                if not board_response.data:
                    raise ValueError("존재하지 않는 게시판입니다")
                board_id = board_response.data[0]["id"]
                stats_query = stats_query.eq("board_id", board_id)
            
            # 전체 게시글 수
            total_response = stats_query.select("*", count="exact").execute()
            total_posts = total_response.count if total_response.count else 0
            
            # 오늘 게시글 수
            today = datetime.now().strftime("%Y-%m-%d")
            today_response = stats_query.select("*", count="exact").gte("created_at", today).execute()
            today_posts = today_response.count if today_response.count else 0
            
            # 총 조회수
            view_response = stats_query.select("view_count").execute()
            total_views = sum(post.get("view_count", 0) for post in view_response.data) if view_response.data else 0
            
            return {
                "total_posts": total_posts,
                "today_posts": today_posts,
                "total_views": total_views,
                "board_slug": board_slug
            }
            
        except Exception as e:
            if "존재하지 않는 게시판" in str(e):
                raise e
            raise ValueError(f"게시글 통계 조회 실패: {str(e)}")

    async def get_latest_posts_for_main(self, limit: int = 5) -> List[Dict[str, Any]]:
        """메인 페이지용 최신 게시글 조회"""
        try:
            # 최신 게시글을 게시판 정보와 작성자 정보와 함께 조회
            response = self.supabase.table("posts")\
                .select("""
                    id, title, content, view_count, created_at,
                    boards(name),
                    users(username, display_name)
                """)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()

            if not response.data:
                return []

            latest_posts = []

            for post in response.data:
                # 댓글 수 조회
                comments_response = self.supabase.table("comments")\
                    .select("id", count="exact")\
                    .eq("post_id", post["id"])\
                    .execute()

                comment_count = comments_response.count or 0

                # 내용 미리보기 생성 (HTML 태그 제거 후 100자 제한)
                import bleach
                content_text = bleach.clean(post["content"], tags=[], strip=True)
                content_preview = content_text[:100] + "..." if len(content_text) > 100 else content_text

                # 데이터 정리
                latest_post = {
                    "id": post["id"],
                    "title": post["title"],
                    "content_preview": content_preview,
                    "view_count": post["view_count"] or 0,
                    "created_at": post["created_at"],
                    "comment_count": comment_count,
                    "board_name": post["boards"]["name"] if post["boards"] else "Unknown",
                    "author_name": post["users"]["display_name"] or post["users"]["username"] if post["users"] else "Unknown"
                }

                latest_posts.append(latest_post)

            return latest_posts

        except Exception as e:
            # 에러 발생 시 빈 리스트 반환하여 서비스 중단 방지
            print(f"최신 게시글 조회 오류: {str(e)}")
            return []