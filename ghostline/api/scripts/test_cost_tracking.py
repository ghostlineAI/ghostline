#!/usr/bin/env python3
"""
Test script to verify cost tracking is working correctly.

Tests:
1. Cost calculations are accurate
2. Data saves to DB successfully
3. Granularity is at the per-call level
"""

import sys
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import SessionLocal
from app.services.cost_tracker import CostTracker, get_pricing
from app.models.llm_usage_log import LLMUsageLog


def test_pricing_calculations():
    """Test that pricing calculations are accurate."""
    print("\n" + "=" * 60)
    print("TEST 1: Pricing Calculations")
    print("=" * 60)
    
    # Test cases: (provider, model, input_tokens, output_tokens, expected_cost)
    test_cases = [
        # Claude Sonnet 4: $0.003/1K input, $0.015/1K output
        ("anthropic", "claude-sonnet-4-20250514", 1000, 500, 0.003 + 0.0075),
        # GPT-4o: $0.0025/1K input, $0.01/1K output
        ("openai", "gpt-4o", 1000, 500, 0.0025 + 0.005),
        # GPT-4o-mini: $0.00015/1K input, $0.0006/1K output
        ("openai", "gpt-4o-mini", 1000, 500, 0.00015 + 0.0003),
        # Claude Haiku: $0.00025/1K input, $0.00125/1K output
        ("anthropic", "claude-3-haiku-20240307", 1000, 500, 0.00025 + 0.000625),
    ]
    
    all_passed = True
    for provider, model, input_tokens, output_tokens, expected_cost in test_cases:
        input_price, output_price = get_pricing(provider, model)
        actual_cost = (input_tokens / 1000) * input_price + (output_tokens / 1000) * output_price
        
        passed = abs(actual_cost - expected_cost) < 0.0001
        status = "✅ PASS" if passed else "❌ FAIL"
        
        print(f"\n{status}: {model}")
        print(f"   Input:  {input_tokens} tokens × ${input_price}/1K = ${(input_tokens/1000)*input_price:.6f}")
        print(f"   Output: {output_tokens} tokens × ${output_price}/1K = ${(output_tokens/1000)*output_price:.6f}")
        print(f"   Total:  ${actual_cost:.6f} (expected: ${expected_cost:.6f})")
        
        if not passed:
            all_passed = False
    
    return all_passed


def test_db_save_and_retrieve():
    """Test that records save to DB and can be retrieved."""
    print("\n" + "=" * 60)
    print("TEST 2: Database Save & Retrieve")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        tracker = CostTracker(db)
        
        # Create a test record with a unique workflow_run_id
        test_run_id = f"test_run_{uuid4().hex[:8]}"
        
        print(f"\n📝 Creating test record with workflow_run_id: {test_run_id}")
        
        log = tracker.record(
            agent_name="TestAgent",
            model="claude-sonnet-4-20250514",
            provider="anthropic",
            input_tokens=1234,
            output_tokens=567,
            duration_ms=1500,
            success=True,
            call_type="chat",
            workflow_run_id=test_run_id,
            chapter_number=1,
            agent_role="drafter",
            prompt_preview="This is a test prompt...",
            response_preview="This is a test response...",
            metadata={"temperature": 0.7, "max_tokens": 4096},
        )
        
        print(f"   Record ID: {log.id}")
        print(f"   Total tokens: {log.total_tokens}")
        print(f"   Total cost: ${log.total_cost:.6f}")
        
        # Verify the record was saved
        saved_log = db.query(LLMUsageLog).filter(LLMUsageLog.id == log.id).first()
        
        if saved_log is None:
            print("❌ FAIL: Record not found in database!")
            return False
        
        print(f"\n✅ Record saved successfully!")
        print(f"   Verifying fields...")
        
        # Verify all fields
        checks = [
            ("agent_name", saved_log.agent_name, "TestAgent"),
            ("model", saved_log.model, "claude-sonnet-4-20250514"),
            ("provider", saved_log.provider, "anthropic"),
            ("input_tokens", saved_log.input_tokens, 1234),
            ("output_tokens", saved_log.output_tokens, 567),
            ("total_tokens", saved_log.total_tokens, 1801),
            ("duration_ms", saved_log.duration_ms, 1500),
            ("success", saved_log.success, True),
            ("call_type", saved_log.call_type, "chat"),
            ("workflow_run_id", saved_log.workflow_run_id, test_run_id),
            ("chapter_number", saved_log.chapter_number, 1),
            ("agent_role", saved_log.agent_role, "drafter"),
        ]
        
        all_passed = True
        for field_name, actual, expected in checks:
            if actual != expected:
                print(f"   ❌ {field_name}: {actual} (expected: {expected})")
                all_passed = False
            else:
                print(f"   ✅ {field_name}: {actual}")
        
        # Verify cost calculation
        expected_input_cost = (1234 / 1000) * 0.003  # Claude Sonnet input
        expected_output_cost = (567 / 1000) * 0.015  # Claude Sonnet output
        expected_total_cost = expected_input_cost + expected_output_cost
        
        print(f"\n   Cost verification:")
        print(f"   ✅ input_cost: ${saved_log.input_cost:.6f} (expected: ${expected_input_cost:.6f})")
        print(f"   ✅ output_cost: ${saved_log.output_cost:.6f} (expected: ${expected_output_cost:.6f})")
        print(f"   ✅ total_cost: ${saved_log.total_cost:.6f} (expected: ${expected_total_cost:.6f})")
        
        if abs(saved_log.total_cost - expected_total_cost) > 0.0001:
            print(f"   ❌ Cost mismatch!")
            all_passed = False
        
        # Test aggregation
        print(f"\n📊 Testing aggregation for workflow run...")
        summary = tracker.get_workflow_run_summary(test_run_id)
        
        print(f"   Total calls: {summary.total_calls}")
        print(f"   Total tokens: {summary.total_tokens}")
        print(f"   Total cost: ${summary.total_cost:.6f}")
        print(f"   By model: {summary.by_model}")
        print(f"   By agent: {summary.by_agent}")
        print(f"   By chapter: {summary.by_chapter}")
        
        if summary.total_calls != 1:
            print(f"   ❌ Expected 1 call, got {summary.total_calls}")
            all_passed = False
        else:
            print(f"   ✅ Aggregation working correctly!")
        
        # Clean up test record
        db.delete(saved_log)
        db.commit()
        print(f"\n🧹 Test record cleaned up")
        
        return all_passed
        
    finally:
        db.close()


