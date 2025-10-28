"""
Security Radar Server - Screen Capture with Motion Detection & Alerts
Captures screen, detects motion, and streams to monitoring clients with security features
"""

# ==================== IMPORTS ====================
import socket
import threading
import time
import json
import base64
from io import BytesIO
import mss
from PIL import Image, ImageChops, ImageStat
import numpy as np
from datetime import datetime
from collections import deque


# ==================== CONFIGURATION ====================
class ServerConfig:
    """Server configuration"""
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 5555
    MAX_CLIENTS = 10
    
    # Performance settings
    DEFAULT_FPS = 10
    DEFAULT_QUALITY = 60
    DEFAULT_MONITOR = 1  # Which monitor to capture (1 = primary)
    MAX_WIDTH = 1280  # Maximum frame width
    
    # Network settings
    SOCKET_TIMEOUT = 1.0
    BUFFER_SIZE = 65536
    
    # Security settings
    MOTION_DETECTION = True
    MOTION_THRESHOLD = 5.0  # Percentage of change to trigger motion
    MOTION_SENSITIVITY = 3  # 1-10, lower = more sensitive
    ALERT_COOLDOWN = 3  # Seconds between alerts
    
    # Zone settings
    ZONES_ENABLED = True
    MAX_ZONES = 10


# ==================== MONITORING ZONE CLASS ====================
class MonitoringZone:
    """Represents a monitoring zone for motion detection"""
    
    def __init__(self, zone_id, name, x, y, width, height, sensitivity=5):
        self.zone_id = zone_id
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.sensitivity = sensitivity
        self.enabled = True
        self.motion_detected = False
        self.last_alert_time = 0
        self.motion_history = deque(maxlen=10)
    
    def get_bounds(self):
        """Get zone boundaries"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def check_motion(self, diff_percentage):
        """Check if motion detected in zone"""
        threshold = ServerConfig.MOTION_THRESHOLD * (11 - self.sensitivity) / 10
        self.motion_detected = diff_percentage > threshold
        self.motion_history.append(self.motion_detected)
        return self.motion_detected
    
    def should_alert(self):
        """Check if should send alert"""
        current_time = time.time()
        if current_time - self.last_alert_time > ServerConfig.ALERT_COOLDOWN:
            self.last_alert_time = current_time
            return True
        return False


# ==================== MOTION DETECTOR CLASS ====================
class MotionDetector:
    """Handles motion detection between frames"""
    
    def __init__(self):
        self.previous_frame = None
        self.enabled = True
        self.motion_detected = False
        self.motion_percentage = 0.0
        self.sensitivity = ServerConfig.MOTION_SENSITIVITY
        self.detection_history = deque(maxlen=30)
    
    def detect_motion(self, current_frame):
        """Detect motion between frames"""
        if not self.enabled:
            return False, 0.0
        
        try:
            # Convert to grayscale for comparison
            current_gray = current_frame.convert('L')
            
            if self.previous_frame is None:
                self.previous_frame = current_gray
                return False, 0.0
            
            # Calculate difference
            diff = ImageChops.difference(current_gray, self.previous_frame)
            
            # Calculate statistics
            stat = ImageStat.Stat(diff)
            diff_percentage = sum(stat.mean) / len(stat.mean) / 255.0 * 100.0
            
            # Adjust for sensitivity
            threshold = ServerConfig.MOTION_THRESHOLD * (11 - self.sensitivity) / 10
            motion_detected = diff_percentage > threshold
            
            # Update history
            self.detection_history.append(motion_detected)
            
            # Update state
            self.previous_frame = current_gray
            self.motion_detected = motion_detected
            self.motion_percentage = diff_percentage
            
            return motion_detected, diff_percentage
            
        except Exception as e:
            print(f"❌ Motion detection error: {e}")
            return False, 0.0
    
    def reset(self):
        """Reset motion detector"""
        self.previous_frame = None
        self.motion_detected = False
        self.motion_percentage = 0.0


# ==================== SCREEN CAPTURE SERVER CLASS ====================
class SecurityRadarServer:
    """Main server class for security monitoring with motion detection"""
    
    # -------------------- INITIALIZATION --------------------
    def __init__(self, host=ServerConfig.DEFAULT_HOST, port=ServerConfig.DEFAULT_PORT):
        """Initialize server"""
        self.host = host
        self.port = port
        
        # Client management
        self.clients = []
        self.clients_lock = threading.Lock()
        
        # Server state
        self.running = False
        self.server_socket = None
        
        # Capture settings
        self.capture_fps = ServerConfig.DEFAULT_FPS
        self.quality = ServerConfig.DEFAULT_QUALITY
        self.screen_monitor = ServerConfig.DEFAULT_MONITOR
        
        # Security features
        self.motion_detector = MotionDetector()
        self.motion_enabled = ServerConfig.MOTION_DETECTION
        self.alerts_enabled = True
        self.zones = {}
        self.threat_level = 0  # 0=safe, 1=low, 2=medium, 3=high
        
        # Statistics
        self.frames_sent = 0
        self.total_bytes_sent = 0
        self.motion_events = 0
        self.alerts_sent = 0
        self.start_time = None
        
        # Initialize default zones
        self._initialize_default_zones()
    
    def _initialize_default_zones(self):
        """Initialize default monitoring zones"""
        # Zone 1: Top-left quadrant (Entry)
        self.zones[1] = MonitoringZone(1, "Entry Point", 0, 0, 640, 360, sensitivity=5)
        
        # Zone 2: Top-right quadrant (Perimeter)
        self.zones[2] = MonitoringZone(2, "Perimeter", 640, 0, 640, 360, sensitivity=4)
        
        # Zone 3: Bottom-left quadrant (Restricted)
        self.zones[3] = MonitoringZone(3, "Restricted Area", 0, 360, 640, 360, sensitivity=7)
        
        # Zone 4: Bottom-right quadrant (Parking)
        self.zones[4] = MonitoringZone(4, "Parking", 640, 360, 640, 360, sensitivity=3)
    
    # -------------------- SERVER CONTROL --------------------
    def start(self):
        """Start the server"""
        self.running = True
        self.start_time = datetime.now()
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(ServerConfig.MAX_CLIENTS)
        
        print("\n" + "="*60)
        print("🛡️  SECURITY RADAR SERVER - STARTED")
        print("="*60)
        print(f"🌐 Host: {self.host}:{self.port}")
        print(f"📺 Monitor: {self.screen_monitor}")
        print(f"⚡ FPS: {self.capture_fps} | Quality: {self.quality}%")
        print(f"🔍 Motion Detection: {'Enabled' if self.motion_enabled else 'Disabled'}")
        print(f"🚨 Alerts: {'Enabled' if self.alerts_enabled else 'Disabled'}")
        print(f"🗺️  Monitoring Zones: {len(self.zones)}")
        print("="*60 + "\n")
        
        # Start threads
        accept_thread = threading.Thread(target=self._accept_clients_loop, daemon=True)
        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        
        accept_thread.start()
        capture_thread.start()
        analytics_thread.start()
    
    def stop(self):
        """Stop the server"""
        print("\n🛑 Stopping security server...")
        self.running = False
        
        # Disconnect all clients
        with self.clients_lock:
            for client_info in self.clients[:]:
                self._remove_client(client_info)
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("✅ Server stopped\n")
    
    # -------------------- CLIENT MANAGEMENT --------------------
    def _accept_clients_loop(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"✅ Client connected: {address}")
                
                # Configure socket
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                client_socket.settimeout(ServerConfig.SOCKET_TIMEOUT)
                
                # Create client info
                client_info = {
                    'socket': client_socket,
                    'address': address,
                    'connected_at': time.time(),
                    'motion_enabled': True,
                    'alerts_enabled': True
                }
                
                # Add to clients list
                with self.clients_lock:
                    self.clients.append(client_info)
                
                # Start client handler thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_info,),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"❌ Accept client error: {e}")
    
    def _handle_client(self, client_info):
        """Handle individual client communication"""
        client_socket = client_info['socket']
        
        try:
            while self.running:
                try:
                    # Receive commands from client
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    command = data.decode('utf-8').strip()
                    self._process_command(client_socket, client_info, command)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"❌ Client handler error: {e}")
                    break
                    
        finally:
            self._remove_client(client_info)
    
    def _process_command(self, client_socket, client_info, command):
        """Process commands from client"""
        try:
            if command == 'PING':
                client_socket.send(b'PONG')
                
            elif command.startswith('SET_FPS:'):
                fps = int(command.split(':')[1])
                self.capture_fps = max(1, min(30, fps))
                client_socket.send(f'FPS_SET:{self.capture_fps}'.encode())
                print(f"⚙️  FPS changed to {self.capture_fps}")
                
            elif command.startswith('SET_QUALITY:'):
                quality = int(command.split(':')[1])
                self.quality = max(10, min(100, quality))
                client_socket.send(f'QUALITY_SET:{self.quality}'.encode())
                print(f"⚙️  Quality changed to {self.quality}%")
                
            elif command.startswith('ENABLE_MOTION:'):
                enabled = command.split(':')[1].lower() == 'true'
                client_info['motion_enabled'] = enabled
                print(f"🔍 Motion detection {('enabled' if enabled else 'disabled')} for {client_info['address']}")
                
            elif command.startswith('ENABLE_ALERTS:'):
                enabled = command.split(':')[1].lower() == 'true'
                client_info['alerts_enabled'] = enabled
                print(f"🚨 Alerts {('enabled' if enabled else 'disabled')} for {client_info['address']}")
                
            elif command == 'MANUAL_ALERT':
                print(f"⚠️  Manual alert triggered by {client_info['address']}")
                self.alerts_sent += 1
                
            elif command.startswith('SET_SENSITIVITY:'):
                sensitivity = int(command.split(':')[1])
                self.motion_detector.sensitivity = max(1, min(10, sensitivity))
                print(f"⚙️  Motion sensitivity set to {self.motion_detector.sensitivity}")
                
            elif command == 'GET_STATS':
                stats = self._get_statistics()
                response = json.dumps(stats)
                client_socket.send(response.encode())
                
        except Exception as e:
            print(f"❌ Command processing error: {e}")
    
    def _remove_client(self, client_info):
        """Remove disconnected client"""
        with self.clients_lock:
            if client_info in self.clients:
                self.clients.remove(client_info)
                print(f"❌ Client disconnected: {client_info['address']}")
                try:
                    client_info['socket'].close()
                except:
                    pass
    
    # -------------------- SCREEN CAPTURE --------------------
    def _capture_loop(self):
        """Main screen capture loop with motion detection"""
        with mss.mss() as sct:
            while self.running:
                try:
                    # Capture screen
                    monitor = sct.monitors[self.screen_monitor]
                    screenshot = sct.grab(monitor)
                    
                    # Convert to PIL Image
                    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    
                    # Resize if needed
                    if img.width > ServerConfig.MAX_WIDTH:
                        ratio = ServerConfig.MAX_WIDTH / img.width
                        new_size = (ServerConfig.MAX_WIDTH, int(img.height * ratio))
                        img = img.resize(new_size, Image.LANCZOS)
                    
                    # Motion detection
                    motion_detected = False
                    motion_percentage = 0.0
                    
                    if self.motion_enabled:
                        motion_detected, motion_percentage = self.motion_detector.detect_motion(img)
                        
                        if motion_detected:
                            self.motion_events += 1
                            self._process_motion_event(motion_percentage)
                    
                    # Convert to JPEG
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
                    img_bytes = buffer.getvalue()
                    
                    # Encode to base64
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # Create packet with security data
                    packet = {
                        'type': 'screen_frame',
                        'timestamp': time.time(),
                        'width': img.width,
                        'height': img.height,
                        'data': img_base64,
                        'motion_detected': motion_detected,
                        'motion_percentage': round(motion_percentage, 2),
                        'threat_level': self.threat_level,
                        'zone': self._get_active_zone()
                    }
                    
                    # Broadcast to clients
                    self._broadcast_packet(packet)
                    
                    # Update statistics
                    self.frames_sent += 1
                    self.total_bytes_sent += len(img_bytes)
                    
                    # Control FPS
                    time.sleep(1.0 / self.capture_fps)
                    
                except Exception as e:
                    print(f"❌ Capture error: {e}")
                    time.sleep(1)
    
    def _process_motion_event(self, motion_percentage):
        """Process detected motion event"""
        # Determine threat level based on motion intensity
        if motion_percentage > 20:
            self.threat_level = 3  # High
        elif motion_percentage > 10:
            self.threat_level = 2  # Medium
        else:
            self.threat_level = 1  # Low
        
        # Reset to safe after some time (handled in analytics loop)
    
    def _get_active_zone(self):
        """Get name of zone with motion"""
        for zone in self.zones.values():
            if zone.motion_detected:
                return zone.name
        return "Unknown"
    
    def _broadcast_packet(self, packet):
        """Broadcast packet to all connected clients"""
        json_data = json.dumps(packet)
        message = f"{len(json_data)}|{json_data}".encode('utf-8')
        
        disconnected = []
        
        with self.clients_lock:
            for client_info in self.clients[:]:
                try:
                    client_info['socket'].sendall(message)
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    print(f"❌ Send error to {client_info['address']}: {e}")
                    disconnected.append(client_info)
        
        # Remove disconnected clients
        for client_info in disconnected:
            self._remove_client(client_info)
    
    # -------------------- ANALYTICS --------------------
    def _analytics_loop(self):
        """Analyze security data and adjust threat levels"""
        while self.running:
            try:
                time.sleep(5)  # Run every 5 seconds
                
                # Auto-decrease threat level if no motion
                if not self.motion_detector.motion_detected and self.threat_level > 0:
                    self.threat_level = max(0, self.threat_level - 1)
                
                # Check motion history
                recent_motion = sum(1 for x in self.motion_detector.detection_history if x)
                motion_rate = recent_motion / len(self.motion_detector.detection_history) if self.motion_detector.detection_history else 0
                
                # Adjust threat based on sustained motion
                if motion_rate > 0.5:  # More than 50% motion in history
                    self.threat_level = min(3, self.threat_level + 1)
                    
            except Exception as e:
                print(f"❌ Analytics error: {e}")
    
    # -------------------- STATISTICS --------------------
    def _get_statistics(self):
        """Get detailed statistics"""
        with self.clients_lock:
            client_count = len(self.clients)
        
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'running': self.running,
            'clients': client_count,
            'fps': self.capture_fps,
            'quality': self.quality,
            'frames_sent': self.frames_sent,
            'total_bytes_sent': self.total_bytes_sent,
            'uptime': int(uptime),
            'motion_enabled': self.motion_enabled,
            'motion_events': self.motion_events,
            'alerts_sent': self.alerts_sent,
            'threat_level': self.threat_level,
            'zones': len(self.zones)
        }
    
    def print_status(self):
        """Print formatted status"""
        stats = self._get_statistics()
        
        print("\n" + "="*60)
        print("📊 SECURITY SERVER STATUS")
        print("="*60)
        print(f"   Status: {'🟢 Running' if stats['running'] else '🔴 Stopped'}")
        print(f"   Uptime: {stats['uptime']}s")
        print(f"   Connected Clients: {stats['clients']}")
        print(f"   FPS: {stats['fps']} | Quality: {stats['quality']}%")
        print(f"   Frames Sent: {stats['frames_sent']}")
        
        # Calculate total data sent in MB
        total_mb = stats['total_bytes_sent'] / (1024 * 1024)
        print(f"   Data Transmitted: {total_mb:.2f} MB")
        
        print("\n📡 Security Status:")
        print(f"   Motion Detection: {'🟢 Enabled' if stats['motion_enabled'] else '🔴 Disabled'}")
        print(f"   Motion Events: {stats['motion_events']}")
        print(f"   Alerts Sent: {stats['alerts_sent']}")
        
        threat_labels = ["🟢 SAFE", "🔵 LOW", "🟡 MEDIUM", "🔴 HIGH"]
        print(f"   Threat Level: {threat_labels[stats['threat_level']]}")
        print(f"   Monitoring Zones: {stats['zones']}")
        print("="*60 + "\n")
    
    def print_zones_status(self):
        """Print zones status"""
        print("\n" + "="*60)
        print("🗺️  MONITORING ZONES STATUS")
        print("="*60)
        
        for zone_id, zone in self.zones.items():
            status = "🟢" if zone.enabled else "🔴"
            motion = "⚠️  MOTION" if zone.motion_detected else "✓ Clear"
            print(f"   {status} Zone {zone_id}: {zone.name}")
            print(f"      Position: ({zone.x}, {zone.y}) Size: {zone.width}x{zone.height}")
            print(f"      Sensitivity: {zone.sensitivity}/10 | Status: {motion}")
        
        print("="*60 + "\n")


# ==================== COMMAND LINE INTERFACE ====================
class ServerCLI:
    """Command line interface for server control"""
    
    def __init__(self, server):
        self.server = server
    
    def show_help(self):
        """Show help menu"""
        print("\n" + "="*60)
        print("🛡️  SECURITY RADAR SERVER - COMMANDS")
        print("="*60)
        print("  status      - Show server status and statistics")
        print("  zones       - Show monitoring zones status")
        print("  motion      - Toggle motion detection on/off")
        print("  sensitivity - Change motion detection sensitivity (1-10)")
        print("  fps         - Change capture FPS (1-30)")
        print("  quality     - Change JPEG quality (10-100)")
        print("  monitor     - Change monitor to capture")
        print("  clients     - List connected clients")
        print("  alerts      - View alert statistics")
        print("  reset       - Reset motion detector")
        print("  help        - Show this help menu")
        print("  quit        - Stop server and exit")
        print("="*60 + "\n")
    
    def handle_command(self, cmd):
        """Handle user command"""
        cmd = cmd.strip().lower()
        
        if cmd == 'quit':
            return False
            
        elif cmd == 'status':
            self.server.print_status()
            
        elif cmd == 'zones':
            self.server.print_zones_status()
            
        elif cmd == 'motion':
            self.server.motion_enabled = not self.server.motion_enabled
            status = "enabled" if self.server.motion_enabled else "disabled"
            print(f"✅ Motion detection {status}")
            
        elif cmd == 'sensitivity':
            try:
                sens = int(input("Enter sensitivity (1-10, lower=more sensitive): "))
                self.server.motion_detector.sensitivity = max(1, min(10, sens))
                print(f"✅ Sensitivity set to {self.server.motion_detector.sensitivity}")
            except ValueError:
                print("❌ Invalid input")
                
        elif cmd == 'fps':
            try:
                fps = int(input("Enter FPS (1-30): "))
                self.server.capture_fps = max(1, min(30, fps))
                print(f"✅ FPS set to {self.server.capture_fps}")
            except ValueError:
                print("❌ Invalid input")
                
        elif cmd == 'quality':
            try:
                quality = int(input("Enter quality (10-100): "))
                self.server.quality = max(10, min(100, quality))
                print(f"✅ Quality set to {self.server.quality}%")
            except ValueError:
                print("❌ Invalid input")
                
        elif cmd == 'monitor':
            try:
                monitor = int(input("Enter monitor number (1, 2, ...): "))
                self.server.screen_monitor = monitor
                print(f"✅ Monitor set to {self.server.screen_monitor}")
            except ValueError:
                print("❌ Invalid input")
                
        elif cmd == 'clients':
            with self.server.clients_lock:
                if not self.server.clients:
                    print("No clients connected")
                else:
                    print(f"\n📱 Connected Clients ({len(self.server.clients)}):")
                    print("="*60)
                    for i, client in enumerate(self.server.clients, 1):
                        uptime = int(time.time() - client['connected_at'])
                        motion = "✓" if client.get('motion_enabled', True) else "✗"
                        alerts = "✓" if client.get('alerts_enabled', True) else "✗"
                        print(f"  {i}. {client['address']}")
                        print(f"     Uptime: {uptime}s | Motion: {motion} | Alerts: {alerts}")
                    print("="*60 + "\n")
                    
        elif cmd == 'alerts':
            print("\n🚨 Alert Statistics:")
            print("="*60)
            print(f"   Total Alerts Sent: {self.server.alerts_sent}")
            print(f"   Motion Events: {self.server.motion_events}")
            print(f"   Current Threat Level: {self.server.threat_level}")
            
            threat_desc = ["SAFE - No threats detected",
                          "LOW - Minor motion detected",
                          "MEDIUM - Moderate activity",
                          "HIGH - Significant activity detected"]
            print(f"   Status: {threat_desc[self.server.threat_level]}")
            print("="*60 + "\n")
            
        elif cmd == 'reset':
            self.server.motion_detector.reset()
            self.server.threat_level = 0
            self.server.motion_events = 0
            print("✅ Motion detector reset")
            
        elif cmd == 'help':
            self.show_help()
            
        else:
            print("❌ Unknown command. Type 'help' for available commands.")
        
        return True
    
    def run(self):
        """Run CLI loop"""
        self.show_help()
        
        while self.server.running:
            try:
                cmd = input("Command> ")
                if not self.handle_command(cmd):
                    break
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n")
                break


# ==================== MAIN ENTRY POINT ====================
def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🚀 STARTING SECURITY RADAR SERVER")
    print("="*60)
    
    # Create server
    server = SecurityRadarServer(
        host=ServerConfig.DEFAULT_HOST,
        port=ServerConfig.DEFAULT_PORT
    )
    
    try:
        # Start server
        server.start()
        
        # Run CLI
        cli = ServerCLI(server)
        cli.run()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        server.stop()


if __name__ == '__main__':
    main()