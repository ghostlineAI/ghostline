#!/usr/bin/env python3
"""
Phase 7 Regression Scan

Comprehensive verification that:
1. We actually implemented what we said we did
2. We didn't accidentally break anything
3. All pieces fit together correctly
4. No deprecated code paths remain

Run with: python scripts/regression_scan_phase7.py
"""

import os
import re
import sys
from pathlib import Path

# Add the api directory to the path
api_dir = Path(__file__).parent.parent
project_root = api_dir.parent.parent
sys.path.insert(0, str(api_dir))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = []


def check(name: str, passed: bool, message: str = ""):
    """Record a check result."""
    results.append((name, passed, message))
    status = PASS if passed else FAIL
    print(f"  {status} {name}")
    if message and not passed:
        print(f"      → {message}")


def warn(name: str, message: str):
    """Record a warning."""
    results.append((name, None, message))
    print(f"  {WARN} {name}")
    print(f"      → {message}")


def read_file_content(path: Path) -> str:
    """Read file content safely."""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return ""


# =============================================================================
# SECTION 1: SCHEMA CONSISTENCY
# =============================================================================
def test_schema_consistency():
    print("\n" + "=" * 70)
    print("1. SCHEMA CONSISTENCY - Migration vs ORM Models")
    print("=" * 70)
    
    # Check migration file exists
    migration_path = api_dir / "alembic" / "versions" / "phase7_schema_reconciliation.py"
    check("Phase 7 migration file exists", migration_path.exists())
    
    if migration_path.exists():
        migration_content = read_file_content(migration_path)
        
        # Check key columns are in migration
        check("Migration adds project_id to content_chunks", 
              'add_column' in migration_content and 'project_id' in migration_content)
        
        check("Migration adds stylometry columns to voice_profiles",
              'avg_sentence_length' in migration_content and 'vocabulary_complexity' in migration_content)
        
        check("Migration adds PAUSED to taskstatus enum",
              "PAUSED" in migration_content)
        
        check("Migration adds workflow_state to generation_tasks",
              'workflow_state' in migration_content)
        
        check("Migration creates workflow_checkpoints table",
              'workflow_checkpoints' in migration_content)
    
    # Check ORM models match
    content_chunk_path = api_dir / "app" / "models" / "content_chunk.py"
    if content_chunk_path.exists():
        cc_content = read_file_content(content_chunk_path)
        
        check("ContentChunk has project_id column",
              "project_id = Column" in cc_content)
        
        check("ContentChunk has source_reference column",
              "source_reference = Column" in cc_content)
        
        check("ContentChunk has chunk_index column",
              "chunk_index = Column" in cc_content)
        
        check("ContentChunk has chunk_metadata column",
              "metadata = Column" in cc_content)
        
        # REGRESSION CHECK: token_count should be nullable
        if "token_count = Column(Integer, nullable=False)" in cc_content:
            warn("ContentChunk.token_count still NOT NULL",
                 "Should be nullable=True for migration compatibility")
    
    # Check VoiceProfile
    voice_profile_path = api_dir / "app" / "models" / "voice_profile.py"
    if voice_profile_path.exists():
        vp_content = read_file_content(voice_profile_path)
        
        check("VoiceProfile has stylometry fields",
              "avg_sentence_length" in vp_content and "vocabulary_complexity" in vp_content)
        
        check("VoiceProfile has embedding_weight",
              "embedding_weight = Column" in vp_content)
        
        check("VoiceProfile has similarity_threshold",
              "similarity_threshold = Column" in vp_content)


# =============================================================================
# SECTION 2: EMBEDDING SERVICE CONSISTENCY
# =============================================================================
def test_embedding_service_consistency():
    print("\n" + "=" * 70)
    print("2. EMBEDDING SERVICE CONSISTENCY")
    print("=" * 70)
    
    embeddings_path = api_dir / "app" / "services" / "embeddings.py"
    if not embeddings_path.exists():
        check("Embedding service exists", False, "File not found")
        return
    
    content = read_file_content(embeddings_path)
    
    # Check for OpenAI integration
    check("Uses OpenAI embeddings",
          "OpenAI" in content or "openai" in content)
    
    check("Uses text-embedding-3-small model",
          "text-embedding-3-small" in content)
    
    check("Has 1536 dimension configuration",
          "1536" in content)
    
    # REGRESSION CHECK: No more padding hack
    if "pad with zeros" in content.lower() or "extend([0.0]" in content:
        warn("Embedding service still has padding hack",
             "Should use native 1536-dim OpenAI embeddings, not padding")
    else:
        check("No padding hack present", True)
    
    # Check for fallback
    check("Has local fallback option",
          "LocalEmbeddingClient" in content or "sentence-transformers" in content.lower())
    
    # REGRESSION CHECK: Make sure we export correctly
    check("Has get_embedding_service function",
          "def get_embedding_service" in content)
    
    # Check other files use the new service correctly
    processing_path = api_dir / "app" / "services" / "processing.py"
    if processing_path.exists():
        proc_content = read_file_content(processing_path)
        check("ProcessingService uses get_embedding_service",
              "get_embedding_service" in proc_content or "EmbeddingService" in proc_content)
    
    generation_path = api_dir / "app" / "tasks" / "generation.py"
    if generation_path.exists():
        gen_content = read_file_content(generation_path)
        check("analyze_voice_task uses get_embedding_service",
              "get_embedding_service" in gen_content)
        
        # REGRESSION CHECK: Old method calls
        if "embed_batch" in gen_content:
            warn("analyze_voice_task still uses embed_batch",
                 "Should use embed_texts (the new method name)")
        else:
            check("analyze_voice_task uses correct method names", True)


