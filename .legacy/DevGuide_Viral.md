## DevGuide_Viral.md — 개발 지침서 (바이럴 리포트 스택·알고리즘·OG·계측)

**요약 (3–5줄)**
Python-first 원칙으로 관계별 집계·PGI·합의도를 **단일 모듈(`core_report`)**에서 계산하고, 프런트는 React + Chart.js로 레이더·스택바·Gap 카드를 구현합니다. **언락(n≥3)**, **OG 템플릿**(1200×630/1080×1920), **GA4 이벤트**, **A/B 실험**이 내장되며, 모든 결과는 **decision_packet**으로 봉인합니다. RFC 9457 오류, X-Request-ID, OpenTelemetry 전파는 필수입니다.

```yaml
---
version: "1.0"
date: "2025-09-19"
audience: ["Backend","Frontend","Data","QA","Ops","Growth"]
owner: "Tech Lead: 이지율"
source_of_truth: "DevGuide_Viral.md"
---
```

### 1) 스택 & 코딩 규약

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, Redis(큐/레이트리밋)
- **Frontend:** React + TypeScript + Vite, React Router, TanStack Query, Zustand, Chart.js
- **OG 생성:** Node(Satori/Sharp) 또는 Headless Chromium, 엔드포인트 `/share/og/{token}.png`
- **Infra:** Cloud Run (BE), Cloud SQL(Postgres), Cloudflare (Pages/CDN/WAF)
- **Observability:** OpenTelemetry, 구조화 JSON 로깅, X-Request-ID 전파

코드 스타일은 Black/Isort/Flake8, FE는 ESLint + Prettier, 커밋은 기존 컨벤션 준수.

---

### 2) 아키텍처 모듈

- `invite`: 토큰 생성, 만료, 정원 관리
- `response`: 관계 태그 포함 응답 수집, 중복/봇 필터링
- `aggregate`: 분포/Top/합의도/PGI 계산 및 캐시
- `report`: 리포트 YAML/텍스트 생성, LLM 폴백 허용
- `og`: 템플릿 엔진, 캐시 키 관리, 이미지 렌더
- `safety`: k-익명 검증, 잠금 상태 제공
- `events`: GA4/UTM/A/B 실험 로깅
- `forensics`: decision_packet, audit 이벤트 기록

---

### 3) 데이터 모델 (DDL 발췌)

```sql
create type relation_tag as enum ('friend','coworker','spouse','family','other');

create table invites (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  token text unique not null,
  max_slots int default 30,
  expires_at timestamptz not null,
  created_at timestamptz default now()
);

create table relation_type_votes (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null,
  rater_id uuid null,
  relation relation_tag not null,
  type char(4) not null,
  submitted_at timestamptz default now(),
  user_agent text,
  ip_hash bytea
);

create table aggregate_rel (
  session_id uuid not null,
  relation relation_tag not null,
  n int not null,
  top1_type char(4) not null,
  top1_pct numeric(5,2) not null,
  top2_type char(4) not null,
  top2_pct numeric(5,2) not null,
  confidence numeric(5,3) not null,
  pgi numeric(5,1) not null,
  gap_axes text[] not null,
  updated_at timestamptz default now(),
  primary key (session_id, relation)
);

create table decision_packets (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null,
  packet_sha256 bytea not null,
  storage_url text not null,
  code_ref text not null,
  created_at timestamptz default now()
);

create table audit_events (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz default now(),
  req_id uuid not null,
  session_id uuid,
  event_type text not null,
  payload jsonb not null,
  prev_hash bytea,
  hash bytea not null,
  code_ref text not null
);
```

---

### 4) `core_report` 알고리즘 (참조 구현)

