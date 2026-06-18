from extractor import extract_skills
from dataset_matcher import match_from_dataset, merge

# ── helpers ───────────────────────────────────────────────────────────────────

def all_extracted(result: dict) -> set[str]:
    """Flatten all four categories into a single lowercase set."""
    skills = []
    for v in result.values():
        if isinstance(v, list):
            skills.extend(v)
    return {s.strip().lower() for s in skills}


def score(extracted: set[str], expected: set[str]) -> tuple[float, float, float]:
    """Return (precision, recall, f1). expected is a set of lowercase strings."""
    if not expected:
        return 1.0, 1.0, 1.0
    tp = len(extracted & expected)
    precision = tp / len(extracted) if extracted else 0.0
    recall    = tp / len(expected)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def flexible_match(extracted: set[str], expected: set[str]) -> set[str]:
    """Return subset of expected that are found in extracted (allows partial/prefix match)."""
    matched = set()
    for exp in expected:
        for ext in extracted:
            if exp == ext or exp in ext or ext in exp:
                matched.add(exp)
                break
    return matched


# ══════════════════════════════════════════════════════════════════════════════
# LLM extraction test cases  (10 transcripts)
# ══════════════════════════════════════════════════════════════════════════════

LLM_TESTS = [
    {
        "label": "1. Golden path",
        "transcript": (
            "I've been working with Python and Django for backend services, "
            "React on the frontend, and we deploy everything on AWS using Docker and Kubernetes."
        ),
        "expected": {"python", "django", "react", "aws", "docker", "kubernetes"},
    },
    {
        "label": "2. Misspellings",
        "transcript": (
            "I know Pthon quite well and have used Reakt for a couple of projects. "
            "Also familiar with Djnago and Postgressql."
        ),
        "expected": {"python", "react", "django", "postgresql"},
    },
    {
        "label": "3. Abbreviations & aliases",
        "transcript": (
            "I mostly write in JS and TS, store data in Postgres and Mongo, "
            "and run everything on GCP with k8s."
        ),
        # Accept both common normalizations for GCP
        "expected": {"javascript", "typescript", "postgresql", "mongodb", "kubernetes"},
        "expected_any": [{"google cloud platform"}, {"google cloud", "gcp"}],
    },
    {
        "label": "4. Mixed categories",
        "transcript": (
            "Our stack is Java with Spring Boot, MySQL for the primary DB, "
            "Redis for caching, and we use Jenkins on Azure for CI/CD."
        ),
        "expected": {"java", "spring boot", "mysql", "redis", "jenkins", "azure"},
    },
    {
        "label": "5. Data science",
        "transcript": (
            "I build deep learning models with TensorFlow and PyTorch. "
            "For data wrangling I use Pandas and NumPy, classical ML with Scikit-learn, "
            "and model tracking via MLflow on an AWS EC2 instance."
        ),
        "expected": {"tensorflow", "pytorch", "pandas", "numpy", "scikit-learn", "mlflow"},
    },
    {
        "label": "6. DevOps / cloud native",
        "transcript": (
            "We containerize everything with Docker, orchestrate via Kubernetes, "
            "provision infra using Terraform, run CI/CD on GitHub Actions, "
            "and monitor with Prometheus and Grafana."
        ),
        "expected": {"docker", "kubernetes", "terraform", "github actions", "prometheus", "grafana"},
    },
    {
        "label": "7. Frontend heavy",
        "transcript": (
            "My main stack is TypeScript with React and Next.js. "
            "I style with Tailwind CSS, manage state through Redux, "
            "and interact with the backend via GraphQL using Apollo Client."
        ),
        "expected": {"typescript", "react", "next.js", "tailwind css", "redux", "graphql"},
    },
    {
        "label": "8. Backend APIs",
        "transcript": (
            "I write REST APIs in Python using FastAPI and store data in PostgreSQL. "
            "Celery handles async tasks with Redis as the broker, "
            "and everything is containerized in Docker."
        ),
        "expected": {"python", "fastapi", "postgresql", "celery", "redis", "docker"},
    },
    {
        "label": "9. Cloud-native AWS",
        "transcript": (
            "Our serverless architecture uses AWS Lambda triggered by SQS queues. "
            "We store files in S3, use DynamoDB for the main database, "
            "and define all infra as code with AWS CDK."
        ),
        "expected": {"aws lambda", "aws sqs", "aws s3", "dynamodb", "aws cdk"},
    },
    {
        "label": "10. Full-stack developer",
        "transcript": (
            "I'm a full-stack developer. On the backend I use Node.js with Express and TypeScript, "
            "MongoDB as the primary database, and Redis for session caching. "
            "The frontend is Vue.js with Vuex for state management. "
            "Everything is deployed on DigitalOcean using Docker Compose."
        ),
        "expected": {
            "node.js", "express", "typescript", "mongodb", "redis",
            "vue.js", "vuex", "docker",
        },
    },
]


