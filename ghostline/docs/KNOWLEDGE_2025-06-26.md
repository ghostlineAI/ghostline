---
Last Updated: 2025-06-28 09:30:52 PDT
---

# GhostLine Project Knowledge Base

This document is the single source of truth for the GhostLine project, designed to be a comprehensive handoff document for any developer or LLM joining the project.

**Project Vision**: To create a multi-agent AI platform that transforms ideas, notes, and voice memos into professionally written, full-length books that authentically capture the author's unique style and voice.

## 1. Current High-Level Status

-   **Frontend**: Deployed and accessible at **[https://dev.ghostline.ai](https://dev.ghostline.ai/)**. A temporary mock authentication and data system is currently active to allow for full UX testing and demonstration while backend database issues are resolved.
-   **Backend API**: Deployed and accessible at **[https://api.dev.ghostline.ai/health](https://api.dev.ghostline.ai/health)**. The service is running but is not yet fully connected to the database.
-   **Infrastructure**: All core AWS infrastructure is provisioned via Terraform, including VPC, RDS, ElastiCache, ECS, and S3.
-   **Database**: The RDS PostgreSQL instance is running, but the schema has not been successfully applied yet. The migration script needs to be re-run or debugged.
-   **CI/CD**: Fully automated. Pushing to the `main` branch of any repository triggers a build and deployment to the `dev` environment.

## 2. Project Milestones & History

This timeline summarizes the major phases of development and key decisions made.

### Phase 4.7: UX Implementation & Mock System (Current)
-   **Goal**: Implement the complete, end-to-end user experience.
-   **Outcome**:
    -   Implemented a comprehensive frontend with a project dashboard, file data room, book creation wizard, and billing page.
    -   Encountered and fixed numerous frontend build failures and CI/CD pipeline issues related to dependencies, linting, and testing scripts.
    -   Discovered the backend API was not fully functional due to an uninitialized database.
    -   **Implemented a full mock authentication and data service** to unblock frontend development and allow for immediate, interactive UX testing.
    -   Force-enabled the mock services for the `dev.ghostline.ai` deployment to ensure a usable demo environment.

### Phase 4.6: Database Schema & Migrations
-   **Goal**: Design and implement the complete database schema.
-   **Outcome**:
    -   Designed a comprehensive 15-table schema in SQLAlchemy.
    -   Models include `users`, `projects`, `source_materials`, `content_chunks` (with pgvector), `chapters`, `billing_plans`, and more.
    -   Created an initial Alembic migration script to create the schema.
    -   **Identified Issue**: The migration script has not been successfully run against the RDS instance, which is the root cause of current backend errors.

### Phase 4: Foundational Scaffolding & CI/CD
-   **Goal**: Scaffold all repositories and set up automated CI/CD.
-   **Outcome**:
    -   Conducted a UI audit of competitor products.
    -   Scaffolded the Next.js frontend, FastAPI backend, and LangGraph agent system.
    -   Established modern development tooling (Poetry, Ruff, ESLint).
    -   Built robust, multi-stage Dockerfiles for all services.
    -   Created comprehensive GitHub Actions workflows for continuous integration and deployment to AWS.

### Phase 3: AWS Landing Zone
-   **Goal**: Provision the core cloud infrastructure using Terraform.
-   **Outcome**:
    -   Built modular Terraform configuration for a secure and scalable AWS environment.
    -   Provisioned a three-tier VPC, security services (WAF, GuardDuty), KMS for encryption, and S3 buckets.
    -   Set up AWS Budgets for cost control and monitoring.
    -   Established a secure backend for Terraform state in S3 with DynamoDB for locking.

### Phase 2: High-Level Architecture
-   **Goal**: Design the system architecture and data flow.
-   **Outcome**:
    -   Created architecture and data flow diagrams.
    -   Selected **AWS ECS Fargate** as the primary compute platform for its balance of serverless convenience and flexibility.
    -   Decided to use **PostgreSQL with the pgvector extension** over a dedicated vector database to simplify the stack.
    -   Designed a queue-based, scale-to-zero architecture for the AI worker agents.

### Phase 1: Technology Selection
-   **Goal**: Research and select the open-source technology stack.
-   **Outcome**:
    -   Performed a capability scan of popular open-source projects.
    -   Selected **LangGraph** for agent orchestration, **Claude 3 Haiku** as the primary LLM, and **Next.js** for the frontend.
    -   Documented all choices and justifications in an ADR.

### Phase 0: Project Bootstrap
-   **Goal**: Set up the foundational project structure and standards.
-   **Outcome**:
    -   Established the 5-repository monorepo structure (`web`, `api`, `agents`, `infra`, `docs`).
    -   Defined project standards with `CODEOWNERS`, pull request templates, and markdown linting.
    -   Authored the initial `PROJECT_CHARTER.md` and `ADR-0000.md`.

- Created GitHub organization: `ghostlineAI`
- Set up 5 repositories: web, api, agents, infra, docs
- Established development standards (CODEOWNERS, PR templates, markdown linting)
- Created PROJECT_CHARTER.md with personas and KPIs
- Created ADR-0000.md documenting foundational decisions

### ✅ Phase 1: Open-Source Capability Scan (COMPLETE)

- Built `oss_capability_scan.py` to analyze GitHub repositories
- Generated `oss_scan.csv` with 18 libraries + 3 LLM benchmarks
- Created ADR-0001.md documenting technology stack
- Confirmed zero AGPL/viral licenses in selected stack

### ✅ Phase 2: High-Level Architecture Blueprint (COMPLETE)

- Created comprehensive architecture diagrams
- Documented data flow: upload → ingestion → chunk/embedding → agent DAG
- Selected AWS ECS Fargate as compute platform
- Created ADR-0002.md with compute platform trade-offs

### ✅ Phase 3: AWS Landing Zone (COMPLETE)

- Created Terraform modules: organization, vpc, security, budget, kms
- Deployed bootstrap infrastructure:
  - S3 state bucket: `ghostline-terraform-state-820242943150`
  - DynamoDB table: `ghostline-terraform-locks`
  - KMS key for state encryption
- Deployed development environment:
  - VPC: `vpc-00d75267879c8f631` (10.0.0.0/16)
  - 6 subnets across 2 AZs (us-west-2a, us-west-2b)
  - S3 buckets: `ghostline-dev-source-materials-820242943150`, `ghostline-dev-outputs-820242943150`
  - Security groups for ALB, ECS, RDS
  - WAF Web ACL: `7529b94c-e8fe-4f43-9d35-cc3b87430d81`
  - GuardDuty, Security Hub, IAM Access Analyzer enabled
  - Budget alerts: $500/month total, service-specific limits
  - 6 KMS keys for different services
- Created deployment scripts: `setup-tools.sh`, `deploy.sh`
- Documented in: DEPLOYMENT_SUMMARY.md, PHASE_3_COMPLETE.md
- Estimated monthly cost: $30-45 for base infrastructure

### ✅ Phase 4: Repo & CI/CD Scaffolding (COMPLETE)

- Conducted competitor UI audit of 5 platforms
- Created ADR-0003.md choosing custom Tailwind + shadcn/ui
- Scaffolded Next.js 15.3.4 frontend with professional landing page
- Scaffolded FastAPI 0.115.14 backend with Poetry
- Scaffolded LangGraph agent system
- Created multi-stage Dockerfiles for all services
- Added GitHub Actions CI/CD pipelines
- Configured linting, testing, and ECR deployment
- **Frontend deployed**: https://dev.ghostline.ai (live)
- **Backend infrastructure deployed**:
  - RDS PostgreSQL 15.8 (db.t3.micro)
  - ElastiCache Redis 7.0 (cache.t3.micro)
  - Application Load Balancer
  - ECS Cluster with Fargate
  - ECR repositories for all services
- **Auto-deployment enabled** for all repositories:
  - Web → S3/CloudFront
  - API → ECS Fargate
  - Agents → ECS Fargate (workers)

### 🔜 Phase 5: Data Layer Foundation (NEXT)

- Set up database migrations with Alembic
- Configure pgvector extension
- Implement connection pooling
- Create initial schema
- Set up Redis for caching/queuing

## Repository Structure

```
ghostline/
├── web/          # Next.js frontend application
│   └── .github/workflows/deploy.yml  # Auto-deploy to S3/CloudFront
├── api/          # FastAPI backend service
│   └── .github/workflows/deploy.yml  # Auto-deploy to ECS
├── agents/       # LangGraph multi-agent system
│   └── .github/workflows/deploy.yml  # Auto-deploy to ECS
├── infra/        # Terraform/AWS infrastructure
│   ├── terraform/
│   │   ├── modules/        # Reusable Terraform modules
│   │   │   ├── vpc/        # Network infrastructure
│   │   │   ├── security/   # WAF, GuardDuty, etc.
│   │   │   ├── kms/        # Encryption keys
│   │   │   ├── budget/     # Cost monitoring
│   │   │   ├── ecs/        # Container orchestration
│   │   │   ├── alb/        # Load balancer
│   │   │   ├── rds/        # PostgreSQL database
│   │   │   ├── redis/      # ElastiCache Redis
│   │   │   ├── route53/    # DNS management
│   │   │   └── frontend/   # S3/CloudFront
│   │   ├── environments/   # Environment-specific configs
│   │   └── backend/        # State management config
│   ├── ecs-task-definitions/  # ECS task definitions
│   ├── deploy.sh          # Deployment script
│   ├── deploy-web.sh      # Web deployment script
│   └── setup-tools.sh     # Tool installation script
└── docs/         # Documentation and ADRs
    ├── adr/      # Architecture Decision Records
    │   ├── ADR-0000.md  # Foundational decisions
    │   ├── ADR-0001.md  # Technology stack
    │   ├── ADR-0002.md  # Compute platform (ECS Fargate)
    │   └── ADR-0003.md  # UI framework (Tailwind + shadcn/ui)
    ├── scripts/  # Utility scripts (oss_capability_scan.py)
    ├── runbooks/ # Operational procedures
    │   └── oncall.md    # On-call runbook with PagerDuty
    ├── oss_scan.csv     # Technology evaluation results
    ├── PHASE_0_COMPLETE.md
    ├── PHASE_1_COMPLETE.md
    ├── PHASE_2_COMPLETE.md
    ├── PHASE_3_COMPLETE.md
    ├── PHASE_4_COMPLETE.md
    ├── DEPLOYMENT_GUIDE.md
    ├── AUTOMATIC_DEPLOYMENT_STATUS.md
    ├── GITHUB_SECRETS_SETUP.md
    └── KNOWLEDGE.md     # This file
```

## System Architecture (from Phase 2)

### High-Level Components

1.  **Client Layer**: Next.js frontend + Typer CLI
2.  **API Gateway**: AWS ALB with WAF protection
3.  **Application Layer**: FastAPI on ECS Fargate
4.  **Agent Orchestration**: LangGraph managing 8 specialized agents
5.  **Data Plane**: PostgreSQL + pgvector, Redis, S3
6.  **AI/ML Services**: AWS Bedrock (Claude) + OpenAI (GPT-4o)

### Data Flow

1.  **Upload**: Multipart to S3 with presigned URLs
2.  **Ingestion**: unstructured.io processing
3.  **Chunking**: 1000-token chunks with embeddings
4.  **Agent DAG**: Iterative chapter generation
5.  **Output**: Book compilation and export

### Compute Strategy (from ADR-0002)

- **Platform**: AWS ECS Fargate (serverless containers)
- **API Service**: 2-20 tasks (always on)
- **Workers**: 0-50 tasks (scale-to-zero)
- **Cost Optimization**: Fargate Spot for 70% savings
- **Scaling**: Queue-based via SQS depth

## Technology Stack (from ADR-0001)

### Core AI/ML

- **LangGraph** (14.8k stars, MIT) - Multi-agent orchestration
- **Claude 3 Haiku** - Primary LLM ($0.00025/1k tokens, 800ms latency)
- **GPT-4o** - Secondary LLM for quality-critical tasks
- **unstructured.io** - Document ingestion
- **sentence-transformers** - Voice similarity analysis

### Frontend

- **Next.js 14** - React framework
- **Zustand** (53.1k stars) - State management
- **Tiptap** (31.1k stars) - Rich text editor
- **TanStack Query** - Data fetching
- **Tailwind CSS + shadcn/ui** - Styling (ADR-0003)

### Backend

- **FastAPI 0.111** - Python web framework
- **PostgreSQL with pgvector** - Database
- **SQLAlchemy** - ORM
- **Celery with Redis** - Task queue
- **Typer** - CLI tool creation

### Infrastructure

- **AWS** - Cloud provider (Bedrock for LLMs)
- **Terraform** - Infrastructure as Code
- **Amazon ECS Fargate** - Container orchestration
- **GitHub Actions** - CI/CD
- **Docker** - Containerization

### Development

- **Ruff** - Python linting
- **ESLint** - JavaScript linting
- **pre-commit** - Git hooks
- **Poetry** - Python dependency management

## Key Design Decisions

### From ADR-0000

1.  **AWS as cloud provider** - For AWS Bedrock access and scalability
2.  **Token-based billing** - Usage-based pricing model
3.  **Multi-agent architecture** - Specialized agents for different tasks

### From ADR-0001

1.  **LangGraph over AutoGen/CrewAI** - Better control for iterative workflows
2.  **Rejected dramatiq** - LGPL license concerns
3.  **Rejected AutoGen** - Creative Commons license uncertainty

### From ADR-0002

1.  **ECS Fargate over EC2** - Zero ops overhead worth 20% premium
2.  **Fargate over Lambda** - Need long-running tasks (>15 min)
3.  **Fargate over EKS** - Simpler operations, faster time to market
4.  **Fargate Spot for workers** - 70% cost reduction

### From ADR-0003

1.  **Custom UI over templates** - AI-native features require custom components
2.  **Tailwind CSS + shadcn/ui** - Modern, accessible, customizable
3.  **No UI templates** - Full control over design and functionality

## Important Context

### User Personas (from PROJECT_CHARTER.md)

1.  **Sarah Chen** - Business author wanting productivity book from blog posts
2.  **Marcus Rodriguez** - Memoirist with 40 years of journals
3.  **Elena Petrov** - Fiction writer wanting series consistency
4.  **David Kim** - Academic compiling research into textbook

### Core KPIs

- Book length: ≥80 pages
- Voice similarity: ≥0.88 cosine similarity
- Generation time: <7 days per book
- User satisfaction: >90% approval rate

### Agent System Design

- **OrchestratorAgent** - Workflow coordination
- **PlannerAgent** - Book structure creation
- **ResearchAgent** - Source material retrieval
- **ChapterAgent** - Chapter drafting
- **CriticAgent** - Quality review
- **VoiceAgent** - Voice/tone matching
- **ConsistencyAgent** - Plot/timeline validation
- **SafetyAgent** - Content policy compliance

## AWS Infrastructure Details (Phase 3 & 4)

### Account Information

- **AWS Account ID**: 820242943150
- **Primary Region**: us-west-2
- **Terraform State**: s3://ghostline-terraform-state-820242943150

### Deployed Resources

| Resource Type  | Resource ID/Name                                 | Purpose                     |
| :------------- | :----------------------------------------------- | :-------------------------- |
| VPC            | vpc-00d75267879c8f631                            | Main network (10.0.0.0/16)  |
| S3 Bucket      | ghostline-dev-source-materials-820242943150      | Source material storage     |
| S3 Bucket      | ghostline-dev-outputs-820242943150               | Generated book storage      |
| S3 Bucket      | ghostline-dev-frontend-820242943150              | Static website hosting      |
| S3 Bucket      | ghostline-terraform-state-820242943150           | Terraform state             |
| DynamoDB Table | ghostline-terraform-locks                        | State locking               |
| WAF Web ACL    | 7529b94c-e8fe-4f43-9d35-cc3b87430d81             | Web application firewall    |
| KMS Keys       | 6 keys created                                   | Encryption for various services |
| RDS Instance   | ghostline-dev                                    | PostgreSQL 15.8 database    |
| Redis Cluster  | ghostline-dev                                    | ElastiCache Redis 7.0       |
| ECS Cluster    | ghostline-dev                                    | Container orchestration     |
| ALB            | ghostline-dev-main                               | Application load balancer   |
| CloudFront     | E3PE8KOGXI4I9Q                                   | CDN for frontend            |
| Route 53       | ghostline.ai                                     | DNS management              |
| ECR Repos      | ghostline-web, ghostline-api, ghostline-agents   | Docker image storage        |

### Security Services Enabled

- **AWS WAF**: Protecting ALB endpoints
- **GuardDuty**: Threat detection active
- **Security Hub**: Compliance monitoring
- **CloudTrail**: Audit logging
- **IAM Access Analyzer**: External access monitoring
- **Budget Alerts**: $500/month limit with service breakdowns

### Networking

- **Availability Zones**: us-west-2a, us-west-2b
- **Public Subnets**: 2 (for ALB)
- **Private Subnets**: 2 (for ECS/compute)
- **Database Subnets**: 2 (for RDS)
- **NAT Gateways**: 2 (one per AZ)
- **Internet Gateway**: 1

### Live URLs

- **Frontend**: https://dev.ghostline.ai (live)
- **API**: https://api.dev.ghostline.ai (deployed, needs database setup)
- **CloudFront**: https://d2thhts2eu7se8.cloudfront.net

## Auto-Deployment Configuration

### GitHub Actions Workflows

All repositories have auto-deployment configured:

1. **Web Repository** (`web/.github/workflows/deploy.yml`)
   - Triggers on push to main
   - Builds Next.js static site
   - Syncs to S3 bucket
   - Invalidates CloudFront cache

2. **API Repository** (`api/.github/workflows/deploy.yml`)
   - Triggers on push to main
   - Builds Docker image
   - Pushes to ECR
   - Updates ECS task definition
   - Rolling deployment to ECS service

3. **Agents Repository** (`agents/.github/workflows/deploy.yml`)
   - Triggers on push to main
   - Builds Docker image
   - Pushes to ECR
   - Updates worker task definition
   - Updates worker ECS service

### Required GitHub Secrets

All repositories need these secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## GitHub Details

- Organization: `ghostlineAI` (<https://github.com/ghostlineAI>)
- All repositories are private
- Markdown linting CI/CD configured
- CODEOWNERS set up for each repository
- Auto-deployment enabled for all repos

## Working Patterns

### File Organization

- Phase completion summaries go in `docs/` (e.g., PHASE_0_COMPLETE.md)
- Scripts for analysis go in `docs/scripts/`
- ADRs go in `docs/adr/` with format ADR-XXXX.md
- Each repository has its own README.md

### Development Flow

1.  Make changes locally in `ghostline/` directory
2.  Push to individual repos
3.  GitHub Actions automatically deploy changes

### Testing Approach

- Unit tests for individual components
- Integration tests for agent workflows
- Voice similarity evaluation suite
- Token usage monitoring

## Common Commands

```bash
# Run OSS capability scan
export GITHUB_TOKEN='your_token'
python ghostline/docs/scripts/oss_capability_scan.py

# AWS/Terraform commands
cd ghostline/infra
./setup-tools.sh              # Install AWS CLI and Terraform
./deploy.sh bootstrap         # Deploy state backend
./deploy.sh dev              # Deploy dev environment
terraform plan               # Preview changes
terraform apply             # Apply changes

# Deploy web manually
cd ghostline/infra
./deploy-web.sh

# Check ECS services
aws ecs describe-services --cluster ghostline-dev --services api --region us-west-2

# View logs
aws logs tail /ecs/ghostline-dev --region us-west-2
```

## Next Phase (Phase 5) Requirements

According to the project plan:

- Set up Alembic for database migrations
- Configure pgvector extension
- Create initial database schema
- Set up Redis for Celery
- Implement connection pooling
- Create seed data for testing

## Notes for Future LLMs

1.  **Always check `ghostline_phase_plan.txt`** for full project roadmap
2.  **Update this KNOWLEDGE.md** after completing significant work
3.  **Create ADRs** for architectural decisions
4.  **Maintain license compliance** - avoid AGPL/GPL libraries
5.  **Follow established patterns** - see existing code for examples
6.  **Test with real data** - use actual PDFs/documents when possible
7.  **Check GitHub Actions** for deployment status after pushes

## Recent Changes Log

### 2025-01-27 (Phase 4.6 - Database Setup)

- Created comprehensive database models:
  - User authentication and profiles
  - Projects, source materials, and chapters
  - Voice profiles with pgvector embeddings
  - Content chunks for vector search
  - Generation tasks for agent workflows
- Configured database infrastructure:
  - Set up SQLAlchemy with connection pooling
  - Configured Alembic for migrations
  - Added pgvector extension support
  - Created Celery configuration for background tasks
- Built deployment scripts:
  - Database initialization script for ECS
  - Task definition for running in VPC
  - Integration with existing infrastructure
- All database code pushed to GitHub repositories

### 2025-01-27 (Comprehensive Schema Implementation)

- Implemented full database schema based on detailed UX requirements:
  - **Users & Billing**: Added billing_plans, token_transactions, Cognito integration
  - **Projects**: Added forking support, book_outlines for hierarchical structure
  - **Content**: Enhanced source_materials with NOTE and VOICE_MEMO types
  - **Generation**: Added similarity scoring, token cost tracking
  - **Quality**: Created qa_findings for automated quality checks
  - **Export**: Added exported_books for multi-format outputs
  - **Notifications**: Built notification system for all channels
- Created comprehensive Alembic migration with:
  - All 15 tables with proper relationships
  - pgvector extension and indexes
  - Enum types for all status fields
  - Proper foreign key constraints
- Schema supports full UX flow:
  - Token-based billing with transparent tracking
  - Iterative chapter generation with feedback
  - Style consistency via voice profiles
  - Automated QA pipeline
  - Multi-format export with versioning

### 2025-01-27 (Phase 4 COMPLETE)

- Deployed full backend infrastructure:
  - RDS PostgreSQL and Redis deployed via Terraform
  - ECS cluster with API and worker services
  - ALB configured with SSL certificate
  - All services integrated and networked
- Set up auto-deployment for all repositories:
  - Created GitHub Actions workflows
  - Configured ECR image builds
  - ECS rolling deployments
- Frontend live at https://dev.ghostline.ai
- API infrastructure ready at https://api.dev.ghostline.ai
- All changes pushed to GitHub repositories

### 2025-01-26 (Phases 0-3 COMPLETE)

- Initial project setup complete
- Technology stack selected and documented
- All repositories pushed to GitHub
- OSS capability scan completed
- Architecture blueprint created with Mermaid diagrams
- Compute platform decision documented (ECS Fargate)
- AWS Landing Zone fully deployed with Terraform:
  - VPC with 6 subnets across 2 AZs
  - S3 buckets for materials and outputs
  - Security services (WAF, GuardDuty, CloudTrail)
  - Budget monitoring ($500/month)
  - All infrastructure operational
- Created comprehensive final review document
- Email notifications pending manual SNS confirmation

---

*Remember to update this document as the project evolves!* 