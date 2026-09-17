import hashlib
import json
from typing import Annotated
from fastapi import FastAPI, Header, Response

app = FastAPI()
body = json.dumps({"service": "catalogue", "version": 1}, sort_keys=True, separators=(",", ":")).encode()
etag = '"' + hashlib.sha256(body).hexdigest() + '"'

@app.get("/catalogue-info")
def catalogue_info(if_none_match: Annotated[str | None, Header()] = None):
    headers = {"ETag": etag, "Cache-Control": "public, max-age=60"}
    candidates = [value.strip().removeprefix("W/") for value in (if_none_match or "").split(",")]
    if "*" in candidates or etag in candidates:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)
