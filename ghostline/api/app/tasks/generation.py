"""
Celery tasks for AI-powered book generation.

These tasks handle the async execution of AI generation workflows.
They are triggered by API endpoints and run in background workers.
"""

from celery import shared_task
from datetime import datetime
from uuid import UUID
import traceback
import os

from app.core.celery_app import celery_app
from app.db.base import SessionLocal
from app.models.generation_task import GenerationTask, TaskStatus, TaskType
from app.models.project import Project
from app.services.workflow_service import WorkflowService


def get_db_session():
    """Get a database session for task execution."""
    return SessionLocal()


@celery_app.task(bind=True, name="app.tasks.generate_book")
def generate_book_task(self, task_id: str):
    """
    Generate a complete book from source materials.
    
    This is the main orchestration task that coordinates:
    1. Outline generation
    2. Chapter-by-chapter drafting
    3. Voice/style consistency
    4. Quality checks
    
    Uses LangGraph BookGenerationWorkflow for durable execution
    with pause/resume capabilities.
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # Update status to running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = "Starting book generation workflow..."
        db.commit()
        
        # Get the project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Set up cost tracking context
        try:
            from agents.base.agent import set_cost_context
            set_cost_context(
                project_id=project.id,
                task_id=task.id,
                workflow_run_id=f"book_{task_id}",
                db_session=db,
            )
        except ImportError:
            pass  # Cost tracking optional
        
        # Initialize workflow service and start generation
        workflow_service = WorkflowService(db)
        result = workflow_service.start_book_generation(task=task, project=project)
        
        # Note: The task may be in PAUSED status if waiting for user approval
        # The status is updated by the workflow_service
        
        return {
            "status": task.status.value,
            "task_id": task_id,
            "workflow_id": result.get("workflow_id"),
            "progress": task.progress,
            "current_step": task.current_step,
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        try:
            from agents.base.agent import clear_cost_context
            clear_cost_context()
        except ImportError:
            pass
        db.close()


@celery_app.task(bind=True, name="app.tasks.generate_outline")
def generate_outline_task(self, task_id: str):
    """
    Generate a book outline from source materials.
    
    Uses the OutlineSubgraph with bounded Planner ↔ Critic conversation
    to create a structured outline for user approval.
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        # Update status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = "Analyzing source materials..."
        task.progress = 10
        db.commit()
        
        # Get the project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Set up cost tracking context
        try:
            from agents.base.agent import set_cost_context
            set_cost_context(
                project_id=project.id,
                task_id=task.id,
                workflow_run_id=f"outline_{task_id}",
                db_session=db,
            )
        except ImportError:
            pass  # Cost tracking optional
        
        # Initialize workflow service and generate outline
        workflow_service = WorkflowService(db)
        result = workflow_service.generate_outline(task=task, project=project)
        
        return {
            "status": "completed",
            "task_id": task_id,
            "outline": result.get("outline"),
            "iterations": result.get("iterations", 0),
            "tokens_used": result.get("tokens_used", 0),
            "cost": result.get("cost", 0.0),
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        try:
            from agents.base.agent import clear_cost_context
            clear_cost_context()
        except ImportError:
            pass
        db.close()


@celery_app.task(bind=True, name="app.tasks.generate_chapter")
def generate_chapter_task(self, task_id: str, chapter_number: int, chapter_outline: dict = None):
    """
    Generate a single chapter based on outline and source materials.
    
    Uses the ChapterSubgraph with bounded Drafter ↔ Voice ↔ FactCheck
    conversation to create high-quality chapter content.
    """
    db = get_db_session()
    conv_logger = None
    _conv_session_id = None
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = f"Drafting chapter {chapter_number}..."
        db.commit()
        
        # Get the project
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Set up cost tracking context for this task
        try:
            from agents.base.agent import set_cost_context
            set_cost_context(
                project_id=project.id,
                task_id=task.id,
                workflow_run_id=f"chapter_{task_id}_ch{chapter_number}",
                chapter_number=chapter_number,
                db_session=db,
            )
        except ImportError:
            pass  # Cost tracking optional

        # Start a dedicated conversation log session for this chapter task so the
        # full agentic trace can be dumped to disk and retrieved later via
        # `/tasks/{task_id}/conversation-logs`.
        try:
            from agents.core import get_conversation_logger

            conv_logger = get_conversation_logger()
            _conv_session_id = f"chapter_task_{task_id}_ch{chapter_number}"
            conv_logger.start_session("chapter_generation", _conv_session_id)
            conv_logger.log_system(
                agent_name="Orchestrator",
                message=(
                    "Starting chapter generation: "
                    f"task_id={task_id}, project_id={project.id}, chapter={chapter_number}"
                ),
            )
        except Exception:
            # Logging must never block generation.
            conv_logger = None
            _conv_session_id = None
        
        # If no chapter_outline provided, try to get from project's existing outline
        if not chapter_outline:
            # Look for an existing outline in a previous task
            outline_task = db.query(GenerationTask).filter(
                GenerationTask.project_id == project.id,
                GenerationTask.task_type == TaskType.OUTLINE_GENERATION,
                GenerationTask.status == TaskStatus.COMPLETED,
            ).order_by(GenerationTask.created_at.desc()).first()
            
            if outline_task and outline_task.output_data:
                outline = outline_task.output_data.get("outline", {})
                chapters = outline.get("chapters", [])
                if chapters and chapter_number <= len(chapters):
                    chapter_outline = chapters[chapter_number - 1]
        
        if not chapter_outline:
            chapter_outline = {
                "number": chapter_number,
                "title": f"Chapter {chapter_number}",
                "summary": "Auto-generated chapter",
            }
        
        # Retrieve grounded source chunks for this chapter (RAG)
        source_chunks: list[str] = []
        source_chunks_with_citations: list[dict] = []
        strict_mode = str(os.getenv("GHOSTLINE_STRICT_MODE", "")).strip().lower() in ("1", "true", "yes", "on")
        try:
            from app.services.rag import RAGService
            
            rag = RAGService()
            query_parts = [
                project.title or "",
                project.description or "",
                chapter_outline.get("title", ""),
                chapter_outline.get("summary", ""),
                " ".join(chapter_outline.get("key_points", []) or []),
            ]
            query = " ".join(p for p in query_parts if p).strip()
            if query:
                rag_result = rag.retrieve(
                    query=query,
                    project_id=project.id,
                    db=db,
                    top_k=20,
                    similarity_threshold=0.2,
                )
                for chunk in (rag_result.chunks or []):
                    source_chunks.append(chunk.to_context_block(include_citation=True))

                    citation_str = None
                    try:
                        if chunk.citation and getattr(chunk.citation, "source_filename", None):
                            citation_str = chunk.citation.source_filename
                        elif chunk.citation and getattr(chunk.citation, "source_reference", None):
                            citation_str = chunk.citation.source_reference
                        elif chunk.citation:
                            citation_str = chunk.citation.to_citation_string()
                    except Exception:
                        citation_str = None

                    source_chunks_with_citations.append(
                        {
                            "content": chunk.content,
                            "citation": citation_str or f"Source chunk {len(source_chunks_with_citations) + 1}",
                        }
                    )
        except Exception:
            if strict_mode:
                raise
            # If retrieval fails, fall back to empty chunks; the agent will handle it
            source_chunks = []
            source_chunks_with_citations = []
        
        # Initialize workflow service and generate chapter
        workflow_service = WorkflowService(db)
        result = workflow_service.generate_chapter(
            task=task,
            project=project,
            chapter_number=chapter_number,
            chapter_outline=chapter_outline,
            source_chunks=source_chunks,
            source_chunks_with_citations=source_chunks_with_citations,
        )

        # Persist the conversation log to disk and record its location on the task.
        try:
            if conv_logger:
                conv_logger.log_system(
                    agent_name="Orchestrator",
                    message=f"Chapter {chapter_number} generation complete; dumping conversation log",
                )
                session = conv_logger.end_session(status="completed")
                log_path = conv_logger.dump_to_file(session=session)
                # IMPORTANT: `output_data` is a JSON column; in-place mutation may not
                # be detected depending on SQLAlchemy config. Assign a new dict to
                # ensure the change is persisted.
                existing_output = task.output_data or {}
                task.output_data = {
                    **dict(existing_output),
                    "conversation_log": str(log_path.resolve()),
                    "conversation_session_id": _conv_session_id,
                }
                db.commit()
        except Exception:
            # Don't fail generation if logging fails.
            try:
                db.rollback()
            except Exception:
                pass
        
        return {
            "status": "completed",
            "task_id": task_id,
            "chapter": chapter_number,
            "word_count": result.get("word_count", 0),
            "voice_score": result.get("voice_score", 0.0),
            "fact_score": result.get("fact_score", 0.0),
            "cohesion_score": result.get("cohesion_score", 0.0),
        }
        
    except Exception as e:
        if task:
            # If any earlier DB operation failed, the session may be in a failed
            # transaction state. Roll back so we can persist the failure details.
            try:
                db.rollback()
            except Exception:
                pass
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            # Try to end/dump conversation log for debugging.
            try:
                if conv_logger:
                    conv_logger.log_system(
                        agent_name="Orchestrator",
                        message=f"ERROR during chapter generation: {str(e)}",
                    )
                    session = conv_logger.end_session(status="failed", error=str(e))
                    log_path = conv_logger.dump_to_file(session=session)
                    existing_output = task.output_data or {}
                    task.output_data = {
                        **dict(existing_output),
                        "conversation_log": str(log_path.resolve()),
                        "conversation_session_id": _conv_session_id,
                    }
            except Exception:
                pass
            try:
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
        raise
    finally:
        # Clear cost tracking context
        try:
            from agents.base.agent import clear_cost_context
            clear_cost_context()
        except ImportError:
            pass
        db.close()


@celery_app.task(bind=True, name="app.tasks.analyze_voice")
def analyze_voice_task(self, task_id: str):
    """
    Analyze source materials to create a voice profile.
    
    Uses OpenAI embeddings + stylometry to:
    1. Generate embeddings from writing samples (1536 dims)
    2. Extract stylometric features for numeric voice matching
    3. Create a VoiceProfile for the project
    """
    db = get_db_session()
    task = None
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.current_step = "Analyzing writing style..."
        db.commit()
        
        # Get project and source materials
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project:
            task.status = TaskStatus.FAILED
            task.error_message = "Project not found"
            db.commit()
            return {"error": "Project not found"}
        
        # Import services
        from app.services.embeddings import get_embedding_service
        from app.services.voice_metrics import VoiceMetricsService
        from app.models.source_material import SourceMaterial
        from app.models.voice_profile import VoiceProfile
        
        embedding_service = get_embedding_service()
        voice_metrics = VoiceMetricsService(embedding_service=embedding_service)
        
        # Get writing samples
        source_materials = db.query(SourceMaterial).filter(
            SourceMaterial.project_id == project.id
        ).all()
        
        task.progress = 20
        task.current_step = "Extracting text from samples..."
        db.commit()
        
        # Collect text from source materials
        all_text = []
        for sm in source_materials:
            # Use extracted_text or extracted_content
            text = sm.extracted_text or sm.extracted_content
            if text:
                all_text.append(text[:10000])  # First 10k chars per source
            elif sm.local_path:
                # Try to read from local file
                import os
                if os.path.exists(sm.local_path):
                    try:
                        with open(sm.local_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()[:10000]
                            all_text.append(content)
                    except Exception:
                        pass
        
        task.progress = 40
        task.current_step = "Extracting stylometry features..."
        db.commit()
        
        # Combine all text for analysis
        combined_text = "\n\n".join(all_text)
        
        if not combined_text:
            task.status = TaskStatus.FAILED
            task.error_message = "No text content found in source materials"
            db.commit()
            return {"error": "No text content"}
        
        # Extract stylometry features
        stylometry_features = voice_metrics.extract_features(combined_text)

        # Build a compact style description + phrase lists (deterministic)
        def _style_description_from_features() -> str:
            avg = float(stylometry_features.avg_sentence_length or 0.0)
            vocab = float(stylometry_features.vocabulary_complexity or 0.0)
            punct = float(stylometry_features.punctuation_density or 0.0)
            length_desc = "short" if avg < 15 else "medium" if avg < 25 else "long"
            vocab_desc = "simple" if vocab < 0.4 else "moderate" if vocab < 0.6 else "rich"
            return (
                f"Writing style with {length_desc} sentences ({avg:.1f} words avg), "
                f"{vocab_desc} vocabulary diversity ({vocab:.2f}), "
                f"and punctuation density {punct:.1f} per 100 words."
            )

        def _extract_phrase_lists(texts: list[str]) -> tuple[list[str], list[str], list[str]]:
            import re
            from collections import Counter

            combined = "\n\n".join(t for t in texts if t).strip()
            if not combined:
                return [], [], []

            word_pat = re.compile(r"\b\w+\b")

            # Sentence starters
            sentence_split = re.split(r"(?<=[.!?])\s+", combined)
            starters: Counter[str] = Counter()
            for s in sentence_split:
                w = word_pat.findall(s.lower())
                if len(w) >= 2:
                    starters[" ".join(w[:2])] += 1
                elif len(w) == 1:
                    starters[w[0]] += 1
            sentence_starters = [p for p, c in starters.most_common(20) if c >= 2][:10]

            # Common phrases (bigrams/trigrams)
            stop = {
                "the", "a", "an", "and", "or", "but", "if", "then", "to", "of", "in", "on", "for", "with",
                "is", "are", "was", "were", "be", "been", "it", "that", "this", "i", "you", "we", "they",
            }
            words = [w for w in word_pat.findall(combined.lower()) if w]
            bigrams = Counter()
            trigrams = Counter()
            for i in range(len(words) - 1):
                w1, w2 = words[i], words[i + 1]
                if w1 in stop and w2 in stop:
                    continue
                bigrams[f"{w1} {w2}"] += 1
            for i in range(len(words) - 2):
                w1, w2, w3 = words[i], words[i + 1], words[i + 2]
                if w1 in stop and w2 in stop and w3 in stop:
                    continue
                trigrams[f"{w1} {w2} {w3}"] += 1
            common_phrases = [p for p, c in (trigrams + bigrams).most_common(30) if c >= 2][:10]

            # Transition words (hand-curated set, counted in samples)
            transitions = [
                "but", "and", "so", "because", "however", "still", "yet", "instead",
                "also", "especially", "for example", "for instance", "in other words",
                "in practice", "at the same time", "on the other hand", "in the end",
            ]
            lower = combined.lower()
            trans_counts: Counter[str] = Counter()
            for t in transitions:
                trans_counts[t] = lower.count(t)
            transition_words = [t for t, c in trans_counts.most_common(20) if c > 0][:12]

            return common_phrases, sentence_starters, transition_words

        style_description = _style_description_from_features()
        common_phrases, sentence_starters, transition_words = _extract_phrase_lists(all_text)
        
        task.progress = 60
        task.current_step = "Generating voice embedding..."
        db.commit()
        
        # Generate embedding for voice (using OpenAI text-embedding-3-small)
        embedding_result = embedding_service.embed_text(combined_text[:8000])  # OpenAI limit
        
        task.progress = 80
        task.current_step = "Creating voice profile..."
        db.commit()
        
        # Create or update voice profile in database
        existing_profile = db.query(VoiceProfile).filter(
            VoiceProfile.project_id == project.id
        ).first()
        
        profile_data = {
            "voice_embedding": embedding_result.embedding,
            "avg_sentence_length": stylometry_features.avg_sentence_length,
            "sentence_length_std": stylometry_features.sentence_length_std,
            "avg_word_length": stylometry_features.avg_word_length,
            "vocabulary_complexity": stylometry_features.vocabulary_complexity,
            "vocabulary_richness": stylometry_features.vocabulary_richness,
            "punctuation_density": stylometry_features.punctuation_density,
            "question_ratio": stylometry_features.question_ratio,
            "exclamation_ratio": stylometry_features.exclamation_ratio,
            "avg_paragraph_length": stylometry_features.avg_paragraph_length,
            "style_description": style_description,
            "sample_text": combined_text[:2000],
            "common_phrases": common_phrases,
            "sentence_starters": sentence_starters,
            "transition_words": transition_words,
            "stylistic_elements": {
                "stylometry": {
                    "avg_sentence_length": stylometry_features.avg_sentence_length,
                    "sentence_length_std": stylometry_features.sentence_length_std,
                    "avg_word_length": stylometry_features.avg_word_length,
                    "vocabulary_complexity": stylometry_features.vocabulary_complexity,
                    "vocabulary_richness": stylometry_features.vocabulary_richness,
                    "punctuation_density": stylometry_features.punctuation_density,
                    "question_ratio": stylometry_features.question_ratio,
                    "exclamation_ratio": stylometry_features.exclamation_ratio,
                    "comma_density": stylometry_features.comma_density,
                    "semicolon_density": stylometry_features.semicolon_density,
                    "avg_paragraph_length": stylometry_features.avg_paragraph_length,
                    "paragraph_count": stylometry_features.paragraph_count,
                    "sentence_count": stylometry_features.sentence_count,
                    "total_words": stylometry_features.total_words,
                    "total_characters": stylometry_features.total_characters,
                }
            },
            "similarity_threshold": 0.85,
            "embedding_weight": 0.4,
            "is_active": True,
        }
        
        if existing_profile:
            for key, value in profile_data.items():
                setattr(existing_profile, key, value)
            profile = existing_profile
        else:
            profile = VoiceProfile(
                project_id=project.id,
                name=f"{project.title} Voice Profile",
                **profile_data,
            )
            db.add(profile)
        
        db.commit()
        db.refresh(profile)
        
        # Prepare output data
        voice_profile_output = {
            "profile_id": str(profile.id),
            "embedding_dimensions": len(embedding_result.embedding),
            "embedding_provider": str(embedding_result.provider),
            "sample_count": len(all_text),
            "total_words": stylometry_features.total_words,
            "stylometry": {
                "avg_sentence_length": stylometry_features.avg_sentence_length,
                "vocabulary_complexity": stylometry_features.vocabulary_complexity,
                "punctuation_density": stylometry_features.punctuation_density,
            },
            "threshold": 0.85,
        }
        
        task.output_data = task.output_data or {}
        task.output_data["voice_profile"] = voice_profile_output
        task.output_entity_type = "voice_profile"
        task.output_entity_id = profile.id
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.progress = 100
        task.current_step = "Voice analysis complete"
        db.commit()
        
        return {"status": "completed", "task_id": task_id, "voice_profile": voice_profile_output}
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.resume_workflow")
def resume_workflow_task(self, task_id: str, user_input: dict = None):
    """
    Resume a paused workflow.
    
    Called when user provides input (e.g., outline approval, feedback).
    """
    db = get_db_session()
    try:
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if not task:
            return {"error": "Task not found"}
        
        if task.status != TaskStatus.PAUSED:
            return {"error": f"Task is not paused, current status: {task.status.value}"}
        
        task.current_step = "Resuming workflow..."
        db.commit()
        
        # Initialize workflow service and resume
        workflow_service = WorkflowService(db)
        result = workflow_service.resume_workflow(task=task, user_input=user_input)
        
        return {
            "status": task.status.value,
            "task_id": task_id,
            "progress": task.progress,
            "current_step": task.current_step,
        }
        
    except Exception as e:
        if task:
            task.status = TaskStatus.FAILED
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            db.commit()
        raise
    finally:
        db.close()
