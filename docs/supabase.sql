-- Supabase 대시보드 → SQL Editor 에서 한 번 실행하세요.
-- 그 다음 .streamlit/secrets.toml 의 [supabase] url, key 를 채우면 앱이 Supabase를 사용합니다.

create table if not exists progress (
    sentence_id  integer primary key,
    learned_at   timestamptz,
    repeat_count integer not null default 0,
    status       text not null default 'new'
                 check (status in ('new', 'learned', 'confused', 'mastered'))
);

create table if not exists test_results (
    id        bigint generated always as identity primary key,
    week      integer not null,          -- 1~10 주간 테스트, 99 최종 테스트
    score     integer not null,
    taken_at  timestamptz not null default now(),
    wrong_ids jsonb not null default '[]'
);

create table if not exists settings (
    key   text primary key,
    value jsonb
);

-- 앱은 service_role 키(서버 전용)로 접속한다고 가정하고 RLS로 외부 접근을 막는다.
alter table progress     enable row level security;
alter table test_results enable row level security;
alter table settings     enable row level security;
