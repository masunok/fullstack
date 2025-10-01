import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from supabase import create_client, Client

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SoftDeleteMixin:
    """Soft Delete 공통 유틸리티"""
    
    @staticmethod
    def get_current_timestamp() -> str:
        """현재 UTC 시간을 ISO 형식으로 반환"""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def get_soft_delete_filter() -> dict:
        """Soft Delete 필터 조건 반환"""
        return {"deleted_at": "null"}
    
    def apply_soft_delete_filter(self, query_builder):
        """쿼리에 Soft Delete 필터 자동 적용"""
        return query_builder.is_("deleted_at", "null")


class UserUpdateRequest(BaseModel):
    """사용자 권한 변경 요청 모델"""
    is_admin: bool


class UserResponse(BaseModel):
    """사용자 응답 모델"""
    id: str
    username: str
    display_name: Optional[str]
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class AdminService(SoftDeleteMixin):
    """관리자 관련 비즈니스 로직 (Soft Delete 지원)"""

    def __init__(self):
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY"))
        )

    async def get_all_users(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """모든 사용자 목록 조회 (페이지네이션) - 삭제된 사용자 제외"""
        try:
            # 전체 사용자 수 조회 (삭제된 사용자 제외)
            count_response = self.supabase.table("users")\
                .select("*", count="exact")\
                .is_("deleted_at", "null")\
                .execute()
            total_count = count_response.count if count_response.count else 0

            # 페이지네이션 계산
            import math
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 사용자 목록 조회 (삭제된 사용자 제외, 추가 통계 포함)
            users_response = self.supabase.table("users")\
                .select("*")\
                .is_("deleted_at", "null")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()

            users = users_response.data if users_response.data else []

            # 각 사용자별 게시글/댓글 통계 추가
            for user in users:
                user_stats = await self._get_user_stats(user["id"])
                user.update(user_stats)

            return {
                "users": users,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages
            }

        except Exception as e:
            raise ValueError(f"사용자 목록 조회 실패: {str(e)}")

    async def get_all_users_including_deleted(self, page: int = 1, limit: int = 20, role: str = "all", sort: str = "created_desc") -> Dict[str, Any]:
        """모든 사용자 목록 조회 (삭제된 사용자 포함)"""
        try:
            # 카운트 쿼리 빌더
            count_query = self.supabase.table("users").select("*", count="exact")
            
            # role 필터 적용
            if role == "admin":
                count_query = count_query.eq("is_admin", True)
            elif role == "user":
                count_query = count_query.eq("is_admin", False)
            
            # 전체 사용자 수 조회 (삭제된 사용자 포함)
            count_response = count_query.execute()
            total_count = count_response.count if count_response.count else 0

            # 페이지네이션 계산
            import math
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 사용자 목록 쿼리 빌더
            users_query = self.supabase.table("users").select("*")
            
            # role 필터 적용
            if role == "admin":
                users_query = users_query.eq("is_admin", True)
            elif role == "user":
                users_query = users_query.eq("is_admin", False)
            
            # 정렬 적용
            if sort == "created_asc":
                users_query = users_query.order("created_at", desc=False)
            elif sort == "created_desc":
                users_query = users_query.order("created_at", desc=True)
            elif sort == "username_asc":
                users_query = users_query.order("username", desc=False)
            elif sort == "username_desc":
                users_query = users_query.order("username", desc=True)
            else:
                # 기본값: 삭제된 사용자 먼저, 그 다음 생성일자 역순
                users_query = users_query.order("deleted_at", desc=False, nullsfirst=True).order("created_at", desc=True)
            
            # 사용자 목록 조회
            users_response = users_query.range(offset, offset + limit - 1).execute()

            users = users_response.data if users_response.data else []
            print(f"[DEBUG] Retrieved {len(users)} users")
            
            # 전체 게시글의 user_id 샘플 확인 (한 번만 실행)
            all_posts_sample = self.supabase.table("posts")\
                .select("user_id")\
                .limit(10)\
                .execute()
            if all_posts_sample.data:
                sample_user_ids = [p.get('user_id') for p in all_posts_sample.data]
                print(f"[DEBUG] Sample user_ids from posts table: {sample_user_ids}")
                print(f"[DEBUG] User IDs types in posts: {[type(uid) for uid in sample_user_ids]}")
            
            # 사용자 ID 샘플
            if users:
                user_ids_sample = [u.get('id') for u in users[:5]]
                print(f"[DEBUG] Sample user IDs from users table: {user_ids_sample}")
                print(f"[DEBUG] User IDs types in users: {[type(uid) for uid in user_ids_sample]}")

            # 각 사용자별 게시글/댓글 통계 추가
            for user in users:
                print(f"[DEBUG] Processing user: {user.get('username', 'unknown')} with ID: {user['id']} (type: {type(user['id'])})")
                user_stats = await self._get_user_stats(user["id"])
                user.update(user_stats)
                
                # 삭제된 사용자 표시를 위한 플래그 추가
                user["is_deleted"] = user.get("deleted_at") is not None

            # 게시글 수에 따른 정렬 (메모리에서 재정렬)
            if sort == "posts_desc":
                users.sort(key=lambda x: x.get("posts_count", 0), reverse=True)

            return {
                "users": users,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "page_size": limit,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                }
            }

        except Exception as e:
            raise ValueError(f"사용자 목록 조회 실패 (삭제된 사용자 포함): {str(e)}")

    async def _get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """사용자별 통계 조회 (게시글 수, 댓글 수)"""
        try:
            # user_id 타입 처리 및 정규화
            if user_id is None:
                return {"posts_count": 0, "comments_count": 0, "last_activity": None}
            
            # user_id를 문자열로 정규화
            user_id_str = str(user_id).strip()
            
            # 디버깅용 로그 - 기본 정보
            print(f"[DEBUG] Processing user_id: {user_id_str} (original: {user_id}, type: {type(user_id)})")
            
            # 게시글 수 조회 - 여러 방법으로 시도
            posts_response = self.supabase.table("posts")\
                .select("*", count="exact")\
                .eq("user_id", user_id_str)\
                .execute()
            posts_count = posts_response.count if posts_response.count else 0
            
            # 만약 posts_count가 0이고 UUID 형태라면, 다른 방법으로 시도
            if posts_count == 0 and len(user_id_str) >= 32:  # UUID 길이 체크
                # PostgreSQL UUID 타입으로 다시 시도
                try:
                    posts_response_uuid = self.supabase.table("posts")\
                        .select("*", count="exact")\
                        .filter("user_id", "eq", user_id_str)\
                        .execute()
                    posts_count = posts_response_uuid.count if posts_response_uuid.count else 0
                    print(f"[DEBUG] UUID 타입으로 재시도 결과: {posts_count}")
                except Exception as uuid_e:
                    print(f"[DEBUG] UUID 타입 시도 실패: {uuid_e}")
            
            print(f"[DEBUG] Final posts count for {user_id_str}: {posts_count}")
            
            # 실제 게시글 데이터 확인
            posts_check = self.supabase.table("posts")\
                .select("id, user_id, title")\
                .eq("user_id", user_id_str)\
                .limit(3)\
                .execute()
            print(f"[DEBUG] Sample posts: {posts_check.data}")

            # 댓글 수
            comments_response = self.supabase.table("comments")\
                .select("*", count="exact")\
                .eq("user_id", user_id_str)\
                .execute()
            comments_count = comments_response.count if comments_response.count else 0

            # 최근 활동 (마지막 게시글 또는 댓글 날짜)
            recent_post_response = self.supabase.table("posts")\
                .select("created_at")\
                .eq("user_id", user_id_str)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            recent_comment_response = self.supabase.table("comments")\
                .select("created_at")\
                .eq("user_id", user_id_str)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()

            last_activity = None
            if recent_post_response.data:
                last_activity = recent_post_response.data[0]["created_at"]

            if recent_comment_response.data:
                comment_time = recent_comment_response.data[0]["created_at"]
                if not last_activity or comment_time > last_activity:
                    last_activity = comment_time

            return {
                "posts_count": posts_count,
                "comments_count": comments_count,
                "last_activity": last_activity
            }

        except Exception as e:
            return {
                "posts_count": 0,
                "comments_count": 0,
                "last_activity": None
            }

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ID로 사용자 조회"""
        try:
            response = self.supabase.table("users").select("*").eq("id", user_id).is_("deleted_at", "null").execute()

            if response.data:
                user = response.data[0]
                # 사용자 통계 추가
                user_stats = await self._get_user_stats(user_id)
                user.update(user_stats)
                return user
            return None

        except Exception as e:
            raise ValueError(f"사용자 조회 실패: {str(e)}")

    async def update_user_permissions(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """사용자 권한 변경"""
        try:
            # 존재 확인
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise ValueError("수정할 사용자를 찾을 수 없습니다")

            # 권한 변경 데이터 검증
            if "is_admin" not in update_data:
                raise ValueError("변경할 권한 정보가 필요합니다")

            if not isinstance(update_data["is_admin"], bool):
                raise ValueError("권한 값은 boolean이어야 합니다")

            # 자기 자신의 관리자 권한 해제 방지
            if existing_user.get("is_admin", False) and not update_data["is_admin"]:
                # 다른 관리자가 있는지 확인
                other_admins_response = self.supabase.table("users")\
                    .select("id")\
                    .eq("is_admin", True)\
                    .neq("id", user_id)\
                    .execute()

                if not other_admins_response.data:
                    raise ValueError("마지막 관리자의 권한을 해제할 수 없습니다")

            # 권한 업데이트
            response = self.supabase.table("users")\
                .update({"is_admin": update_data["is_admin"]})\
                .eq("id", user_id)\
                .execute()

            # 업데이트 후 사용자 정보 다시 조회해서 반환
            updated_user = await self.get_user_by_id(user_id)
            return updated_user

        except Exception as e:
            if any(msg in str(e) for msg in ["찾을 수 없습니다", "권한", "마지막 관리자"]):
                raise e
            raise ValueError(f"사용자 권한 변경 실패: {str(e)}")

    async def delete_user(self, user_id: str) -> bool:
        """사용자 삭제 (soft delete: deleted_at 필드 사용)"""
        try:
            # 존재 확인
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                return False

            # 이미 삭제된 사용자인지 확인
            if existing_user.get("deleted_at"):
                raise ValueError("이미 삭제된 사용자입니다")

            # 관리자 삭제 방지
            if existing_user.get("is_admin", False):
                # 다른 관리자가 있는지 확인 (삭제되지 않은 관리자만)
                other_admins_response = self.supabase.table("users")\
                    .select("id")\
                    .eq("is_admin", True)\
                    .neq("id", user_id)\
                    .is_("deleted_at", "null")\
                    .execute()

                if not other_admins_response.data:
                    raise ValueError("마지막 관리자는 삭제할 수 없습니다")

            # Soft Delete 수행 (공통 유틸리티 사용)
            now = self.get_current_timestamp()
            
            # 1. public.users 테이블 soft delete
            response = self.supabase.table("users")\
                .update({
                    "deleted_at": now
                    # is_admin 값은 그대로 유지 (삭제 취소 시 권한 복원을 위해)
                })\
                .eq("id", user_id)\
                .execute()

            # 2. auth.users 테이블 soft delete (RPC Function 사용)
            try:
                # PostgreSQL Function을 통해 auth.users 테이블 업데이트
                rpc_response = self.supabase.rpc(
                    'update_auth_user_deleted_at',
                    {'user_id': user_id, 'deleted_at': now}
                ).execute()
                logger.info(f"Auth.users soft deleted via RPC: {user_id} at {now}")
            except Exception as rpc_error:
                logger.warning(f"RPC function failed for {user_id}: {rpc_error}")
                
                # Admin API를 통한 대안 시도 (메타데이터 업데이트)
                try:
                    # 현재 사용자 정보 조회
                    current_user = self.supabase.auth.admin.get_user_by_id(user_id)
                    if current_user and current_user.user:
                        # 기존 메타데이터 유지하면서 deleted_at 추가
                        existing_metadata = current_user.user.app_metadata or {}
                        existing_metadata["deleted_at"] = now
                        
                        admin_response = self.supabase.auth.admin.update_user_by_id(
                            user_id,
                            {"app_metadata": existing_metadata}
                        )
                        logger.info(f"Auth user metadata updated with deleted_at: {user_id}")
                    else:
                        logger.warning(f"Could not retrieve user for metadata update: {user_id}")
                except Exception as admin_error:
                    logger.warning(f"Failed to update auth user metadata: {admin_error}")
                    logger.info(f"Note: auth.users deleted_at not updated for {user_id}, but public.users soft delete successful")

            logger.info(f"User soft deleted successfully: {user_id} at {now}")
            return True

        except Exception as e:
            if "마지막 관리자" in str(e) or "이미 삭제된" in str(e):
                raise e
            raise ValueError(f"사용자 삭제 실패: {str(e)}")

    async def restore_user(self, user_id: str) -> bool:
        """사용자 복원 (deleted_at을 NULL로 설정)"""
        try:
            # 삭제된 사용자인지 확인
            existing_user_response = self.supabase.table("users")\
                .select("*")\
                .eq("id", user_id)\
                .execute()
            
            if not existing_user_response.data:
                return False
            
            existing_user = existing_user_response.data[0]
            if not existing_user.get("deleted_at"):
                raise ValueError("이미 활성화된 사용자입니다")

            # 1. public.users 테이블 복원
            response = self.supabase.table("users")\
                .update({"deleted_at": None})\
                .eq("id", user_id)\
                .execute()

            # 2. auth.users 테이블 복원 (RPC Function 사용)
            try:
                # PostgreSQL Function을 통해 auth.users 테이블 복원
                rpc_response = self.supabase.rpc(
                    'restore_auth_user_deleted_at',
                    {'user_id': user_id}
                ).execute()
                logger.info(f"Auth.users restored via RPC: {user_id}")
            except Exception as rpc_error:
                logger.warning(f"RPC restore function failed for {user_id}: {rpc_error}")
                
                # Admin API를 통한 대안 시도 (메타데이터에서 deleted_at 제거)
                try:
                    # 현재 사용자 정보 조회
                    current_user = self.supabase.auth.admin.get_user_by_id(user_id)
                    if current_user and current_user.user:
                        # 기존 메타데이터에서 deleted_at만 제거
                        existing_metadata = current_user.user.app_metadata or {}
                        if "deleted_at" in existing_metadata:
                            del existing_metadata["deleted_at"]
                        
                        admin_response = self.supabase.auth.admin.update_user_by_id(
                            user_id,
                            {"app_metadata": existing_metadata}
                        )
                        logger.info(f"Auth user metadata restored (deleted_at removed): {user_id}")
                    else:
                        logger.warning(f"Could not retrieve user for metadata restore: {user_id}")
                except Exception as admin_error:
                    logger.warning(f"Failed to restore auth user metadata: {admin_error}")
                    logger.info(f"Note: auth.users deleted_at not restored for {user_id}, but public.users restore successful")

            logger.info(f"User restored successfully: {user_id}")
            return True

        except Exception as e:
            if "이미 활성화된" in str(e):
                raise e
            raise ValueError(f"사용자 복원 실패: {str(e)}")

    async def get_admin_stats(self) -> Dict[str, Any]:
        """관리자 대시보드용 전체 통계"""
        try:
            # 전체 사용자 수 (삭제된 사용자 제외)
            users_response = self.supabase.table("users")\
                .select("*", count="exact")\
                .is_("deleted_at", "null")\
                .execute()
            total_users = users_response.count if users_response.count else 0

            # 관리자 수 (삭제된 사용자 제외)
            admins_response = self.supabase.table("users")\
                .select("*", count="exact")\
                .eq("is_admin", True)\
                .is_("deleted_at", "null")\
                .execute()
            admin_count = admins_response.count if admins_response.count else 0

            # 전체 게시글 수
            posts_response = self.supabase.table("posts").select("*", count="exact").execute()
            total_posts = posts_response.count if posts_response.count else 0

            # 전체 댓글 수
            comments_response = self.supabase.table("comments").select("*", count="exact").execute()
            total_comments = comments_response.count if comments_response.count else 0

            # 오늘 가입 사용자 수
            today = datetime.now().strftime("%Y-%m-%d")
            today_users_response = self.supabase.table("users")\
                .select("*", count="exact")\
                .gte("created_at", today)\
                .is_("deleted_at", "null")\
                .execute()
            today_users = today_users_response.count if today_users_response.count else 0

            # 오늘 게시글 수
            today_posts_response = self.supabase.table("posts")\
                .select("*", count="exact")\
                .gte("created_at", today)\
                .execute()
            today_posts = today_posts_response.count if today_posts_response.count else 0

            # 활성 사용자 수 계산 (예: 최근 30일 이내 활동)
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

            # 최근 활동이 있는 사용자 조회 (게시글 또는 댓글 작성)
            active_users_posts = self.supabase.table("posts")\
                .select("user_id", count="exact")\
                .gte("created_at", thirty_days_ago)\
                .execute()

            active_users_comments = self.supabase.table("comments")\
                .select("user_id", count="exact")\
                .gte("created_at", thirty_days_ago)\
                .execute()

            # 실제 활성 사용자 수 계산 로직 필요
            active_users = total_users  # 임시로 전체 사용자 수로 설정

            return {
                "total_users": total_users,
                "admin_count": admin_count,
                "total_posts": total_posts,
                "total_comments": total_comments,

                "new_users_today": today_users,
                "today_posts": today_posts,
                "active_users": active_users
            }

        except Exception as e:
            raise ValueError(f"관리자 통계 조회 실패: {str(e)}")

    async def get_filtered_admin_stats(self, 
                                     query: Optional[str] = None, 
                                     search_type: str = "all", 
                                     role: str = "all", 
                                     include_deleted: bool = False) -> Dict[str, Any]:
        """검색/필터에 따른 동적 사용자 통계"""
        try:
            # 기본 쿼리 빌더
            query_builder = self.supabase.table("users").select("*", count="exact")
            
            # 삭제된 사용자 포함 여부
            if not include_deleted:
                query_builder = query_builder.is_("deleted_at", "null")
            
            # 검색어 적용
            if query and query.strip():
                search_pattern = f"%{query.strip()}%"
                if search_type == "username":
                    query_builder = query_builder.ilike("username", search_pattern)
                elif search_type == "email":
                    query_builder = query_builder.ilike("email", search_pattern)
                elif search_type == "display_name":
                    query_builder = query_builder.ilike("display_name", search_pattern)
                else:  # all
                    query_builder = query_builder.or_(
                        f"username.ilike.{search_pattern},"
                        f"email.ilike.{search_pattern},"
                        f"display_name.ilike.{search_pattern}"
                    )
            
            # 권한 필터 적용
            if role == "admin":
                query_builder = query_builder.eq("is_admin", True)
            elif role == "user":
                query_builder = query_builder.eq("is_admin", False)
            # "all"인 경우 필터 없음
            
            # 총 사용자 수 (필터 적용)
            total_response = query_builder.execute()
            total_users = total_response.count if total_response.count else 0
            
            # 활성 사용자 수 (필터 적용 + 삭제되지 않은 사용자)
            active_query_builder = self.supabase.table("users").select("*", count="exact").is_("deleted_at", "null")
            
            if query and query.strip():
                search_pattern = f"%{query.strip()}%"
                if search_type == "username":
                    active_query_builder = active_query_builder.ilike("username", search_pattern)
                elif search_type == "email":
                    active_query_builder = active_query_builder.ilike("email", search_pattern)
                elif search_type == "display_name":
                    active_query_builder = active_query_builder.ilike("display_name", search_pattern)
                else:  # all
                    active_query_builder = active_query_builder.or_(
                        f"username.ilike.{search_pattern},"
                        f"email.ilike.{search_pattern},"
                        f"display_name.ilike.{search_pattern}"
                    )
            
            if role == "admin":
                active_query_builder = active_query_builder.eq("is_admin", True)
            elif role == "user":
                active_query_builder = active_query_builder.eq("is_admin", False)
                
            active_response = active_query_builder.execute()
            active_users = active_response.count if active_response.count else 0
            
            # 관리자 수 (필터 적용)
            admin_query_builder = self.supabase.table("users").select("*", count="exact").eq("is_admin", True)
            
            if not include_deleted:
                admin_query_builder = admin_query_builder.is_("deleted_at", "null")
                
            if query and query.strip():
                search_pattern = f"%{query.strip()}%"
                if search_type == "username":
                    admin_query_builder = admin_query_builder.ilike("username", search_pattern)
                elif search_type == "email":
                    admin_query_builder = admin_query_builder.ilike("email", search_pattern)
                elif search_type == "display_name":
                    admin_query_builder = admin_query_builder.ilike("display_name", search_pattern)
                else:  # all
                    admin_query_builder = admin_query_builder.or_(
                        f"username.ilike.{search_pattern},"
                        f"email.ilike.{search_pattern},"
                        f"display_name.ilike.{search_pattern}"
                    )
            
            admin_response = admin_query_builder.execute()
            admin_count = admin_response.count if admin_response.count else 0
            
            # 오늘 신규 사용자 수 (필터 적용)
            today = datetime.now().strftime("%Y-%m-%d")
            today_query_builder = self.supabase.table("users").select("*", count="exact").gte("created_at", today)
            
            if not include_deleted:
                today_query_builder = today_query_builder.is_("deleted_at", "null")
                
            if query and query.strip():
                search_pattern = f"%{query.strip()}%"
                if search_type == "username":
                    today_query_builder = today_query_builder.ilike("username", search_pattern)
                elif search_type == "email":
                    today_query_builder = today_query_builder.ilike("email", search_pattern)
                elif search_type == "display_name":
                    today_query_builder = today_query_builder.ilike("display_name", search_pattern)
                else:  # all
                    today_query_builder = today_query_builder.or_(
                        f"username.ilike.{search_pattern},"
                        f"email.ilike.{search_pattern},"
                        f"display_name.ilike.{search_pattern}"
                    )
            
            if role == "admin":
                today_query_builder = today_query_builder.eq("is_admin", True)
            elif role == "user":
                today_query_builder = today_query_builder.eq("is_admin", False)
                
            today_response = today_query_builder.execute()
            new_users_today = today_response.count if today_response.count else 0
            
            return {
                "total_users": total_users,
                "active_users": active_users,
                "admin_count": admin_count,
                "new_users_today": new_users_today
            }
            
        except Exception as e:
            raise ValueError(f"필터링된 통계 조회 실패: {str(e)}")

    async def search_users(self, query: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """사용자 검색 - 삭제된 사용자 제외"""
        try:
            if not query.strip():
                raise ValueError("검색어를 입력해주세요")

            # 검색 패턴
            search_pattern = f"%{query}%"

            # 검색 결과 수 조회 (삭제된 사용자 제외)
            count_response = self.supabase.table("users")\
                .select("*", count="exact")\
                .or_(f"username.ilike.{search_pattern},display_name.ilike.{search_pattern}")\
                .not_.like("username", "[삭제된 사용자%")\
                .execute()
            total_count = count_response.count if count_response.count else 0

            # 페이지네이션 계산
            import math
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 검색 실행 (삭제된 사용자 제외)
            search_response = self.supabase.table("users")\
                .select("*")\
                .or_(f"username.ilike.{search_pattern},display_name.ilike.{search_pattern}")\
                .not_.like("username", "[삭제된 사용자%")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()

            users = search_response.data if search_response.data else []

            # 각 사용자별 통계 추가
            for user in users:
                user_stats = await self._get_user_stats(user["id"])
                user.update(user_stats)

            return {
                "users": users,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "query": query
            }

        except Exception as e:
            if "검색어를 입력" in str(e):
                raise e
            raise ValueError(f"사용자 검색 실패: {str(e)}")

    async def get_all_users_with_filters(self, page: int = 1, limit: int = 20, role: str = "all", sort: str = "created_desc") -> Dict[str, Any]:
        """필터와 정렬이 적용된 사용자 목록 조회 - 삭제된 사용자 제외"""
        try:
            # 기본 쿼리 빌더 (삭제된 사용자 제외)
            query_builder = self.supabase.table("users")\
                .select("*")\
                .is_("deleted_at", "null")

            # 권한 필터 적용
            if role == "admin":
                query_builder = query_builder.eq("is_admin", True)
            elif role == "user":
                query_builder = query_builder.eq("is_admin", False)
            # "all"인 경우 필터 없음

            # 전체 카운트 조회 (삭제된 사용자 제외)
            count_query = self.supabase.table("users")\
                .select("*", count="exact")\
                .is_("deleted_at", "null")

            if role == "admin":
                count_query = count_query.eq("is_admin", True)
            elif role == "user":
                count_query = count_query.eq("is_admin", False)

            count_response = count_query.execute()
            total_count = count_response.count if count_response.count else 0

            # 정렬 적용
            if sort == "created_asc":
                query_builder = query_builder.order("created_at", desc=False)
            elif sort == "username_asc":
                query_builder = query_builder.order("username", desc=False)
            elif sort == "posts_desc":
                # 게시글 많은순 정렬은 통계를 계산한 후 메모리에서 정렬해야 함
                # 일단 created_at으로 정렬하고 나중에 메모리에서 재정렬
                query_builder = query_builder.order("created_at", desc=True)
            else:  # "created_desc" (기본값)
                query_builder = query_builder.order("created_at", desc=True)

            # 페이지네이션 계산
            import math
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 데이터 조회
            response = query_builder.range(offset, offset + limit - 1).execute()
            users = response.data if response.data else []

            # 각 사용자별 게시글/댓글 통계 추가
            for user in users:
                user_stats = await self._get_user_stats(user["id"])
                user.update(user_stats)

            # 게시글 수에 따른 정렬 (메모리에서 재정렬)
            if sort == "posts_desc":
                users.sort(key=lambda x: x.get("posts_count", 0), reverse=True)

            return {
                "users": users,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "filters": {"role": role, "sort": sort}
            }

        except Exception as e:
            raise ValueError(f"필터된 사용자 목록 조회 실패: {str(e)}")

    async def search_users_with_filters(self, query: str, page: int = 1, limit: int = 20, search_type: str = "all", role: str = "all", sort: str = "created_desc") -> Dict[str, Any]:
        """검색과 필터가 적용된 사용자 조회 - 삭제된 사용자 제외"""
        try:
            if not query.strip():
                raise ValueError("검색어를 입력해주세요")

            # 검색 패턴
            search_pattern = f"%{query}%"

            # 기본 검색 쿼리 빌더
            search_conditions = []
            if search_type == "username" or search_type == "all":
                search_conditions.append(f"username.ilike.{search_pattern}")
            if search_type == "display_name" or search_type == "all":
                search_conditions.append(f"display_name.ilike.{search_pattern}")
            if search_type == "email" or search_type == "all":
                search_conditions.append(f"email.ilike.{search_pattern}")

            # 검색 조건이 없으면 오류 발생 방지
            if not search_conditions:
                raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

            search_filter = ",".join(search_conditions)

            # 카운트 쿼리 (삭제된 사용자 제외)
            count_query = self.supabase.table("users")\
                .select("*", count="exact")\
                .or_(search_filter)\
                .is_("deleted_at", "null")

            if role == "admin":
                count_query = count_query.eq("is_admin", True)
            elif role == "user":
                count_query = count_query.eq("is_admin", False)

            count_response = count_query.execute()
            total_count = count_response.count if count_response.count else 0

            # 검색 쿼리 (삭제된 사용자 제외)
            query_builder = self.supabase.table("users")\
                .select("*")\
                .or_(search_filter)\
                .is_("deleted_at", "null")

            # 권한 필터 적용
            if role == "admin":
                query_builder = query_builder.eq("is_admin", True)
            elif role == "user":
                query_builder = query_builder.eq("is_admin", False)

            # 정렬 적용
            if sort == "created_asc":
                query_builder = query_builder.order("created_at", desc=False)
            elif sort == "username_asc":
                query_builder = query_builder.order("username", desc=False)
            elif sort == "posts_desc":
                # 게시글 많은순 정렬은 통계를 계산한 후 메모리에서 정렬해야 함
                # 일단 created_at으로 정렬하고 나중에 메모리에서 재정렬
                query_builder = query_builder.order("created_at", desc=True)
            else:  # "created_desc" (기본값)
                query_builder = query_builder.order("created_at", desc=True)

            # 페이지네이션 계산
            import math
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 검색 실행
            response = query_builder.range(offset, offset + limit - 1).execute()
            users = response.data if response.data else []

            # 각 사용자별 통계 추가
            for user in users:
                user_stats = await self._get_user_stats(user["id"])
                user.update(user_stats)

            # 게시글 수에 따른 정렬 (메모리에서 재정렬)
            if sort == "posts_desc":
                users.sort(key=lambda x: x.get("posts_count", 0), reverse=True)

            return {
                "users": users,
                "total_count": total_count,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "query": query,
                "filters": {"search_type": search_type, "role": role, "sort": sort}
            }

        except Exception as e:
            if "검색어를 입력" in str(e):
                raise e
            raise ValueError(f"필터된 사용자 검색 실패: {str(e)}")

    async def search_users_including_deleted(self, query: str, page: int = 1, limit: int = 20, search_type: str = "all", role: str = "all", sort: str = "created_desc") -> Dict[str, Any]:
        """사용자 검색 (삭제된 사용자 포함)"""
        try:
            # 빈 검색어인 경우 모든 사용자 반환 (필터 적용)
            if not query.strip():
                return await self.get_all_users_including_deleted(page, limit, role, sort)

            # 검색 패턴
            search_pattern = f"%{query}%"

            # 기본 검색 쿼리 빌더
            search_conditions = []
            if search_type == "username" or search_type == "all":
                search_conditions.append(f"username.ilike.{search_pattern}")
            if search_type == "display_name" or search_type == "all":
                search_conditions.append(f"display_name.ilike.{search_pattern}")
            if search_type == "email" or search_type == "all":
                search_conditions.append(f"email.ilike.{search_pattern}")

            # 검색 조건이 없으면 오류 발생 방지
            if not search_conditions:
                raise ValueError(f"지원하지 않는 검색 타입입니다: {search_type}")

            search_filter = ",".join(search_conditions)

            # 카운트 쿼리 (삭제된 사용자 포함)
            count_query = self.supabase.table("users")\
                .select("*", count="exact")\
                .or_(search_filter)

            if role == "admin":
                count_query = count_query.eq("is_admin", True)
            elif role == "user":
                count_query = count_query.eq("is_admin", False)

            count_response = count_query.execute()
            total_count = count_response.count if count_response.count else 0

            # 페이지네이션 계산
            import math
            offset = (page - 1) * limit
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

            # 메인 검색 쿼리 (삭제된 사용자 포함)
            query_builder = self.supabase.table("users")\
                .select("*")\
                .or_(search_filter)

            if role == "admin":
                query_builder = query_builder.eq("is_admin", True)
            elif role == "user":
                query_builder = query_builder.eq("is_admin", False)

            # 정렬 적용
            if sort == "created_asc":
                query_builder = query_builder.order("created_at", desc=False)
            elif sort == "username_asc":
                query_builder = query_builder.order("username", desc=False)
            elif sort == "posts_desc":
                # 게시글 많은순 정렬은 통계를 계산한 후 메모리에서 정렬해야 함
                # 일단 created_at으로 정렬하고 나중에 메모리에서 재정렬
                query_builder = query_builder.order("created_at", desc=True)
            else:  # "created_desc" (기본값)
                query_builder = query_builder.order("created_at", desc=True)

            # 페이지네이션 적용
            users_response = query_builder.range(offset, offset + limit - 1).execute()
            users = users_response.data if users_response.data else []

            # 각 사용자별 게시글/댓글 통계 추가
            for user in users:
                user_stats = await self._get_user_stats(user["id"])
                user.update(user_stats)
                
                # 삭제된 사용자 표시를 위한 플래그 추가
                user["is_deleted"] = user.get("deleted_at") is not None

            # 게시글 수에 따른 정렬 (메모리에서 재정렬)
            if sort == "posts_desc":
                users.sort(key=lambda x: x.get("posts_count", 0), reverse=True)

            return {
                "users": users,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "page_size": limit,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "search_query": query,
                "search_type": search_type,
                "role_filter": role,
                "sort": sort
            }

        except Exception as e:
            raise ValueError(f"사용자 검색 실패 (삭제된 사용자 포함): {str(e)}")

    async def check_user_content(self, user_id: str) -> Dict[str, Any]:
        """사용자가 작성한 게시글과 댓글 존재 여부 및 상세 정보 체크"""
        try:
            # 디버깅: 사용자 ID 로깅
            logger.info(f"[DEBUG] Checking content for user_id: {user_id}")
            
            # 게시글 수 조회
            posts_response = self.supabase.table("posts")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            posts_count = posts_response.count if posts_response.count else 0
            logger.info(f"[DEBUG] Posts count: {posts_count}")

            # 댓글 수 조회 (부모댓글 + 답글 모두 포함)
            comments_response = self.supabase.table("comments")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .execute()
            comments_count = comments_response.count if comments_response.count else 0
            logger.info(f"[DEBUG] Comments count: {comments_count}")

            # 답글 수 별도 조회
            replies_response = self.supabase.table("comments")\
                .select("*", count="exact")\
                .eq("user_id", user_id)\
                .not_.is_("parent_id", "null")\
                .execute()
            replies_count = replies_response.count if replies_response.count else 0

            # 최근 게시글 상세 정보 (최대 5개)
            recent_posts = []
            if posts_count > 0:
                recent_posts_response = self.supabase.table("posts")\
                    .select("id, title, created_at")\
                    .eq("user_id", user_id)\
                    .order("created_at", desc=True)\
                    .limit(5)\
                    .execute()
                if recent_posts_response.data:
                    recent_posts = [
                        {
                            "id": post["id"],
                            "title": post["title"][:50] + ("..." if len(post["title"]) > 50 else ""),
                            "created_at": post["created_at"][:16]  # YYYY-MM-DD HH:MM 형식
                        }
                        for post in recent_posts_response.data
                    ]

            # 최근 댓글 상세 정보 (최대 5개)
            recent_comments = []
            if comments_count > 0:
                recent_comments_response = self.supabase.table("comments")\
                    .select("id, content, created_at, parent_id")\
                    .eq("user_id", user_id)\
                    .order("created_at", desc=True)\
                    .limit(5)\
                    .execute()
                if recent_comments_response.data:
                    recent_comments = [
                        {
                            "id": comment["id"],
                            "content": comment["content"][:100] + ("..." if len(comment["content"]) > 100 else ""),
                            "created_at": comment["created_at"][:16],  # YYYY-MM-DD HH:MM 형식
                            "is_reply": comment["parent_id"] is not None
                        }
                        for comment in recent_comments_response.data
                    ]

            # 사용자가 참여한 게시글 수 (댓글을 단 게시글)
            participated_posts_response = self.supabase.table("comments")\
                .select("post_id")\
                .eq("user_id", user_id)\
                .execute()

            participated_posts_count = 0
            if participated_posts_response.data:
                unique_post_ids = set(comment["post_id"] for comment in participated_posts_response.data)
                participated_posts_count = len(unique_post_ids)

            return {
                "has_content": posts_count > 0 or comments_count > 0,
                "posts_count": posts_count,
                "comments_count": comments_count,
                "replies_count": replies_count,
                "participated_posts_count": participated_posts_count,
                "recent_posts": recent_posts,
                "recent_comments": recent_comments,
                "deletion_type": "soft_delete"  # 모든 사용자에 대해 soft delete 수행
            }

        except Exception as e:
            logger.error(f"[ERROR] check_user_content failed for user_id {user_id}: {str(e)}")
            logger.error(f"[ERROR] Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                "has_content": False,
                "posts_count": 0,
                "comments_count": 0,
                "replies_count": 0,
                "participated_posts_count": 0,
                "recent_posts": [],
                "recent_comments": [],
                "deletion_type": "soft_delete",  # 에러 발생시에도 soft delete
                "error": str(e)
            }

    async def bulk_delete_users(self, user_ids: List[str], current_admin_id: str) -> Dict[str, Any]:
        """사용자 일괄 삭제"""
        try:
            if not user_ids:
                return {"success": 0, "failed": 0, "errors": []}

            success_count = 0
            failed_count = 0
            errors = []

            for user_id in user_ids:
                try:
                    # 자기 자신 삭제 방지
                    if user_id == current_admin_id:
                        errors.append(f"{user_id}: 자기 자신은 삭제할 수 없습니다")
                        failed_count += 1
                        continue

                    # 사용자 삭제 (기존 delete_user 메서드 사용)
                    result = await self.delete_user(user_id)
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{user_id}: 삭제 실패")

                except Exception as e:
                    failed_count += 1
                    if "마지막 관리자" in str(e):
                        errors.append(f"{user_id}: 마지막 관리자는 삭제할 수 없습니다")
                    else:
                        errors.append(f"{user_id}: {str(e)}")

            return {
                "success": success_count,
                "failed": failed_count,
                "errors": errors
            }

        except Exception as e:
            raise ValueError(f"일괄 삭제 실패: {str(e)}")

    async def bulk_promote_users(self, user_ids: List[str]) -> Dict[str, Any]:
        """사용자 일괄 승급 (관리자 권한 부여)"""
        try:
            if not user_ids:
                return {"success": 0, "failed": 0, "errors": []}

            success_count = 0
            failed_count = 0
            errors = []

            for user_id in user_ids:
                try:
                    # 사용자 존재 확인
                    user = await self.get_user_by_id(user_id)
                    if not user:
                        errors.append(f"{user_id}: 사용자를 찾을 수 없습니다")
                        failed_count += 1
                        continue

                    # 이미 관리자인 경우 스킵
                    if user.get("is_admin", False):
                        errors.append(f"{user['username']}: 이미 관리자입니다")
                        failed_count += 1
                        continue

                    # 관리자 권한 부여
                    result = await self.update_user_permissions(user_id, {"is_admin": True})
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{user.get('username', user_id)}: 권한 변경 실패")

                except Exception as e:
                    failed_count += 1
                    errors.append(f"{user_id}: {str(e)}")

            return {
                "success": success_count,
                "failed": failed_count,
                "errors": errors
            }

        except Exception as e:
            raise ValueError(f"일괄 승급 실패: {str(e)}")

    async def bulk_demote_users(self, user_ids: List[str], current_admin_id: str) -> Dict[str, Any]:
        """사용자 일괄 강등 (관리자 권한 제거)"""
        try:
            if not user_ids:
                return {"success": 0, "failed": 0, "errors": []}

            success_count = 0
            failed_count = 0
            errors = []

            # 전체 관리자 수 확인 (삭제된 사용자 제외)
            admins_response = self.supabase.table("users")\
                .select("id")\
                .eq("is_admin", True)\
                .not_.like("username", "[삭제된 사용자%")\
                .execute()
            total_admin_count = len(admins_response.data) if admins_response.data else 0

            # 강등 대상 중 관리자 수 확인
            admin_targets = []
            for user_id in user_ids:
                if user_id != current_admin_id:  # 자기 자신 제외
                    user = await self.get_user_by_id(user_id)
                    if user and user.get("is_admin", False):
                        admin_targets.append(user_id)

            # 마지막 관리자 보호
            if total_admin_count - len(admin_targets) < 1:
                return {
                    "success": 0,
                    "failed": len(user_ids),
                    "errors": ["최소 1명의 관리자가 남아있어야 합니다"]
                }

            for user_id in user_ids:
                try:
                    # 자기 자신 강등 방지
                    if user_id == current_admin_id:
                        errors.append(f"{user_id}: 자기 자신은 강등할 수 없습니다")
                        failed_count += 1
                        continue

                    # 사용자 존재 확인
                    user = await self.get_user_by_id(user_id)
                    if not user:
                        errors.append(f"{user_id}: 사용자를 찾을 수 없습니다")
                        failed_count += 1
                        continue

                    # 일반 사용자인 경우 스킵
                    if not user.get("is_admin", False):
                        errors.append(f"{user['username']}: 이미 일반 사용자입니다")
                        failed_count += 1
                        continue

                    # 관리자 권한 제거
                    result = await self.update_user_permissions(user_id, {"is_admin": False})
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"{user.get('username', user_id)}: 권한 변경 실패")

                except Exception as e:
                    failed_count += 1
                    errors.append(f"{user_id}: {str(e)}")

            return {
                "success": success_count,
                "failed": failed_count,
                "errors": errors
            }

        except Exception as e:
            raise ValueError(f"일괄 강등 실패: {str(e)}")