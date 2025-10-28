"""
Security Radar Monitoring System - Client Application with Firebase
Professional desktop UI for security monitoring with real-time Firebase sync
"""

# ==================== IMPORTS ====================
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty
from kivy.animation import Animation
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineIconListItem, IconLeftWidget
import socket
import threading
import json
import base64
from datetime import datetime
import os
import shutil
from collections import deque

# Firebase imports
import firebase_admin
from firebase_admin import credentials, db

# ==================== CONFIGURATION ====================
class Config:
    MIN_WIDTH = 1400
    MIN_HEIGHT = 800
    
    # Server settings
    DEFAULT_IP = "localhost"
    DEFAULT_PORT = 5555
    AUTO_CONNECT = True
    
    # Theme
    THEME_STYLE = "Dark"
    PRIMARY_PALETTE = "Blue"
    
    # Network
    BUFFER_SIZE = 65536
    SOCKET_TIMEOUT = 0.1
    
    # Security
    ALERT_SOUND = True
    AUTO_RECORD_ON_ALERT = False
    ALERT_HISTORY_MAX = 50
    MOTION_THRESHOLD = 5  # percent
    
    # Media
    DEFAULT_QUALITY = 60
    SCREENSHOT_DIR = "security_captures"
    RECORDING_DIR = "security_recordings"
    ALERT_DIR = "security_alerts"
    
    # Firebase
    FIREBASE_CRED = "chat-c6931-firebase-adminsdk-fbsvc-1ac13d1b84.json"
    FIREBASE_URL = "https://chat-c6931-default-rtdb.firebaseio.com/"


