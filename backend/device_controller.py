"""
Device controller - executes commands for full device control
"""
import os
import subprocess
import psutil
import pyautogui
from pathlib import Path
from typing import Dict, Optional, List
import webbrowser
from datetime import datetime
import platform
import config

# Configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

class DeviceController:
    """Handles all device control operations"""
    
    def __init__(self):
        self.system = platform.system()
    
    # ==================== Application Control ====================
    
    def open_application(self, app_name: str) -> Dict:
        """Open an application"""
        try:
            # Get full path from aliases
            app_path = config.COMMAND_ALIASES.get(app_name.lower(), app_name)
            
            if self.system == "Windows":
                subprocess.Popen(app_path, shell=True)
            else:
                subprocess.Popen([app_path])
            
            return {
                "success": True,
                "message": f"Opened {app_name}",
                "app_name": app_name
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to open {app_name}: {str(e)}",
                "error": str(e)
            }
    
    def close_application(self, app_name: str) -> Dict:
        """Close an application"""
        try:
            app_name_lower = app_name.lower()
            closed_count = 0
            
            # Find and terminate processes
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    if app_name_lower in proc_name or proc_name.startswith(app_name_lower):
                        proc.terminate()
                        closed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if closed_count > 0:
                return {
                    "success": True,
                    "message": f"Closed {closed_count} instance(s) of {app_name}",
                    "count": closed_count
                }
            else:
                return {
                    "success": False,
                    "message": f"{app_name} is not running",
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to close {app_name}: {str(e)}",
                "error": str(e)
            }
    
    # ==================== File Operations ====================
    
    def create_file(self, filename: str, content: str = "") -> Dict:
        """Create a new file"""
        try:
            # Default to Documents folder
            file_path = config.DOCUMENTS_PATH / filename
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            
            return {
                "success": True,
                "message": f"Created file: {filename}",
                "path": str(file_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create file: {str(e)}",
                "error": str(e)
            }
    
    def delete_file(self, filename: str) -> Dict:
        """Delete a file"""
        try:
            # Check in common locations
            search_paths = [
                config.DOCUMENTS_PATH / filename,
                config.DESKTOP_PATH / filename,
                config.DOWNLOADS_PATH / filename,
                Path(filename),  # Absolute path
            ]
            
            deleted = False
            for file_path in search_paths:
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    deleted = True
                    return {
                        "success": True,
                        "message": f"Deleted file: {filename}",
                        "path": str(file_path)
                    }
            
            if not deleted:
                return {
                    "success": False,
                    "message": f"File not found: {filename}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to delete file: {str(e)}",
                "error": str(e)
            }
    
    def list_files(self, directory: str = "documents") -> Dict:
        """List files in a directory"""
        try:
            # Resolve directory path
            dir_path = config.PATH_ALIASES.get(directory.lower())
            if not dir_path:
                dir_path = Path(directory)
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "message": f"Directory not found: {directory}"
                }
            
            files = []
            for item in dir_path.iterdir():
                if item.is_file():
                    files.append({
                        "name": item.name,
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
            
            files.sort(key=lambda x: x["name"])
            
            return {
                "success": True,
                "message": f"Found {len(files)} files in {directory}",
                "files": files[:20],  # Limit to 20 files
                "total": len(files),
                "directory": str(dir_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list files: {str(e)}",
                "error": str(e)
            }
    
    def search_files(self, query: str, directory: str = "documents") -> Dict:
        """Search for files"""
        try:
            dir_path = config.PATH_ALIASES.get(directory.lower(), Path(directory))
            
            if not dir_path.exists():
                return {
                    "success": False,
                    "message": f"Directory not found: {directory}"
                }
            
            matches = []
            query_lower = query.lower()
            
            for item in dir_path.rglob("*"):
                if item.is_file() and query_lower in item.name.lower():
                    matches.append({
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size
                    })
            
            return {
                "success": True,
                "message": f"Found {len(matches)} files matching '{query}'",
                "matches": matches[:10],  # Limit to 10 results
                "total": len(matches)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to search files: {str(e)}",
                "error": str(e)
            }
    
    # ==================== System Control ====================
    
    def adjust_volume(self, direction: str) -> Dict:
        """Adjust system volume"""
        try:
            if self.system == "Windows":
                if direction == "up":
                    pyautogui.press("volumeup", presses=2)
                elif direction == "down":
                    pyautogui.press("volumedown", presses=2)
                elif direction == "mute":
                    pyautogui.press("volumemute")
                
                return {
                    "success": True,
                    "message": f"Volume {direction}",
                }
            else:
                return {
                    "success": False,
                    "message": "Volume control not supported on this system"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to adjust volume: {str(e)}",
                "error": str(e)
            }
    
    def adjust_brightness(self, direction: str) -> Dict:
        """Adjust screen brightness"""
        try:
            import screen_brightness_control as sbc
            
            current = sbc.get_brightness()[0]
            
            if direction == "up":
                new_brightness = min(100, current + 10)
            else:
                new_brightness = max(0, current - 10)
            
            sbc.set_brightness(new_brightness)
            
            return {
                "success": True,
                "message": f"Brightness set to {new_brightness}%",
                "brightness": new_brightness
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to adjust brightness: {str(e)}",
                "error": str(e)
            }
    
    def take_screenshot(self) -> Dict:
        """Take a screenshot"""
        try:
            screenshots_dir = config.DESKTOP_PATH / "Screenshots"
            screenshots_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = screenshots_dir / filename
            
            # Use PIL ImageGrab directly instead of pyautogui to avoid import issues
            try:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
            except ImportError:
                # Fallback to pyautogui if PIL doesn't have ImageGrab (Linux/Mac)
                screenshot = pyautogui.screenshot()
                screenshot.save(filepath)
            
            return {
                "success": True,
                "message": f"Screenshot saved to {filename}",
                "path": str(filepath)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to take screenshot: {str(e)}",
                "error": str(e)
            }
    
    def shutdown_system(self) -> Dict:
        """Shutdown the system"""
        if not config.ENABLE_DANGEROUS_COMMANDS:
            return {
                "success": False,
                "message": "Dangerous commands are disabled. Enable in config."
            }
        
        try:
            if self.system == "Windows":
                os.system("shutdown /s /t 30")
                return {
                    "success": True,
                    "message": "System will shutdown in 30 seconds"
                }
            else:
                return {
                    "success": False,
                    "message": "Shutdown not supported on this system"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to shutdown: {str(e)}",
                "error": str(e)
            }
    
    def restart_system(self) -> Dict:
        """Restart the system"""
        if not config.ENABLE_DANGEROUS_COMMANDS:
            return {
                "success": False,
                "message": "Dangerous commands are disabled. Enable in config."
            }
        
        try:
            if self.system == "Windows":
                os.system("shutdown /r /t 30")
                return {
                    "success": True,
                    "message": "System will restart in 30 seconds"
                }
            else:
                return {
                    "success": False,
                    "message": "Restart not supported on this system"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to restart: {str(e)}",
                "error": str(e)
            }
    
    # ==================== Information ====================
    
    def get_system_info(self) -> Dict:
        """Get system information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            info = {
                "system": self.system,
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "disk_usage": f"{disk.percent}%",
                "memory_total": f"{memory.total / (1024**3):.1f} GB",
                "disk_total": f"{disk.total / (1024**3):.1f} GB",
            }
            
            return {
                "success": True,
                "message": "System information retrieved",
                "info": info
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get system info: {str(e)}",
                "error": str(e)
            }
    
    # ==================== Web & Automation ====================
    
    def web_search(self, query: str) -> Dict:
        """Perform web search"""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            
            return {
                "success": True,
                "message": f"Searching for: {query}",
                "query": query
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to search: {str(e)}",
                "error": str(e)
            }
    
    def type_text(self, text: str) -> Dict:
        """Type text using keyboard"""
        try:
            pyautogui.write(text, interval=0.05)
            
            return {
                "success": True,
                "message": f"Typed: {text}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to type text: {str(e)}",
                "error": str(e)
            }
    
    def press_key(self, key: str) -> Dict:
        """Press a keyboard key"""
        try:
            pyautogui.press(key)
            
            return {
                "success": True,
                "message": f"Pressed key: {key}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to press key: {str(e)}",
                "error": str(e)
            }

# Global device controller instance
device_controller = DeviceController()
