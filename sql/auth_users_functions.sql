-- Supabase Auth Users Soft Delete Functions
-- 이 SQL을 Supabase Dashboard의 SQL Editor에서 실행하세요.

-- 1. auth.users 테이블의 deleted_at 업데이트 함수
CREATE OR REPLACE FUNCTION update_auth_user_deleted_at(user_id UUID, deleted_at TIMESTAMPTZ)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- auth.users 테이블의 deleted_at 컬럼 업데이트
    UPDATE auth.users 
    SET deleted_at = update_auth_user_deleted_at.deleted_at
    WHERE id = update_auth_user_deleted_at.user_id;
    
    -- 업데이트된 행이 있으면 TRUE 반환
    RETURN FOUND;
END;
$$;

-- 2. auth.users 테이블의 deleted_at 복원 함수 (NULL로 설정)
CREATE OR REPLACE FUNCTION restore_auth_user_deleted_at(user_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- auth.users 테이블의 deleted_at을 NULL로 설정
    UPDATE auth.users 
    SET deleted_at = NULL
    WHERE id = restore_auth_user_deleted_at.user_id;
    
    -- 업데이트된 행이 있으면 TRUE 반환
    RETURN FOUND;
END;
$$;

-- 3. 함수들에 대한 권한 설정 (서비스 역할에만 실행 권한 부여)
GRANT EXECUTE ON FUNCTION update_auth_user_deleted_at(UUID, TIMESTAMPTZ) TO service_role;
GRANT EXECUTE ON FUNCTION restore_auth_user_deleted_at(UUID) TO service_role;

-- 함수 사용 예제:
-- SELECT update_auth_user_deleted_at('user-uuid-here', NOW());
-- SELECT restore_auth_user_deleted_at('user-uuid-here');

-- 4. Boards 테이블 시퀀스 수정 함수
CREATE OR REPLACE FUNCTION fix_boards_sequence()
RETURNS TABLE(
    message TEXT,
    old_sequence_value BIGINT,
    new_sequence_value BIGINT,
    max_id_found INTEGER
) AS $$
DECLARE
    max_id INTEGER;
    old_seq_val BIGINT;
    new_seq_val BIGINT;
BEGIN
    -- 현재 boards 테이블의 최대 ID 찾기
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM public.boards;
    
    -- 현재 시퀀스 값 확인
    SELECT last_value INTO old_seq_val FROM pg_sequences WHERE sequencename = 'boards_id_seq';
    
    -- 시퀀스를 최대 ID + 1로 설정
    PERFORM setval('boards_id_seq', max_id + 1, false);
    
    -- 새 시퀀스 값 확인
    SELECT last_value INTO new_seq_val FROM pg_sequences WHERE sequencename = 'boards_id_seq';
    
    -- 결과 반환
    RETURN QUERY SELECT 
        'Boards sequence fixed successfully'::TEXT as message,
        old_seq_val as old_sequence_value,
        new_seq_val as new_sequence_value,
        max_id as max_id_found;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execution rights to the service_role
GRANT EXECUTE ON FUNCTION fix_boards_sequence() TO service_role;
