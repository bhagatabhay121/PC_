"""
Desktop Screen Monitoring App - Organized Code
Professional desktop UI for PC with modular sections
"""

# ==================== IMPORTS ====================
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.animation import Animation
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
import socket
import threading
import json
import base64
from datetime import datetime
import os
import shutil

# ==================== CONFIGURATION ====================
class Config:
    """Application configuration"""
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 800
    MIN_WIDTH = 1200
    MIN_HEIGHT = 700
    
    # Server settings
    DEFAULT_IP = "localhost"
    DEFAULT_PORT = 5555
    AUTO_CONNECT = True
    
    # Theme
    THEME_STYLE = "Dark"
    PRIMARY_PALETTE = "Blue"
    
    # Network
    BUFFER_SIZE = 65536
    SOCKET_TIMEOUT = 0.01
    
    # Media
    DEFAULT_QUALITY = 60
    SCREENSHOT_DIR = "screenshots"
    RECORDING_DIR = "recordings"


# ==================== WINDOW SETUP ====================
Window.size = (Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
Window.minimum_width = Config.MIN_WIDTH
Window.minimum_height = Config.MIN_HEIGHT


# ==================== UI LAYOUT (KV) ====================
KV = '''
#:import hex kivy.utils.get_color_from_hex

<InfoRow@MDBoxLayout>:
    icon: ""
    label: ""
    value: ""
    size_hint_y: None
    height: dp(40)
    spacing: dp(16)
    
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: app.theme_cls.primary_color
        size_hint_x: None
        width: dp(32)
        font_size: dp(24)
        
    MDBoxLayout:
        orientation: 'vertical'
        spacing: dp(2)
        
        MDLabel:
            text: root.label
            font_style: "Caption"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: dp(16)
            
        MDLabel:
            text: root.value
            font_style: "Body1"
            bold: True

MDScreen:
    name: 'main'
    
    MDBoxLayout:
        orientation: 'horizontal'
        
        # ==================== LEFT SIDEBAR ====================
        MDCard:
            orientation: 'vertical'
            size_hint_x: None
            width: dp(320)
            elevation: 4
            radius: [0, 0, 0, 0]
            md_bg_color: app.theme_cls.bg_dark if app.theme_cls.theme_style == "Dark" else hex("#f5f5f5")
            
            # Logo Section
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(120)
                padding: dp(20)
                spacing: dp(8)
                
                MDIcon:
                    icon: "monitor-screenshot"
                    font_size: dp(48)
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    size_hint_y: None
                    height: dp(56)
                    
                MDLabel:
                    text: "Screen Monitor Pro"
                    font_style: "H6"
                    halign: "center"
                    size_hint_y: None
                    height: dp(32)
            
            MDSeparator:
            
            # Connection Status
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(100)
                padding: dp(20)
                spacing: dp(12)
                
                MDLabel:
                    text: "Connection Status"
                    font_style: "Subtitle2"
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: dp(20)
                
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(48)
                    spacing: dp(12)
                    
                    MDIcon:
                        id: status_icon
                        icon: "circle"
                        theme_text_color: "Custom"
                        text_color: hex("#757575")
                        size_hint: None, None
                        size: dp(24), dp(24)
                        pos_hint: {"center_y": 0.5}
                        
                    MDLabel:
                        id: status_text
                        text: "Disconnected"
                        font_style: "Body1"
                        bold: True
            
            MDSeparator:
            
            # Statistics
            MDScrollView:
                do_scroll_x: False
                
                MDBoxLayout:
                    orientation: 'vertical'
                    adaptive_height: True
                    padding: dp(20)
                    spacing: dp(16)
                    
                    MDLabel:
                        text: "Live Statistics"
                        font_style: "Subtitle2"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: dp(24)
                    
                    InfoRow:
                        icon: "clock-outline"
                        label: "UPTIME"
                        value: app.uptime_text
                    
                    InfoRow:
                        icon: "image-multiple"
                        label: "FRAMES"
                        value: app.frames_text
                    
                    InfoRow:
                        icon: "speedometer"
                        label: "FPS"
                        value: app.fps_text
                    
                    InfoRow:
                        icon: "download-network"
                        label: "BANDWIDTH"
                        value: app.bandwidth_text
                    
                    InfoRow:
                        icon: "timer-outline"
                        label: "LATENCY"
                        value: app.latency_text
                    
                    InfoRow:
                        icon: "monitor"
                        label: "RESOLUTION"
                        value: app.resolution_text
            
            # Bottom Actions
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(200)
                padding: dp(20)
                spacing: dp(12)
                
                MDSeparator:
                
                Widget:
                    size_hint_y: None
                    height: dp(12)
                
                MDRaisedButton:
                    id: connect_btn
                    text: "CONNECT TO SERVER"
                    icon: "lan-connect"
                    size_hint_x: 1
                    on_release: app.toggle_connection()
                    md_bg_color: app.theme_cls.primary_color
                
                MDRaisedButton:
                    text: "SETTINGS"
                    icon: "cog"
                    size_hint_x: 1
                    on_release: app.show_settings()
                    
                MDRaisedButton:
                    text: "ABOUT"
                    icon: "information"
                    size_hint_x: 1
                    on_release: app.show_about()
        
        # ==================== MAIN CONTENT ====================
        MDBoxLayout:
            orientation: 'vertical'
            
            # Top Bar
            MDTopAppBar:
                title: "Live Screen Preview"
                elevation: 2
                md_bg_color: app.theme_cls.primary_color
            
            # Content Area
            MDBoxLayout:
                orientation: 'vertical'
                padding: dp(24)
                spacing: dp(20)
                
                # Preview Card
                MDCard:
                    elevation: 4
                    radius: [dp(12)]
                    
                    MDCard:
                        md_bg_color: hex("#000000")
                        radius: [dp(12)]
                        
                        Image:
                            id: screen_preview
                            allow_stretch: True
                            keep_ratio: True
                
                # Controls
                MDBoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(200)
                    spacing: dp(20)
                    
                    # Recording Controls
                    MDCard:
                        orientation: 'vertical'
                        padding: dp(20)
                        spacing: dp(16)
                        elevation: 3
                        radius: [dp(12)]
                        size_hint_x: 0.4
                        
                        MDLabel:
                            text: "Recording Controls"
                            font_style: "H6"
                            size_hint_y: None
                            height: dp(32)
                        
                        MDBoxLayout:
                            spacing: dp(12)
                            size_hint_y: None
                            height: dp(56)
                            
                            MDRaisedButton:
                                text: "Screenshot"
                                icon: "camera"
                                size_hint_x: 0.5
                                on_release: app.take_screenshot()
                                
                            MDRaisedButton:
                                id: record_btn
                                text: "Record"
                                icon: "record-circle-outline"
                                size_hint_x: 0.5
                                on_release: app.toggle_recording()
                    
                    # Quality Control
                    MDCard:
                        orientation: 'vertical'
                        padding: dp(20)
                        spacing: dp(16)
                        elevation: 3
                        radius: [dp(12)]
                        size_hint_x: 0.6
                        
                        MDLabel:
                            text: "Stream Quality"
                            font_style: "H6"
                            size_hint_y: None
                            height: dp(32)
                        
                        MDBoxLayout:
                            spacing: dp(16)
                            size_hint_y: None
                            height: dp(56)
                            
                            MDLabel:
                                text: "Quality:"
                                size_hint_x: None
                                width: dp(80)
                            
                            MDSlider:
                                id: quality_slider
                                min: 10
                                max: 100
                                value: 60
                                hint: True
                                on_value: app.update_quality(self.value)
                            
                            MDLabel:
                                text: str(int(quality_slider.value)) + "%"
                                size_hint_x: None
                                width: dp(60)
                                bold: True
    
    # ==================== FULLSCREEN OVERLAY ====================
    MDBoxLayout:
        id: fullscreen_overlay
        orientation: 'vertical'
        md_bg_color: hex("#000000")
        opacity: 0
        pos_hint: {"x": 0, "y": 0}
        size_hint: (1, 1)
        
        MDTopAppBar:
            title: "Full Screen Preview"
            md_bg_color: hex("#1a1a1a")
            left_action_items: [["close-fullscreen", lambda x: app.toggle_fullscreen()]]
            
        Image:
            id: fullscreen_image
            allow_stretch: True
            keep_ratio: True
'''


# ==================== MAIN APPLICATION CLASS ====================
class ScreenMonitorApp(MDApp):
    """Main application class"""
    
    # Properties for live updates
    uptime_text = StringProperty("0s")
    frames_text = StringProperty("0")
    fps_text = StringProperty("0")
    bandwidth_text = StringProperty("0 KB/s")
    latency_text = StringProperty("0ms")
    resolution_text = StringProperty("N/A")
    
    # -------------------- INITIALIZATION --------------------
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Network state
        self.connected = False
        self.socket = None
        self.receive_thread = None
        
        # Statistics
        self.start_time = None
        self.frame_count = 0
        self.fps = 0
        self.last_frame_time = 0
        self.data_received = 0
        self.latency = 0
        self.current_resolution = "N/A"
        
        # Media
        self.recording = False
        self.recorded_frames = []
        
        # UI state
        self.fullscreen_mode = False
        self.connection_dialog = None
        
    def build(self):
        """Build the application"""
        self.theme_cls.theme_style = Config.THEME_STYLE
        self.theme_cls.primary_palette = Config.PRIMARY_PALETTE
        self.title = "Screen Monitor Pro"
        return Builder.load_string(KV)
        
    def on_start(self):
        """Called when app starts"""
        Clock.schedule_interval(self.update_stats, 1)
        
        if Config.AUTO_CONNECT:
            Clock.schedule_once(lambda dt: self.connect_to_server(), 0.5)
    
    def on_stop(self):
        """Called when app stops"""
        self.disconnect_from_server()
    
    # -------------------- CONNECTION METHODS --------------------
    def toggle_connection(self):
        """Toggle connection"""
        if not self.connected:
            self.show_connection_dialog()
        else:
            self.disconnect_from_server()
    
    def show_connection_dialog(self):
        """Show connection dialog"""
        if not self.connection_dialog:
            content = MDBoxLayout(
                orientation='vertical',
                spacing=dp(20),
                size_hint_y=None,
                height=dp(160)
            )
            
            ip_field = MDTextField(
                hint_text="Server IP",
                text=Config.DEFAULT_IP,
                helper_text="Enter server IP address",
                helper_text_mode="persistent"
            )
            
            port_field = MDTextField(
                hint_text="Port",
                text=str(Config.DEFAULT_PORT),
                helper_text="Enter port number",
                helper_text_mode="persistent"
            )
            
            content.add_widget(ip_field)
            content.add_widget(port_field)
            
            self.connection_dialog = MDDialog(
                title="Connect to Server",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=lambda x: self.connection_dialog.dismiss()
                    ),
                    MDRaisedButton(
                        text="CONNECT",
                        on_release=lambda x: self.connect_with_inputs(ip_field.text, port_field.text)
                    )
                ]
            )
        
        self.connection_dialog.open()
    
    def connect_with_inputs(self, ip, port):
        """Connect with user inputs"""
        self.connection_dialog.dismiss()
        
        try:
            Config.DEFAULT_IP = ip
            Config.DEFAULT_PORT = int(port)
            self.connect_to_server()
        except ValueError:
            self.show_notification("Invalid port number", "error")
    
    def connect_to_server(self):
        """Connect to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(Config.SOCKET_TIMEOUT)
            self.socket.connect((Config.DEFAULT_IP, Config.DEFAULT_PORT))
            
            self.connected = True
            self.start_time = datetime.now()
            self.frame_count = 0
            self.data_received = 0
            
            # Update UI
            self.update_connection_ui(True)
            self.show_notification("Connected successfully!", "success")
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self.receive_data, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            self.show_notification(f"Connection failed: {str(e)}", "error")
    
    def disconnect_from_server(self):
        """Disconnect from server"""
        self.connected = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.update_connection_ui(False)
        self.show_notification("Disconnected", "info")
        
        self.start_time = None
        self.frame_count = 0
    
    # -------------------- DATA RECEPTION --------------------
    def receive_data(self):
        """Receive data from server"""
        buffer = b""
        
        while self.connected:
            try:
                data = self.socket.recv(Config.BUFFER_SIZE)
                if not data:
                    break
                
                buffer += data
                
                # Process complete messages
                while b'|' in buffer:
                    separator_index = buffer.find(b'|')
                    size_str = buffer[:separator_index]
                    
                    try:
                        size = int(size_str.decode('utf-8'))
                    except (ValueError, UnicodeDecodeError):
                        buffer = buffer[separator_index + 1:]
                        continue
                    
                    message_start = separator_index + 1
                    message_end = message_start + size
                    
                    if len(buffer) >= message_end:
                        message = buffer[message_start:message_end].decode('utf-8')
                        buffer = buffer[message_end:]
                        Clock.schedule_once(lambda dt, msg=message: self.process_frame(msg), 0)
                    else:
                        break
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.connected:
                    print(f"Receive error: {e}")
                    Clock.schedule_once(lambda dt: self.disconnect_from_server(), 0)
                break
    
    def process_frame(self, message):
        """Process received frame"""
        try:
            packet = json.loads(message)
            
            if packet['type'] == 'screen_frame':
                img_data = base64.b64decode(packet['data'])
                
                # Update stats
                self.frame_count += 1
                self.data_received += len(img_data)
                self.current_resolution = f"{packet['width']}x{packet['height']}"
                
                # Calculate FPS
                current_time = datetime.now().timestamp()
                if self.last_frame_time > 0:
                    frame_time = current_time - self.last_frame_time
                    self.fps = int(1 / frame_time) if frame_time > 0 else 0
                    self.latency = int((current_time - packet['timestamp']) * 1000)
                self.last_frame_time = current_time
                
                # Save and display
                temp_path = f'temp_frame_{self.frame_count % 2}.jpg'
                with open(temp_path, 'wb') as f:
                    f.write(img_data)
                
                self.root.ids.screen_preview.source = temp_path
                self.root.ids.screen_preview.reload()
                
                if self.fullscreen_mode:
                    self.root.ids.fullscreen_image.source = temp_path
                    self.root.ids.fullscreen_image.reload()
                
                # Recording
                if self.recording:
                    self.recorded_frames.append(img_data)
                    
        except Exception as e:
            print(f"Process error: {e}")
    
    # -------------------- STATISTICS --------------------
    def update_stats(self, dt):
        """Update statistics display"""
        if self.start_time:
            uptime = int((datetime.now() - self.start_time).total_seconds())
            self.uptime_text = f"{uptime}s"
        else:
            self.uptime_text = "0s"
        
        self.frames_text = str(self.frame_count)
        self.fps_text = str(self.fps)
        
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                bandwidth = (self.data_received / 1024) / elapsed
                self.bandwidth_text = f"{bandwidth:.1f} KB/s"
        else:
            self.bandwidth_text = "0 KB/s"
        
        self.latency_text = f"{self.latency}ms"
        self.resolution_text = self.current_resolution
    
    # -------------------- UI UPDATES --------------------
    def update_connection_ui(self, connected):
        """Update connection UI"""
        try:
            icon = self.root.ids.status_icon
            text = self.root.ids.status_text
            btn = self.root.ids.connect_btn
            
            if connected:
                icon.text_color = [0, 1, 0, 1]
                text.text = "Connected"
                btn.text = "DISCONNECT"
                btn.icon = "lan-disconnect"
            else:
                icon.text_color = [0.46, 0.46, 0.46, 1]
                text.text = "Disconnected"
                btn.text = "CONNECT TO SERVER"
                btn.icon = "lan-connect"
        except:
            pass
    
    # -------------------- MEDIA METHODS --------------------
    def take_screenshot(self):
        """Take screenshot"""
        if not self.connected:
            self.show_notification("Not connected!", "error")
            return
        
        try:
            os.makedirs(Config.SCREENSHOT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{Config.SCREENSHOT_DIR}/screenshot_{timestamp}.jpg"
            
            temp_path = f'temp_frame_{self.frame_count % 2}.jpg'
            if os.path.exists(temp_path):
                shutil.copy(temp_path, filename)
                self.show_notification("Screenshot saved!", "success")
            else:
                self.show_notification("No frame available", "error")
        except Exception as e:
            self.show_notification(f"Failed: {str(e)}", "error")
    
    def toggle_recording(self):
        """Toggle recording"""
        if not self.connected:
            self.show_notification("Not connected!", "error")
            return
        
        if not self.recording:
            self.recording = True
            self.recorded_frames = []
            self.root.ids.record_btn.icon = "stop"
            self.root.ids.record_btn.md_bg_color = [0.8, 0.2, 0.2, 1]
            self.show_notification("Recording started", "info")
        else:
            self.recording = False
            self.root.ids.record_btn.icon = "record-circle-outline"
            self.root.ids.record_btn.md_bg_color = self.theme_cls.primary_color
            self.save_recording()
    
    def save_recording(self):
        """Save recording"""
        if not self.recorded_frames:
            self.show_notification("No frames recorded", "error")
            return
        
        try:
            os.makedirs(Config.RECORDING_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for i, frame in enumerate(self.recorded_frames):
                filename = f"{Config.RECORDING_DIR}/rec_{timestamp}_frame_{i:04d}.jpg"
                with open(filename, 'wb') as f:
                    f.write(frame)
            
            self.show_notification(f"Saved {len(self.recorded_frames)} frames", "success")
        except Exception as e:
            self.show_notification(f"Save failed: {str(e)}", "error")
    
    # -------------------- UI METHODS --------------------
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        overlay = self.root.ids.fullscreen_overlay
        
        if not self.fullscreen_mode:
            anim = Animation(opacity=1, duration=0.3)
            anim.start(overlay)
            self.fullscreen_mode = True
        else:
            anim = Animation(opacity=0, duration=0.3)
            anim.start(overlay)
            self.fullscreen_mode = False
    
    def update_quality(self, value):
        """Update quality"""
        if self.connected and self.socket:
            try:
                command = f"SET_QUALITY:{int(value)}"
                self.socket.send(command.encode('utf-8'))
            except:
                pass
    
    def show_settings(self):
        """Show settings"""
        dialog = MDDialog(
            title="Settings",
            text="Adjust stream settings from the controls panel.\nQuality slider: 10-100%\nConnection: Change in connection dialog",
            buttons=[MDRaisedButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()
    
    def show_about(self):
        """Show about"""
        dialog = MDDialog(
            title="About Screen Monitor Pro",
            text="Version 2.0\nDesktop Screen Monitoring Application\n\nFeatures:\nâ€¢ Live screen streaming\nâ€¢ Screenshot capture\nâ€¢ Video recording\nâ€¢ Adjustable quality\n\nDeveloped with KivyMD",
            buttons=[MDRaisedButton(text="OK", on_release=lambda x: dialog.dismiss())]
        )
        dialog.open()
    
    def show_notification(self, message, type="info"):
        """Show notification"""
        print(f"[{type.upper()}] {message}")


# ==================== MAIN ENTRY POINT ====================
if __name__ == '__main__':
    ScreenMonitorApp().run()