# =============================================================================
# SECTION 3: AGENT GROUNDING CONSISTENCY
# =============================================================================
def test_agent_grounding_consistency():
    print("\n" + "=" * 70)
    print("3. AGENT GROUNDING & CITATION CONSISTENCY")
    print("=" * 70)
    
    agents_dir = project_root / "ghostline" / "agents" / "agents" / "specialized"
    
    # ContentDrafterAgent
    drafter_path = agents_dir / "content_drafter.py"
    if drafter_path.exists():
        content = read_file_content(drafter_path)
        
        check("ContentDrafterAgent has grounding requirement",
              "grounding_requirement" in content or "GROUNDING" in content)
        
        check("ContentDrafterAgent mentions citations",
              "citation" in content.lower())
        
        check("ContentDrafterAgent has source_chunks_with_citations",
              "source_chunks_with_citations" in content)
        
        # REGRESSION CHECK: Still has old source_chunks too for backwards compat
        check("ContentDrafterAgent keeps legacy source_chunks",
              "source_chunks: list[str]" in content)
    else:
        check("ContentDrafterAgent exists", False)
    
    # FactCheckerAgent
    fact_path = agents_dir / "fact_checker.py"
    if fact_path.exists():
        content = read_file_content(fact_path)
        
        check("FactCheckerAgent has claim mapping",
              "claim_mapping" in content.lower() or "ClaimMapping" in content)
        
        check("FactCheckerAgent tracks unsupported claims",
              "unsupported_claims" in content)
        
        check("FactCheckerAgent has source_chunks_with_citations",
              "source_chunks_with_citations" in content)
    else:
        check("FactCheckerAgent exists", False)


# =============================================================================
# SECTION 4: VOICE METRICS CONSISTENCY
# =============================================================================
def test_voice_metrics_consistency():
    print("\n" + "=" * 70)
    print("4. VOICE METRICS CONSISTENCY")
    print("=" * 70)
    
    # Check VoiceMetricsService exists
    vm_path = api_dir / "app" / "services" / "voice_metrics.py"
    if not vm_path.exists():
        check("VoiceMetricsService exists", False)
        return
    
    content = read_file_content(vm_path)
    
    check("VoiceMetricsService has stylometry extraction",
          "extract_features" in content or "StylometryFeatures" in content)
    
    check("VoiceMetricsService has numeric similarity",
          "compute_similarity" in content)
    
    check("VoiceMetricsService uses threshold",
          "threshold" in content)
    
    check("VoiceMetricsService combines embedding + stylometry",
          "embedding_weight" in content or "stylometry_weight" in content)
    
    # Check VoiceEditorAgent uses numeric metrics
    agents_dir = project_root / "ghostline" / "agents" / "agents" / "specialized"
    voice_editor_path = agents_dir / "voice_editor.py"
    
    if voice_editor_path.exists():
        ve_content = read_file_content(voice_editor_path)
        
        check("VoiceEditorAgent mentions numeric metrics",
              "numeric" in ve_content.lower() or "NUMERIC" in ve_content)
        
        check("VoiceEditorAgent has voice_embedding field",
              "voice_embedding" in ve_content)
        
        check("VoiceEditorAgent has stylometry_features field",
              "stylometry_features" in ve_content)
        
        check("VoiceEditorAgent has similarity_threshold config",
              "similarity_threshold" in ve_content)
        
        # REGRESSION CHECK: Still has LLM fallback
        if "analyze_voice_match" in ve_content:
            check("VoiceEditorAgent keeps LLM fallback", True)
        else:
            warn("VoiceEditorAgent lost LLM fallback",
                 "Should keep analyze_voice_match for when numeric profile unavailable")


