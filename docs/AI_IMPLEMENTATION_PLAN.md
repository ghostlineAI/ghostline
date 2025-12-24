# GhostLine AI Implementation Plan

**Last Updated**: Dec 24, 2025 - Added Ask1-3 review findings (architecture + code reuse + science/ML)

> **Note**: This file contains some **historical** notes from early phases. The current priority is **Phase 7 (below)**: fix schema drift + make the AI scientifically grounded (RAG), measurable (voice/facts), safe (mental-health domain), and durable (pause/resume across restarts).

---

## 2025-12-24 Status Snapshot (Post-Phase 6 + Ask1-3 Reviews)

### What exists (scaffolding / plumbing)
- **Frontend ↔ Backend wiring** exists for generation triggers, polling, outline review UI, content viewing, and conversation-log viewing.
- **Agent orchestration** exists as bounded LangGraph subgraphs (planner/critic; drafter/voice/fact/cohesion) with structured logging.
- **Core AI services exist** (LLM client, document processor, embeddings) — but they are not yet fully integrated into a correct ingest→RAG→draft loop.

### What is not sound yet (blockers)
- **Schema drift**: Alembic migrations ≠ ORM models ≠ services. This blocks reliable ingestion, embedding persistence, retrieval, and task pause/resume.
- **RAG/memory not actually used** in drafting/fact-check today (source chunks are often empty), so outputs will be generic/hallucination-prone.
- **Voice similarity KPI (≥ 0.88) is not implemented as a real metric**. Current “voice score” is LLM-self-reported and uncalibrated.
- **Fact checking is LLM-self-reported** (no claim-to-source enforcement, no citations contract).
- **Durability**: the current LangGraph checkpointer is in-memory (`MemorySaver`), so “pause for hours/days” and “recovery after restart” are not guaranteed.
- **Model routing/cost accounting** is inconsistent across API vs agents (risk of 404 model errors + misleading cost/tokens).

### Immediate objective
Deliver an end-to-end **“10-page mental health book”** run that is:
- Grounded in uploaded sources (RAG + citations)
- Safe for mental-health content
- Measurable (voice/facts signals)
- Durable (pause/resume survives process restarts)

---

## Architecture Decision: LangGraph + Bounded Agent Conversations

Based on analysis, we're using **LangGraph as the backbone** with agent "talk" happening inside **controlled subgraphs**:

### Why LangGraph (not AutoGen as primary)
- ✅ Durable state + persistence for jobs that take minutes/hours
- ✅ Pause/resume for user feedback (hours/days between interactions)
- ✅ Job recovery after worker restarts
- ✅ Structured outputs + audit logs
- ✅ Strict cost/latency controls per step

### Architecture Pattern
```
LangGraph Outer Graph (production state machine):
  Ingest → Embed → OutlineSubgraph → UserApproveOutline → 
  DraftChapterSubgraph → UserEdits → Finalize → Export

Inside OutlineSubgraph / DraftChapterSubgraph:
  - Multi-agent conversation loop (Planner ↔ Critic ↔ Editor)
  - Hard limits: max turns, max tokens, max cost, stop conditions
  - Output: structured artifact {outline, open_questions, rationale, risks}
```

### Where Agents "Talk" (Bounded Subgraphs)
1. **Outline creation**: Planner ↔ Critic ↔ Marketability agent → converge on outline
2. **Chapter revision loop**: Drafter ↔ Style ↔ Continuity → negotiate changes
3. **Conflict resolution**: Timeline agent flags → Drafter proposes fixes → Orchestrator chooses
4. **Idea generation (fiction)**: Worldbuilding ↔ Character-arc ↔ Plot-beats

---

## E2E Test Results Summary

> **Historical note**: the following “confirmed gaps” reflect early test runs before Phases 0–6 were implemented. Current blockers are tracked in **Phase 7**.

```
================================================================================
CONFIRMED GAPS (verified by automated tests)
================================================================================
  📍 GenerationService is EMPTY (gap)
  📍 ProcessingService is EMPTY (gap)
  📍 Generation endpoint MISSING (gap)
  📍 Outline generation endpoint MISSING (gap)
  📍 Task routes defined but tasks MISSING (gap)
  📍 No LLM client service exists (gap)
  📍 No embedding service exists (gap)
  📍 No document processor exists (gap)
  📍 Agent base/ is EMPTY (gap)
  📍 Agent specialized/ is EMPTY (gap)
```

