# if i were you - Perception Gap Service

This project is now focused on one clear product goal:

- Compare "how I perceive myself" and "how others perceive me"
- Surface the gap in a safe, structured way
- Help people sustain healthier relationships through understanding, not judgment

The previous multi-service/platform direction has been archived under `.legacy/`.

## Active Service

- `mbti-arcade/` - FastAPI app for self/other input, invite flow, aggregation, and result views

## Archived (Legacy)

Moved to `.legacy/`:

- `main-service/`
- `nginx/`
- `docker-compose.yml`
- `README-Docker-Integrated.md`
- `PRD_Viral.md`
- `DevGuide_Viral.md`

## Quick Start

```bash
cd mbti-arcade
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- App: `http://localhost:8000`
- Health: `http://localhost:8000/healthz`

## Core Product Flow

1. Self input (`/mbti/self-test`)
2. Invite others (`/mbti/share`)
3. Compare self vs others in results

## Key Guardrails

- RFC 9457 Problem Details for API errors
- k>=3 anonymity threshold for aggregate exposure
- `noindex` policy for share/result surfaces
- Request ID and observability hooks
