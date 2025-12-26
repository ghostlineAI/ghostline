#!/usr/bin/env python3
"""
Background script to generate a 20-page book with full logging.
Run with: nohup python scripts/run_20page_generation.py > /tmp/book_gen.log 2>&1 &
"""
import os
import sys
import json
import logging
from datetime import datetime
from uuid import UUID

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 70)
    logger.info("🚀 STARTING 20-PAGE BOOK GENERATION")
    logger.info("=" * 70)
    
    # Import after path setup
    from app.db.base import SessionLocal
    from app.models.generation_task import GenerationTask, TaskStatus, TaskType
    from app.models.project import Project
    from app.models.voice_profile import VoiceProfile
    from app.services.workflow_service import WorkflowService
    from sqlalchemy import func
    from app.models.llm_usage_log import LLMUsageLog
    
    db = SessionLocal()
    
    try:
        # Get project
        project = db.query(Project).filter(Project.title == 'Mental Health Guide').first()
        if not project:
            logger.error("Project 'Mental Health Guide' not found!")
            return
        
        logger.info(f"Project: {project.id} - {project.title}")
        
        # Check voice profile
        voice = db.query(VoiceProfile).filter(VoiceProfile.project_id == project.id).first()
        logger.info(f"Voice Profile: {voice.id if voice else 'None'}")
        
        # Cancel any running tasks
        db.query(GenerationTask).filter(
            GenerationTask.project_id == project.id,
            GenerationTask.status.in_(['QUEUED', 'RUNNING', 'PAUSED'])
        ).update({'status': TaskStatus.CANCELLED})
        db.commit()
        
        # Create new task
        task = GenerationTask(
            project_id=project.id,
            task_type=TaskType.CHAPTER_GENERATION,
            status=TaskStatus.RUNNING,
            current_step='Starting 20-page generation',
            progress=0,
            input_data={
                'target_pages': 20,
                'target_chapters': 6,
                'words_per_page': 250,
            },
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task ID: {task.id}")
        logger.info(f"Target: 6 chapters, ~5000 words")
        
        # Start workflow
        logger.info("\n" + "=" * 70)
        logger.info("📝 PHASE 1: OUTLINE GENERATION")
        logger.info("=" * 70)
        
        workflow_service = WorkflowService(db)
        result = workflow_service.start_book_generation(task, project)
        
        # Check if paused for approval
        state = result.get('state', {})
        if state.get('pending_user_action') == 'approve_outline':
            logger.info("Outline generated - auto-approving...")
            outline = state.get('outline', {})
            logger.info(f"Outline: {outline.get('title')}")
            for ch in outline.get('chapters', []):
                logger.info(f"  Ch{ch.get('number')}: {ch.get('title')}")
        
        # Get outline from task
        task = db.query(GenerationTask).filter(GenerationTask.id == task.id).first()
        ws = task.output_data.get('workflow_state', {}) if task.output_data else {}
        outline = ws.get('outline', {})
        chapters_outline = outline.get('chapters', [])
        
        logger.info("\n" + "=" * 70)
        logger.info("📖 PHASE 2: CHAPTER GENERATION")
        logger.info("=" * 70)
        
        chapters_data = []
        
        for i, ch_out in enumerate(chapters_outline, 1):
            logger.info(f"\n--- Chapter {i}/{len(chapters_outline)}: {ch_out.get('title')} ---")
            start_time = datetime.now()
            
            try:
                result = workflow_service.generate_chapter(task, project, i, ch_out)
                
                duration = (datetime.now() - start_time).total_seconds()
                chapter_content = result.get('content', '')
                word_count = len(chapter_content.split())
                
                quality_gates_passed = bool(result.get("quality_gates_passed", False))
                chapters_data.append({
                    'number': i,
                    'title': ch_out.get('title'),
                    'content': chapter_content,
                    'content_clean': result.get("content_clean") or chapter_content,
                    'word_count': word_count,
                    'citations': result.get('citations', []),
                    'citation_report': result.get('citation_report', {}),
                    'voice_score': result.get('voice_score', 0),
                    'fact_score': result.get('fact_score', 0),
                    'cohesion_score': result.get('cohesion_score', 0),
                    'quality_gates_passed': quality_gates_passed,
                    'quality_gate_report': result.get('quality_gate_report', {}),
                    'revision_history': result.get('revision_history', []),
                })
                
                logger.info(f"  ✅ {word_count} words in {duration:.1f}s")
                logger.info(
                    f"     Scores: voice={result.get('voice_score', 0):.2f}, "
                    f"fact={result.get('fact_score', 0):.2f}, "
                    f"quality_ok={quality_gates_passed}"
                )

            except Exception as e:
                logger.error(f"  ❌ Error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                chapters_data.append({
                    'number': i,
                    'title': ch_out.get('title'),
                    'content': "",
                    'content_clean': "",
                    'word_count': 0,
                    'citations': [],
                    'citation_report': {},
                    'voice_score': 0,
                    'fact_score': 0,
                    'cohesion_score': 0,
                    'quality_gates_passed': False,
                    'quality_gate_report': {},
                    'revision_history': [],
                    'error': str(e),
                })
                
            # Save progress after each chapter (success or failure)
            ws['chapters'] = chapters_data
            task.output_data = {'workflow_state': ws}
            task.progress = int((i / len(chapters_outline)) * 100)
            task.current_step = f'Completed chapter {i}/{len(chapters_outline)}'
            db.commit()
        
        # Finalize
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.current_step = f'Done - {len(chapters_data)} chapters'
        db.commit()
        
        # Summary
        total_words = sum(c['word_count'] for c in chapters_data)
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 FINAL SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Chapters Generated: {len(chapters_data)}")
        logger.info(f"Total Words: {total_words}")
        logger.info(f"Approx Pages: {total_words / 250:.1f}")
        
        for ch in chapters_data:
            logger.info(f"  Ch{ch['number']}: {ch['title'][:40]} | {ch['word_count']} words")
        
        # Cost summary
        cost = db.query(func.sum(LLMUsageLog.total_cost)).filter(
            LLMUsageLog.task_id == task.id
        ).scalar() or 0
        calls = db.query(func.count(LLMUsageLog.id)).filter(
            LLMUsageLog.task_id == task.id
        ).scalar() or 0
        tokens = db.query(func.sum(LLMUsageLog.total_tokens)).filter(
            LLMUsageLog.task_id == task.id
        ).scalar() or 0
        
        logger.info(f"\n💰 COST SUMMARY:")
        logger.info(f"  Total Cost: ${cost:.4f}")
        logger.info(f"  API Calls: {calls}")
        logger.info(f"  Tokens: {tokens:,}")
        
        logger.info("\n" + "=" * 70)
        logger.info("🏁 GENERATION COMPLETE")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()


if __name__ == "__main__":
    main()