```python
# core_report.py
from collections import Counter
import math

TYPES = [
    "INTJ","INTP","ENTJ","ENTP","INFJ","INFP","ENFJ","ENFP",
    "ISTJ","ISFJ","ESTJ","ESFJ","ISTP","ISFP","ESTP","ESFP"
]
AXES = ["EI","SN","TF","JP"]

def entropy_confidence(counts: dict[str, int]) -> float:
    total = sum(counts.values()) or 1
    probs = [c/total for c in counts.values() if c > 0]
    entropy = -sum(p * math.log(p) for p in probs)
    return 1 - (entropy / math.log(len(TYPES)))

def hamming_axes(self_type: str, other_type: str):
    diffs = [axis for axis, (s, o) in zip(AXES, zip(self_type, other_type)) if s != o]
    return diffs, len(diffs)

def compute_relation_agg(self_type: str, votes: list[str]) -> dict:
    counts = Counter(votes)
    if not counts:
        return {
            "n": 0,
            "top1_type": self_type,
            "top1_pct": 0.0,
            "top2_type": self_type,
            "top2_pct": 0.0,
            "confidence": 0.0,
            "pgi": 0.0,
            "gap_axes": []
        }
    n = sum(counts.values())
    top1, c1 = counts.most_common(1)[0]
    second = counts.most_common(2)
    top2, c2 = (second[1] if len(second) > 1 else (self_type, 0))
    conf = entropy_confidence(counts)
    axes, distance = hamming_axes(self_type, top1)
    pgi = 25.0 * distance * (0.5 + 0.5 * conf)
    return {
        "n": n,
        "top1_type": top1,
        "top1_pct": round(100*c1/n, 1),
        "top2_type": top2,
        "top2_pct": round(100*c2/n, 1),
        "confidence": round(conf, 3),
        "pgi": round(pgi, 1),
        "gap_axes": axes
    }

def aggregate_session(self_type: str, votes_by_relation: dict[str, list[str]]):
    rel_results = {rel: compute_relation_agg(self_type, votes) for rel, votes in votes_by_relation.items()}
    total_weight, weighted = 0.0, 0.0
    weights = {"spouse": 1.2, "coworker": 1.1}
    for rel, data in rel_results.items():
        if data["n"] < 1:
            continue
        w = weights.get(rel, 1.0)
        weighted += data["pgi"] * w
        total_weight += w
    overall_pgi = round(weighted / total_weight, 1) if total_weight else 0.0
    return rel_results, overall_pgi
```

테스트: 단일 타입만 존재(n=10) → conf≈1, distance=0 → PGI=0. 균등분포 → conf≈0, PGI는 거리 기반. 경계(n<3) → 잠금 로직 확인.

---

### 5) API 요약 & 오류 규약

- `POST /v1/invite` → {relations[], max_n, expires_at} → 201 `{token, links[]}`
- `POST /v1/response/{token}` → {relation, answers} → 204
- `POST /v1/aggregate/{session_id}` → 집계 upsert, decision_packet 작성
- `GET /v1/report/{token}` → 관계별 카드/PGI/잠금 상태
- `GET /v1/share/og/{token}.png?style=story` → OG 이미지 반환 (<200ms)
- 오류 포맷: RFC 9457 Problem Details (`type,title,status,detail,instance,errors?`)
- 헤더: `X-Request-ID` 입력 → 미존재 시 생성, 응답/로그/트레이스 전파

---

### 6) 프런트엔드 구현 지침

- 라우팅: `/self`, `/invite`, `/respond/:token`, `/report/:token`
- 상태: TanStack Query로 API 캐싱/재검증, Zustand로 로컬 UI 상태 관리
- 차트: Chart.js Radar (Self vs 관계 평균), Stacked Bar (16유형×관계), 접근성 라벨 제공
- 잠금 UI: `n<3` 시 데이터 블러 처리 + “3명 더 받기” CTA + 배지
- OG 미리보기: FE에서 이미지 URL 로드, 공유 버튼(스토리/X/카카오) 이벤트 로깅

---

### 7) OG 이미지 생성

- 템플릿: 1200×630(링크), 1080×1920(스토리), 1080×1350(피드)
- 요소: 타이틀, Self/Top 배지, 미니 레이더, PGI, 응답자 수, 워터마크
- 캐시 키: `sha256(session_id + agg_sha + template_version)`
- SLA: 서버 렌더 <200ms, Cloudflare CDN 캐시 HIT 비율≥95%

---

### 8) 이벤트/분석/실험

