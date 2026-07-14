begin;

alter table public.fr_sections
  add column if not exists tags text[] not null default '{}'::text[];

alter table public.fr_sections
  add column if not exists featured_rank integer not null default 1000;

alter table public.fr_sections
  add constraint fr_sections_featured_rank_check
  check (featured_rank between 1 and 9999);

comment on column public.fr_sections.tags is
  'Canonical multi-value public profile labels. The client translates known labels.';

comment on column public.fr_sections.featured_rank is
  'Editorial discovery order only; it is not a popularity or AI score.';

update public.fr_sections
set kind = 'game',
    tags = array['mobile','supercell'],
    featured_rank = 1
where slug = 'brawl-stars';

update public.fr_sections
set tags = array['living-project'],
    featured_rank = 90
where slug = 'cuaderno-madre';

insert into public.fr_sections
  (slug, name, emoji, kind, tagline, tagline_es, tags, featured_rank)
values
  ('rubius', 'Rubius', '🕶️', 'creator',
   'Ideas from his community, gathered in one useful place.',
   'Ideas de su comunidad, reunidas en un lugar útil.',
   array['spain','streamer','youtuber','tiktoker'], 2),
  ('orslok', 'Orslok', '🎙️', 'creator',
   'Suggestions from the community, without getting lost in the feed.',
   'Sugerencias de la comunidad, sin perderse en el feed.',
   array['spain','streamer','youtuber','podcaster'], 3),
  ('ibai', 'Ibai', '🏆', 'creator',
   'Fan ideas ranked by usefulness and community demand.',
   'Ideas de fans ordenadas por utilidad y apoyo de la comunidad.',
   array['spain','streamer','youtuber','tiktoker'], 4),
  ('roblox', 'Roblox', '🧱', 'game',
   'Ideas for the game, creator tools and the wider platform.',
   'Ideas para el juego, las herramientas de creación y la plataforma.',
   array['platform','ugc','multiplayer'], 5),
  ('discord', 'Discord', '💬', 'social',
   'Community ideas for better conversations, servers and moderation.',
   'Ideas para mejorar conversaciones, servidores y moderación.',
   array['communities','chat','platform'], 6),
  ('x-twitter', 'X / Twitter', '🗣️', 'social',
   'Suggestions for a clearer, safer and more useful public conversation.',
   'Sugerencias para una conversación pública más clara, segura y útil.',
   array['social-network','microblogging','platform'], 7),
  ('chatgpt', 'ChatGPT', '✨', 'ai',
   'Ideas for a more capable, understandable and useful AI assistant.',
   'Ideas para un asistente de IA más capaz, comprensible y útil.',
   array['assistant','openai','productivity'], 8),
  ('claude', 'Claude', '🧠', 'ai',
   'Community suggestions for a more useful and trustworthy AI assistant.',
   'Sugerencias para un asistente de IA más útil y fiable.',
   array['assistant','anthropic','productivity'], 9)
on conflict (slug) do update
set name = excluded.name,
    emoji = excluded.emoji,
    kind = excluded.kind,
    tagline = excluded.tagline,
    tagline_es = excluded.tagline_es,
    tags = excluded.tags,
    featured_rank = excluded.featured_rank;

create or replace view public.fr_sections_stats
with (security_invoker = true)
as
select
  s.slug,
  s.name,
  s.emoji,
  s.kind,
  s.tagline,
  s.tagline_es,
  count(i.id)::integer as ideas,
  coalesce(sum(i.origin_upvotes), 0)::integer as reddit_upvotes,
  coalesce(sum(i.web_votes), 0)::integer as fan_votes,
  s.verification_status,
  s.tags,
  s.featured_rank,
  count(i.id) filter (where i.created_at >= now() - interval '30 days')::integer as recent_ideas
from public.fr_sections s
left join public.fr_ideas i
  on i.section = s.slug and i.approved = true
group by s.slug;

grant select on public.fr_sections_stats to anon, authenticated;

commit;
