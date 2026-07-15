# FanRank v5 — entity access and ranking guardrails

## Product boundary

FanRank accepts a suggestion without an account. A submission is a private inbox item, not a public idea: it starts as `received` and can only become a canonical public idea through review. Contact details are private and are stored only when the sender explicitly opts in.

A claim is also only a review request. It grants no team permissions until a reviewer marks the profile verified and creates its initial owner membership.

## Verified profile roles

| Role | Can do |
| --- | --- |
| Owner | Rate ideas with 1–5 official stars, choose the non-owner cap (1 or 3), invite/revoke admins and contributors. |
| Admin | Rate ideas up to the configured non-owner cap and invite/revoke contributors. |
| Contributor | Rate ideas up to the configured non-owner cap. |

No member can revoke themself or the owner. All role decisions are read from the live database inside the RPCs; browser state and JWT metadata never grant authority.

## Team invitations

- The server creates a cryptographically random token, stores only its hash, and expires it after 48 hours.
- The token is single-use and acceptance locks the invitation row.
- Acceptance requires a signed-in account whose confirmed email exactly matches the invite email.
- The invite token lives in the URL fragment (`#invite=`), so it is not sent in normal HTTP requests; the page removes it once handled.
- The public interface exposes only aggregate official-star signals. It never exposes which individual member rated an idea.

## Ranking signal

The deployed organic ranking is intentionally independent from the verified team:

```text
organic score = AI base + min(FanRank hearts × 2, 20)
official team signal = owner stars + aggregate member support (separate tab)
```

Team stars are evidence, not a 100-point override and not a guarantee that an idea ranks first. They are only available for a verified profile and order the separate official-team view. A future learned company criterion must run in shadow mode first, with logged rating changes, exposures and rank snapshots; it may order a private team inbox but must never change public ordering.

The legacy `owner_pick` field is pinned to `false` and is excluded from every browser ordering path. It cannot turn a team star into an automatic featured or first-ranked organic idea.

## Database boundary

- Private queues (`fr_submissions`, claims, team memberships, invitations, individual interests and votes) have no anonymous read access.
- Anonymous users can only create a constrained anonymous submission or vote through the allowed public path. They cannot publish, approve, set an owner pick, or create team data.
- Team operations use narrowly granted `SECURITY DEFINER` RPCs with `search_path` pinned to empty. The functions are executable only by `authenticated`, except the deliberately non-enumerable receipt-status lookup available to the sender.
- The team-star, membership and profile-invite tables have RLS without permissive anonymous reads by design; guarded RPCs enforce role, profile and star-cap boundaries.

## Verification evidence

Run from the repository root:

```powershell
python tests\test_fanrank.py
python tests\test_fanrank.py --live
```

The live suite checks public directory access, no fake verified-team signal, blocked anonymous reads/writes, blocked anonymous team RPCs, and a non-enumerable receipt lookup. On 2026-07-14 a separate live end-to-end probe created an anonymous suggestion (`201`), looked it up only through its private receipt (`200`, `received`), and immediately deleted it; the deletion check returned zero remaining rows.

## Required public-auth launch setting

The client uses Supabase passwordless email sign-in. Before promoting sign-in publicly, configure the Supabase Auth Site URL and allowed redirect URL for:

```text
https://eltonylfgi-blip.github.io/fanrank/
```

and configure a custom SMTP sender. The public Auth settings observed on 2026-07-14 showed email enabled but no Site URL or redirect allow-list. Without those settings, a magic-link redirect cannot be considered launched; Supabase also recommends custom SMTP for production deliverability and rate limits.