---

## Gap Analysis: AI_plan.txt vs Current Implementation

### What Exists (Infrastructure Layer) ✅ VERIFIED BY TESTS

| Component | Status | Location | Test |
|-----------|--------|----------|------|
| **Database Models (15 tables)** | ✅ Complete | `ghostline/api/app/models/` | `test_models_load` |
| - VoiceProfile (with 1536-dim embedding) | ✅ | `voice_profile.py` | `test_voice_profile_embedding` |
| - ContentChunk (with embedding) | ✅ | `content_chunk.py` | `test_content_chunk_embedding` |
| - GenerationTask (task tracking) | ✅ | `generation_task.py` | `test_generation_task_model` |
| - Chapter, BookOutline, ChapterRevision | ✅ | respective files | included in model test |
| **pgvector Extension** | ✅ Configured | Alembic migration | `test_api_pgvector` |
| **Celery for Async Tasks** | ✅ Configured | `celery_app.py` | `test_celery_config` |
| **File Storage (local mode)** | ✅ Working | `services/storage.py` | `test_storage_service` |
| **Auth Service** | ✅ Working | `services/auth.py` | `test_auth_service` |
| **API Endpoints (projects, auth, files)** | ✅ Working | `api/v1/endpoints/` | multiple tests |
| **Frontend Generation UI** | ✅ Shell exists | `generation-wizard.tsx` | manual inspection |
| **Dependencies (agents pyproject)** | ✅ | LangGraph, sentence-transformers, unstructured | 3 tests |

### What's Missing (The "Science") ❌ VERIFIED BY TESTS

| Component | Status | Required By | Test |
|-----------|--------|-------------|------|
| **LLM Integration** | ❌ Empty | All agents | `test_no_llm_client` |
| **Document Processing** | ❌ Not implemented | Source material ingestion | `test_no_doc_processor` |
| **Embedding Generation** | ❌ Not implemented | Voice analysis, RAG | `test_no_embedding_service` |
| **GenerationService** | ❌ `class GenerationService: pass` | API | `test_generation_service_empty` |
| **ProcessingService** | ❌ `class ProcessingService: pass` | API | `test_processing_service_empty` |
| **Generation Endpoint** | ❌ Frontend calls non-existent endpoint | Frontend | `test_generation_endpoint_missing` |
| **Outline Generation** | ❌ No POST to outline | Frontend | `test_outline_generation_missing` |
| **Celery Tasks** | ❌ Routes defined, tasks don't exist | Background jobs | `test_celery_tasks_missing` |
| **Agent base class** | ❌ Empty folder | All agents | `test_agents_base_empty` |
| **Specialized agents** | ❌ Empty folder | Core workflow | `test_agents_specialized_empty` |

---

## Implementation Roadmap

---

## Phase 7 (Current Priority): Schema + Science/ML Hardening

### 7.0 Schema alignment (blocking)
**Goal**: Make DB schema, ORM models, and services agree so ingestion + retrieval + task state are real.

- Align `content_chunks` migration with `ContentChunk` ORM (token_count, embedding_model, position fields, etc.).
- Align `generation_tasks.status` enum to include `QUEUED` + `PAUSED` (and any other states used in code).
- Align `source_materials` fields used by processing services (extracted_text, processing_status, file path/key fields).
- Add a repeatable local reset/migrate flow (drop/recreate + `alembic upgrade head`) for deterministic dev/test runs.

### 7.1 Embeddings strategy (make it mathematically coherent)
**Goal**: One clear embedding story for RAG + any similarity metrics.

- Decide the canonical embedding dimension + model:
  - **Option A (local-first)**: use a sentence-transformers model (e.g. 768/1024 dims) and set DB vector dims to match.
  - **Option B (API-first)**: use OpenAI embeddings (e.g. 1536 dims) consistently and accept external dependency.
- Remove padding/truncation hacks; enforce dimension checks at runtime.
- Persist `embedding_model` per chunk/profile and version it.

### 7.2 Memory/RAG that actually feeds generation (no more generic output)
**Goal**: Drafting and checking must be grounded in retrieved chunks.

- Implement pgvector-backed similarity search (SQL, not Python O(N) scans).
- Store chunk metadata needed for citations: file_id, filename, page range, char offsets, extraction method.
- Add a “retrieval budget” contract per step (max chunks, max tokens, diversity across sources).
- Require citations in outline/chapter outputs (chunk IDs / filenames + page numbers when available).

