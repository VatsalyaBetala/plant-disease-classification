from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import List
import uuid
from src.inference import classify_plant, classify_disease

# Initialize FastAPI app
app = FastAPI()

# Global dictionary to store predictions (temporary, replace with a database in production)
PREDICTIONS = {}

# CORS Middleware (restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (uploaded images)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Ensure uploads directory exists
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Root endpoint - Serve homepage
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("views/index.html")

# Live view endpoint
@app.get("/live-view", response_class=HTMLResponse)
async def live_view():
    return FileResponse("views/live-view.html")

# Upload images page
@app.get("/upload-images", response_class=HTMLResponse)
async def image_view():
    return FileResponse("views/upload-images.html")

# View images page
@app.get("/view-images", response_class=HTMLResponse)
async def view_images():
    return FileResponse("views/view-images.html")

# Record video page
@app.get("/record-video", response_class=HTMLResponse)
async def record_video():
    return FileResponse("views/record-video.html")

# Upload files endpoint
@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    predictions = []
    for file in files:
        # Validate file type
        allowed_extensions = {"png", "jpg", "jpeg"}
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PNG, JPG, and JPEG are allowed.")

        # Generate unique filename
        unique_name = f"{uuid.uuid4()}.{file_ext}"
        file_location = f"uploads/{unique_name}"

        # Save the uploaded file to disk
        try:
            with open(file_location, "wb") as f:
                contents = await file.read()
                f.write(contents)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # Run the plant classification model
        try:
            plant_prediction = classify_plant(file_location)
            # Run the disease classification using the predicted plant type
            disease_prediction = classify_disease(file_location, plant_prediction)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Model inference failed: {str(e)}")

        # Store prediction
        pred = {
            "filename": unique_name,
            "plant": plant_prediction,
            "disease": disease_prediction
        }
        predictions.append(pred)
        PREDICTIONS[unique_name] = pred

    return {"message": "Files successfully uploaded", "predictions": predictions}

# Get uploaded images and their predictions
@app.get("/images")
async def get_images():
    files = os.listdir("uploads")
    results = []
    for file in files:
        pred = PREDICTIONS.get(file, {"plant": "", "disease": ""})
        results.append({
            "filename": file,
            "plant": pred.get("plant", ""),
            "disease": pred.get("disease", "")
        })
    return results

# Delete all uploaded images
@app.delete("/delete-images")
async def delete_images():
    try:
        files = os.listdir("uploads")
        for file in files:
            os.remove(f"uploads/{file}")
            if file in PREDICTIONS:
                del PREDICTIONS[file]
        return {"message": "All images deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete images: {str(e)}")

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)