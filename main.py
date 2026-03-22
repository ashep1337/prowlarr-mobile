import shutil
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config

app = FastAPI(title="Prowlarr Mobile")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------------------------------------------------------------------
# qBittorrent session management
# ---------------------------------------------------------------------------
qbt_cookie: str | None = None


async def qbt_login() -> str:
    """Authenticate with qBittorrent and return the SID cookie."""
    global qbt_cookie
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{config.QBITTORRENT_URL}/api/v2/auth/login",
            data={
                "username": config.QBITTORRENT_USERNAME,
                "password": config.QBITTORRENT_PASSWORD,
            },
        )
        resp.raise_for_status()
        sid = resp.cookies.get("SID")
        if sid:
            qbt_cookie = sid
            return sid
    raise RuntimeError("Failed to authenticate with qBittorrent")


async def qbt_request(method: str, path: str, **kwargs) -> httpx.Response:
    """Make an authenticated request to qBittorrent, re-logging in if needed."""
    global qbt_cookie
    if qbt_cookie is None:
        await qbt_login()

    url = f"{config.QBITTORRENT_URL}{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, url, cookies={"SID": qbt_cookie}, **kwargs
        )
        if resp.status_code == 403:
            await qbt_login()
            resp = await client.request(
                method, url, cookies={"SID": qbt_cookie}, **kwargs
            )
        return resp


# ---------------------------------------------------------------------------
# Prowlarr helpers
# ---------------------------------------------------------------------------
def prowlarr_headers() -> dict:
    return {"X-Api-Key": config.PROWLARR_API_KEY}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------------------------------------------------------
# Prowlarr endpoints
# ---------------------------------------------------------------------------
@app.get("/api/search")
async def search(query: str = Query(...), indexer_ids: str = Query(default="")):
    """Search Prowlarr indexers."""
    params: dict = {"query": query, "type": "search"}
    if indexer_ids:
        params["indexerIds"] = [int(i) for i in indexer_ids.split(",")]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            f"{config.PROWLARR_URL}/api/v1/search",
            headers=prowlarr_headers(),
            params=params,
        )
        resp.raise_for_status()
        results = resp.json()

    simplified = []
    for r in results:
        simplified.append({
            "title": r.get("title", ""),
            "size": r.get("size", 0),
            "seeders": r.get("seeders", 0),
            "leechers": r.get("leechers", 0),
            "indexer": r.get("indexer", ""),
            "downloadUrl": r.get("downloadUrl", ""),
            "magnetUrl": r.get("magnetUrl", ""),
            "infoUrl": r.get("infoUrl", ""),
            "categories": [c.get("name", "") for c in r.get("categories", [])],
        })

    simplified.sort(key=lambda x: x["seeders"], reverse=True)
    return JSONResponse(simplified)


@app.get("/api/indexers")
async def indexers():
    """List configured Prowlarr indexers."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.PROWLARR_URL}/api/v1/indexer",
            headers=prowlarr_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    return JSONResponse([
        {"id": idx["id"], "name": idx["name"], "enable": idx.get("enable", True)}
        for idx in data
    ])


# ---------------------------------------------------------------------------
# qBittorrent endpoints
# ---------------------------------------------------------------------------
@app.get("/api/torrents")
async def torrents():
    """List all torrents in qBittorrent."""
    resp = await qbt_request("GET", "/api/v2/torrents/info")
    resp.raise_for_status()
    data = resp.json()

    simplified = []
    for t in data:
        simplified.append({
            "hash": t["hash"],
            "name": t["name"],
            "size": t["size"],
            "progress": t["progress"],
            "dlspeed": t["dlspeed"],
            "upspeed": t["upspeed"],
            "state": t["state"],
            "eta": t.get("eta", 0),
            "ratio": t.get("ratio", 0),
            "added_on": t.get("added_on", 0),
            "num_seeds": t.get("num_seeds", 0),
            "num_leechs": t.get("num_leechs", 0),
        })

    return JSONResponse(simplified)


@app.post("/api/torrents/add")
async def add_torrent(request: Request):
    """Add a torrent to qBittorrent via magnet or download URL."""
    body = await request.json()
    url = body.get("magnetUrl") or body.get("downloadUrl")
    if not url:
        return JSONResponse({"error": "No URL provided"}, status_code=400)

    resp = await qbt_request(
        "POST",
        "/api/v2/torrents/add",
        data={"urls": url},
    )
    if resp.status_code == 200 and resp.text == "Ok.":
        return JSONResponse({"status": "ok"})
    return JSONResponse({"error": resp.text}, status_code=resp.status_code)


@app.post("/api/torrents/pause")
async def pause_torrent(request: Request):
    body = await request.json()
    resp = await qbt_request(
        "POST", "/api/v2/torrents/pause", data={"hashes": body["hash"]}
    )
    return JSONResponse({"status": "ok"} if resp.status_code == 200 else {"error": resp.text})


@app.post("/api/torrents/resume")
async def resume_torrent(request: Request):
    body = await request.json()
    resp = await qbt_request(
        "POST", "/api/v2/torrents/resume", data={"hashes": body["hash"]}
    )
    return JSONResponse({"status": "ok"} if resp.status_code == 200 else {"error": resp.text})


@app.post("/api/torrents/delete")
async def delete_torrent(request: Request):
    body = await request.json()
    resp = await qbt_request(
        "POST",
        "/api/v2/torrents/delete",
        data={
            "hashes": body["hash"],
            "deleteFiles": str(body.get("deleteFiles", False)).lower(),
        },
    )
    return JSONResponse({"status": "ok"} if resp.status_code == 200 else {"error": resp.text})


# ---------------------------------------------------------------------------
# File management
# ---------------------------------------------------------------------------
@app.post("/api/files/move")
async def move_files(request: Request):
    """Move completed downloads to Movies or TV Shows folder."""
    body = await request.json()
    media_type = body.get("type")
    if media_type not in ("movie", "show"):
        return JSONResponse({"error": "Invalid type. Use 'movie' or 'show'."}, status_code=400)

    dest = Path(config.MOVIES_DIR) if media_type == "movie" else Path(config.TV_SHOWS_DIR)
    src = Path(config.TORRENTS_DIR)

    if not src.exists():
        return JSONResponse({"error": "Torrents directory not found"}, status_code=404)

    items = list(src.iterdir())
    if not items:
        return JSONResponse({"error": "No files to move"}, status_code=400)

    dest.mkdir(parents=True, exist_ok=True)
    moved = 0
    errors = []
    for item in items:
        try:
            shutil.move(str(item), str(dest / item.name))
            moved += 1
        except Exception as e:
            errors.append(f"{item.name}: {e}")

    if errors:
        return JSONResponse({"status": "partial", "moved": moved, "errors": errors})
    return JSONResponse({"status": "ok", "moved": moved})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
