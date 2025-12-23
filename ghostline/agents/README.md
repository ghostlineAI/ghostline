# GhostLine AI Agents

This repository contains the multi-agent system for AI-powered book generation.

## Overview

The GhostLine agent system consists of specialized AI agents that collaborate to transform source materials into publishable books:

- **OrchestratorAgent**: Coordinates the entire workflow
- **PlannerAgent**: Creates book outlines and structure
- **ResearchAgent**: Retrieves context from source materials
- **ChapterAgent**: Drafts individual chapters
- **CriticAgent**: Reviews for quality and consistency
- **VoiceAgent**: Ensures voice/tone matching (target: ≥ 0.88 similarity)
- **ConsistencyAgent**: Validates plot, timeline, and facts
- **SafetyAgent**: Ensures content policy compliance

## Tech Stack

- **Framework**: LangGraph / LangChain
- **Models**: AWS Bedrock (Claude, Llama, Titan)
- **Vector Store**: pgvector / OpenSearch
- **Orchestration**: Custom workflow engine
- **Monitoring**: OpenTelemetry

## Getting Started

```bash
# Install dependencies
poetry install

# Run tests
pytest

# Run agent evaluation suite
python -m agents.evaluate

# Build Docker image
docker build -t ghostline-agents .
```

## Project Structure

```
agents/
├── agents/            # Individual agent implementations
├── orchestrator/      # Workflow orchestration logic
├── prompts/          # Prompt templates
├── models/           # Model configurations
├── evaluations/      # Agent evaluation metrics
├── utils/            # Shared utilities
└── tests/            # Test files
```

## Key Metrics

- **Voice Similarity**: Target ≥ 0.88 cosine similarity
- **Book Length**: Minimum 80 pages
- **Generation Time**: Target < 7 days per book
- **Token Efficiency**: Optimize for cost-effectiveness

## Contributing

Please see our [Contributing Guide](../docs/CONTRIBUTING.md) for details.

## License

Copyright © 2025 GhostLine. All rights reserved.

<!-- Data layer checkpoint: 2025-06-29 02:38 UTC -->

<!-- CHECKPOINT: Unit tests passing and login functionality restored - 2025-06-29 -->

<!-- CHECKPOINT: app_user security implementation complete - 2025-06-29 --> 