-- leads 名單表
create table if not exists leads (
  id bigserial primary key,
  name text,
  email text not null,
  phone text,
  case_id text,
  tag text,
  payload_json jsonb,
  created_at timestamptz default now()
);

-- events 事件表（下載、聊天、提交等）
create table if not exists events (
  id bigserial primary key,
  kind text not null,          -- e.g. download_pdf / chat / submit_form
  ref_id bigint,               -- 關聯的 lead id（可為 null）
  note text,
  payload_json jsonb,
  created_at timestamptz default now()
);
