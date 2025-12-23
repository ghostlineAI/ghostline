import os
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# --- Configuration ---

# To avoid rate limiting, you should use a GitHub Personal Access Token.
# Generate one here: https://github.com/settings/tokens
# And set it as an environment variable: export GITHUB_TOKEN='your_token_here'
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Warning: GITHUB_TOKEN environment variable not set. API requests may be rate-limited.")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

# List of open-source repositories to scan, categorized for clarity.
# Format: "owner/repo"
OSS_REPOS_TO_SCAN = {
    "Agentic Frameworks": [
        "langchain-ai/langgraph",
        "microsoft/autogen",
        "stanfordnlp/dspy",
        "run-llama/llama_index",
        "joaomdmoura/crewAI",
    ],
    "AI & Data Processing": [
        "Unstructured-IO/unstructured",
        "UKPLab/sentence-transformers",
        "zilliztech/gptcache",
        "langfuse/langfuse",
        "Bogdanp/dramatiq",
    ],
    "Frontend (Web)": [
        "pmndrs/zustand",
        "ueberdosis/tiptap",
        "TanStack/query",
    ],
    "Backend (API)": [
        "tiangolo/typer",
        "pydantic/pydantic-settings",
    ],
    "Developer Experience": [
        "pre-commit/pre-commit",
        "astral-sh/ruff",
        "eslint/eslint",
    ],
}

# --- Task 1.1: Scrape GitHub Data ---

def get_repo_data(repo_path: str) -> Optional[Dict[str, Any]]:
    """
    Fetches repository data from the GitHub API.
    """
    api_url = f"https://api.github.com/repos/{repo_path}"
    try:
        response = requests.get(api_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        license_name = (data.get("license") or {}).get("name", "N/A")
        last_commit_date = datetime.strptime(data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ").date()
        
        return {
            "name": data["name"],
            "category": "", # Will be filled in later
            "url": data["html_url"],
            "stars": data["stargazers_count"],
            "license": license_name,
            "last_commit": last_commit_date,
            "description": data["description"],
        }
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching data for {repo_path}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred for {repo_path}: {e}")
        return None

def calculate_fit_score(repo_data: Dict[str, Any]) -> float:
    """
    Calculates a 'fit score' based on license, activity, and popularity.
    This is a heuristic and can be adjusted based on project priorities.
    """
    score = 0
    
    # License check (higher score for permissive licenses)
    permissive_licenses = ["MIT", "Apache 2.0", "BSD"]
    if any(lic in repo_data["license"] for lic in permissive_licenses):
        score += 40
    elif "AGPL" in repo_data["license"] or "GPL" in repo_data["license"]:
        score -= 50 # Penalize viral licenses heavily
    
    # Last commit date (higher score for recent activity)
    days_since_commit = (datetime.now().date() - repo_data["last_commit"]).days
    if days_since_commit < 30:
        score += 30
    elif days_since_commit < 90:
        score += 15
    
    # Stars (higher score for more popular repos)
    if repo_data["stars"] > 10000:
        score += 30
    elif repo_data["stars"] > 1000:
        score += 15
        
    return max(0, min(100, score)) # Normalize score to 0-100

# --- Task 1.2: Benchmark LLMs (Placeholder) ---

def benchmark_llms() -> Dict[str, Dict[str, float]]:
    """
    Benchmarks LLMs for latency and cost for a 1-page draft.
    
    This is a placeholder function. In a real scenario, this would involve:
    1. Defining a standard 1-page draft prompt.
    2. Calling APIs for GPT-4o, Claude 3 Haiku, and Mixtral-8x22B.
    3. Measuring latency (time from request to full response).
    4. Calculating cost based on input/output tokens and provider pricing.
    """
    print("\n--- Benchmarking LLMs (Placeholder) ---")
    print("This is a simulated benchmark.")
    
    # Simulated data based on general knowledge of these models
    benchmark_results = {
        "GPT-4o": {"latency_ms": 1500, "cost_per_1k_tokens": 0.0075}, # Hypothetical blend of speed/cost
        "Claude 3 Haiku": {"latency_ms": 800, "cost_per_1k_tokens": 0.00025}, # Known for speed and low cost
        "Mixtral-8x22B": {"latency_ms": 2500, "cost_per_1k_tokens": 0.0007}, # Open model, latency can vary
    }
    
    print("Benchmark Results (Simulated):")
    for model, data in benchmark_results.items():
        print(f"  - {model}: Latency={data['latency_ms']}ms, Cost=${data['cost_per_1k_tokens']}/1k tokens")
        
    return benchmark_results

# --- Task 1.3: Generate CSV Report ---

def generate_csv_report(all_repo_data: List[Dict[str, Any]], output_path: str):
    """
    Generates a CSV report from the scraped and calculated data.
    """
    if not all_repo_data:
        print("No repository data to generate report.")
        return
        
    df = pd.DataFrame(all_repo_data)
    
    # Add benchmark data to the dataframe
    # For this exercise, we will add the benchmark data to the agentic frameworks
    benchmarks = benchmark_llms()
    
    # Create rows for each model and add them to the dataframe
    model_rows = []
    for model_name, data in benchmarks.items():
        model_rows.append({
            "category": "Language Model",
            "name": model_name,
            "license": "Proprietary",
            "stars": "N/A",
            "last_commit": "N/A",
            "fit_score": "N/A",
            "latency_ms": data['latency_ms'],
            "cost_per_1k_tokens": data['cost_per_1k_tokens'],
            "url": "N/A",
            "description": f"Benchmark data for {model_name}"
        })

    # Combine the two dataframes
    df_models = pd.DataFrame(model_rows)
    df_combined = pd.concat([df, pd.DataFrame(model_rows)], ignore_index=True)


    # Reorder columns for clarity
    column_order = [
        "category", "name", "license", "stars", "last_commit", "fit_score", 
        "latency_ms", "cost_per_1k_tokens", "url", "description"
    ]
    # Create any missing columns with NA
    for col in column_order:
        if col not in df_combined.columns:
            df_combined[col] = "N/A"

    df_combined = df_combined[column_order]
    
    df_combined.to_csv(output_path, index=False)
    print(f"\nSuccessfully generated OSS capability scan report at: {output_path}")


def run_oss_scan():
    """
    Main function to run the open-source capability scan.
    """
    print("--- Starting Phase 1: Open-Source Capability Scan ---")
    
    # Task 1.1
    print("\n--- Scraping GitHub for repository data (Task 1.1) ---")
    all_repo_data = []
    for category, repos in OSS_REPOS_TO_SCAN.items():
        print(f"\nScanning category: {category}")
        for repo_path in repos:
            data = get_repo_data(repo_path)
            if data:
                data["category"] = category
                data["fit_score"] = calculate_fit_score(data)
                # Initialize benchmark columns
                data["latency_ms"] = "N/A"
                data["cost_per_1k_tokens"] = "N/A"
                all_repo_data.append(data)
                print(f"  - Fetched: {repo_path} (Stars: {data['stars']}, License: {data['license']})")

    # Task 1.2 & 1.3
    output_dir = "ghostline/docs"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "oss_scan.csv")
    generate_csv_report(all_repo_data, output_path)

if __name__ == "__main__":
    run_oss_scan()
