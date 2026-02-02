import psutil
import time
import asyncio
import threading
from datetime import datetime, timedelta
import config
from text_to_speech import tts

class SystemMonitor:
    def __init__(self, websocket_manager):
        self.manager = websocket_manager
        self.running = False
        self.thread = None
        self.last_alerts = {} # Type -> Timestamp
        
        # Thresholds
        self.CPU_THRESHOLD = 90.0 # Percent
        self.RAM_THRESHOLD = 95.0 # Percent
        self.BATTERY_THRESHOLD = 20 # Percent
        
        # Cooldown
        self.ALERT_COOLDOWN = 300 # 5 minutes

    def start(self):
        """Start the monitor thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("✓ System Monitor started")

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _should_alert(self, alert_type):
        """Check cooldown"""
        last_time = self.last_alerts.get(alert_type)
        if not last_time:
            return True
        
        if (datetime.now() - last_time).total_seconds() > self.ALERT_COOLDOWN:
            return True
        
        return False

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Check metrics
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory()
                battery = psutil.sensors_battery()
                
                alert_msg = ""
                alert_type = ""
                
                # Logic
                if cpu > self.CPU_THRESHOLD and self._should_alert("cpu"):
                    alert_type = "cpu"
                    alert_msg = f"Sir, CPU usage is critical at {cpu} percent."
                    
                elif ram.percent > self.RAM_THRESHOLD and self._should_alert("ram"):
                    alert_type = "ram"
                    alert_msg = f"Sir, Memory usage is very high at {ram.percent} percent."
                    
                elif battery and battery.percent < self.BATTERY_THRESHOLD and not battery.power_plugged and self._should_alert("battery"):
                    alert_type = "battery"
                    alert_msg = f"Sir, Battery is low at {battery.percent} percent. Please plug in."

                # Send Alert
                if alert_msg:
                    print(f"⚠ System Alert: {alert_msg}")
                    self.last_alerts[alert_type] = datetime.now()
                    
                    # Generate Audio
                    # We need to run async function from this sync thread
                    # The safest way is to use existing event loop or run_coroutine_threadsafe
                    # But tts.text_to_audio_base64 is synchronous-compatible in its call (it manages its own process)
                    
                    audio_base64 = tts.text_to_audio_base64(alert_msg)
                    
                    if audio_base64 and self.manager:
                         # Broadcast via WebSocket
                         # self.manager.broadcast is async. We need to schedule it.
                         self._broadcast_alert(alert_msg, audio_base64)
                
            except Exception as e:
                print(f"Monitor Error: {e}")
            
            # Sleep 60s
            time.sleep(60)

    def _broadcast_alert(self, message, audio):
        """Helper to send alert to event loop"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.manager.broadcast({
                        "type": "result",
                        "success": True,
                        "message": message,
                        "audio": audio,
                        "data": {"intent": "system_alert"}
                    }), 
                    loop
                )
        except:
             # If no loop found (rare in this context), safe fail
             pass

