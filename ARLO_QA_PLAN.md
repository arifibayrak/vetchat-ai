# Arlo — Speed, Accuracy, Evidence & UX Plan

> Synthesised from two QA passes (Claude structured probe suite + nanobot hands-on UX test) on the live deployment at https://askarlo.co.uk.
>
> **One-line diagnosis:** *The clinical synthesis is already vet-grade. Everything downstream of Claude is what's holding Arlo back — retrieval corpus is tiny, evidence plumbing is leaky, and onboarding friction kills first impressions.*

---

## Scorecard (combined from both testers)

| Dimension | Score | Primary driver |
|---|---|---|
| Visual design / positioning | 4.0 / 5 | Clean, credible, vet-specific — brand works |
| Completion reliability (2nd run) | 4.5 / 5 | Improved after retry; auth was the blocker |
| Emergency / clinical usefulness | 4.5 / 5 | Claude synthesis is strong |
| Follow-up structure | 4.0 / 5 | Directionally great when it fires; `reuse_prior` broken |
| Chat response structure | 3.75 / 5 | "Limited direct evidence" opens almost every answer |
| **Evidence integrity** | **2.5 / 5** | **Corpus is 108 journal stubs + mock chunks** |
| **Reference UX** | **2.5 / 5** | Raw DOIs, no "why it matters", empty quotes |
| **Perceived speed** | **2.5 / 5** | 28–59s vs "< 10s" landing-page promise |
| Auth / onboarding | 3.0 / 5 | Register→login handoff breaks on repeat |
| Overall trustworthiness | 3.75 / 5 | Brand promises more than product currently delivers |

---

## The "only 4 sources" root cause

**The retrieval corpus is mostly empty.**

- `backend/scripts/seed_taylor_francis.py:31-44` seeds each T&F entry as `"Journal: X | Subtitle: Y | Publisher: T&F | ISSN: … | URL: …"` — that's a 6-field metadata stub, **not an article abstract**. 108 stubs can never rank high against a clinical query like "xylitol toxicity in dogs".
- `backend/app/main.py:33-44` also seeds mock chunks on empty Chroma — real live users see DOIs like `10.1016/mock.2019.xylitol.001` cited as evidence.
- Live ScienceDirect + Springer results are gated by an MS-MARCO cross-encoder (`reranker.py:17-19`) tuned for web search, not biomed. Threshold `-0.5` cuts most biomedical abstracts, fallback `_MIN_RESULTS=2` kicks in. Same for Chroma.
- Net result on every probe: **~2 live (min floor) + ~2 Chroma (min floor) = 4 total sources.** Not a cap, a floor.

Fixing this is the single highest-leverage change in the plan.

---

## Phase 1 — Trust foundations (Week 1)

Goal: stop bleeding trust on the first impression.

### 1.1 Purge mock data from production [P0, 30 min]
- Add a boot-time cleanup in `backend/app/main.py` that deletes any Chroma entry where `doi LIKE '%mock%'` or `source_type == 'abstract' AND publisher == 'Literature'`.
- Remove the `seed_mock` call from `_background_boot` (main.py:41). Keep the script for local dev but gate it behind `settings.seed_mock_data` (default `False`; enable only in `ENV=dev`).
- Redeploy. Verify on live: no citation should ever show publisher `"Literature"` or DOI containing `mock`.

### 1.2 Fix the 4-sources floor [P0, 2 days]
Two moves. Either alone helps; both together solve it.

**A. Loosen the cross-encoder gate for biomedical text (1 hour)**
- `backend/app/services/reranker.py:17-20`:
  ```py
  _CHROMA_THRESHOLD = -2.0   # was -1.0
  _LIVE_THRESHOLD = -1.5     # was -0.5
  _MIN_RESULTS = 4           # was 2
  ```
- Rationale: MS-MARCO scores are shifted ~2 points negative for biomed abstracts vs web queries. Current thresholds mostly force the `_MIN_RESULTS` fallback. Raising the floor to 4 + loosening the gate lifts typical total to 8–10.

**B. Swap the reranker for a biomed-aware one (1 day)**
- Replace `cross-encoder/ms-marco-MiniLM-L-6-v2` with `ncbi/MedCPT-Cross-Encoder` or `pritamdeka/S-PubMedBert-MS-MARCO`.
- Both are ~100MB, Railway-compatible, and trained on PubMed.
- Keep the score→bucket mapping in `score_to_bucket()` but recalibrate the thresholds empirically: run the 12-probe suite, pick thresholds at the 25th percentile of real hits.