# ==================== FIREBASE MANAGER ====================
class FirebaseManager:
    """Manages Firebase integration for the client"""
    
    def __init__(self):
        self.initialized = False
        self.user_id = None  # Will be set to actual IP address
        self.user_ref = None
        self.alerts_ref = None
        self.blocked_ref = None
        
    def get_local_ip(self):
        """Get actual local IP address of the client"""
        try:
            # Create a socket to determine the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                # Connect to external address (doesn't actually send data)
                s.connect(('10.255.255.255', 1))
                ip_address = s.getsockname()[0]
            except Exception:
                # Fallback to localhost if can't determine
                ip_address = '127.0.0.1'
            finally:
                s.close()
            
            # Clean IP for Firebase key (replace dots with dashes)
            # Firebase keys can't contain . $ # [ ] /
            clean_ip = ip_address.replace('.', '-')
            return clean_ip
        except Exception as e:
            print(f"⚠️ Could not determine IP: {e}")
            # Fallback to hostname-based identifier
            try:
                import uuid
                hostname = socket.gethostname()
                return f"{hostname}-{str(uuid.uuid4())[:8]}"
            except:
                return f"user-{str(uuid.uuid4())[:8]}"
    
    def initialize(self):
        """Initialize Firebase"""
        try:
            cred = credentials.Certificate(Config.FIREBASE_CRED)
            firebase_admin.initialize_app(cred, {
                'databaseURL': Config.FIREBASE_URL
            })
            
            # Get actual IP address as user_id
            self.user_id = self.get_local_ip()
            
            # Setup references with IP-based user_id
            self.user_ref = db.reference(f'security_radar/users/{self.user_id}')
            self.alerts_ref = db.reference('security_radar/alerts')
            self.blocked_ref = db.reference(f'security_radar/blocked_users/{self.user_id}')
            
            self.initialized = True
            print(f"✅ Firebase initialized - User ID (IP): {self.user_id}")
            
            # Register user
            self.register_user()
            
            return True
        except Exception as e:
            print(f"❌ Firebase init error: {e}")
            return False
    
    def register_user(self):
        """Register user in Firebase with IP address"""
        try:
            # Get the original IP for display (with dots)
            display_ip = self.user_id.replace('-', '.')
            
            self.user_ref.set({
                'user_id': self.user_id,
                'ip_address': display_ip,  # Store readable IP
                'connected_at': datetime.now().isoformat(),
                'last_seen': datetime.now().timestamp(),
                'status': 'online',
                'alert_count': 0,
                'blocked': False,
                'fps': 0,
                'latency': 0,
                'resolution': 'N/A',
                'motion_enabled': True,
                'alerts_enabled': True,
                'recording': False,
                'threat_level': 0
            })
            print(f"✅ Registered with IP: {display_ip}")
        except Exception as e:
            print(f"❌ Register error: {e}")
    
    def update_heartbeat(self):
        """Update user heartbeat"""
        try:
            if self.user_ref:
                self.user_ref.update({
                    'last_seen': datetime.now().timestamp(),
                    'status': 'online'
                })
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
    
    def update_stats(self, stats_data):
        """Update user statistics"""
        try:
            if self.user_ref:
                # Ensure last_seen is always updated
                stats_data['last_seen'] = datetime.now().timestamp()
                stats_data['status'] = 'online'
                self.user_ref.update(stats_data)
        except Exception as e:
            print(f"❌ Stats update error: {e}")
    
    def push_alert(self, alert_data):
        """Push alert to Firebase"""
        try:
            if self.alerts_ref:
                alert_data['user_id'] = self.user_id
                alert_data['ip_address'] = self.user_id.replace('-', '.')
                alert_data['timestamp'] = datetime.now().isoformat()
                self.alerts_ref.push(alert_data)
                
                # Increment user alert count
                if self.user_ref:
                    current_data = self.user_ref.get()
                    if current_data:
                        count = current_data.get('alert_count', 0)
                        self.user_ref.update({'alert_count': count + 1})
        except Exception as e:
            print(f"❌ Alert push error: {e}")
    
    def check_blocked_status(self):
        """Check if user is blocked"""
        try:
            if self.blocked_ref:
                blocked = self.blocked_ref.get()
                return blocked is not None and blocked == True
            return False
        except Exception as e:
            print(f"❌ Block check error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect user"""
        try:
            if self.user_ref:
                self.user_ref.update({
                    'status': 'offline',
                    'disconnected_at': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"❌ Disconnect error: {e}")


# ==================== UI LAYOUT (KV) ====================
KV = '''
#:import hex kivy.utils.get_color_from_hex

<InfoRow@MDBoxLayout>:
    icon: ""
    label: ""
    value: ""
    value_color: [1, 1, 1, 1]
    size_hint_y: None
    height: dp(40)
    spacing: dp(12)
    
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: app.theme_cls.primary_color
        size_hint_x: None
        width: dp(28)
        font_size: dp(22)
        
    MDBoxLayout:
        orientation: 'vertical'
        spacing: dp(2)
        
        MDLabel:
            text: root.label
            font_style: "Caption"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: dp(14)
            
        MDLabel:
            text: root.value
            font_style: "Body2"
            bold: True
            theme_text_color: "Custom"
            text_color: root.value_color

<AlertItem@OneLineIconListItem>:
    alert_type: ""
    
    IconLeftWidget:
        icon: "alert-circle" if root.alert_type == "HIGH" else "alert" if root.alert_type == "MEDIUM" else "information"
        theme_text_color: "Custom"
        text_color: hex("#FF5252") if root.alert_type == "HIGH" else hex("#FFA726") if root.alert_type == "MEDIUM" else hex("#42A5F5")

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
            md_bg_color: hex("#1a1a1a") if app.theme_cls.theme_style == "Dark" else hex("#f5f5f5")
            
            # Logo Section
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(110)
                padding: dp(20)
                spacing: dp(6)
                
                MDIcon:
                    icon: "shield-check"
                    font_size: dp(44)
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    size_hint_y: None
                    height: dp(50)
                    
                MDLabel:
                    text: "Security Radar"
                    font_style: "H6"
                    halign: "center"
                    size_hint_y: None
                    height: dp(28)
                    
                MDLabel:
                    text: "Monitoring System"
                    font_style: "Caption"
                    halign: "center"
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: dp(16)
            
            MDSeparator:
            
            # Connection Status
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(110)
                padding: [dp(20), dp(12), dp(20), dp(12)]
                spacing: dp(8)
                
                MDLabel:
                    text: "System Status"
                    font_style: "Subtitle2"
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: dp(18)
                
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    spacing: dp(12)
                    
                    MDIcon:
                        id: status_icon
                        icon: "circle"
                        theme_text_color: "Custom"
                        text_color: hex("#757575")
                        size_hint: None, None
                        size: dp(20), dp(20)
                        pos_hint: {"center_y": 0.5}
                        
                    MDLabel:
                        id: status_text
                        text: "Offline"
                        font_style: "Body1"
                        bold: True
                
                MDLabel:
                    id: user_id_label
                    text: f"User ID: {app.firebase.user_id.replace('-', '.') if app.firebase and app.firebase.user_id else 'N/A'}"
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: dp(18)
            
            MDSeparator:
            
            # Security Stats
            MDScrollView:
                do_scroll_x: False
                
                MDBoxLayout:
                    orientation: 'vertical'
                    adaptive_height: True
                    padding: dp(20)
                    spacing: dp(14)
                    
                    MDLabel:
                        text: "Security Metrics"
                        font_style: "Subtitle2"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: dp(22)
                    
                    InfoRow:
                        icon: "shield-alert"
                        label: "THREAT LEVEL"
                        value: app.threat_level_text
                        value_color: app.threat_level_color
                    
                    InfoRow:
                        icon: "motion-sensor"
                        label: "MOTION DETECTED"
                        value: app.motion_text
                        value_color: app.motion_color
                    
                    InfoRow:
                        icon: "bell-ring"
                        label: "ALERTS TODAY"
                        value: app.alerts_today_text
                    
                    InfoRow:
                        icon: "clock-outline"
                        label: "UPTIME"
                        value: app.uptime_text
                    
                    InfoRow:
                        icon: "video"
                        label: "RECORDING"
                        value: app.recording_text
                        value_color: app.recording_color
                    
                    MDSeparator:
                    
                    MDLabel:
                        text: "Network Stats"
                        font_style: "Subtitle2"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: dp(22)
                    
                    InfoRow:
                        icon: "speedometer"
                        label: "FPS"
                        value: app.fps_text
                    
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
                height: dp(180)
                padding: dp(20)
                spacing: dp(10)
                
                MDSeparator:
                
                Widget:
                    size_hint_y: None
                    height: dp(8)
                
                MDRaisedButton:
                    id: connect_btn
                    text: "CONNECT"
                    icon: "lan-connect"
                    size_hint_x: 1
                    on_release: app.toggle_connection()
                    md_bg_color: app.theme_cls.primary_color
                
                MDRaisedButton:
                    text: "ZONES"
                    icon: "floor-plan"
                    size_hint_x: 1
                    on_release: app.show_zones()
                    
                MDRaisedButton:
                    text: "SETTINGS"
                    icon: "cog"
                    size_hint_x: 1
                    on_release: app.show_settings()
        
        # ==================== MAIN CONTENT ====================
        MDBoxLayout:
            orientation: 'vertical'
            
            # Top Bar
            MDTopAppBar:
                title: "Live Security Feed"
                elevation: 3
                md_bg_color: app.theme_cls.primary_color
                right_action_items: [["fullscreen", lambda x: app.toggle_fullscreen()]]
            
            # Blocked Overlay
            MDCard:
                id: blocked_overlay
                orientation: 'vertical'
                padding: dp(40)
                spacing: dp(20)
                md_bg_color: [0.1, 0.1, 0.1, 0.95]
                opacity: 0
                pos_hint: {"center_x": 0.5, "center_y": 0.5}
                size_hint: (0.5, 0.4)
                elevation: 10
                radius: [dp(20)]
                
                MDIcon:
                    icon: "block-helper"
                    font_size: dp(80)
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: [0.96, 0.26, 0.21, 1]
                    size_hint_y: None
                    height: dp(100)
                
                MDLabel:
                    text: "ACCESS BLOCKED"
                    font_style: "H4"
                    halign: "center"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: [0.96, 0.26, 0.21, 1]
                    size_hint_y: None
                    height: dp(50)
                
                MDLabel:
                    text: "Your access has been blocked by the administrator.\\nPlease contact support for assistance."
                    font_style: "Body1"
                    halign: "center"
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: dp(60)
            
            # Content Area
            MDBoxLayout:
                orientation: 'horizontal'
                padding: dp(20)
                spacing: dp(20)
                
                # Left: Video Feed
                MDBoxLayout:
                    orientation: 'vertical'
                    spacing: dp(16)
                    size_hint_x: 0.65
                    
                    # Preview Card
                    MDCard:
                        elevation: 6
                        radius: [dp(12)]
                        
                        MDBoxLayout:
                            orientation: 'vertical'
                            
                            # Motion Indicator
                            MDBoxLayout:
                                size_hint_y: None
                                height: dp(40)
                                padding: dp(12)
                                md_bg_color: hex("#1a1a1a")
                                
                                MDIcon:
                                    id: motion_indicator
                                    icon: "motion-sensor"
                                    theme_text_color: "Custom"
                                    text_color: hex("#757575")
                                    size_hint_x: None
                                    width: dp(32)
                                
                                MDLabel:
                                    text: "Motion Detection Active"
                                    font_style: "Caption"
                                    theme_text_color: "Secondary"
                                
                                MDLabel:
                                    id: motion_percentage
                                    text: "0%"
                                    font_style: "Caption"
                                    halign: "right"
                                    bold: True
                            
                            MDCard:
                                md_bg_color: hex("#000000")
                                radius: [0, 0, dp(12), dp(12)]
                                
                                Image:
                                    id: screen_preview
                                    allow_stretch: True
                                    keep_ratio: True
                    
                    # Controls
                    MDBoxLayout:
                        orientation: 'horizontal'
                        size_hint_y: None
                        height: dp(160)
                        spacing: dp(16)
                        
                        # Recording Controls
                        MDCard:
                            orientation: 'vertical'
                            padding: dp(16)
                            spacing: dp(12)
                            elevation: 3
                            radius: [dp(10)]
                            
                            MDLabel:
                                text: "Quick Actions"
                                font_style: "Subtitle1"
                                size_hint_y: None
                                height: dp(24)
                            
                            MDBoxLayout:
                                spacing: dp(10)
                                size_hint_y: None
                                height: dp(48)
                                
                                MDRaisedButton:
                                    text: "Capture"
                                    icon: "camera"
                                    size_hint_x: 0.33
                                    on_release: app.take_screenshot()
                                    
                                MDRaisedButton:
                                    id: record_btn
                                    text: "Record"
                                    icon: "record-circle-outline"
                                    size_hint_x: 0.33
                                    on_release: app.toggle_recording()
                                    
                                MDRaisedButton:
                                    id: alert_btn
                                    text: "Alert"
                                    icon: "bell-ring"
                                    size_hint_x: 0.34
                                    on_release: app.trigger_manual_alert()
                                    md_bg_color: hex("#FFA726")
                            
                            MDBoxLayout:
                                spacing: dp(10)
                                size_hint_y: None
                                height: dp(48)
                                
                                MDRaisedButton:
                                    text: "Motion: ON" if app.motion_enabled else "Motion: OFF"
                                    icon: "motion-sensor"
                                    size_hint_x: 0.5
                                    on_release: app.toggle_motion_detection()
                                    md_bg_color: hex("#4CAF50") if app.motion_enabled else hex("#757575")
                                    
                                MDRaisedButton:
                                    text: "Alerts: ON" if app.alerts_enabled else "Alerts: OFF"
                                    icon: "bell"
                                    size_hint_x: 0.5
                                    on_release: app.toggle_alerts()
                                    md_bg_color: hex("#4CAF50") if app.alerts_enabled else hex("#757575")
                
                # Right: Alerts & Info
                MDBoxLayout:
                    orientation: 'vertical'
                    spacing: dp(16)
                    size_hint_x: 0.35
                    
                    # Alerts Panel
                    MDCard:
                        orientation: 'vertical'
                        padding: dp(16)
                        spacing: dp(12)
                        elevation: 4
                        radius: [dp(10)]
                        
                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(32)
                            spacing: dp(8)
                            
                            MDIcon:
                                icon: "alert-circle"
                                theme_text_color: "Custom"
                                text_color: hex("#FF5252")
                                size_hint_x: None
                                width: dp(28)
                            
                            MDLabel:
                                text: "Security Alerts"
                                font_style: "H6"
                                size_hint_y: None
                                height: dp(32)
                            
                            MDRaisedButton:
                                text: "Clear"
                                size_hint: None, None
                                size: dp(80), dp(32)
                                on_release: app.clear_alerts()
                        
                        MDSeparator:
                        
                        ScrollView:
                            do_scroll_x: False
                            
                            MDList:
                                id: alerts_list
                    
                    # Zone Status
                    MDCard:
                        orientation: 'vertical'
                        padding: dp(16)
                        spacing: dp(12)
                        elevation: 4
                        radius: [dp(10)]
                        size_hint_y: None
                        height: dp(200)
                        
                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(32)
                            spacing: dp(8)
                            
                            MDIcon:
                                icon: "floor-plan"
                                theme_text_color: "Custom"
                                text_color: app.theme_cls.primary_color
                                size_hint_x: None
                                width: dp(28)
                            
                            MDLabel:
                                text: "Monitoring Zones"
                                font_style: "H6"
                                size_hint_y: None
                                height: dp(32)
                        
                        MDSeparator:
                        
                        MDBoxLayout:
                            orientation: 'vertical'
                            spacing: dp(8)
                            
                            MDLabel:
                                text: "Zone 1: Entry Point"
                                font_style: "Body2"
                                
                            MDLabel:
                                text: "Zone 2: Perimeter"
                                font_style: "Body2"
                                
                            MDLabel:
                                text: "Zone 3: Restricted Area"
                                font_style: "Body2"
                                
                            MDLabel:
                                text: "Zone 4: Parking"
                                font_style: "Body2"
    
    # ==================== FULLSCREEN OVERLAY ====================
    MDBoxLayout:
        id: fullscreen_overlay
        orientation: 'vertical'
        md_bg_color: hex("#000000")
        opacity: 0
        pos_hint: {"x": 0, "y": 0}
        size_hint: (1, 1)
        
        MDTopAppBar:
            title: "Full Screen Security Monitor"
            md_bg_color: hex("#1a1a1a")
            left_action_items: [["close-fullscreen", lambda x: app.toggle_fullscreen()]]
            
        Image:
            id: fullscreen_image
            allow_stretch: True
            keep_ratio: True
'''

class AlertItem(OneLineIconListItem):
    """Custom list item for security alerts"""
    
    def __init__(self, alert_type="LOW", **kwargs):
        super().__init__(**kwargs)
        self.alert_type = alert_type
        
        icon_name = {
            "HIGH": "alert-circle",
            "MEDIUM": "alert",
            "LOW": "information"
        }.get(alert_type, "information")
        
        icon_color = {
            "HIGH": [1, 0.32, 0.32, 1],
            "MEDIUM": [1, 0.65, 0.15, 1],
            "LOW": [0.26, 0.65, 0.96, 1]
        }.get(alert_type, [0.5, 0.5, 0.5, 1])
        
        icon_widget = IconLeftWidget(
            icon=icon_name,
            theme_text_color="Custom",
            text_color=icon_color
        )
        self.add_widget(icon_widget)


# ==================== MAIN APPLICATION CLASS ====================
class SecurityRadarApp(MDApp):
    """Main application class for security monitoring with Firebase"""
    
    # Properties for live updates
    uptime_text = StringProperty("0s")
    fps_text = StringProperty("0")
    latency_text = StringProperty("0ms")
    resolution_text = StringProperty("N/A")
    
    # Security properties
    threat_level_text = StringProperty("SAFE")
    threat_level_color = ListProperty([0.3, 0.8, 0.3, 1])
    motion_text = StringProperty("NO")
    motion_color = ListProperty([0.5, 0.5, 0.5, 1])
    alerts_today_text = StringProperty("0")
    recording_text = StringProperty("OFF")
    recording_color = ListProperty([0.5, 0.5, 0.5, 1])
    
    motion_enabled = BooleanProperty(True)
    alerts_enabled = BooleanProperty(True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Firebase
        self.firebase = FirebaseManager()
        self.is_blocked = False
        
        # Network state
        self.connected = False
        self.socket = None
        self.receive_thread = None
        
        # Statistics
        self.start_time = None
        self.frame_count = 0
        self.fps = 0
        self.last_frame_time = 0
        self.latency = 0
        self.current_resolution = "N/A"
        
        # Security
        self.motion_detected = False
        self.motion_percentage = 0
        self.alerts = deque(maxlen=Config.ALERT_HISTORY_MAX)
        self.alerts_today = 0
        self.threat_level = 0
        
        # Media
        self.recording = False
        self.recorded_frames = []
        
        # UI state
        self.fullscreen_mode = False
        self.dialogs = {}
        
    def build(self):
        """Build the application"""
        self.theme_cls.theme_style = Config.THEME_STYLE
        self.theme_cls.primary_palette = Config.PRIMARY_PALETTE
        self.title = "Security Radar Monitor"
        return Builder.load_string(KV)
        
    def on_start(self):
        """Called when app starts"""
        # Initialize Firebase
        self.firebase.initialize()
        
        # Update user ID label after Firebase init
        Clock.schedule_once(self.update_user_id_label, 0.5)
        
        # Schedule updates
        Clock.schedule_interval(self.update_stats, 1)
        Clock.schedule_interval(self.update_ui_elements, 0.5)
        Clock.schedule_interval(self.firebase_heartbeat, 5)
        Clock.schedule_interval(self.check_blocked_status, 3)
        
        # Create directories
        for dir in [Config.SCREENSHOT_DIR, Config.RECORDING_DIR, Config.ALERT_DIR]:
            os.makedirs(dir, exist_ok=True)
        
        if Config.AUTO_CONNECT:
            Clock.schedule_once(lambda dt: self.connect_to_server(), 0.5)
    
    def update_user_id_label(self, dt):
        """Update user ID label in UI"""
        try:
            if self.firebase and self.firebase.user_id:
                display_ip = self.firebase.user_id.replace('-', '.')
                self.root.ids.user_id_label.text = f"User ID: {display_ip}"
        except:
            pass
    
    def on_stop(self):
        """Called when app stops"""
        self.disconnect_from_server()
        if self.firebase:
            self.firebase.disconnect()
    
    # ==================== FIREBASE METHODS ====================
    def firebase_heartbeat(self, dt):
        """Send heartbeat to Firebase"""
        if self.firebase and self.firebase.initialized:
            self.firebase.update_heartbeat()
            
            # Update stats
            stats = {
                'fps': self.fps,
                'latency': self.latency,
                'resolution': self.current_resolution,
                'motion_enabled': self.motion_enabled,
                'alerts_enabled': self.alerts_enabled,
                'alert_count': self.alerts_today,
                'recording': self.recording,
                'threat_level': self.threat_level
            }
            self.firebase.update_stats(stats)
    
    def check_blocked_status(self, dt):
        """Check if user is blocked"""
        if self.firebase and self.firebase.initialized:
            blocked = self.firebase.check_blocked_status()
            
            if blocked and not self.is_blocked:
                # User just got blocked
                self.is_blocked = True
                self.handle_blocked()
            elif not blocked and self.is_blocked:
                # User unblocked
                self.is_blocked = False
                self.handle_unblocked()
    
    def handle_blocked(self):
        """Handle user being blocked"""
        print("⛔ User has been blocked by admin")
        
        # Disconnect from server
        if self.connected:
            self.disconnect_from_server()
        
        # Show blocked overlay
        overlay = self.root.ids.blocked_overlay
        Animation(opacity=1, duration=0.5).start(overlay)
        
        # Clear preview
        self.root.ids.screen_preview.source = ""
    
    def handle_unblocked(self):
        """Handle user being unblocked"""
        print("✅ User has been unblocked")
        
        # Hide blocked overlay
        overlay = self.root.ids.blocked_overlay
        Animation(opacity=0, duration=0.5).start(overlay)
        
        # Show notification
        self.show_notification("Access restored!", "success")
    
    # ==================== CONNECTION METHODS ====================
    def toggle_connection(self):
        """Toggle connection"""
        if self.is_blocked:
            self.show_notification("Access blocked by administrator", "error")
            return
        
        if not self.connected:
            self.show_connection_dialog()
        else:
            self.disconnect_from_server()
    
    def show_connection_dialog(self):
        """Show connection dialog"""
        if 'connection' not in self.dialogs:
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
            
            self.dialogs['connection'] = MDDialog(
                title="Connect to Security Server",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=lambda x: self.dialogs['connection'].dismiss()
                    ),
                    MDRaisedButton(
                        text="CONNECT",
                        on_release=lambda x: self.connect_with_inputs(ip_field.text, port_field.text)
                    )
                ]
            )
        
        self.dialogs['connection'].open()
    
    def connect_with_inputs(self, ip, port):
        """Connect with user inputs"""
        self.dialogs['connection'].dismiss()
        
        try:
            Config.DEFAULT_IP = ip
            Config.DEFAULT_PORT = int(port)
            self.connect_to_server()
        except ValueError:
            self.show_notification("Invalid port number", "error")
    
    def connect_to_server(self):
        """Connect to server"""
        if self.is_blocked:
            self.show_notification("Cannot connect - Access blocked", "error")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(Config.SOCKET_TIMEOUT)
            self.socket.connect((Config.DEFAULT_IP, Config.DEFAULT_PORT))
            
            self.connected = True
            self.start_time = datetime.now()
            self.frame_count = 0
            self.alerts_today = 0
            
            # Enable security features
            self.send_command(f"ENABLE_MOTION:{self.motion_enabled}")
            self.send_command(f"ENABLE_ALERTS:{self.alerts_enabled}")
            
            # Update UI
            self.update_connection_ui(True)
            self.show_notification("Connected to security server!", "success")
            
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
        self.show_notification("Disconnected from server", "info")
        
        self.start_time = None
        self.frame_count = 0
        self.motion_detected = False
    
    def send_command(self, command):
        """Send command to server"""
        if self.connected and self.socket:
            try:
                self.socket.send(command.encode('utf-8'))
            except:
                pass
    
    # ==================== DATA RECEPTION ====================
    def receive_data(self):
        """Receive data from server"""
        buffer = b""
        
        while self.connected and not self.is_blocked:
            try:
                data = self.socket.recv(Config.BUFFER_SIZE)
                if not data:
                    break
                
                buffer += data
                
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
        if self.is_blocked:
            return
        
        try:
            packet = json.loads(message)
            
            if packet['type'] == 'screen_frame':
                img_data = base64.b64decode(packet['data'])
                
                # Update stats
                self.frame_count += 1
                self.current_resolution = f"{packet['width']}x{packet['height']}"
                
                # Calculate FPS
                current_time = datetime.now().timestamp()
                if self.last_frame_time > 0:
                    frame_time = current_time - self.last_frame_time
                    self.fps = int(1 / frame_time) if frame_time > 0 else 0
                    self.latency = int((current_time - packet['timestamp']) * 1000)
                self.last_frame_time = current_time
                
                # Process security data
                if 'motion_detected' in packet:
                    self.motion_detected = packet['motion_detected']
                    self.motion_percentage = packet.get('motion_percentage', 0)
                    
                    if self.motion_detected and self.alerts_enabled:
                        self.handle_motion_alert(packet)
                
                if 'threat_level' in packet:
                    self.threat_level = packet['threat_level']
                
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
    
    def handle_motion_alert(self, packet):
        """Handle motion detection alert"""
        alert_data = {
            'type': 'MOTION',
            'severity': 'MEDIUM' if self.motion_percentage > 15 else 'LOW',
            'details': f"Motion detected: {self.motion_percentage:.1f}%",
            'zone': packet.get('zone', 'Unknown'),
            'motion_percentage': self.motion_percentage
        }
        
        self.add_alert(alert_data)
        
        # Push to Firebase
        if self.firebase and self.firebase.initialized:
            self.firebase.push_alert(alert_data)
        
        # Auto-record if enabled
        if Config.AUTO_RECORD_ON_ALERT and not self.recording:
            self.toggle_recording()
    
    def add_alert(self, alert_data):
        """Add new alert to history"""
        alert_data['timestamp'] = datetime.now()
        self.alerts.append(alert_data)
        self.alerts_today += 1
        
        # Update alerts list
        alerts_list = self.root.ids.alerts_list
        
        time_str = alert_data['timestamp'].strftime("%H:%M:%S")
        alert_text = f"{time_str} - {alert_data['details']}"
        
        item = AlertItem(text=alert_text, alert_type=alert_data['severity'])
        alerts_list.add_widget(item)
        
        # Keep only last 20 visible
        if len(alerts_list.children) > 20:
            alerts_list.remove_widget(alerts_list.children[-1])
    
    # ==================== STATISTICS ====================
    def update_stats(self, dt):
        """Update statistics display"""
        if self.start_time:
            uptime = int((datetime.now() - self.start_time).total_seconds())
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            seconds = uptime % 60
            if hours > 0:
                self.uptime_text = f"{hours}h {minutes}m"
            elif minutes > 0:
                self.uptime_text = f"{minutes}m {seconds}s"
            else:
                self.uptime_text = f"{seconds}s"
        else:
            self.uptime_text = "0s"
        
        self.fps_text = str(self.fps)
        self.latency_text = f"{self.latency}ms"
        self.resolution_text = self.current_resolution
        self.alerts_today_text = str(self.alerts_today)
        
        # Update threat level
        if self.threat_level == 0:
            self.threat_level_text = "SAFE"
            self.threat_level_color = [0.3, 0.8, 0.3, 1]
        elif self.threat_level == 1:
            self.threat_level_text = "LOW"
            self.threat_level_color = [0.4, 0.7, 1, 1]
        elif self.threat_level == 2:
            self.threat_level_text = "MEDIUM"
            self.threat_level_color = [1, 0.65, 0.15, 1]
        else:
            self.threat_level_text = "HIGH"
            self.threat_level_color = [1, 0.2, 0.2, 1]
        
        # Update motion status
        if self.motion_detected:
            self.motion_text = "YES"
            self.motion_color = [1, 0.3, 0.3, 1]
        else:
            self.motion_text = "NO"
            self.motion_color = [0.5, 0.5, 0.5, 1]
        
        # Update recording status
        if self.recording:
            elapsed = int((datetime.now() - self.recording_start).total_seconds())
            self.recording_text = f"ON ({elapsed}s)"
            self.recording_color = [1, 0.2, 0.2, 1]
        else:
            self.recording_text = "OFF"
            self.recording_color = [0.5, 0.5, 0.5, 1]
    
    def update_ui_elements(self, dt):
        """Update UI elements that need frequent refresh"""
        try:
            motion_icon = self.root.ids.motion_indicator
            motion_pct = self.root.ids.motion_percentage
            
            if self.motion_detected:
                motion_icon.text_color = [1, 0.3, 0.3, 1]
                motion_pct.text = f"{self.motion_percentage:.1f}%"
            else:
                motion_icon.text_color = [0.46, 0.46, 0.46, 1]
                motion_pct.text = "0%"
        except:
            pass
    
    # ==================== UI UPDATES ====================
    def update_connection_ui(self, connected):
        """Update connection UI"""
        try:
            icon = self.root.ids.status_icon
            text = self.root.ids.status_text
            btn = self.root.ids.connect_btn
            
            if connected:
                icon.text_color = [0, 1, 0, 1]
                text.text = "Online"
                btn.text = "DISCONNECT"
                btn.icon = "lan-disconnect"
            else:
                icon.text_color = [0.46, 0.46, 0.46, 1]
                text.text = "Offline"
                btn.text = "CONNECT"
                btn.icon = "lan-connect"
        except:
            pass
    
    # ==================== SECURITY METHODS ====================
    def toggle_motion_detection(self):
        """Toggle motion detection"""
        if self.is_blocked:
            self.show_notification("Access blocked", "error")
            return
        
        self.motion_enabled = not self.motion_enabled
        self.send_command(f"ENABLE_MOTION:{self.motion_enabled}")
        
        status = "enabled" if self.motion_enabled else "disabled"
        self.show_notification(f"Motion detection {status}", "info")
    
    def toggle_alerts(self):
        """Toggle alerts"""
        if self.is_blocked:
            self.show_notification("Access blocked", "error")
            return
        
        self.alerts_enabled = not self.alerts_enabled
        self.send_command(f"ENABLE_ALERTS:{self.alerts_enabled}")
        
        status = "enabled" if self.alerts_enabled else "disabled"
        self.show_notification(f"Alerts {status}", "info")
    
    def trigger_manual_alert(self):
        """Trigger manual alert"""
        if self.is_blocked:
            self.show_notification("Access blocked", "error")
            return
        
        if not self.connected:
            self.show_notification("Not connected!", "error")
            return
        
        alert_data = {
            'type': 'MANUAL',
            'severity': 'HIGH',
            'details': 'Manual alert triggered by operator',
            'zone': 'All Zones'
        }
        
        self.add_alert(alert_data)
        
        # Push to Firebase
        if self.firebase and self.firebase.initialized:
            self.firebase.push_alert(alert_data)
        
        self.send_command("MANUAL_ALERT")
        self.show_notification("Manual alert triggered!", "warning")
    
    def clear_alerts(self):
        """Clear all alerts"""
        alerts_list = self.root.ids.alerts_list
        alerts_list.clear_widgets()
        self.alerts.clear()
        self.show_notification("Alerts cleared", "info")
    
    # ==================== MEDIA METHODS ====================
    def take_screenshot(self):
        """Take screenshot"""
        if self.is_blocked:
            self.show_notification("Access blocked", "error")
            return
        
        if not self.connected:
            self.show_notification("Not connected!", "error")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{Config.SCREENSHOT_DIR}/capture_{timestamp}.jpg"
            
            temp_path = f'temp_frame_{self.frame_count % 2}.jpg'
            if os.path.exists(temp_path):
                shutil.copy(temp_path, filename)
                
                if self.motion_detected:
                    alert_filename = f"{Config.ALERT_DIR}/alert_{timestamp}.jpg"
                    shutil.copy(temp_path, alert_filename)
                
                self.show_notification("Screenshot saved!", "success")
            else:
                self.show_notification("No frame available", "error")
        except Exception as e:
            self.show_notification(f"Failed: {str(e)}", "error")
    
    def toggle_recording(self):
        """Toggle recording"""
        if self.is_blocked:
            self.show_notification("Access blocked", "error")
            return
        
        if not self.connected:
            self.show_notification("Not connected!", "error")
            return
        
        if not self.recording:
            self.recording = True
            self.recording_start = datetime.now()
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for i, frame in enumerate(self.recorded_frames):
                filename = f"{Config.RECORDING_DIR}/rec_{timestamp}_frame_{i:04d}.jpg"
                with open(filename, 'wb') as f:
                    f.write(frame)
            
            self.show_notification(f"Saved {len(self.recorded_frames)} frames", "success")
        except Exception as e:
            self.show_notification(f"Save failed: {str(e)}", "error")
    
    # ==================== UI METHODS ====================
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
    
    def show_zones(self):
        """Show zones configuration"""
        if 'zones' not in self.dialogs:
            self.dialogs['zones'] = MDDialog(
                title="Monitoring Zones",
                text="Zone Configuration:\n\n"
                     "🟢 Zone 1: Entry Point - ACTIVE\n"
                     "🟢 Zone 2: Perimeter - ACTIVE\n"
                     "🟢 Zone 3: Restricted Area - ACTIVE\n"
                     "🟢 Zone 4: Parking - ACTIVE\n\n"
                     "All zones are being monitored with motion detection enabled.",
                buttons=[MDRaisedButton(text="OK", on_release=lambda x: self.dialogs['zones'].dismiss())]
            )
        
        self.dialogs['zones'].open()
    
    def show_settings(self):
        """Show settings"""
        if 'settings' not in self.dialogs:
            display_ip = self.firebase.user_id.replace('-', '.') if self.firebase and self.firebase.user_id else 'N/A'
            self.dialogs['settings'] = MDDialog(
                title="Security Settings",
                text=f"Current Configuration:\n\n"
                     f"• User ID (IP): {display_ip}\n"
                     f"• Motion Detection: {'Enabled' if self.motion_enabled else 'Disabled'}\n"
                     f"• Alert System: {'Enabled' if self.alerts_enabled else 'Disabled'}\n"
                     f"• Auto-Record on Alert: Enabled\n"
                     f"• Motion Threshold: 5%\n"
                     f"• Firebase Sync: {'Connected' if self.firebase and self.firebase.initialized else 'Disconnected'}\n\n"
                     "Use the Quick Actions panel to adjust settings in real-time.",
                buttons=[MDRaisedButton(text="OK", on_release=lambda x: self.dialogs['settings'].dismiss())]
            )
        
        self.dialogs['settings'].open()
    
    def show_notification(self, message, type="info"):
        """Show notification"""
        emoji = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
        print(f"{emoji.get(type, 'ℹ️')} [{type.upper()}] {message}")


# ==================== MAIN ENTRY POINT ====================
if __name__ == '__main__':
    SecurityRadarApp().run()