### 7.3 Voice fidelity: define + measure + enforce
**Goal**: Voice is measurable (not LLM-self-scored) and used to drive revisions.

- Define a VoiceProfile that includes:
  - Stylometric features (sentence length distribution, punctuation, function word frequencies, readability)
  - Optional embeddings (for semantic consistency, not as the sole “voice” metric)
- Calibrate the ≥0.88 threshold (or revise KPI for MVP) using a small evaluation set.
- Make VoiceEditor compute a deterministic score + only use LLM for rewriting.

### 7.4 Fact checking: claim-to-source enforcement
**Goal**: “Fact check” produces verifiable artifacts, not vibes.

- Extract claims → retrieve evidence → mark each claim as supported/unsupported/uncertain.
- Require at least one citation per non-trivial claim, or flag for user review.
- Add a “no invention” mode for sensitive domains (mental health): prefer “unknown” over hallucination.

### 7.5 Safety layer (mental-health domain)
**Goal**: Generate a helpful book without unsafe medical/clinical advice.

- Implement SafetyAgent pass: detect self-harm, crisis language, medical claims.
- Enforce policy: educational tone, disclaimers, crisis resources, “consult a professional” guidance.
- Add redaction controls for conversation logs (avoid storing raw sensitive text where possible).

### 7.6 Evaluation harness (science guardrails)
**Goal**: We can tell if outputs are grounded, non-generic, and improving over time.

- Add offline eval scripts + CI checks:
  - Grounding: % of paragraphs with citations; % claims supported
  - Non-generic: presence of unique entities/phrases from sources; avoid boilerplate templates
  - Voice: stylometry score movement pre/post edit
- Add “golden run” tests using the mental-health sample set (local + live key mode).

### Phase 1: Core AI Foundation (Week 1)
**Goal**: Build the primitives that all agents will use

#### 1.1 LLM Client Service
Create a unified interface for calling LLMs (Claude, GPT-4, local models).

```
ghostline/api/app/services/llm.py
├── LLMClient (abstract base)
├── ClaudeClient (Anthropic API)
├── OpenAIClient (OpenAI API)
└── LocalLLMClient (for testing without API costs)
```

**Key Features**:
- Streaming support for real-time generation
- Token counting and cost estimation
- Retry logic with exponential backoff
- Model routing (cheap models for simple tasks, expensive for quality-critical)

**Dependencies to add**:
```
anthropic>=0.40.0
openai>=1.50.0
tiktoken>=0.7.0
```

#### 1.2 Embedding Service
Generate and store embeddings for voice analysis and RAG.

```
ghostline/api/app/services/embeddings.py
├── EmbeddingService
│   ├── generate_embedding(text) -> list[float]
│   ├── batch_embed(texts) -> list[list[float]]
│   └── similarity(embedding1, embedding2) -> float
```

**Uses**: `sentence-transformers` (as specified in ADR-0001)
- Model: `all-MiniLM-L6-v2` for speed, or `all-mpnet-base-v2` for accuracy
- Fallback: OpenAI `text-embedding-ada-002`

**Dependencies to add**:
```
sentence-transformers>=3.0.0
```

#### 1.3 Document Processing Service
Extract text from various file formats.

```
ghostline/api/app/services/document_processor.py
├── DocumentProcessor
│   ├── process(file_path, file_type) -> ExtractedContent
│   ├── chunk_text(text, chunk_size=1000) -> list[Chunk]
│   └── extract_metadata(file_path) -> dict
```

**Uses**: `unstructured` (as specified in ADR-0001)
- Supports: PDF, DOCX, TXT, Markdown, Audio transcripts
- Outputs: Clean text with structural metadata

**Dependencies to add**:
```
unstructured>=0.15.0
unstructured[pdf]>=0.15.0
python-docx>=1.1.0
```

---

### Phase 2: Memory System (Week 2)
**Goal**: Enable agents to retrieve relevant context and maintain consistency

#### 2.1 Vector Store Service
Query the pgvector database for semantic search.

```
ghostline/api/app/services/vector_store.py
├── VectorStore
│   ├── index_chunk(chunk: ContentChunk) -> None
│   ├── search(query: str, project_id: UUID, top_k=5) -> list[ContentChunk]
│   ├── search_by_embedding(embedding, top_k=5) -> list[ContentChunk]
│   └── delete_by_source_material(source_id) -> None
```