- 이벤트: `begin_self`, `finish_self`, `invite_created(rel)`, `begin_other(rel)`, `finish_other`, `unlock_insight(n)`, `share_click(channel)`, `og_render(style)`
- 실험: OG 문구/색상, 언락 임계(3 vs 5), CTA 위치 → Feature flag/GA4 Experiment 관리
- 지표: K-Factor, 공유 CTR, 언락 달성률, 평균 응답자 수, PGI 중앙값

---

### 9) 보안 · 프라이버시 · 안전

- k-익명: n<3 세부 정보 차단, 잠금 상태 API/FE 동기화
- noindex: `X-Robots-Tag: noindex, nofollow`, `<meta name="robots" content="noindex">`
- 남용 방지: 레이트리밋, 허니팟 필드, 응답 시간 분석, IP/UA 해시 보관
- 데이터 최소화: 이메일/전화 미수집 기본, 닉네임/관계만 수집

---

### 10) 관측 · 포렌식

- Audit 이벤트: `invite.create`, `other.submit`, `aggregate.compute`, `share.og.create`
- Decision Packet: 입력(응답 스냅샷)·코드 버전·출력(집계/PGI)·OG 파라미터 해시 → WORM 저장
- Trace: OpenTelemetry span → DB/Redis/OG 렌더 포함, 로그와 요청 ID 조인 검증 ≥99%

---

### 11) 테스트 전략

- 유닛: 집계/PGI/합의도 → 균등/단일/이중피크/저응답 케이스
- 통합: n<3 잠금, OG 렌더 캐시키, RFC9457 오류 스냅샷, GA4 이벤트 전송 모킹
- E2E (Playwright): A 초대 → B 응답≥3 (친구/회사/연인) → 리포트 → OG 공유 (5 시나리오)
- 성능: k6 점증 부하, API P95<1s, OG <200ms, Redis 캐시 HIT≥90%
- 접근성: 키보드 탐색, 라벨, 차트 대체 텍스트, `prefers-reduced-motion` 처리

---

### 12) 배포 · 운영

- CI/CD: GitHub Actions → 테스트/빌드 → 스테이징 → Cloud Run 카나리(10→50→100)
- FE: Cloudflare Pages, BE: Cloud Run revision, DB: Cloud SQL, 캐시: Redis(Managed)
- 롤백: 에러율/INP 악화 시 즉시 이전 리비전으로 Rollback, 결정 패킷 롤백 로그 기록
- 비밀: Google Secret Manager, `.env.example` 공유, 실 비밀 미커밋

---

### 13) 카피/톤 가이드

- 표현: “~해 보일 수 있어요”, “~로 느껴질 여지가 있습니다” (단정/진단/비하 금지)
- 변수: `{relation_label, top1_type, top1_pct, confidence_label, gap_axes, pgi}`
- 실패 시: 규칙 기반 문구로 폴백(LLM 실패 대비)

---

### 14) 체크리스트 (Go-Live)

- [ ] 집계/PGI/합의도 스냅샷 테스트 통과
- [ ] n<3 잠금, OG 비식별, `noindex` 헤더 검증
- [ ] RFC9457 오류·요청 ID·OTel TraceJoin 성공
- [ ] Web Vitals (P75) 충족
- [ ] 레이트리밋/봇 억제 룰 적용
- [ ] Decision Packet 해시 검증 성공

---

### 부록 A. 리포트 YAML 템플릿 (발췌)

```yaml
header: >
  {user_name}님의 "관계별 인식 지도"입니다. Self={self_type}, 응답 {respondent_total}명.
relation_block: >
  [{relation_label}]에서는 {top1_type}({top1_pct}%) 경향이 두드러지며,
  의견 일치도는 {confidence_label}입니다.
gap_block: >
  Self({self_type})와 비교해 {relation_label}에서는 {gap_axes} 축에서 차이가 큽니다.
  (PGI {pgi_score}/100)
suggestion_block: >
  {relation_label} 상황에서는 {axis_tips}. 회의 전 기대치 정렬/발언 순서 합의 등.
closing: >
  3명 추가 응답 시 상세 인사이트가 열립니다. 공유 링크로 의견을 더 받아보세요.
```

