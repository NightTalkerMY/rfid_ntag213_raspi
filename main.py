import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from nfc_reader import NTAGReader

# Create a global placeholder for our hardware reader
nfc_hardware = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    global nfc_hardware
    print("========================================")
    print("Initializing Capstone NFC Hardware...")
    nfc_hardware = NTAGReader()
    print("Hardware Ready!")
    print("========================================")
    yield
    # --- Shutdown ---
    print("\nShutting down and cleaning up GPIO pins...")
    if nfc_hardware:
        nfc_hardware.cleanup()

# Initialize FastAPI with the lifespan manager
app = FastAPI(lifespan=lifespan)

@app.get("/scan")
def scan_rfid_tag():
    """
    Endpoint to check if a tag is present.
    If your frontend polls this endpoint, it gets instant JSON feedback.
    """
    data = nfc_hardware.get_tag_data()
    return data

if __name__ == "__main__":
    # This block allows you to run the file directly via 'python main.py'
    print("\nStarting Local API Server...")
    print("Test it here: http://127.0.0.1:8000/scan\n")
    
    # Run the uvicorn server programmatically
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)