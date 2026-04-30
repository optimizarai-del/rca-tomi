import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8010"))
    reload = os.getenv("RELOAD", "0") == "1"
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)
