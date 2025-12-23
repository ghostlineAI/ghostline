---
Last Updated: 2025-06-28 09:30:52 PDT
---

# GhostLine GitHub Workflow & Setup Guide

This document outlines the standard GitHub workflow, repository setup, and CI/CD process for the GhostLine project.

## 1. Repository Structure

The project is organized into a multi-repository structure under the [ghostlineAI GitHub Organization](https://github.com/ghostlineAI).

-   `web`: Frontend Next.js application.
-   `api`: Backend FastAPI service.
-   `agents`: Python system for AI agent orchestration (LangGraph).
-   `infra`: Terraform code for all AWS infrastructure.
-   `docs`: Centralized project documentation.

## 2. Standard Workflow

1.  **Create a Feature Branch**: All work should be done on a feature branch, e.g., `feature/add-user-authentication`.
2.  **Open a Pull Request (PR)**: Once the feature is complete, open a PR against the `main` branch of the respective repository. Use the provided PR template to describe the changes.
3.  **CI Checks**: Automated CI checks will run via GitHub Actions. These include linting, type-checking, testing, and build validation. All checks must pass.
4.  **Code Review**: At least one other developer must review and approve the PR.
5.  **Merge to `main`**: Once approved and all checks pass, the PR can be merged into `main`.

## 3. Continuous Deployment (CI/CD)

**Merging a PR to the `main` branch automatically triggers a deployment to the `dev` environment.**

-   **Frontend (`web`)**: Deploys to S3 and invalidates the CloudFront cache. Live at `https://dev.ghostline.ai`.
-   **Backend (`api`)**: Builds a Docker image, pushes it to ECR, and triggers a rolling update of the ECS service. Live at `https://api.dev.ghostline.ai`.
-   **Agents (`agents`)**: Builds a Docker image, pushes it to ECR, and updates the ECS worker service definition.

### GitHub Secrets for Deployment

To enable deployments, the following secrets must be configured in the "Actions" settings for **each repository**:

-   `AWS_ACCESS_KEY_ID`: An AWS IAM access key with permissions to deploy.
-   `AWS_SECRET_ACCESS_KEY`: The corresponding secret key.
-   `AWS_REGION`: The AWS region, typically `us-west-2`.

These secrets are used by the GitHub Actions workflows to authenticate with AWS and manage resources.

## 4. CODEOWNERS

Each repository has a `CODEOWNERS` file to automatically assign PR reviewers. Please keep this file updated as team responsibilities change.

---
*This guide provides the essential information for contributing to the GhostLine project. Adhering to these standards ensures code quality and a smooth development process.* 