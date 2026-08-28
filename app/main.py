from fastapi import FastAPI

app = FastAPI(
    title="Jira Analytics Tool API",
    description="Enterprise AI-PMO Platform",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Jira Analytics Tool API"}

@app.get("/health")
async def health():
    return {"status": "ok"}