### 1.3 Fix auth friction [P0, 3 hours]
From nanobot: `/register` → "already registered" without auto-login kills new-user flow.
- `backend/app/api/auth.py:31-60` — on `register` with existing email, return the same token response as `login` (passwordless anyway) instead of 409. Add a log line; don't surface the error to the user.
- Frontend: `/register` and `/login` should render as a single "Continue with email" screen that handles both cases server-side. The user's UX shouldn't differ.
- Rename the landing CTA "Login via mail" → "Continue with email". Four places in `LandingPage.tsx:68, 155, 938, 970`.

### 1.4 Fix emergency false-positives [P0, 2 hours]
Both QA runs surfaced this. My probe 3 ("chocolate **lab** puppy") and probe 11 ("**human toddler** ibuprofen") both fired `emergency: true`.
- `backend/app/services/emergency_detector.py`: add a negation window around each toxin keyword.
  - If `chocolate` is within 3 tokens of `lab`, `labrador`, `retriever`, `breed`, `patient is a`, suppress.
  - If any toxin keyword appears within 5 tokens of `human`, `toddler`, `child`, `pediatric`, `person`, suppress — and route to the out-of-scope refusal instead of the emergency card.
- Add a regression test: `tests/test_emergency_detector.py` — add both probes as explicit negative cases.

### 1.5 Write Privacy Policy + Terms of Service [P0, 2 hours]
The footer (`LandingPage.tsx:998`) links to `#`. For a UK beta with veterinarians:
- Short Privacy Policy covering GDPR basics, query retention, Anthropic data-handling.
- ToS covering beta status, no clinical-substitute clause, RCVS framing.
- Replace the landing-page claim "Your queries are not stored or used for training" (line 905) with whatever is actually true after implementing.

### 1.6 Honest latency copy [P0, 5 min]
Replace `LandingPage.tsx:774` "under 10 seconds" with "a structured, cited answer in under a minute" until Phase 2 lands. Overclaiming on speed is a credibility leak.

---

## Phase 2 — Rebuild the evidence layer (Weeks 2–3)

Goal: retrieval that actually supports the answer.