# =============================================================================
# SECTION 5: SAFETY SERVICE CONSISTENCY
# =============================================================================
def test_safety_service_consistency():
    print("\n" + "=" * 70)
    print("5. SAFETY SERVICE CONSISTENCY")
    print("=" * 70)
    
    safety_path = api_dir / "app" / "services" / "safety.py"
    if not safety_path.exists():
        check("SafetyService exists", False)
        return
    
    content = read_file_content(safety_path)
    
    check("SafetyService has crisis detection",
          "crisis" in content.lower() or "CRISIS" in content)
    
    check("SafetyService has medical advice detection",
          "medical" in content.lower() or "MEDICAL" in content)
    
    check("SafetyService has disclaimer support",
          "disclaimer" in content.lower())
    
    check("SafetyService has crisis resources",
          "988" in content or "741741" in content)  # US crisis lines
    
    # REGRESSION CHECK: Is it integrated into workflow?
    workflow_path = project_root / "ghostline" / "agents" / "orchestrator" / "workflow.py"
    if workflow_path.exists():
        wf_content = read_file_content(workflow_path)
        
        if "safety" in wf_content.lower() or "SafetyService" in wf_content:
            check("Safety integrated into workflow", True)
        else:
            warn("Safety NOT integrated into workflow",
                 "SafetyService exists but workflow doesn't call it")


# =============================================================================
# SECTION 6: IMPORT/DEPENDENCY CHECKS
# =============================================================================
def test_imports_and_dependencies():
    print("\n" + "=" * 70)
    print("6. IMPORT & DEPENDENCY CHECKS")
    print("=" * 70)
    
    # Check for circular imports in key files
    files_to_check = [
        api_dir / "app" / "services" / "embeddings.py",
        api_dir / "app" / "services" / "rag.py",
        api_dir / "app" / "services" / "voice_metrics.py",
        api_dir / "app" / "services" / "safety.py",
        api_dir / "app" / "services" / "processing.py",
    ]
    
    for file_path in files_to_check:
        if not file_path.exists():
            continue
        
        content = read_file_content(file_path)
        
        # Check for problematic imports
        if "from app.models" in content and "from app.db.base" in content:
            warn(f"{file_path.name} imports both models and db.base",
                 "May cause circular import")
        else:
            check(f"{file_path.name} has clean imports", True)
    
    # Check RAG service doesn't import models at module level (circular import risk)
    rag_path = api_dir / "app" / "services" / "rag.py"
    if rag_path.exists():
        rag_content = read_file_content(rag_path)
        
        # Check if model imports are at top level
        lines = rag_content.split('\n')
        top_imports = []
        for line in lines[:50]:  # First 50 lines
            if line.startswith('from app.models') or line.startswith('import app.models'):
                top_imports.append(line)
        
        if top_imports:
            warn("RAG service imports models at module level",
                 f"Found: {top_imports[0][:60]}...")
        else:
            check("RAG service has safe model imports", True)


# =============================================================================
# SECTION 7: DEPRECATED CODE PATHS
# =============================================================================
def test_deprecated_code_paths():
    print("\n" + "=" * 70)
    print("7. DEPRECATED CODE PATHS CHECK")
    print("=" * 70)
    
    # Check for old embedding dimension padding
    embeddings_path = api_dir / "app" / "services" / "embeddings.py"
    if embeddings_path.exists():
        content = read_file_content(embeddings_path)
        
        if "_target_dims = 1536" in content and "extend([0.0]" in content:
            warn("Old padding logic still present in embeddings.py",
                 "Should not need to pad if using OpenAI natively")
    
    # Check for old embed_batch method calls
    gen_tasks_path = api_dir / "app" / "tasks" / "generation.py"
    if gen_tasks_path.exists():
        content = read_file_content(gen_tasks_path)
        
        if "embed_batch" in content:
            warn("Old embed_batch method called in generation.py",
                 "Should use embed_texts instead")
        else:
            check("No deprecated embed_batch calls", True)
        
        if "file_path" in content and "process_file" in content:
            warn("Old file_path/process_file pattern in generation.py",
                 "Should use extracted_text/extracted_content from model")
        
        if "doc_processor.process_file" in content:
            warn("Old doc_processor.process_file call",
                 "Should read from model's extracted_text field")
    
    # Check for old voice score pattern (LLM-judged)
    agents_dir = project_root / "ghostline" / "agents" / "agents" / "specialized"
    voice_editor_path = agents_dir / "voice_editor.py"
    if voice_editor_path.exists():
        content = read_file_content(voice_editor_path)
        
        # Check if still using LLM-only scoring
        if 'structured_data.get("score"' in content and "numeric" not in content.lower():
            warn("VoiceEditorAgent may still use LLM-only scoring",
                 "Should use numeric metrics as primary, LLM as fallback")
        else:
            check("VoiceEditorAgent uses numeric metrics appropriately", True)


