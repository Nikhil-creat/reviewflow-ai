-- Review-source connector settings per business
alter table public.businesses add column if not exists connector text not null default 'demo'
  check (connector in ('demo','google_places','manual'));
alter table public.businesses add column if not exists google_place_id text;
alter table public.businesses add column if not exists last_synced_at timestamptz;
