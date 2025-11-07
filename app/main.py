from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from storage import save_file, get_file

app = FastAPI(title="Object Storage API", version="1.0.0", description="API for uploading and downloading files.")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify frontend domains
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],  # Or ["Content-Type"]
)




@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), folder: str = ""):
    print(file.filename)
    file_id = save_file(file, folder)
    return {"file_id": file_id, "folder": folder}



@app.get("/download/{file_id}")
async def download_file(file_id: str, folder: str = ""):
    file_path = get_file(file_id, folder)

    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@app.get("/")
async def root():
    return {"message": "Welcome to the Object Storage API!"}


if __name__ == "__main__":
    import uvicorn
    #uvicorn.run(app, host="127.0.0.1", port=8001)
    uvicorn.run(app, host="0.0.0.0", port=8001)
