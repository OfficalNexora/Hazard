import subprocess
import logging
import time

logger = logging.getLogger("SMSWorker")

class SMSWorker:
    def __init__(self):
        self.adb_path = "adb" # Assume in path or use specific path
        self.device_id = None
        
    def check_connection(self):
        """Check if an Android device is connected via ADB."""
        try:
            result = subprocess.run([self.adb_path, "devices"], capture_output=True, text=True)
            lines = result.stdout.strip().split("\n")
            # First line is "List of devices attached"
            for line in lines[1:]:
                if line.strip() and "device" in line:
                    parts = line.split("\t")
                    if len(parts) > 0:
                        self.device_id = parts[0]
                        return True
            return False
        except FileNotFoundError:
            logger.error("ADB not found in path.")
            return False

    def send_sms(self, phone_number, message):
        """Send SMS using ADB service call."""
        if not self.check_connection():
            return {"success": False, "error": "No Device Connected"}
            
        try:
            # Command to send SMS via service call
            # This works on most Android phones without needing a special app
            cmd = [
                self.adb_path, "-s", self.device_id, "shell", "service", "call", "isms", "7", 
                "i32", "0", 
                "s16", "null", 
                "s16", phone_number, 
                "s16", "null", 
                "s16", message
            ]
            
            # Alternative: simpler intent dispatch
            # cmd = [self.adb_path, "shell", "am", "start", "-a", "android.intent.action.SENDTO", "-d", f"sms:{phone_number}", "--es", "sms_body", message, "--ez", "exit_on_sent", "true"]
            # But the service call is more direct for background sending.
            
            subprocess.run(cmd, check=True)
            return {"success": True, "message": "SMS Sent"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}

    def make_call(self, phone_number):
        """Initiate proper call via ADB."""
        if not self.check_connection():
            return {"success": False, "error": "No Device Connected"}
            
        try:
            cmd = [
                self.adb_path, "-s", self.device_id, "shell", "am", "start", 
                "-a", "android.intent.action.CALL", 
                "-d", f"tel:{phone_number}"
            ]
            subprocess.run(cmd, check=True)
            return {"success": True, "message": "Call Initiated"}
        except subprocess.CalledProcessError as e:
            return {"success": False, "error": str(e)}

    def push_audio(self, local_path):
        """Push MP3 to Android device sdcard."""
        if not self.check_connection(): return False
        try:
            subprocess.run([self.adb_path, "-s", self.device_id, "push", local_path, "/sdcard/alert.mp3"], check=True)
            return True
        except:
            return False

    def play_audio(self):
        """Play the pushed MP3 on the device."""
        if not self.check_connection(): return False
        try:
            # Force speakerphone and high volume
            subprocess.run([self.adb_path, "-s", self.device_id, "shell", "media", "volume", "--stream", "3", "--set", "15"], check=False)
            
            # Start audio playback via intent
            cmd = [
                self.adb_path, "-s", self.device_id, "shell", "am", "start", 
                "-a", "android.intent.action.VIEW", 
                "-d", "file:///sdcard/alert.mp3", 
                "-t", "audio/mp3"
            ]
            subprocess.run(cmd, check=True)
            return True
        except:
            return False

# Global instance
sms_worker = SMSWorker()

def get_sms_worker():
    return sms_worker
