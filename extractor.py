import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a precise technical skill extractor for interview transcripts.

Your job: extract ONLY the technical skills that are EXPLICITLY mentioned in the transcript. Do NOT infer, assume, or add skills that are not clearly stated.

Categorize into exactly four groups:
- languages: Programming languages (Python, JavaScript, Java, TypeScript, C++, Go, Rust, etc.)
- frameworks: Frameworks & libraries (React, Django, FastAPI, Spring Boot, TensorFlow, Express, etc.)
- databases: Databases & data stores (PostgreSQL, MySQL, MongoDB, Redis, DynamoDB, Elasticsearch, etc.)
- cloud: Cloud platforms & DevOps tools (AWS, GCP, Azure, Docker, Kubernetes, Terraform, CI/CD tools, etc.)

Strict rules:
1. Only include skills the speaker EXPLICITLY names — no guessing from context.
2. Normalize to the canonical name: "JS" → "JavaScript", "k8s" → "Kubernetes", "Postgres" → "PostgreSQL", "Mongo" → "MongoDB", "GCP" → "Google Cloud Platform".
3. Fix clear misspellings: "Pthon" → "Python", "Reakt" → "React".
4. Each skill appears in exactly ONE category, exactly ONCE. No duplicates across or within categories.
5. If a skill does not clearly belong to any category, omit it.

Return valid JSON with exactly these four keys: "languages", "frameworks", "databases", "cloud".
Each value is an array of canonical skill name strings. Use an empty array if none found."""


def _deduplicate(skills: list[str]) -> list[str]:
    seen = {}
    for s in skills:
        key = s.strip().lower()
        if key not in seen:
            seen[key] = s.strip()
    return sorted(seen.values())


def extract_skills(transcript: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract only the technical skills explicitly mentioned in this transcript:\n\n{transcript}",
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
        "languages": _deduplicate(data.get("languages", [])),
        "frameworks": _deduplicate(data.get("frameworks", [])),
        "databases": _deduplicate(data.get("databases", [])),
        "cloud": _deduplicate(data.get("cloud", [])),
    }
