import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from nfc_reader import NTAGReader

nfc_hardware = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global nfc_hardware
    print("========================================")
    print("Initializing Capstone NFC Hardware...")
    nfc_hardware = NTAGReader()
    print("Hardware Ready!")
    print("========================================")
    yield
    print("\nShutting down and cleaning up GPIO pins...")
    if nfc_hardware:
        nfc_hardware.cleanup()

app = FastAPI(lifespan=lifespan)

# Allow all frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/scan")
def scan_rfid_tag():
    """
    When hit, this endpoint will block for up to 10 seconds 
    waiting for the hardware to find a tag.
    """
    # The timeout defaults to 10 seconds in the class method
    data = nfc_hardware.get_tag_data(timeout_seconds=10.0)
    return data

if __name__ == "__main__":
    print("\nStarting Local API Server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)