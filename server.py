"""
Screen Capture Server - Organized Code
Captures screen and streams to monitoring clients
"""

# ==================== IMPORTS ====================
import socket
import threading
import time
import json
import base64
from io import BytesIO
import mss
from PIL import Image


# ==================== CONFIGURATION ====================
class ServerConfig:
    """Server configuration"""
    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 5555
    MAX_CLIENTS = 10
    
    # Performance settings
    DEFAULT_FPS = 60
    DEFAULT_QUALITY = 60
    DEFAULT_MONITOR = 1  # Which monitor to capture (1 = primary)
    MAX_WIDTH = 1280  # Maximum frame width
    
    # Network settings
    SOCKET_TIMEOUT = 1.0
    BUFFER_SIZE = 65536


# ==================== SCREEN CAPTURE SERVER CLASS ====================
class ScreenCaptureServer:
    """Main server class for screen capture and streaming"""
    
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
        
        # Statistics
        self.frames_sent = 0
        self.total_bytes_sent = 0
    
    # -------------------- SERVER CONTROL --------------------
    def start(self):
        """Start the server"""
        self.running = True
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(ServerConfig.MAX_CLIENTS)
        
        print(f"🚀 Server started on {self.host}:{self.port}")
        print(f"📺 Capturing monitor {self.screen_monitor}")
        print(f"⚡ FPS: {self.capture_fps}, Quality: {self.quality}%\n")
        
        # Start threads
        accept_thread = threading.Thread(target=self._accept_clients_loop, daemon=True)
        capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        
        accept_thread.start()
        capture_thread.start()
    
    def stop(self):
        """Stop the server"""
        print("\n🛑 Stopping server...")
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
        
        print("✅ Server stopped")
    
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
                    'connected_at': time.time()
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
                    self._process_command(client_socket, command)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"❌ Client handler error: {e}")
                    break
                    
        finally:
            self._remove_client(client_info)
    
    def _process_command(self, client_socket, command):
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
        """Main screen capture loop"""
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
                    
                    # Convert to JPEG
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
                    img_bytes = buffer.getvalue()
                    
                    # Encode to base64
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # Create packet
                    packet = {
                        'type': 'screen_frame',
                        'timestamp': time.time(),
                        'width': img.width,
                        'height': img.height,
                        'data': img_base64
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
    
    # -------------------- STATUS & STATISTICS --------------------
    def get_status(self):
        """Get server status"""
        with self.clients_lock:
            client_count = len(self.clients)
        
        return {
            'running': self.running,
            'clients': client_count,
            'fps': self.capture_fps,
            'quality': self.quality,
            'frames_sent': self.frames_sent,
            'total_bytes_sent': self.total_bytes_sent
        }
    
    def print_status(self):
        """Print formatted status"""
        status = self.get_status()
        
        print("\n" + "="*50)
        print("📊 SERVER STATUS")
        print("="*50)
        print(f"   Running: {status['running']}")
        print(f"   Connected Clients: {status['clients']}")
        print(f"   FPS: {status['fps']}")
        print(f"   Quality: {status['quality']}%")
        print(f"   Frames Sent: {status['frames_sent']}")
        
        # Calculate total data sent in MB
        total_mb = status['total_bytes_sent'] / (1024 * 1024)
        print(f"   Total Data Sent: {total_mb:.2f} MB")
        print("="*50 + "\n")


# ==================== COMMAND LINE INTERFACE ====================
class ServerCLI:
    """Command line interface for server control"""
    
    def __init__(self, server):
        self.server = server
    
    def show_help(self):
        """Show help menu"""
        print("\n" + "="*50)
        print("📺 SCREEN CAPTURE SERVER - COMMANDS")
        print("="*50)
        print("  status   - Show server status and statistics")
        print("  fps      - Change capture FPS (1-30)")
        print("  quality  - Change JPEG quality (10-100)")
        print("  monitor  - Change monitor to capture")
        print("  clients  - List connected clients")
        print("  help     - Show this help menu")
        print("  quit     - Stop server and exit")
        print("="*50 + "\n")
    
    def handle_command(self, cmd):
        """Handle user command"""
        cmd = cmd.strip().lower()
        
        if cmd == 'quit':
            return False
            
        elif cmd == 'status':
            self.server.print_status()
            
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
                    print(f"\nConnected Clients ({len(self.server.clients)}):")
                    for i, client in enumerate(self.server.clients, 1):
                        print(f"  {i}. {client['address']}")
                    print()
                    
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
    print("\n" + "="*50)
    print("🚀 STARTING SCREEN CAPTURE SERVER")
    print("="*50)
    
    # Create server
    server = ScreenCaptureServer(
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
        
    finally:
        server.stop()


if __name__ == '__main__':
    main()