**Implementation**:
- Uses SQLAlchemy with pgvector for similarity queries
- Cosine similarity: `embedding <=> query_embedding`
- Indexed with `vector_cosine_ops`

#### 2.2 Memory Service (Running Summaries)
Track what's happened in the book so far.

```
ghostline/api/app/services/memory.py
├── MemoryService
│   ├── get_book_context(project_id) -> BookContext
│   ├── get_chapter_summary(chapter_id) -> str
│   ├── update_chapter_summary(chapter_id, summary) -> None
│   └── get_character_facts(project_id, character_name) -> list[str]
```

**BookContext includes**:
- Current outline
- Summaries of all previous chapters
- Key entities/characters mentioned
- Timeline of events (if applicable)

#### 2.3 Story Graph (Optional - Advanced)
Structured representation of narrative elements.

```
ghostline/api/app/services/story_graph.py
├── StoryGraph
│   ├── add_event(event: NarrativeEvent) -> None
│   ├── get_timeline() -> list[NarrativeEvent]
│   ├── check_consistency(new_event) -> list[Conflict]
│   └── get_related_events(entity) -> list[NarrativeEvent]
```

**Note**: This is advanced functionality. Start without it and add later.

---

### Phase 3: Base Agent Framework (Week 3)
**Goal**: Create reusable agent patterns

#### 3.1 Agent Base Class

```
ghostline/agents/agents/base/agent.py
├── BaseAgent (ABC)
│   ├── name: str
│   ├── description: str
│   ├── llm_client: LLMClient
│   ├── execute(input: AgentInput) -> AgentOutput
│   ├── build_prompt(context) -> str
│   └── parse_response(response) -> AgentOutput
```

**Features**:
- Standardized input/output schemas
- Automatic token tracking
- Logging and observability hooks
- Error handling

#### 3.2 Orchestrator

```
ghostline/agents/orchestrator/workflow.py
├── BookGenerationWorkflow
│   ├── state: WorkflowState
│   ├── run_outline_phase() -> Outline
│   ├── run_chapter_phase(chapter_num) -> Chapter
│   ├── request_user_feedback(question) -> None
│   └── compile_book() -> Book
```

**Pattern**: Sequential with checkpoints
1. Analyze source materials
2. Generate outline → User approval checkpoint
3. For each chapter:
   - Draft → Stylize → Fact-check → Cohesion check
   - User approval checkpoint
4. Final compilation

**Option**: Use LangGraph for state machine, OR simpler Python async workflows first.

#### 3.3 Prompt Templates

```
ghostline/agents/prompts/
├── outline_planner.py
├── content_drafter.py
├── stylistic_editor.py
├── fact_checker.py
└── cohesion_analyst.py
```

Each contains structured prompts with:
- System prompt (agent role)
- Context injection points
- Output format specification
- Examples (few-shot)

---

### Phase 4: Specialized Agents (Week 4-5)
**Goal**: Implement the "writer's room" agents from the plan

#### 4.1 Outline Planner Agent
```python
class OutlinePlannerAgent(BaseAgent):
    """Creates book structure from source materials."""
    
    def execute(self, project_id: UUID) -> BookOutline:
        # 1. Retrieve all source material summaries
        # 2. Analyze themes, chronology, key points
        # 3. Generate hierarchical outline
        # 4. Return structured outline for user approval
```

#### 4.2 Content Drafter Agent
```python
class ContentDrafterAgent(BaseAgent):
    """Writes chapter prose based on outline and sources."""
    
    def execute(self, chapter_outline: ChapterOutline, context: BookContext) -> str:
        # 1. Retrieve relevant chunks via vector search
        # 2. Include previous chapter summaries
        # 3. Generate chapter content matching target length
        # 4. Track word count and key facts introduced
```

#### 4.3 Voice/Stylistic Editor Agent
```python
class VoiceAgent(BaseAgent):
    """Ensures output matches author's writing style."""
    
    def execute(self, draft: str, voice_profile: VoiceProfile) -> str:
        # 1. Compare draft embedding to voice profile embedding
        # 2. If similarity < 0.88, rewrite to match style
        # 3. Preserve factual content while adjusting voice
        # 4. Return similarity score + revised text
```

