from extractor import extract_skills

transcripts = [
    # Happy path
    (
        "Golden path",
        "I've been working with Python and Django for backend services, React on the frontend, "
        "and we deploy everything on AWS using Docker and Kubernetes.",
    ),
    # Misspellings
    (
        "Misspellings",
        "I know Pthon quite well and have used Reakt for a couple of projects. "
        "Also familiar with Djnago and Postgressql.",
    ),
    # Abbreviations & aliases
    (
        "Aliases & abbreviations",
        "I mostly write in JS and TS, store data in Postgres and Mongo, "
        "and run everything on GCP with k8s.",
    ),
    # Mixed categories
    (
        "Mixed categories",
        "Our stack is Java with Spring Boot, MySQL for the primary DB, "
        "Redis for caching, and we use Jenkins on Azure for CI/CD.",
    ),
]

for label, text in transcripts:
    result = extract_skills(text)
    print(f"[{label}]")
    print(f"  Input      : {text[:80]}...")
    print(f"  Languages  : {result['languages']}")
    print(f"  Frameworks : {result['frameworks']}")
    print(f"  Databases  : {result['databases']}")
    print(f"  Cloud      : {result['cloud']}")
    print()
