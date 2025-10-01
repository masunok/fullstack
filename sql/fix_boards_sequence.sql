-- 게시판 테이블의 ID 시퀀스 수정
-- 현재 최대 ID를 찾아서 시퀀스를 올바르게 설정

-- 1. 현재 boards 테이블의 최대 ID 확인
DO $$
DECLARE
    max_id INTEGER;
    seq_name TEXT := 'boards_id_seq';
BEGIN
    -- 최대 ID 값 조회
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM public.boards;
    
    RAISE NOTICE 'Current max ID in boards table: %', max_id;
    
    -- 시퀀스를 최대 ID + 1로 설정
    PERFORM setval(seq_name, max_id + 1, false);
    
    RAISE NOTICE 'Sequence % reset to: %', seq_name, max_id + 1;
    
    -- 현재 시퀀스 값 확인
    RAISE NOTICE 'Next sequence value will be: %', nextval(seq_name);
    
    -- 시퀀스를 다시 최대 ID + 1로 되돌림 (nextval로 인해 증가했으므로)
    PERFORM setval(seq_name, max_id + 1, false);
    
END $$;

-- 2. 시퀀스 정보 확인
SELECT 
    schemaname,
    sequencename,
    last_value,
    start_value,
    increment_by,
    max_value,
    min_value,
    cache_value,
    log_cnt,
    is_cycled,
    is_called
FROM pg_sequences 
WHERE sequencename = 'boards_id_seq';