#### 4.4 Fact Checker Agent
```python
class FactCheckerAgent(BaseAgent):
    """Validates consistency with source materials."""
    
    def execute(self, chapter: str, project_id: UUID) -> FactCheckResult:
        # 1. Extract factual claims from chapter
        # 2. Search source materials for each claim
        # 3. Flag unsupported or contradictory claims
        # 4. Return list of issues + suggested corrections
```

#### 4.5 Cohesion Analyst Agent
```python
class CohesionAgent(BaseAgent):
    """Reviews for narrative flow and engagement."""
    
    def execute(self, chapter: str, outline: BookOutline, prev_chapters: list) -> CohesionResult:
        # 1. Check chapter covers outline beats
        # 2. Verify transitions from previous chapter
        # 3. Analyze pacing and engagement
        # 4. Suggest improvements
```

---

### Phase 5: Workflow Integration (Week 6)
**Goal**: Wire agents to API and frontend

#### 5.1 Generation Endpoints
```
POST /api/v1/projects/{id}/analyze      # Start source material analysis
POST /api/v1/projects/{id}/outline      # Generate book outline
POST /api/v1/projects/{id}/generate     # Start chapter generation
GET  /api/v1/projects/{id}/tasks        # Get generation task status
POST /api/v1/projects/{id}/feedback     # Submit user feedback
```

#### 5.2 Celery Task Definitions
```
ghostline/api/app/tasks/generation.py
├── analyze_source_materials_task
├── generate_outline_task
├── generate_chapter_task
├── run_quality_checks_task
└── compile_book_task
```

#### 5.3 Progress Tracking
- Update `GenerationTask` records in real-time
- WebSocket or polling for frontend updates
- Emit events: `task_started`, `task_progress`, `task_completed`, `feedback_needed`

---

### Phase 6: User Feedback Loop (Week 7)
**Goal**: Enable iterative collaboration

#### 6.1 Feedback System
```
ghostline/api/app/services/feedback.py
├── FeedbackService
│   ├── request_clarification(question, context) -> FeedbackRequest
│   ├── await_response(request_id) -> FeedbackResponse
│   └── apply_feedback(response, workflow_state) -> None
```

**Feedback Types**:
- `APPROVAL` - User approves outline/chapter
- `REVISION` - User requests changes
- `CLARIFICATION` - User answers AI's question
- `REJECTION` - User wants complete rewrite

#### 6.2 Question Generation
AI generates clarifying questions when:
- Source materials are ambiguous
- Timeline/facts are unclear
- User intent for a section is uncertain
- Conflicting information found

---

## Recommended Starting Point

Given that the local dev environment is now working, I recommend this order:

### Immediate Next Steps (This Session)

1. **Add AI dependencies to `pyproject.toml`**
   - anthropic, openai, sentence-transformers, unstructured

2. **Create LLM Client Service** (`services/llm.py`)
   - Start with OpenAI/Anthropic API wrappers
   - Add mock mode for testing without API keys

3. **Create Embedding Service** (`services/embeddings.py`)
   - Use sentence-transformers locally
   - Wire to ContentChunk model

4. **Create Document Processor** (`services/document_processor.py`)
   - Basic text extraction from uploaded files
   - Chunking with overlap

5. **Create Vector Store Service** (`services/vector_store.py`)
   - pgvector queries
   - Test with sample data

### What Can Be Reused

✅ **Keep and extend**:
- All database models (well-designed)
- GenerationTask tracking system
- Celery infrastructure
- Frontend generation wizard (just needs real API)
- Project/chapter structure

### What Needs Rebuilding