# =============================================================================
# SECTION 8: RAG SERVICE INTEGRATION
# =============================================================================
def test_rag_integration():
    print("\n" + "=" * 70)
    print("8. RAG SERVICE INTEGRATION CHECK")
    print("=" * 70)
    
    rag_path = api_dir / "app" / "services" / "rag.py"
    if not rag_path.exists():
        check("RAG service exists", False)
        return
    
    content = read_file_content(rag_path)
    
    check("RAG service has pgvector query",
          "<=>" in content or "vector_cosine_ops" in content.lower())
    
    check("RAG service has Citation class",
          "class Citation" in content)
    
    check("RAG service has RetrievedChunk class",
          "class RetrievedChunk" in content)
    
    check("RAG service has similarity threshold",
          "similarity_threshold" in content)
    
    check("RAG service has fallback retrieval",
          "fallback" in content.lower())
    
    # Check if RAG is used anywhere
    subgraphs_path = project_root / "ghostline" / "agents" / "orchestrator" / "subgraphs.py"
    if subgraphs_path.exists():
        sg_content = read_file_content(subgraphs_path)
        if "rag" in sg_content.lower() or "RAGService" in sg_content:
            check("RAG integrated into subgraphs", True)
        else:
            warn("RAG NOT integrated into subgraphs",
                 "ChapterSubgraph should use RAG to retrieve source chunks")


# =============================================================================
# SECTION 9: TEST COVERAGE
# =============================================================================
def test_test_coverage():
    print("\n" + "=" * 70)
    print("9. TEST COVERAGE CHECK")
    print("=" * 70)
    
    scripts_dir = api_dir / "scripts"
    
    test_files = {
        "test_phase7_schema.py": ["ContentChunk", "VoiceProfile", "GenerationTask"],
        "test_phase7_embeddings.py": ["OpenAI", "similarity", "1536"],
        "test_phase7_services.py": ["RAG", "Voice", "Safety"],
    }
    
    for test_file, expected_coverage in test_files.items():
        test_path = scripts_dir / test_file
        if test_path.exists():
            content = read_file_content(test_path)
            
            covered = sum(1 for term in expected_coverage if term in content)
            check(f"{test_file} covers expected areas",
                  covered >= len(expected_coverage) * 0.7,
                  f"Covers {covered}/{len(expected_coverage)} expected terms")
        else:
            check(f"{test_file} exists", False)


# =============================================================================
# SUMMARY
# =============================================================================
def print_summary():
    print("\n" + "=" * 70)
    print("REGRESSION SCAN SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, ok, _ in results if ok is True)
    failed = sum(1 for _, ok, _ in results if ok is False)
    warned = sum(1 for _, ok, _ in results if ok is None)
    
    print(f"\n  {PASS} Passed: {passed}")
    print(f"  {FAIL} Failed: {failed}")
    print(f"  {WARN} Warnings: {warned}")
    
    if failed > 0:
        print("\n  FAILED CHECKS:")
        for name, ok, msg in results:
            if ok is False:
                print(f"    ❌ {name}")
                if msg:
                    print(f"       → {msg}")
    
    if warned > 0:
        print("\n  WARNINGS:")
        for name, ok, msg in results:
            if ok is None:
                print(f"    ⚠️ {name}")
                if msg:
                    print(f"       → {msg}")
    
    if failed == 0 and warned == 0:
        print("\n🎉 ALL REGRESSION CHECKS PASSED!")
        return 0
    elif failed == 0:
        print(f"\n⚠️  PASSED WITH {warned} WARNINGS - Review recommended")
        return 0
    else:
        print(f"\n💥 {failed} REGRESSION FAILURES DETECTED")
        return 1


def main():
    print("\n" + "=" * 70)
    print("PHASE 7 REGRESSION SCAN")
    print("Verifying: Did we do what we said? Did we break anything?")
    print("=" * 70)
    
    test_schema_consistency()
    test_embedding_service_consistency()
    test_agent_grounding_consistency()
    test_voice_metrics_consistency()
    test_safety_service_consistency()
    test_imports_and_dependencies()
    test_deprecated_code_paths()
    test_rag_integration()
    test_test_coverage()
    
    return print_summary()


if __name__ == "__main__":
    sys.exit(main())

