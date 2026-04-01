import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time 

# Initialize the base reader, completely bypassing the limited "Simple" wrapper
reader = MFRC522()

def get_crc(data):
    """Safely handles the CRC calculation, accounting for a known typo in the standard library."""
    try:
        return reader.CalulateCRC(data)
    except AttributeError:
        return reader.CalculateCRC(data)

def select_ntag_7byte():
    """
    Handles the 2-step Cascade Level 2 handshake. 
    Required to fully wake up 7-byte NTAGs so they accept read/write commands.
    """
    # 1. Scan for cards in the magnetic field
    (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
    if status != reader.MI_OK:
        return False, None
        
    # 2. Anticollision - Cascade Level 1 (Ask for the first part of the ID)
    (status, uid_1) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        return False, None
        
    # 3. Check for the "Cascade Tag" marker (0x88 or 136)
    if uid_1[0] == 0x88:
        # Select Level 1: "I see your first half, stay awake"
        buf1 = [0x93, 0x70] + uid_1[:5]
        reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, buf1 + get_crc(buf1))
        
        # Anticollision Level 2: Ask for the second half of the UID
        (status2, uid_2, bits) = reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, [0x95, 0x20])
        if status2 == reader.MI_OK:
            # Select Level 2: "I have your full UID, wake up completely"
            buf2 = [0x95, 0x70] + uid_2[:5]
            reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, buf2 + get_crc(buf2))
            
            # The Tag is now fully ACTIVE. Combine the pieces for the true UID.
            full_uid = uid_1[1:4] + uid_2[:4]
            return True, full_uid
    else:
        # Fallback just in case an older 4-byte tag is scanned
        reader.MFRC522_SelectTag(uid_1)
        return True, uid_1[:4]
        
    return False, None

def read_ntag_pages(page_addr):
    """
    Bypasses the library's strict 16-byte check by sending the raw 
    READ command (0x30) directly to the tag and catching the 18-byte response.
    Returns exactly 16 bytes of user data.
    """
    cmd = [0x30, page_addr]
    cmd += get_crc(cmd)
    
    (status, backData, backLen) = reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, cmd)
    
    if status == reader.MI_OK and backData:
        return backData[:16] # Strip the 2 CRC bytes at the end
    return None

def decode_ndef_text(raw_bytes):
    """
    Navigates the NDEF memory structure to extract clean Text records,
    ignoring lock bytes, capability containers, and language codes.
    """
    records = []
    idx = 0
    
    try:
        while idx < len(raw_bytes):
            if raw_bytes[idx] == 0xFE: # NDEF Terminator block
                break
            
            if raw_bytes[idx] == 0x00: # Null padding block
                idx += 1
                continue
            
            tlv_type = raw_bytes[idx]
            tlv_len = raw_bytes[idx+1]
            
            if tlv_type == 0x03: # Magic number for an NDEF Message
                ndef_data = raw_bytes[idx+2 : idx+2+tlv_len]
                
                i = 0
                while i < len(ndef_data):
                    header = ndef_data[i]
                    type_len = ndef_data[i+1]
                    payload_len = ndef_data[i+2]
                    
                    record_type = ndef_data[i+3 : i+3+type_len]
                    payload_start = i + 3 + type_len
                    payload = ndef_data[payload_start : payload_start+payload_len]
                    
                    # 0x54 is the ASCII code for 'T' (Text Record)
                    if len(record_type) > 0 and record_type[0] == 0x54:
                        # Find the length of the language code (e.g., 'en') and skip it
                        lang_len = payload[0] & 0x3F
                        text_bytes = payload[1+lang_len:]
                        
                        # Decode the remaining bytes into a clean string
                        text = "".join([chr(c) for c in text_bytes])
                        records.append(text)
                        
                    i = payload_start + payload_len # Jump to next record
                break
            else:
                idx += 2 + tlv_len # Skip non-NDEF message blocks
                
    except IndexError:
        pass # Catch if the memory cuts off unexpectedly
        
    return records


# ==========================================
# MAIN EXECUTION LOOP
# ==========================================

print("NFC Reader Active. Ready for Demo! (Press Ctrl+C to stop)")

try:
    while True:
        # Check for a tag using our custom handshake
        success, full_uid = select_ntag_7byte()
        
        if success:
            print("\n" + "="*40)
            
            # Format and print the hardware UID
            tag_id = "-".join([str(i) for i in full_uid])
            print(f"Hardware UID : {tag_id}")
            
            # Read 48 bytes of memory (Pages 4 through 15). 
            # This is plenty of room for multiple NDEF text records.
            chunk1 = read_ntag_pages(4)  # Pages 4, 5, 6, 7
            chunk2 = read_ntag_pages(8)  # Pages 8, 9, 10, 11
            chunk3 = read_ntag_pages(12) # Pages 12, 13, 14, 15
            
            if chunk1 and chunk2 and chunk3:
                full_memory = chunk1 + chunk2 + chunk3
                
                # Pass the raw memory through our clean parser
                extracted_records = decode_ndef_text(full_memory)
                
                print("-" * 40)
                if extracted_records:
                    print("Data Found:")
                    for index, record in enumerate(extracted_records):
                        print(f"  Record {index + 1}: {record}")
                else:
                    print("No NDEF Text records found on this tag.")
            else:
                print("Read Error: Please hold the tag steady.")
            
            print("="*40)
            
            # Pause so the terminal doesn't spam while the tag is still resting on the reader
            time.sleep(1.5) 
            print("\nWaiting for next tag...")

        # A tiny delay keeps the infinite loop from maxing out the Pi's CPU
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nShutting down reader...")
finally:
    # Always release the GPIO pins so they aren't locked on the next boot
    GPIO.cleanup()