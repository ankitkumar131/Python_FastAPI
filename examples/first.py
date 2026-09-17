from fastapi import FastAPI

app = FastAPI(title="Product school")

@app.get("/")
def home():
    return {"message": "Hello World"}
