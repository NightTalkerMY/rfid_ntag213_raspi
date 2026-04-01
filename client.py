import requests
import sys

# CHANGE THIS TO YOUR PI'S IP ADDRESS
API_URL = "http://127.0.0.1:8000/scan"

print("Sending scan request to Raspberry Pi...")
print("Waiting up to 10 seconds for a tag to be scanned...")

try:
    # Set timeout to 12s to give the server's 10s loop time to finish and respond
    response = requests.get(API_URL, timeout=12)
    data = response.json()
    
    if data.get("status") == "success":
        records = data.get("records", [])
        
        if records:
            print("\n--- Records Retrieved ---")
            for record in records:
                print(record)
        else:
            print("\nTag detected, but it contains no text records.")
            
    elif data.get("status") == "timeout":
        print("\nServer Timeout: No tag was presented within 10 seconds.")
        
    else:
        print(f"\nRead Error: Please try scanning again.")

except requests.exceptions.ReadTimeout:
    print("\nError: The client timed out before the server responded.")
except requests.exceptions.ConnectionError:
    print("\nError: Could not connect to the Raspberry Pi. Is main.py running?")

# Client terminates immediately after the single request is handled
sys.exit(0)