### 2.1 Replace T&F journal stubs with real article ingestion [P0, 1 week]
The current `taylor_francis_journals.json` is 108 journal *names*. Useless for RAG.
- Build an ingest script that pulls the **top 100 most-cited articles per T&F journal** (or the last 3 years' articles) via the Crossref API (free, no key) — pulls title, abstract, DOI, year, authors.
- Target corpus size: **~10,000 real abstracts** across the 108 journals. Chroma handles this comfortably.
- Reuse `backend/app/ingestion/chunker.py` and `embedder.py` — already built.
- Gate this behind a one-time script run, not the boot-time auto-seed (which blocks startup).

### 2.2 Populate `abstract` and `relevant_quote` fields [P0, 1 day]
Every citation in production has empty `relevant_quote` and empty `abstract`. The `CitationItem` fields are designed for it (`backend/app/models/chat.py:15-18`) and the UI renders them (`MessageBubble.tsx`) — they're just not being populated.
- During ingestion, store the full abstract in the chunk metadata.
- `backend/app/api/chat.py:49-81` (`_extract_relevant_quote`) — verify it runs; it returns "" when `abstract` is empty, which is always. Fix once 2.1 ships abstracts.

### 2.3 Fix `reuse_prior` follow-up path [P1, 4 hours]
My probe 10 proved it's broken — sent `prior_citations` on a follow-up, full retrieval ran anyway, pulled in an unrelated human-pharmacology paper.
- Audit the guard at `chat.py:326` — confirm when `reuse_prior` evaluates true.
- Frontend: confirm `ChatPage.tsx` / `useChat.ts` sends `prior_citations: parent_message.citations` on follow-ups.
- Regression test: `tests/test_chat_reliability.py` already has `test_follow_up_fast_path` patterns — add a live integration test.

### 2.4 Emit `emergency_preliminary` events [P1, 2 hours]
Probes 1 and 2 were genuine emergencies but **no** `emergency_preliminary` SSE event fired. The `EmergencyPreliminaryCard` in the frontend is dead code as a result.
- `backend/app/api/chat.py` emergency branch — yield an `emergency_preliminary` event **before** the full RAG runs, with `{category, heading, priorities[]}`.
- This also enables nanobot's suggestion of a "short clinical shell first, then full synthesis".

### 2.5 Retune the `[Direct evidence]` tagger [P1, 4 hours]
`backend/app/services/evidence_tagger.py` — currently assigns `[Direct evidence]` too liberally. Probe 1 tagged a *mock* paper as "Direct evidence". New rule:
- `[Direct evidence]` requires `rerank_score ≥ 2.0` **and** `species_relevance matches detected species` **and** a non-mock DOI.
- Downgrade to `[Review]` or `[Weak indirect]` otherwise.

---

## Phase 3 — Reference UX redesign (Week 3)

Goal: vets trust the sources at a glance.

### 3.1 Source cards, not citation dumps [P1, 2 days]
Today the references panel renders citations as academic-style lists. Nanobot's suggested format (which aligns with the `CitationItem` fields that already exist):

```
Smith et al. · 2022
Journal of Veterinary Emergency and Critical Care
🟢 Direct evidence · 🐕 Dogs · 📘 Review article
"Furosemide remains first-line for acute CHF; recommended dose 2–4 mg/kg IV…"
Why it matters: supports the furosemide dose and the 4–6-hour reassessment window above.
[Hide DOI ▾]
```

- Rebuild `frontend/components/MessageBubble.tsx` references panel around this card format.
- Collapse DOI behind a "Copy citation" button; surface the `why_it_matters` field that already exists in `CitationItem` but is usually blank.

### 3.2 Generate `why_it_matters` server-side [P1, 4 hours]
The field exists (`backend/app/models/chat.py:33`) but isn't populated.
- After Claude finishes, make one small follow-up call per cited source: *"In one clinician-friendly sentence, why does this source support the claim at [n]?"*
- Low cost: Haiku 4.5 + ~200-token prompt × cited_count. ~50ms each, parallel.

### 3.3 Inline evidence tags stay; drop the "Evidence: Limited · 1 of 4 sources cited" banner [P2, 1 hour]
Nanobot flagged this banner as trust-damaging when it fires on almost every answer. Replace with a subtler footer: just the source-card strip. If `cited_count < 2`, append a sentence in the "Evidence Gaps" section — but don't lead with it.

---

## Phase 4 — Perceived speed (Week 3)

Goal: 28–59s is the real floor; make the wait feel like 5s.

### 4.1 Immediate clinical shell (< 2s) [P1, 1 day]
Nanobot called this out explicitly.
- When query arrives, route to Haiku 4.5 in parallel with retrieval.
- Haiku emits a 3-line "Immediate Priorities" block based on the query alone, with `[Preliminary — evidence synthesis in progress]` tag.
- Stream this as `answer_chunk` events before retrieval completes.
- When the full RAG result arrives, stream the replacement. Frontend shows the shell, then transitions to the full answer — user sees progress in < 2s.

### 4.2 Parallelise retrieval steps [P2, 4 hours]
Current flow: `refine_query → Chroma || live_search → rerank → claude_stream`. The first two can be parallelised; they already are (`chat.py:232`, `loop.run_in_executor`). Audit that they truly overlap and are not serialised by thread-pool starvation.

### 4.3 Warm the cross-encoder on boot [P2, 1 hour]
Cold-start of the reranker model adds ~3s on the first query after a Railway deploy. Load it in `_background_boot` (`main.py:29`) with a single dummy predict to warm the weights.

### 4.4 Progress steps with real substance [P2, 2 hours]
Current steps are generic ("Understanding…", "Searching…"). Replace with specifics the vet can see value in:
- `step 1: "Detected: 9-year-old feline, PU/PD, weight loss"` (from `detect_species` + query parse)
- `step 2: "Querying ScienceDirect + Scopus for feline polyuria/polydipsia differentials"`
- `step 3: "Found 12 sources, 4 highly relevant, 3 review articles"`

---

## Phase 5 — Launch readiness (Week 4)

### 5.1 Telemetry [P1, 1 day]
Log per-request: `evidence_mode`, `fallback_kind`, `cited_count`, `total_sources`, `latency_ms`, `first_chunk_ms`, `emergency_flag_correct` (from user thumbs-up/down). Pipe to a simple dashboard (Railway + Logtail or Grafana Cloud free tier). This gives you the data to track whether Phase 2 actually improved quality.

### 5.2 Vet-only gate option [P2, 4 hours]
Anonymous `/chat` works today. For public launch, either:
- Keep open (good for demos, bad for rate-limiting) — add Cloudflare Turnstile or similar
- Gate behind email auth — simplest lever is to require a token on the Next.js proxy at `frontend/app/api/chat/route.ts`.

### 5.3 RCVS / medico-legal framing [P2, 2 hours]
- Landing page: add a short banner near the hero: *"For use by registered veterinary professionals. Not a substitute for clinical judgment."*
- Chat disclaimer: already present, fine.
- Footer: add RCVS number / company registration once registered (you mentioned a domain for beta).

### 5.4 Mobile pass [P2, 1 day]
Landing page's 4-column `HowItWorks` pipeline (`LandingPage.tsx:786`) clips on mobile. Chat UI rendering on iPhone-width not yet verified. Do one pass with a 390px viewport.

---

## Prioritised ship list (concrete)

| # | Action | Effort | File(s) | Impact |
|---|--------|--------|---------|--------|
| 1 | Purge mock data + disable auto-seed | 30 min | `main.py`, `seed_mock_data.py` | **Stops fake DOIs reaching vets** |
| 2 | Loosen rerank thresholds + `_MIN_RESULTS=4` | 1 hr | `reranker.py:17-20` | **Doubles source count immediately** |
| 3 | Fix auth register→login auto-token | 3 hr | `auth.py:31-60`, frontend | Unblocks first-time users |
| 4 | Fix emergency false-positives | 2 hr | `emergency_detector.py` | Stops embarrassing misfires |
| 5 | Replace CTA copy + landing latency claim | 15 min | `LandingPage.tsx:68,155,774` | Honest marketing |
| 6 | Write Privacy + ToS | 2 hr | new pages + footer | Legal hygiene |
| 7 | Ingest real T&F/Crossref abstracts (~10k) | 1 week | new script + ingestion pipeline | **Real evidence for the first time** |
| 8 | Populate `abstract` + `relevant_quote` | 1 day | ingestion + `_extract_relevant_quote` | Reference cards have content |
| 9 | Swap reranker to MedCPT or S-PubMedBert | 1 day | `reranker.py:30` | Better biomed relevance |
| 10 | Fix `reuse_prior` follow-up path | 4 hr | `chat.py:326` + frontend | Delta-shaped follow-ups |
| 11 | Immediate clinical shell via Haiku | 1 day | `chat.py` + `useChat.ts` | Perceived speed in < 2s |
| 12 | Redesign reference cards + `why_it_matters` | 2 days | `MessageBubble.tsx` + server call | Trust jump |
| 13 | Emit `emergency_preliminary` events | 2 hr | `chat.py` | Activates dead UI code |
| 14 | Retune evidence tagger | 4 hr | `evidence_tagger.py` | No more `[Direct evidence]` on weak sources |
| 15 | Telemetry dashboard | 1 day | server logging + dashboard | Measure the improvement |

**Week 1 goal (items 1–6):** live site never cites fake papers, never misfires emergencies, onboarding works. ~2 days of work.

**Weeks 2–3 goal (items 7–14):** real evidence layer, fast-feeling responses, vet-friendly references. ~2 weeks of work.

**Week 4 (item 15 + polish):** ready for wider beta.

---

## What explicitly stays the same

- Claude's system prompt and answer structure — both QA runs praise it.
- Disclaimer injection — working, appropriate.
- Adversarial / out-of-scope refusal quality — strong (probe 12 + nanobot observations).
- Progress step pattern — keep, just make labels meaningful.
- Landing page visual design — keep; brand works.
- Three tab example section + algorithm cards — keep; strong differentiators.

---

## Verification checklist (post-Phase 1)

Run the same 12-probe suite after each phase. Success criteria:

**After Phase 1:**
- 0 citations with DOI containing `mock` or publisher `"Literature"`
- Probes 3 and 11 return `emergency: false`
- Register with existing email → user lands in chat, not error screen
- Privacy Policy + ToS links resolve

**After Phase 2:**
- Median `total_sources` ≥ 8 (vs current 4)
- Median `cited_count` ≥ 4 (vs current 1–2)
- `relevant_quote` non-empty on ≥ 80% of citations
- Probe 10 returns `reuse_prior=true` path with no new retrievals
- Probes 1–2 emit `emergency_preliminary` before RAG completes

**After Phase 4:**
- Time-to-first-visible-content ≤ 2s on all probes
- Total answer latency median ≤ 20s (vs current 35s)

**After Phase 5:**
- Dashboard exists, shows per-query `cited_count`, `evidence_mode`, latency
- Mobile layout doesn't clip at 390px width
