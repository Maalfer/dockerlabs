import uvicorn

if __name__ == "__main__":
    uvicorn.run("asgi:application", host="0.0.0.0", port=5000, reload=True)
