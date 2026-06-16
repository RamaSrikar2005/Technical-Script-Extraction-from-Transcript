import os
import json
from concurrent.futures import ThreadPoolExecutor
from groq import Groq
from dotenv import load_dotenv
from dataset_matcher import match_from_dataset, merge

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a technical skill extractor specialized in parsing interview transcripts.

Extract ALL technical skills mentioned by the candidate, grouped into four categories:
- languages: Programming Languages (Python, JavaScript, Java, Go, Rust, C++, TypeScript, etc.)
- frameworks: Frameworks & Libraries (React, Django, FastAPI, Spring, TensorFlow, etc.)
- databases: Databases (PostgreSQL, MySQL, MongoDB, Redis, DynamoDB, etc.)
- cloud: Cloud Platforms & DevOps (AWS, GCP, Azure, Docker, Kubernetes, Terraform, etc.)

Rules:
- Fix misspellings: "Pthon" → "Python", "Reakt" → "React"
- Expand abbreviations: "JS" → "JavaScript", "k8s" → "Kubernetes", "GCP" → "Google Cloud"
- Canonical names: "Postgres" → "PostgreSQL", "Mongo" → "MongoDB"
- Deduplicate: include each skill only once
- Extract EVERY skill mentioned, including niche or uncommon ones
- Include only clearly technical skills

Return JSON with exactly these four keys: "languages", "frameworks", "databases", "cloud".
Each key maps to an array of normalized skill name strings (empty array if none found).
"""


def _llm_extract(transcript: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract all technical skills from this interview transcript:\n\n{transcript}",
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1024,
    )
    content = response.choices[0].message.content
    if not content:
        return {"languages": [], "frameworks": [], "databases": [], "cloud": []}
    data = json.loads(content)
    return {
        "languages": data.get("languages", []),
        "frameworks": data.get("frameworks", []),
        "databases": data.get("databases", []),
        "cloud": data.get("cloud", []),
    }


def extract_skills(transcript: str) -> dict:
    with ThreadPoolExecutor(max_workers=2) as executor:
        llm_future = executor.submit(_llm_extract, transcript)
        dataset_result = match_from_dataset(transcript)
        llm_result = llm_future.result()

    return merge(dataset_result, llm_result)
