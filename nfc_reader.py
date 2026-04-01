import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time

class NTAGReader:
    def __init__(self):
        self.reader = MFRC522()

    def _get_crc(self, data):
        try:
            return self.reader.CalulateCRC(data)
        except AttributeError:
            return self.reader.CalculateCRC(data)

    def _select_ntag_7byte(self):
        # Reset SPI comms before asking to clear any previous hanging states
        self.reader.MFRC522_Init()
        
        (status, TagType) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
        if status != self.reader.MI_OK:
            return False, None
            
        (status, uid_1) = self.reader.MFRC522_Anticoll()
        if status != self.reader.MI_OK:
            return False, None
            
        if uid_1[0] == 0x88:
            buf1 = [0x93, 0x70] + uid_1[:5]
            self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, buf1 + self._get_crc(buf1))
            
            (status2, uid_2, bits) = self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, [0x95, 0x20])
            if status2 == self.reader.MI_OK:
                buf2 = [0x95, 0x70] + uid_2[:5]
                self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, buf2 + self._get_crc(buf2))
                full_uid = uid_1[1:4] + uid_2[:4]
                return True, full_uid
        else:
            self.reader.MFRC522_SelectTag(uid_1)
            return True, uid_1[:4]
            
        return False, None

    def _read_ntag_pages(self, page_addr):
        cmd = [0x30, page_addr]
        cmd += self._get_crc(cmd)
        (status, backData, backLen) = self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, cmd)
        
        if status == self.reader.MI_OK and backData:
            return backData[:16]
        return None

    @staticmethod
    def _decode_ndef_text(raw_bytes):
        records = []
        idx = 0
        try:
            while idx < len(raw_bytes):
                if raw_bytes[idx] == 0xFE:
                    break
                if raw_bytes[idx] == 0x00:
                    idx += 1
                    continue
                
                tlv_type = raw_bytes[idx]
                tlv_len = raw_bytes[idx+1]
                
                if tlv_type == 0x03:
                    ndef_data = raw_bytes[idx+2 : idx+2+tlv_len]
                    i = 0
                    while i < len(ndef_data):
                        type_len = ndef_data[i+1]
                        payload_len = ndef_data[i+2]
                        record_type = ndef_data[i+3 : i+3+type_len]
                        payload_start = i + 3 + type_len
                        payload = ndef_data[payload_start : payload_start+payload_len]
                        
                        if len(record_type) > 0 and record_type[0] == 0x54:
                            lang_len = payload[0] & 0x3F
                            text_bytes = payload[1+lang_len:]
                            text = "".join([chr(c) for c in text_bytes])
                            records.append(text)
                            
                        i = payload_start + payload_len
                    break
                else:
                    idx += 2 + tlv_len
        except IndexError:
            pass
        return records

    def get_tag_data(self, timeout_seconds=10.0):
        """
        Loops INTERNALLY for up to 10 seconds looking for a tag.
        Returns data immediately if found, or a timeout status if not.
        """
        start_time = time.time()
        
        # Keep looking until the timer runs out
        while time.time() - start_time < timeout_seconds:
            success, full_uid = self._select_ntag_7byte()
            
            if success:
                tag_id = "-".join([str(i) for i in full_uid])
                
                chunk1 = self._read_ntag_pages(4)
                chunk2 = self._read_ntag_pages(8)
                chunk3 = self._read_ntag_pages(12)
                
                if chunk1 and chunk2 and chunk3:
                    full_memory = chunk1 + chunk2 + chunk3
                    extracted_records = self._decode_ndef_text(full_memory)
                    
                    return {
                        "status": "success",
                        "uid": tag_id,
                        "records": extracted_records
                    }
                else:
                    return {
                        "status": "read_error",
                        "uid": tag_id,
                        "records": []
                    }
            
            # Tiny delay to prevent the Pi's CPU from spiking to 100%
            time.sleep(0.1)

        # If the loop finishes without returning, the 10 seconds are up.
        return {"status": "timeout", "uid": None, "records": []}

    def cleanup(self):
        GPIO.cleanup()