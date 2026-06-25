from ett_gns_app.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ett_gns_app.main:app", host="0.0.0.0", port=5000, reload=False)
