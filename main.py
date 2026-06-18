from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from extractor import extract_skills
from file_parser import parse_file
import os

app = FastAPI(title="Technical Skill Extractor")

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class TranscriptRequest(BaseModel):
    transcript: str


class SkillsResponse(BaseModel):
    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    cloud: list[str]
    skills: list[str]  # flat sorted union of all categories


@app.get("/")
def index():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.post("/upload", response_model=SkillsResponse)
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    transcript = parse_file(file.filename, content)
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="File appears to be empty")
    result = extract_skills(transcript)
    return SkillsResponse(**result)


@app.post("/extract", response_model=SkillsResponse)
def extract(request: TranscriptRequest):
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")
    result = extract_skills(request.transcript)
    return SkillsResponse(**result)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
