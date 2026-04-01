import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time 

reader = MFRC522()

def get_crc(data):
    try:
        return reader.CalulateCRC(data)
    except AttributeError:
        return reader.CalculateCRC(data)

def select_ntag_7byte():
    """Handles the 2-step Cascade Level 2 handshake to wake up the NTAG."""
    # Reset communication before asking
    reader.MFRC522_Init()
    
    (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
    if status != reader.MI_OK:
        return False, None
        
    (status, uid_1) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        return False, None
        
    if uid_1[0] == 0x88:
        buf1 = [0x93, 0x70] + uid_1[:5]
        reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, buf1 + get_crc(buf1))
        
        (status2, uid_2, bits) = reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, [0x95, 0x20])
        if status2 == reader.MI_OK:
            buf2 = [0x95, 0x70] + uid_2[:5]
            reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, buf2 + get_crc(buf2))
            
            full_uid = uid_1[1:4] + uid_2[:4]
            return True, full_uid
    else:
        reader.MFRC522_SelectTag(uid_1)
        return True, uid_1[:4]
        
    return False, None

def write_ntag_page(page_addr, data_4_bytes):
    """
    Sends the raw NTAG Write command (0xA2). We ignore the return status 
    because the tag's 4-bit ACK will intentionally fail the library's byte-check.
    """
    if len(data_4_bytes) != 4:
        raise ValueError("Must write exactly 4 bytes per page!")
        
    cmd = [0xA2, page_addr] + data_4_bytes
    cmd += get_crc(cmd)
    
    # Send command and ignore the expected library panic
    reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, cmd)
    
    # CRITICAL: NTAG EEPROM needs time to physically burn the memory
    time.sleep(0.015) 

def generate_ndef_text_payload(text):
    """Wraps a string in the official NDEF format for smartphones."""
    text_bytes = text.encode('utf-8')
    payload_len = len(text_bytes) + 3 
    
    # NDEF Record Envelope
    ndef_record = [0xD1, 0x01, payload_len, 0x54, 0x02, 0x65, 0x6E] + list(text_bytes)
    tlv_len = len(ndef_record)
    
    # NDEF Message Envelope + Terminator (0xFE)
    full_payload = [0x03, tlv_len] + ndef_record + [0xFE]
    
    # Pad to perfectly fit 4-byte pages
    while len(full_payload) % 4 != 0:
        full_payload.append(0x00)
        
    return full_payload

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================

try:
    while True:
        print("\n" + "="*40)
        user_input = input("Enter the text you want to write (or type 'exit'): ")
        
        if user_input.lower() == 'exit':
            break
            
        payload = generate_ndef_text_payload(user_input)
        
        if len(payload) > 130:
            print("Error: Message too long for a standard NTAG213!")
            continue
            
        print(f"\nWaiting for tag... (Hold tag steady until SUCCESS)")
        
        tag_detected = False
        while not tag_detected:
            success, uid = select_ntag_7byte()
            
            if success:
                tag_detected = True
                print("Tag detected! Burning data...")
                
                current_page = 4
                pages_written = 0
                total_pages = len(payload) // 4
                
                # Write loop: 4 bytes (1 page) at a time
                for i in range(0, len(payload), 4):
                    chunk = payload[i:i+4]
                    
                    # Force a re-handshake before EVERY page to clear the panic state
                    retry = 0
                    while retry < 5:
                        ready, _ = select_ntag_7byte()
                        if ready:
                            write_ntag_page(current_page, chunk)
                            pages_written += 1
                            break
                        retry += 1
                        time.sleep(0.01)
                    
                    if retry == 5:
                        print(f"\n[!] Write failed at Page {current_page}. You moved the tag too early.")
                        break
                        
                    current_page += 1
                
                if pages_written == total_pages:
                    print("-" * 40)
                    print(f"SUCCESS! Wrote '{user_input}' completely.")
                    print("You can now scan it with your phone or your read.py script.")
                    print("-" * 40)
                
                # Pause to prevent accidental rapid-fire rewrites
                time.sleep(2) 
            else:
                time.sleep(0.1)

except KeyboardInterrupt:
    print("\nShutting down writer...")
finally:
    GPIO.cleanup()