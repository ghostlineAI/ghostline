#!/usr/bin/env python3
"""
Cost Analysis Script for GhostLine.

Analyzes LLM API costs at various granularity levels:
- Per task/run
- Per project
- Per agent
- Per model
- Per chapter

Usage:
    # Analyze costs for a specific task
    python scripts/analyze_costs.py --task-id <uuid>
    
    # Analyze costs for a project
    python scripts/analyze_costs.py --project-id <uuid>
    
    # Analyze all costs in a date range
    python scripts/analyze_costs.py --start-date 2024-12-01 --end-date 2024-12-25
    
    # Export to JSON
    python scripts/analyze_costs.py --task-id <uuid> --output costs.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.base import SessionLocal
from app.services.cost_tracker import CostTracker, CostSummary
from app.models.llm_usage_log import LLMUsageLog


def format_currency(amount: float) -> str:
    """Format a number as USD currency."""
    return f"${amount:.6f}"


def format_number(n: int | float) -> str:
    """Format a number with commas."""
    if isinstance(n, float):
        return f"{n:,.2f}"
    return f"{n:,}"


def print_summary(summary: CostSummary, title: str = "Cost Summary"):
    """Print a formatted cost summary to stdout."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)
    
    print(f"\n📊 TOTALS")
    print(f"   Total API Calls:     {format_number(summary.total_calls)}")
    print(f"   Total Tokens:        {format_number(summary.total_tokens)}")
    print(f"      Input Tokens:     {format_number(summary.total_input_tokens)}")
    print(f"      Output Tokens:    {format_number(summary.total_output_tokens)}")
    print(f"   Total Cost:          {format_currency(summary.total_cost)}")
    print(f"      Input Cost:       {format_currency(summary.total_input_cost)}")
    print(f"      Output Cost:      {format_currency(summary.total_output_cost)}")
    
    print(f"\n📈 AVERAGES")
    print(f"   Avg Cost/Call:       {format_currency(summary.avg_cost_per_call)}")
    print(f"   Avg Tokens/Call:     {format_number(summary.avg_tokens_per_call)}")
    print(f"   Avg Duration:        {format_number(summary.avg_duration_ms)} ms")
    print(f"   Success Rate:        {summary.success_rate * 100:.1f}%")
    
    if summary.by_provider:
        print(f"\n🏢 BY PROVIDER")
        for provider, data in sorted(summary.by_provider.items()):
            print(f"   {provider.upper()}")
            print(f"      Calls:  {format_number(data['calls'])}")
            print(f"      Tokens: {format_number(data['tokens'])}")
            print(f"      Cost:   {format_currency(data['cost'])}")
    
    if summary.by_model:
        print(f"\n🤖 BY MODEL")
        for model, data in sorted(summary.by_model.items(), key=lambda x: x[1]['cost'], reverse=True):
            print(f"   {model}")
            print(f"      Calls:         {format_number(data['calls'])}")
            print(f"      Total Tokens:  {format_number(data['tokens'])}")
            print(f"      Input Tokens:  {format_number(data.get('input_tokens', 0))}")
            print(f"      Output Tokens: {format_number(data.get('output_tokens', 0))}")
            print(f"      Cost:          {format_currency(data['cost'])}")
    
    if summary.by_agent:
        print(f"\n🤖 BY AGENT")
        for agent, data in sorted(summary.by_agent.items(), key=lambda x: x[1]['cost'], reverse=True):
            print(f"   {agent}")
            print(f"      Calls:  {format_number(data['calls'])}")
            print(f"      Tokens: {format_number(data['tokens'])}")
            print(f"      Cost:   {format_currency(data['cost'])}")
    
    if summary.by_chapter:
        print(f"\n📖 BY CHAPTER")
        for chapter, data in sorted(summary.by_chapter.items()):
            print(f"   Chapter {chapter}")
            print(f"      Calls:  {format_number(data['calls'])}")
            print(f"      Tokens: {format_number(data['tokens'])}")
            print(f"      Cost:   {format_currency(data['cost'])}")
    
    print("\n" + "=" * 70 + "\n")


def print_detailed_logs(logs: list[LLMUsageLog], limit: int = 20):
    """Print detailed log entries."""
    print(f"\n📝 DETAILED LOGS (showing {min(len(logs), limit)} of {len(logs)})")
    print("-" * 100)
    
    for i, log in enumerate(logs[:limit]):
        timestamp = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "N/A"
        status = "✅" if log.success else "❌"
        fallback = " [FALLBACK]" if log.is_fallback else ""
        
        print(f"{i+1}. {status} {timestamp} | {log.agent_name} | {log.model}{fallback}")
        print(f"   Tokens: {log.input_tokens} in / {log.output_tokens} out = {log.total_tokens} total")
        print(f"   Cost: {format_currency(log.total_cost)} ({format_currency(log.input_cost)} in / {format_currency(log.output_cost)} out)")
        print(f"   Duration: {log.duration_ms} ms")
        if log.chapter_number:
            print(f"   Chapter: {log.chapter_number}")
        if log.error_message:
            print(f"   Error: {log.error_message[:100]}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Analyze GhostLine LLM costs")
    parser.add_argument("--task-id", type=str, help="Task ID to analyze")
    parser.add_argument("--project-id", type=str, help="Project ID to analyze")
    parser.add_argument("--workflow-run-id", type=str, help="Workflow run ID to analyze")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--detailed", action="store_true", help="Show detailed logs")
    parser.add_argument("--limit", type=int, default=20, help="Limit for detailed logs")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path")
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None
    
    # Parse UUIDs
    task_id = UUID(args.task_id) if args.task_id else None
    project_id = UUID(args.project_id) if args.project_id else None
    
    # Connect to database
    db = SessionLocal()
    try:
        tracker = CostTracker(db)
        
        # Get summary based on filters
        if task_id:
            summary = tracker.get_task_summary(task_id)
            title = f"Cost Summary for Task {task_id}"
        elif project_id:
            summary = tracker.get_project_summary(project_id)
            title = f"Cost Summary for Project {project_id}"
        elif args.workflow_run_id:
            summary = tracker.get_workflow_run_summary(args.workflow_run_id)
            title = f"Cost Summary for Workflow Run {args.workflow_run_id}"
        else:
            summary = tracker.get_all_summary(start_date=start_date, end_date=end_date)
            title = "Overall Cost Summary"
            if start_date or end_date:
                date_range = []
                if start_date:
                    date_range.append(f"from {start_date.date()}")
                if end_date:
                    date_range.append(f"to {end_date.date()}")
                title += f" ({' '.join(date_range)})"
        
        # Print summary
        print_summary(summary, title)
        
        # Print detailed logs if requested
        if args.detailed:
            logs = tracker.get_detailed_logs(
                task_id=task_id,
                project_id=project_id,
                workflow_run_id=args.workflow_run_id,
                limit=args.limit,
            )
            print_detailed_logs(logs, args.limit)
        
        # Export to JSON if requested
        if args.output:
            output_data = tracker.export_to_dict(summary)
            output_data["generated_at"] = datetime.utcnow().isoformat()
            output_data["filters"] = {
                "task_id": str(task_id) if task_id else None,
                "project_id": str(project_id) if project_id else None,
                "workflow_run_id": args.workflow_run_id,
                "start_date": str(start_date.date()) if start_date else None,
                "end_date": str(end_date.date()) if end_date else None,
            }
            
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            
            print(f"📁 Exported to {args.output}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

