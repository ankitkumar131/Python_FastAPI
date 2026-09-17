from fastapi import FastAPI
app = FastAPI()
@app.get("/products")
def products():
    return ["Notebook", "Pen", "Pencil"]