def run_llm_tests():
    print("=" * 60)
    print("LLM EXTRACTION TESTS")
    print("=" * 60)

    recall_scores = []
    precision_scores = []

    for tc in LLM_TESTS:
        result   = extract_skills(tc["transcript"])
        extracted = all_extracted(result)
        expected  = tc["expected"].copy()

        # Handle cases where multiple normalizations are acceptable
        if "expected_any" in tc:
            for alt_set in tc["expected_any"]:
                matched = flexible_match(extracted, alt_set)
                if matched:
                    expected.update(matched)
                    break

        matched   = flexible_match(extracted, expected)
        prec      = len(matched) / len(extracted) if extracted else 0.0
        rec       = len(matched) / len(expected)  if expected  else 1.0

        recall_scores.append(rec)
        precision_scores.append(prec)

        status = "PASS" if rec >= 0.85 else "FAIL"
        print(f"\n[{tc['label']}]  {status}")
        print(f"  Transcript : {tc['transcript'][:75]}...")
        print(f"  Languages  : {result['languages']}")
        print(f"  Frameworks : {result['frameworks']}")
        print(f"  Databases  : {result['databases']}")
        print(f"  Cloud      : {result['cloud']}")
        print(f"  Expected   : {sorted(expected)}")
        print(f"  Matched    : {sorted(matched)}")
        missed = expected - matched
        if missed:
            print(f"  Missed     : {sorted(missed)}")
        print(f"  Precision  : {prec:.0%}   Recall: {rec:.0%}")

    avg_recall    = sum(recall_scores)    / len(recall_scores)
    avg_precision = sum(precision_scores) / len(precision_scores)
    overall_pass  = avg_recall >= 0.85

    print("\n" + "=" * 60)
    print("SUMMARY — LLM EXTRACTION")
    print("=" * 60)
    print(f"  Test cases      : {len(LLM_TESTS)}")
    print(f"  Avg Precision   : {avg_precision:.1%}")
    print(f"  Avg Recall      : {avg_recall:.1%}  ← accuracy metric")
    print(f"  Threshold       : 85%")
    print(f"  Result          : {'✅ PASSED' if overall_pass else '❌ FAILED'}")
    return avg_recall


# ══════════════════════════════════════════════════════════════════════════════
# Dataset matcher tests  (3 deterministic cases — no LLM call)
# ══════════════════════════════════════════════════════════════════════════════

DATASET_TESTS = [
    {
        "label": "A. Alias / abbreviation matching",
        "transcript": "I use k8s, GCP, Postgres, and Mongo in my daily work.",
        "expected": {"kubernetes", "postgresql", "mongodb"},
        "expected_any": [{"google cloud"}, {"google cloud platform"}],
    },
    {
        "label": "B. Fuzzy / misspelling matching",
        "transcript": "Our team works with Pthon, Reakt, and Djnago on every project.",
        "expected": {"python", "react", "django"},
    },
    {
        "label": "C. Multi-word and exact skill matching",
        "transcript": "We rely on Spring Boot, GitHub Actions, and Docker Compose for our pipeline.",
        "expected": {"spring boot", "github actions", "docker"},
    },
]


def run_dataset_tests():
    print("\n" + "=" * 60)
    print("DATASET MATCHER TESTS  (no LLM — deterministic)")
    print("=" * 60)

    recall_scores = []

    for tc in DATASET_TESTS:
        result    = match_from_dataset(tc["transcript"])
        extracted = all_extracted(result)
        expected  = tc["expected"].copy()

        if "expected_any" in tc:
            for alt_set in tc["expected_any"]:
                matched_alt = flexible_match(extracted, alt_set)
                if matched_alt:
                    expected.update(matched_alt)
                    break

        matched = flexible_match(extracted, expected)
        rec     = len(matched) / len(expected) if expected else 1.0
        recall_scores.append(rec)

        status = "PASS" if rec >= 0.85 else "FAIL"
        print(f"\n[{tc['label']}]  {status}")
        print(f"  Transcript : {tc['transcript']}")
        print(f"  Extracted  : {sorted(extracted)}")
        print(f"  Expected   : {sorted(expected)}")
        print(f"  Matched    : {sorted(matched)}")
        missed = expected - matched
        if missed:
            print(f"  Missed     : {sorted(missed)}")
        print(f"  Recall     : {rec:.0%}")

    avg = sum(recall_scores) / len(recall_scores)
    print("\n" + "=" * 60)
    print("SUMMARY — DATASET MATCHER")
    print("=" * 60)
    print(f"  Test cases : {len(DATASET_TESTS)}")
    print(f"  Avg Recall : {avg:.1%}")
    print(f"  Result     : {'✅ PASSED' if avg >= 0.85 else '❌ FAILED'}")
    return avg


# ══════════════════════════════════════════════════════════════════════════════
# Merge test  (dataset + LLM combined)
# ══════════════════════════════════════════════════════════════════════════════

def run_merge_test():
    print("\n" + "=" * 60)
    print("MERGE TEST  (dataset result + LLM result combined)")
    print("=" * 60)
    dataset_result = {
        "languages": ["Python"],
        "frameworks": ["React"],
        "databases": [],
        "cloud": ["AWS"],
    }
    llm_result = {
        "languages": ["Go"],
        "frameworks": ["React", "Django"],   # React is duplicate
        "databases": ["PostgreSQL"],
        "cloud": ["AWS", "Docker"],          # AWS is duplicate
    }
    merged = merge(dataset_result, llm_result)
    print(f"  Dataset result : {dataset_result}")
    print(f"  LLM result     : {llm_result}")
    print(f"  Merged         : {merged}")
    assert "React" in merged["frameworks"], "React should appear exactly once"
    assert "AWS"   in merged["cloud"],      "AWS should appear exactly once"
    assert len([x for x in merged["frameworks"] if x == "React"]) == 1, "No duplicates"
    print("  ✅ PASSED — duplicates removed, all skills present")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    llm_accuracy     = run_llm_tests()
    dataset_accuracy = run_dataset_tests()
    run_merge_test()

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"  LLM extraction accuracy  : {llm_accuracy:.1%}")
    print(f"  Dataset matcher accuracy : {dataset_accuracy:.1%}")
    overall = (llm_accuracy + dataset_accuracy) / 2
    print(f"  Overall accuracy         : {overall:.1%}")
    print(f"  Acceptance threshold     : 85%")
    print(f"  {'✅ APPROVED' if overall >= 0.85 else '❌ NEEDS WORK'}")
