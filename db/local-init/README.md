Local-only bootstrap files run by the `db` container on first boot (alphabetical order).
Do not run `000_local_supabase_stub.sql` against a real Supabase project - Supabase already
provides `auth`, roles and RLS support; only `supabase/migrations/*.sql` is meant for Supabase.
