# Owner Progress Funnel (MVP)

This doc describes the login-less owner funnel patterns implemented for the NamBTI-style benchmark.

## Owner Access Model

- Exchange URL: `GET /o/{owner_token}`
  - Purpose: one-time entry point that sets `owner_token` as an HttpOnly cookie and redirects to `/me`.
  - Storage: only `sha256(owner_token)` is stored in DB as `sessions.owner_token_hash`.
  - Rationale: avoids keeping owner secrets in URLs after the initial exchange.

- Owner pages:
  - `GET /me` (progress + share UI)
  - `GET /me/report` (minimal HTML report page)

## Polling-Safe Status Endpoint

- Endpoint: `GET /v1/invites/{invite_token}/status`
- Auth: public-by-invite-token (count-only)
- Cache: `Cache-Control: no-store`

Response fields:

```json
{
  "respondent_count": 1,
  "threshold": 3,
  "unlocked": false,
  "expires_at": "2026-02-25T00:00:00Z",
  "max_raters": 50,
  "updated_at": "2026-02-25T00:00:00Z"
}
```

Semantics:

- `respondent_count` counts participants where `participants.answers_submitted_at IS NOT NULL`.
- `unlocked` flips when `respondent_count >= threshold`.

## Owner-Only Data Surfaces

The following are restricted to owners (require `Cookie: owner_token=...`):

- `GET /v1/participants/{invite_token}/preview`
- `GET /v1/report/session/{session_id}`
- `GET /v1/report/participant/{participant_id}`

## Client Polling Behavior

On `/me` the client polls `data-status-url`:

- initial interval: ~4s
- backoff: multiply by ~1.5 on unchanged, up to 30s
- error backoff: multiply by ~2 on errors, up to 30s
- jitter: 0-700ms added per tick
- stop: once unlocked, UI flips to unlocked state and polling stops

## Kakao Readiness Checklist (Optional)

Current MVP uses the Web Share API (when available) and falls back to copy.

To add KakaoTalk share later:

- Register a Kakao Developers app and whitelist domains.
- Add env var name (no values in git): `KAKAO_JAVASCRIPT_KEY`.
- Ensure CSP allows Kakao SDK if needed.
- Keep fallback order: Kakao -> Web Share API -> copy.
