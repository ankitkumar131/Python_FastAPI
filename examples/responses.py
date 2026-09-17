from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI()

class PublicUser(BaseModel):
    id: int
    name: str

class OutOfStock(Exception):
    pass

@app.exception_handler(OutOfStock)
async def out_of_stock_handler(request: Request, error: OutOfStock):
    return JSONResponse(status_code=409, content={"detail": "Insufficient stock"})

@app.get("/users/{user_id}", response_model=PublicUser)
def get_user(user_id: int):
    if user_id != 1:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": 1, "name": "Asha", "password_hash": "never-public"}

@app.delete("/users/{user_id}", status_code=204, response_class=Response)
def delete_user(user_id: int):
    return Response(status_code=204)

@app.get("/stock/{quantity}")
def stock(quantity: int):
    if quantity > 5:
        raise OutOfStock()
    return {"available": True}

@app.get("/health", response_class=PlainTextResponse)
def health():
    return "ok"

@app.get("/old-users", include_in_schema=False)
def old_users():
    return RedirectResponse("/users/1", status_code=307)
