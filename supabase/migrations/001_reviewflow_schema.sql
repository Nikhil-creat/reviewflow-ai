-- =====================================================================
-- ReviewFlow AI - core schema  (Supabase / Postgres 15+ with pgvector)
-- Embeddings: 384 dims (sentence-transformers all-MiniLM-L6-v2, runs free
-- inside the backend container - Groq does not offer an embeddings API).
-- If you change EMBEDDING_MODEL, change vector(384) everywhere below.
-- =====================================================================

create extension if not exists pgcrypto;
create extension if not exists vector;
create extension if not exists pg_trgm;

-- ---------- enums ----------------------------------------------------
do $$ begin
  create type review_platform  as enum ('google','yelp','facebook','trustpilot','tripadvisor','manual');
  create type review_sentiment as enum ('positive','neutral','negative','volatile');
  create type review_status    as enum ('pending','analyzing','drafted','auto_replied','needs_human','approved','dismissed');
  create type embedding_kind   as enum ('past_reply','faq','policy','tone_sample');
  create type run_status       as enum ('running','completed','failed');
  create type event_level      as enum ('info','success','warning','error');
  create type member_role      as enum ('owner','admin','editor','viewer');
exception when duplicate_object then null; end $$;

-- ---------- helpers --------------------------------------------------
create or replace function public.set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ---------- profiles -------------------------------------------------
create table if not exists public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  email       text,
  full_name   text,
  avatar_url  text,
  plan        text not null default 'free' check (plan in ('free','pro','agency')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create trigger trg_profiles_updated before update on public.profiles
  for each row execute function public.set_updated_at();

-- auto-create a profile whenever someone signs up
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- businesses -----------------------------------------------
create table if not exists public.businesses (
  id                   uuid primary key default gen_random_uuid(),
  owner_id             uuid not null references public.profiles(id) on delete cascade,
  name                 text not null,
  industry             text,
  location             text,
  website              text,
  brand_voice_summary  text,                       -- distilled by the RAG agent
  auto_reply_enabled   boolean not null default true,
  auto_reply_min_stars smallint not null default 4 check (auto_reply_min_stars between 1 and 5),
  quote_card_theme     text not null default 'aurora',
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);
create index if not exists idx_businesses_owner on public.businesses(owner_id);
create trigger trg_businesses_updated before update on public.businesses
  for each row execute function public.set_updated_at();

create table if not exists public.business_members (
  business_id uuid not null references public.businesses(id) on delete cascade,
  user_id     uuid not null references public.profiles(id) on delete cascade,
  role        member_role not null default 'viewer',
  primary key (business_id, user_id)
);
create index if not exists idx_members_user on public.business_members(user_id);

-- access helper used by every RLS policy
create or replace function public.has_business_access(b uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.businesses x where x.id = b and x.owner_id = auth.uid())
      or exists (select 1 from public.business_members m where m.business_id = b and m.user_id = auth.uid());
$$;

-- ---------- reviews --------------------------------------------------
create table if not exists public.reviews (
  id               uuid primary key default gen_random_uuid(),
  business_id      uuid not null references public.businesses(id) on delete cascade,
  platform         review_platform not null default 'manual',
  external_id      text not null,                   -- id on the source platform (dedupe key)
  author_name      text,
  rating           smallint not null check (rating between 1 and 5),
  body             text not null default '',
  reviewed_at      timestamptz not null default now(),
  -- agent output
  sentiment        review_sentiment,
  sentiment_score  real,                            -- -1.0 .. 1.0
  intent_tags      text[] not null default '{}',    -- e.g. {refund,staff,pricing}
  risk_flags       text[] not null default '{}',    -- e.g. {legal_threat,profanity}
  key_phrases      text[] not null default '{}',    -- feeds the quote-card generator
  status           review_status not null default 'pending',
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (business_id, platform, external_id)
);
create index if not exists idx_reviews_business_status on public.reviews(business_id, status, reviewed_at desc);
create index if not exists idx_reviews_business_rating on public.reviews(business_id, rating);
create index if not exists idx_reviews_body_trgm on public.reviews using gin (body gin_trgm_ops);
create trigger trg_reviews_updated before update on public.reviews
  for each row execute function public.set_updated_at();

-- ---------- reply drafts (AI + human versions) ------------------------
create table if not exists public.reply_drafts (
  id                uuid primary key default gen_random_uuid(),
  review_id         uuid not null references public.reviews(id) on delete cascade,
  business_id       uuid not null references public.businesses(id) on delete cascade,
  body              text not null,
  model             text,
  confidence        real check (confidence between 0 and 1),
  voice_match       real check (voice_match between 0 and 1),  -- avg similarity of retrieved chunks
  retrieved_chunks  uuid[] not null default '{}',
  auto_posted       boolean not null default false,
  approved_by       uuid references public.profiles(id),
  posted_at         timestamptz,
  created_at        timestamptz not null default now()
);
create index if not exists idx_drafts_review on public.reply_drafts(review_id, created_at desc);
create index if not exists idx_drafts_business on public.reply_drafts(business_id, created_at desc);

-- ---------- brand-voice embeddings (RAG memory) ------------------------
create table if not exists public.embeddings (
  id           uuid primary key default gen_random_uuid(),
  business_id  uuid not null references public.businesses(id) on delete cascade,
  kind         embedding_kind not null default 'past_reply',
  content      text not null,
  metadata     jsonb not null default '{}'::jsonb,
  embedding    vector(384) not null,
  created_at   timestamptz not null default now()
);
create index if not exists idx_embeddings_business_kind on public.embeddings(business_id, kind);
-- HNSW = fast approximate cosine search, no training step required
create index if not exists idx_embeddings_hnsw on public.embeddings
  using hnsw (embedding vector_cosine_ops) with (m = 16, ef_construction = 64);

-- semantic retrieval used by the RAG Brand Voice Agent
create or replace function public.match_brand_chunks(
  p_business_id uuid,
  p_query       vector(384),
  p_match_count int default 5,
  p_min_sim     float default 0.25,
  p_kinds       embedding_kind[] default null
) returns table (id uuid, kind embedding_kind, content text, metadata jsonb, similarity float)
language sql stable as $$
  select e.id, e.kind, e.content, e.metadata, 1 - (e.embedding <=> p_query) as similarity
  from public.embeddings e
  where e.business_id = p_business_id
    and (p_kinds is null or e.kind = any(p_kinds))
    and 1 - (e.embedding <=> p_query) >= p_min_sim
  order by e.embedding <=> p_query
  limit p_match_count;
$$;

-- ---------- social assets (vision pipeline output) ---------------------
create table if not exists public.social_assets (
  id           uuid primary key default gen_random_uuid(),
  business_id  uuid not null references public.businesses(id) on delete cascade,
  review_id    uuid not null references public.reviews(id) on delete cascade,
  theme        text not null default 'aurora',
  image_path   text not null,
  quote_text   text not null,
  width        int not null default 1080,
  height       int not null default 1080,
  created_at   timestamptz not null default now()
);
create index if not exists idx_assets_business on public.social_assets(business_id, created_at desc);
create index if not exists idx_assets_review on public.social_assets(review_id);

-- ---------- agent runs + live telemetry ---------------------------------
create table if not exists public.agent_runs (
  id            uuid primary key default gen_random_uuid(),
  business_id   uuid not null references public.businesses(id) on delete cascade,
  review_id     uuid references public.reviews(id) on delete set null,
  status        run_status not null default 'running',
  reviews_seen  int not null default 0,
  auto_replied  int not null default 0,
  flagged       int not null default 0,
  error         text,
  started_at    timestamptz not null default now(),
  finished_at   timestamptz
);
create index if not exists idx_runs_business on public.agent_runs(business_id, started_at desc);

create table if not exists public.agent_events (
  id           bigint generated always as identity primary key,
  run_id       uuid references public.agent_runs(id) on delete cascade,
  business_id  uuid not null references public.businesses(id) on delete cascade,
  agent        text not null,          -- scraper | sentiment | rag_voice | dispatcher | vision
  level        event_level not null default 'info',
  message      text not null,
  duration_ms  int,
  payload      jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);
create index if not exists idx_events_business_time on public.agent_events(business_id, created_at desc);
create index if not exists idx_events_run on public.agent_events(run_id, id);

-- ---------- row level security ------------------------------------------
alter table public.profiles          enable row level security;
alter table public.businesses        enable row level security;
alter table public.business_members  enable row level security;
alter table public.reviews           enable row level security;
alter table public.reply_drafts      enable row level security;
alter table public.embeddings        enable row level security;
alter table public.social_assets     enable row level security;
alter table public.agent_runs        enable row level security;
alter table public.agent_events      enable row level security;

create policy "own profile"       on public.profiles for all using (id = auth.uid()) with check (id = auth.uid());

create policy "owner manages business" on public.businesses for all
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy "members read business"  on public.businesses for select
  using (public.has_business_access(id));

create policy "owner manages members" on public.business_members for all
  using (exists (select 1 from public.businesses b where b.id = business_id and b.owner_id = auth.uid()))
  with check (exists (select 1 from public.businesses b where b.id = business_id and b.owner_id = auth.uid()));
create policy "see own membership"    on public.business_members for select using (user_id = auth.uid());

create policy "tenant reviews"   on public.reviews        for all using (public.has_business_access(business_id)) with check (public.has_business_access(business_id));
create policy "tenant drafts"    on public.reply_drafts   for all using (public.has_business_access(business_id)) with check (public.has_business_access(business_id));
create policy "tenant embeds"    on public.embeddings     for all using (public.has_business_access(business_id)) with check (public.has_business_access(business_id));
create policy "tenant assets"    on public.social_assets  for all using (public.has_business_access(business_id)) with check (public.has_business_access(business_id));
create policy "tenant runs"      on public.agent_runs     for select using (public.has_business_access(business_id));
create policy "tenant events"    on public.agent_events   for select using (public.has_business_access(business_id));
-- The backend uses the service_role key, which bypasses RLS for writes.

-- ---------- realtime (Supabase) ------------------------------------------
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
    alter publication supabase_realtime add table public.reviews;
    alter publication supabase_realtime add table public.agent_events;
    alter publication supabase_realtime add table public.reply_drafts;
  end if;
exception when duplicate_object then null; end $$;

-- ---------- storage bucket for quote cards (Supabase only) ----------------
do $$
begin
  if exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    insert into storage.buckets (id, name, public)
    values ('social-assets', 'social-assets', true)
    on conflict (id) do nothing;
  end if;
end $$;
