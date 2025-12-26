# GhostLine Review Report (ASK1–ASK3)

**Last Updated**: 2025-12-24  
**Purpose**: Living review of product intent vs current implementation, across architecture/features, code reuse, and science/ML.

---

## Executive Verdict: Does the app match the product intent?

**Not end-to-end yet.** The monorepo contains solid scaffolding (projects, uploads, task tracking, LangGraph subgraphs, frontend wiring), but the core promise—**grounded long-form ghostwriting with durable human-in-the-loop checkpoints**—is blocked by:

- **Schema drift** (migrations ≠ ORM ≠ services)
- **RAG/memory not actually feeding generation**
- **Voice/fact “scores” are currently LLM-self-reported, not measured**
- **Durability is not guaranteed** (in-memory LangGraph checkpointing)
- **Safety layer is missing** (important for mental-health content)

See `docs/AI_IMPLEMENTATION_PLAN.md` for the updated roadmap.

---

## ASK1 — Architecture / Feature Review

### Critical correctness bugs (architecture level)
- **WorkflowService field mismatches**: outline generation references non-existent DB fields (e.g., `Project.name`, `SourceMaterial.metadata/original_filename` vs current schema).
- **“Full book generation”** uses an outer workflow that is largely placeholder (ingest/embed/draft nodes are not executing the real pipeline).
- **Task state model vs DB enum mismatch** risks runtime failures when persisting `PAUSED/QUEUED` and other states.

### Key architecture mismatches vs `docs/AI_plan.txt`
- Durable async pipeline exists conceptually, but durability is not real without persistent checkpointing.
- Multi-agent “talk” exists in subgraphs, but the outer pipeline doesn’t yet use ingestion+RAG in a production-correct way.
- Memory system (vector DB + summaries + structured artifacts) is present as tables/models, but not functioning end-to-end.

---

## ASK2 — Code Reuse Audit (DEPRECATED-* repos)

### What was found
- **DEPRECATED-api**: helpful *endpoint patterns* for chapters/outline/export UX, but **no hidden AI pipeline** (services were placeholders there).
- **DEPRECATED-web**: valuable as a *frontend baseline* (strong testing harness; had Tiptap dependencies), but it did not contain a full editor UX.
- **DEPRECATED-agents**: essentially empty (no agent logic to reuse).
- **DEPRECATED-infra**: mostly AWS scripts; conceptually useful (safe migrations, restricted DB user), but not reusable as-is for local-first dev.
- **DEPRECATED-docs**: mainly duplicates of documentation already present in-monorepo.

### Net outcome
**The missing functionality is not “forgotten code” in old repos.** The blocking gaps are primarily:
- schema drift
- incomplete wiring (ingest → chunks → embeddings → retrieval → drafting)
- missing evaluation + safety contracts

---

## ASK3 — Science / ML Review

### Embeddings (current state)
- Uses sentence-transformers and then **pads/truncates** to a fixed 1536 dimension to match DB.
- This is operationally workable, but it’s a smell: it complicates reasoning about models and makes it easy to silently drift.
- **More importantly**: the embedding model is not clearly separated by purpose:
  - RAG retrieval embeddings ≠ “voice style” embeddings

### Memory / RAG (current state)
- Chunk storage + retrieval is not reliably functional due to schema drift.
- Retrieval currently tends to be **missing from generation calls**, leading to generic content.
- Retrieval implementation is not pgvector-backed (no efficient similarity query path in use yet).

### Voice similarity (current state)
- The code defines a **VoiceProfile** schema with a similarity threshold (0.88), but the agent loop uses a **LLM-judged “score”** (self-report) rather than a measured metric.
- No calibration dataset exists, so the 0.88 KPI is not grounded.

### Fact checking (current state)
- Fact checker is also LLM-driven and does not enforce claim-to-source mapping or citations.
- Without retrieval + citations, “fact checking” becomes a vibe check rather than verifiable.

### Orchestration + durability (current state)
- Subgraphs implement bounded conversations (good).
- Outer workflow checkpointing is currently in-memory, which conflicts with “pause for hours/days” and “recovery after restart.”

### Model routing + cost math (current state)
- Models are inconsistent across API vs agents.
- Cost accounting is approximate and not enforced against budgets.

### Safety (mental health domain)
- Missing explicit safety policy enforcement (e.g., avoid medical advice, crisis escalation guidance).
- Logging currently captures raw content; for sensitive notes this needs a retention/redaction plan.

---

## Consolidated Risk Register

| Risk | Severity | Likelihood | Notes |
|------|----------|------------|------|
| Schema drift blocks ingestion/RAG/task state | Critical | High | Must be fixed before real “10-page” run |
| Ungrounded generation produces generic/hallucinated output | Critical | High | RAG must feed drafting/checking |
| Voice KPI not measurable | High | High | Need deterministic metric + calibration |
| Fact checking not verifiable | High | High | Need citations + claim-to-source pipeline |
| Durability not real | High | Medium | Need persistent checkpointing |
| Sensitive data in logs | High | Medium | Need redaction/retention controls |

---

## Fix Order (short)

1. **Schema alignment** (migrations ↔ ORM ↔ services)  
2. **Ingestion pipeline** (extract → chunk → embed → persist)  
3. **RAG retrieval** (pgvector similarity + citations metadata)  
4. **Generation grounding** (drafter + checker consume retrieval; no empty contexts)  
5. **Voice metric** (deterministic + calibrated; LLM rewrite driven by score)  
6. **Fact/citations contract** (claim-to-source mapping; “unknown” over invention)  
7. **Safety layer** (mental-health constraints + logging redaction)  
8. **Eval harness** (golden runs + CI checks for grounding/non-generic output)




