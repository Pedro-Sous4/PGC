from fastapi import FastAPI

app = FastAPI(title="FastAPI Test App")

@app.get("/")
def read_root():
    return {"message": "FastAPI Test App", "status": "working"}