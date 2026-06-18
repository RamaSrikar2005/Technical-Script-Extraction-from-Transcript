import os
import json
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
from dotenv import load_dotenv
from dataset_matcher import match_from_dataset, merge

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a precise technical skill extractor for interview transcripts.

Extract ALL technical skills that are EXPLICITLY mentioned. Fix misspellings and expand abbreviations to canonical names.

Output four JSON keys:
- "languages"  : Programming languages
- "frameworks" : Frameworks, libraries, tools (including data science libs like Pandas, NumPy, Matplotlib)
- "databases"  : Databases and data stores
- "cloud"      : Cloud platforms, DevOps, CI/CD, monitoring tools

Normalization rules:
- JS → JavaScript, TS → TypeScript, py → Python
- k8s → Kubernetes, GCP → Google Cloud Platform, AWS → AWS
- Postgres / PG → PostgreSQL, Mongo → MongoDB, MS SQL → SQL Server
- Tailwind → Tailwind CSS, sklearn → Scikit-learn
- Fix typos: "Pthon" → Python, "Reakt" → React, "Djnago" → Django, "Panads" → Pandas, "Numyp" → NumPy

Rules:
1. Each skill appears in exactly ONE category, exactly ONCE.
2. Pandas, NumPy, SciPy, Matplotlib, Seaborn, Plotly → frameworks (libraries).
3. Only omit a skill if it genuinely does not fit any category.
4. Return empty array [] if nothing found in a category.

--- EXAMPLES ---

Transcript: "I mostly write JS and TS, deploy on GCP with k8s, store data in Postgres and Mongo."
Output: {"languages":["JavaScript","TypeScript"],"frameworks":[],"databases":["MongoDB","PostgreSQL"],"cloud":["Google Cloud Platform","Kubernetes"]}

Transcript: "I use Pthon for data science with Panads, Numyp, and Scikit-learn. Models trained in TensorFlow."
Output: {"languages":["Python"],"frameworks":["NumPy","Pandas","Scikit-learn","TensorFlow"],"databases":[],"cloud":[]}

Transcript: "Our stack is Java with Spring Boot, MySQL for the primary DB, Redis for caching, Jenkins on Azure for CI/CD."
Output: {"languages":["Java"],"frameworks":["Spring Boot"],"databases":["MySQL","Redis"],"cloud":["Azure","Jenkins"]}

Transcript: "Frontend is React with TypeScript and Tailwind CSS. State managed by Redux. Backend is Node.js with Express."
Output: {"languages":["JavaScript","TypeScript"],"frameworks":["Express","Node.js","React","Redux","Tailwind CSS"],"databases":[],"cloud":[]}

Transcript: "We containerize with Docker, orchestrate on Kubernetes, provision infra via Terraform, monitor using Prometheus and Grafana."
Output: {"languages":[],"frameworks":[],"databases":[],"cloud":["Docker","Grafana","Kubernetes","Prometheus","Terraform"]}

--- END EXAMPLES ---

Return valid JSON with exactly these four keys: "languages", "frameworks", "databases", "cloud"."""


def _deduplicate(skills: list[str]) -> list[str]:
    seen = {}
    for s in skills:
        key = s.strip().lower()
        if key not in seen:
            seen[key] = s.strip()
    return sorted(seen.values())


def _llm_extract(transcript: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract all technical skills explicitly mentioned in this transcript:\n\n{transcript}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=1024,
    )
    content = response.choices[0].message.content
    if not content:
        return {"languages": [], "frameworks": [], "databases": [], "cloud": []}

    data = json.loads(content)
    return {
        "languages":  _deduplicate(data.get("languages",  [])),
        "frameworks": _deduplicate(data.get("frameworks", [])),
        "databases":  _deduplicate(data.get("databases",  [])),
        "cloud":      _deduplicate(data.get("cloud",      [])),
    }


def extract_skills(transcript: str) -> dict:
    # Run LLM and dataset matcher in parallel, then merge
    with ThreadPoolExecutor(max_workers=2) as executor:
        llm_future     = executor.submit(_llm_extract, transcript)
        dataset_result = match_from_dataset(transcript)
        llm_result     = llm_future.result()

    combined = merge(dataset_result, llm_result)

    # Deduplicate each category after merge
    for cat in combined:
        combined[cat] = _deduplicate(combined[cat])

    combined["skills"] = sorted(
        combined["languages"] + combined["frameworks"] +
        combined["databases"] + combined["cloud"]
    )
    return combined