❌ **Replace/implement from scratch**:
- `services/generation.py` (currently empty)
- `services/processing.py` (currently empty)
- All agent implementations (empty folders)
- Orchestrator logic (doesn't exist)

---

## Technology Decisions

Based on AI_plan.txt and ADR-0001, use:

| Component | Technology | Reason |
|-----------|------------|--------|
| Agent Framework | Start simple, consider LangGraph later | LangGraph is powerful but complex; validate concept first |
| Primary LLM | Claude 3.5 Sonnet via Anthropic API | Best quality/cost for long-form writing |
| Secondary LLM | GPT-4o via OpenAI API | Fallback + specific tasks |
| Embeddings | sentence-transformers (local) | Free, fast, good quality |
| Document Processing | unstructured.io | Multi-format support |
| Vector DB | pgvector (already set up) | Already integrated, simple |
| Async Processing | Celery + Redis (already set up) | Already integrated |

---

## Cost Estimates (per book)

Assuming a 50,000-word book (10 chapters):

| Task | Tokens | Model | Cost |
|------|--------|-------|------|
| Source Analysis | ~100k input | Claude Haiku | $0.025 |
| Outline Generation | ~50k in/out | Claude Sonnet | $0.45 |
| Chapter Drafting (10x) | ~500k in/out | Claude Sonnet | $4.50 |
| Voice Editing (10x) | ~300k in/out | Claude Haiku | $0.075 |
| Fact Checking (10x) | ~200k in/out | Claude Haiku | $0.05 |
| **Total** | | | **~$5.10/book** |

This is rough but shows the system is economically viable.

---

---

## Revised Implementation Phases (Based on E2E Tests)

Based on E2E test results, here's the prioritized implementation order:

### Phase 0: Fix Critical Frontend/Backend Mismatch (BLOCKING)
The frontend's `generation-wizard.tsx` calls `POST /projects/{id}/generate` which doesn't exist.

**Files to create/modify:**
1. `ghostline/api/app/api/v1/endpoints/generation.py` - New generation endpoints
2. `ghostline/api/app/api/v1/router.py` - Include generation router
3. `ghostline/api/app/tasks/__init__.py` - Create tasks module
4. `ghostline/api/app/tasks/generation.py` - Define Celery tasks (stub)

### Phase 1: Core AI Services (Foundation)
Build the services that all agents will use.

**Files to create:**
1. `ghostline/api/app/services/llm.py` - LLM client (Anthropic/OpenAI)
2. `ghostline/api/app/services/embeddings.py` - Embedding generation
3. `ghostline/api/app/services/document_processor.py` - Text extraction

**Dependencies to add to `ghostline/api/pyproject.toml`:**
```toml
anthropic = "^0.40.0"
openai = "^1.50.0"
tiktoken = "^0.7.0"
sentence-transformers = "^3.0.0"
unstructured = "^0.15.0"
```

### Phase 2: Implement Empty Services
Fill in the empty service classes.

**Files to modify:**
1. `ghostline/api/app/services/generation.py` - Real implementation
2. `ghostline/api/app/services/processing.py` - Real implementation

**Files to create:**
1. `ghostline/api/app/services/vector_store.py` - pgvector queries

### Phase 3: Agent Framework
Build the agent infrastructure in `ghostline/agents/`.

**Files to create:**
1. `ghostline/agents/agents/base/agent.py` - Abstract base agent
2. `ghostline/agents/agents/base/prompts.py` - Prompt template system
3. `ghostline/agents/orchestrator/workflow.py` - Book generation workflow

### Phase 4: Specialized Agents
Implement the agents from AI_plan.txt.

**Files to create:**
1. `ghostline/agents/agents/specialized/outline_planner.py`
2. `ghostline/agents/agents/specialized/content_drafter.py`
3. `ghostline/agents/agents/specialized/voice_editor.py`
4. `ghostline/agents/agents/specialized/fact_checker.py`
5. `ghostline/agents/agents/specialized/cohesion_analyst.py`

### Phase 5: Celery Tasks (Wire It Together)
Connect agents to async background processing.

**Files to modify:**
1. `ghostline/api/app/tasks/generation.py` - Real task implementations
2. `ghostline/api/app/core/celery_app.py` - Verify task discovery

### Phase 6: User Feedback Loop
Enable iterative collaboration.

**Files to create:**
1. `ghostline/api/app/services/feedback.py` - Feedback management
2. `ghostline/api/app/api/v1/endpoints/feedback.py` - Feedback endpoints

---

## Phase 7: Schema + Science/ML Hardening (COMPLETED)

This phase addresses critical correctness bugs, science/ML assumptions, and grounding requirements.

### 7.1 Schema Reconciliation ✅ COMPLETED
- Created Alembic migration to reconcile ORM models with database
- Fixed `ContentChunk` model (added `project_id`, `source_reference`, `chunk_index`)
- Fixed `VoiceProfile` model (added stylometry fields for numeric metrics)
- Fixed `GenerationTask` status enum (added `PAUSED`, `QUEUED`)
- Added `workflow_state` to `GenerationTask` for LangGraph checkpoints
- Test: `scripts/test_phase7_schema.py` - ALL PASSED

### 7.2 OpenAI Embedding Service ✅ COMPLETED
- Replaced sentence-transformers padding hack with native OpenAI embeddings
- Using `text-embedding-3-small` (1536 dimensions - matches DB schema)
- Added fallback to local sentence-transformers for offline testing
- Test: `scripts/test_phase7_embeddings.py` - ALL PASSED (live OpenAI API)

### 7.3 RAG Service with Citation Tracking ✅ COMPLETED
- Created `RAGService` with pgvector similarity search
- Added `Citation` and `RetrievedChunk` classes for grounding
- Integrated citation markers into context building
- Test: `scripts/test_phase7_services.py` - RAG tests PASSED

### 7.4 Grounded Agent Updates ✅ COMPLETED
- Updated `ContentDrafterAgent` to require source chunks with citations
- Updated `FactCheckerAgent` with claim-to-source mapping
- Added grounding score computation and enforcement
- Agents now include `[citation]` markers in output

### 7.5 Numeric Voice Metrics ✅ COMPLETED
- Created `VoiceMetricsService` with stylometry feature extraction
- Implemented numeric voice similarity (embedding + stylometry combined)
- Features: sentence length, vocabulary complexity, punctuation density, etc.
- Updated `VoiceEditorAgent` to use numeric metrics (not LLM-judged)
- Threshold logic: reject content if similarity < 0.85
- Test: `scripts/test_phase7_services.py` - Voice tests PASSED

### 7.6 Mental Health Safety Service ✅ COMPLETED
- Created `SafetyService` for content validation
- Detects: crisis language, medical advice, diagnosis claims, therapy substitutes
- Suggests appropriate disclaimers for mental health content
- Includes crisis hotline resources
- Test: `scripts/test_phase7_services.py` - Safety tests PASSED

### 7.7 Task and Service Fixes ✅ COMPLETED
- Fixed `analyze_voice_task` to use correct service methods
- Fixed `ProcessingService` to use correct model fields (`voice_embedding`)
- Updated to use OpenAI embeddings + stylometry extraction

### Files Created/Modified in Phase 7:
```
ghostline/api/alembic/versions/phase7_schema_reconciliation.py (NEW)
ghostline/api/app/services/embeddings.py (REWRITTEN)
ghostline/api/app/services/rag.py (NEW)
ghostline/api/app/services/voice_metrics.py (NEW)
ghostline/api/app/services/safety.py (NEW)
ghostline/api/app/services/processing.py (UPDATED)
ghostline/api/app/tasks/generation.py (UPDATED)
ghostline/api/app/models/content_chunk.py (UPDATED)
ghostline/api/app/models/voice_profile.py (UPDATED)
ghostline/api/app/models/source_material.py (UPDATED)
ghostline/api/app/models/generation_task.py (UPDATED)
ghostline/api/app/models/project.py (UPDATED)
ghostline/agents/agents/specialized/content_drafter.py (UPDATED)
ghostline/agents/agents/specialized/fact_checker.py (UPDATED)
ghostline/agents/agents/specialized/voice_editor.py (UPDATED)
ghostline/api/scripts/test_phase7_schema.py (NEW)
ghostline/api/scripts/test_phase7_embeddings.py (NEW)
ghostline/api/scripts/test_phase7_services.py (NEW)
```

---

## Remaining Work (Phase 8+)

### Phase 8.1: PostgresCheckpointer for Durable LangGraph State
- Replace `MemorySaver` with PostgreSQL-backed checkpointer
- Enable true pause/resume across worker restarts

### Phase 8.2: Eval Harness
- Create golden test cases for grounding and voice matching
- Add CI checks for non-generic output
- Test with the mental health PDFs/PNG provided by user

### Phase 8.3: Full E2E Test Suite
- Run complete workflow from upload → outline → approve → generate → export
- Validate conversation logs for debugging

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-23 | OpenAI embeddings (not local sentence-transformers) | Native 1536 dims match DB schema, no padding hack |
| 2025-12-23 | Strict numeric voice metric (not LLM-judged) | Reproducible, calibrated, deterministic |
| 2025-12-23 | Safety service for mental health | Domain-specific risk mitigation |
| 2025-12-23 | Claim-to-source mapping in FactChecker | Grounding enforcement, not just LLM opinion |