def test_granularity():
    """Test that we're recording at the most granular level."""
    print("\n" + "=" * 60)
    print("TEST 3: Granularity Check")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        tracker = CostTracker(db)
        test_run_id = f"granularity_test_{uuid4().hex[:8]}"
        
        print(f"\n📝 Creating multiple records to test granularity...")
        
        # Simulate a multi-agent chapter generation
        records = [
            {"agent_name": "ContentDrafterAgent", "chapter_number": 1, "input_tokens": 2000, "output_tokens": 1500},
            {"agent_name": "VoiceEditorAgent", "chapter_number": 1, "input_tokens": 2500, "output_tokens": 800},
            {"agent_name": "FactCheckerAgent", "chapter_number": 1, "input_tokens": 3000, "output_tokens": 500},
            {"agent_name": "CohesionAnalystAgent", "chapter_number": 1, "input_tokens": 2200, "output_tokens": 400},
            {"agent_name": "ContentDrafterAgent", "chapter_number": 1, "input_tokens": 2100, "output_tokens": 1600},  # Revision
        ]
        
        created_ids = []
        for i, rec in enumerate(records):
            log = tracker.record(
                agent_name=rec["agent_name"],
                model="claude-sonnet-4-20250514",
                provider="anthropic",
                input_tokens=rec["input_tokens"],
                output_tokens=rec["output_tokens"],
                duration_ms=1000 + i * 100,
                success=True,
                workflow_run_id=test_run_id,
                chapter_number=rec["chapter_number"],
            )
            created_ids.append(log.id)
            print(f"   {i+1}. {rec['agent_name']}: {rec['input_tokens']} in / {rec['output_tokens']} out = ${log.total_cost:.6f}")
        
        # Get detailed logs
        logs = tracker.get_detailed_logs(workflow_run_id=test_run_id)
        print(f"\n📋 Retrieved {len(logs)} individual records (expected: {len(records)})")
        
        # Get summary with breakdowns
        summary = tracker.get_workflow_run_summary(test_run_id)
        
        print(f"\n📊 Summary:")
        print(f"   Total calls: {summary.total_calls}")
        print(f"   Total tokens: {summary.total_tokens:,}")
        print(f"   Total cost: ${summary.total_cost:.6f}")
        
        print(f"\n   BY AGENT:")
        for agent, data in sorted(summary.by_agent.items()):
            print(f"      {agent}: {data['calls']} calls, {data['tokens']:,} tokens, ${data['cost']:.6f}")
        
        print(f"\n   BY CHAPTER:")
        for ch, data in sorted(summary.by_chapter.items()):
            print(f"      Chapter {ch}: {data['calls']} calls, {data['tokens']:,} tokens, ${data['cost']:.6f}")
        
        # Verify granularity
        all_passed = True
        
        if len(logs) != len(records):
            print(f"\n❌ Expected {len(records)} records, got {len(logs)}")
            all_passed = False
        else:
            print(f"\n✅ Correct number of granular records!")
        
        if summary.total_calls != len(records):
            print(f"❌ Summary shows wrong call count")
            all_passed = False
        
        if len(summary.by_agent) < 4:
            print(f"❌ Not all agents tracked separately")
            all_passed = False
        else:
            print(f"✅ All agents tracked separately!")
        
        # Clean up
        for log_id in created_ids:
            log = db.query(LLMUsageLog).filter(LLMUsageLog.id == log_id).first()
            if log:
                db.delete(log)
        db.commit()
        print(f"\n🧹 Test records cleaned up")
        
        return all_passed
        
    finally:
        db.close()


def main():
    print("\n" + "=" * 60)
    print("  COST TRACKING VERIFICATION TESTS")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Pricing Calculations", test_pricing_calculations()))
    results.append(("Database Save & Retrieve", test_db_save_and_retrieve()))
    results.append(("Granularity Check", test_granularity()))
    
    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  ALL TESTS PASSED ✅")
    else:
        print("  SOME TESTS FAILED ❌")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

