"""
Security Radar Admin Panel - Modern UI Edition
Combining the robust functionality of admin.py with the sleek UI of object.py
"""

# ==================== IMPORTS ====================
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty, DictProperty
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel, MDIcon
import firebase_admin
from firebase_admin import credentials, db
import threading
from datetime import datetime, timedelta
import json
from collections import defaultdict

# ==================== FIREBASE CONFIGURATION ====================
class FirebaseConfig:
    """Firebase configuration and initialization"""
    
    CRED_PATH = "chat-c6931-firebase-adminsdk-fbsvc-1ac13d1b84.json"
    DATABASE_URL = "https://chat-c6931-default-rtdb.firebaseio.com/"
    
    USERS_PATH = "security_radar/users"
    ALERTS_PATH = "security_radar/alerts"
    STATS_PATH = "security_radar/stats"
    BLOCKED_PATH = "security_radar/blocked_users"
    SYSTEM_PATH = "security_radar/system"
    
    @staticmethod
    def initialize():
        """Initialize Firebase"""
        try:
            cred = credentials.Certificate(FirebaseConfig.CRED_PATH)
            firebase_admin.initialize_app(cred, {
                'databaseURL': FirebaseConfig.DATABASE_URL
            })
            print("✅ Firebase initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            return False


# ==================== CONFIGURATION ====================
class AdminConfig:
    """Admin panel configuration"""
    MIN_WIDTH = 1400
    MIN_HEIGHT = 900
    
    THEME_STYLE = "Dark"
    PRIMARY_PALETTE = "Blue"
    
    STATS_REFRESH = 2
    USERS_REFRESH = 2
    ALERTS_REFRESH = 3
    
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin123"


# ==================== MODERN UI LAYOUT ====================
KV = '''
#:import hex kivy.utils.get_color_from_hex

<MetricCard@BoxLayout>:
    icon: ""
    title: ""
    value: ""
    icon_color: hex("#4F46E5")
    
    orientation: 'vertical'
    padding: dp(24)
    spacing: dp(12)
    size_hint_y: None
    height: dp(140)
    
    canvas.before:
        Color:
            rgba: hex("#1F2937")
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
    
    MDIcon:
        icon: root.icon
        font_size: dp(40)
        theme_text_color: "Custom"
        text_color: root.icon_color
        size_hint_y: None
        height: dp(48)
    
    MDLabel:
        text: root.value
        font_style: "H4"
        bold: True
        theme_text_color: "Custom"
        text_color: hex("#FFFFFF")
        size_hint_y: None
        height: dp(48)
    
    MDLabel:
        text: root.title
        font_style: "Caption"
        theme_text_color: "Custom"
        text_color: hex("#9CA3AF")
        size_hint_y: None
        height: dp(20)

<NavButton@MDRaisedButton>:
    selected: False
    size_hint_y: None
    height: dp(48)
    elevation: 0
    md_bg_color: hex("#374151") if self.selected else hex("#1F2937")
    text_color: hex("#FFFFFF") if self.selected else hex("#9CA3AF")

ScreenManager:
    id: screen_manager
    
    # ==================== MODERN LOGIN SCREEN ====================
    Screen:
        name: 'login'
        
        canvas.before:
            Color:
                rgba: hex("#111827")
            Rectangle:
                pos: self.pos
                size: self.size
        
        BoxLayout:
            orientation: 'vertical'
            size_hint: None, None
            size: dp(420), dp(560)
            pos_hint: {"center_x": 0.5, "center_y": 0.5}
            padding: dp(40)
            spacing: dp(24)
            
            canvas.before:
                Color:
                    rgba: hex("#1F2937")
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(16)]
            
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(120)
                spacing: dp(12)
                
                MDIcon:
                    icon: "shield-check"
                    font_size: dp(72)
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: hex("#4F46E5")
                    size_hint_y: None
                    height: dp(80)
                
                MDLabel:
                    text: "Security Radar"
                    font_style: "H5"
                    halign: "center"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: hex("#FFFFFF")
                    size_hint_y: None
                    height: dp(32)
            
            MDLabel:
                text: "Admin Dashboard"
                font_style: "Body1"
                halign: "center"
                theme_text_color: "Custom"
                text_color: hex("#9CA3AF")
                size_hint_y: None
                height: dp(24)
            
            Widget:
                size_hint_y: None
                height: dp(20)
            
            MDTextField:
                id: username_field
                hint_text: "Username"
                icon_left: "account"
                size_hint_y: None
                height: dp(56)
                font_size: dp(16)
                text_color_normal: hex("#FFFFFF")
                line_color_normal: hex("#374151")
                line_color_focus: hex("#4F46E5")
            
            MDTextField:
                id: password_field
                hint_text: "Password"
                icon_left: "lock"
                password: True
                size_hint_y: None
                height: dp(56)
                font_size: dp(16)
                text_color_normal: hex("#FFFFFF")
                line_color_normal: hex("#374151")
                line_color_focus: hex("#4F46E5")
            
            Widget:
                size_hint_y: None
                height: dp(16)
            
            MDRaisedButton:
                text: "SIGN IN"
                size_hint_x: 1
                size_hint_y: None
                height: dp(52)
                font_size: dp(15)
                bold: True
                md_bg_color: hex("#4F46E5")
                on_release: app.login()
            
            MDLabel:
                text: "v2.0 | Security Monitoring System"
                font_style: "Caption"
                halign: "center"
                theme_text_color: "Custom"
                text_color: hex("#6B7280")
                size_hint_y: None
                height: dp(24)
    
    # ==================== MODERN DASHBOARD ====================
    Screen:
        name: 'dashboard'
        
        canvas.before:
            Color:
                rgba: hex("#111827")
            Rectangle:
                pos: self.pos
                size: self.size
        
        BoxLayout:
            orientation: 'horizontal'
            spacing: 0
            
            # ==================== SIDEBAR ====================
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: None
                width: dp(260)
                padding: [0, dp(20), 0, dp(20)]
                spacing: dp(8)
                
                canvas.before:
                    Color:
                        rgba: hex("#1F2937")
                    Rectangle:
                        pos: self.pos
                        size: self.size
                
                # Logo
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(60)
                    padding: [dp(20), 0]
                    spacing: dp(12)
                    
                    MDIcon:
                        icon: "shield-check"
                        font_size: dp(36)
                        theme_text_color: "Custom"
                        text_color: hex("#4F46E5")
                        size_hint_x: None
                        width: dp(40)
                    
                    MDLabel:
                        text: "Security Radar"
                        font_style: "H6"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: hex("#FFFFFF")
                        valign: "center"
                
                # Navigation
                ScrollView:
                    do_scroll_x: False
                    
                    BoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(4)
                        padding: [dp(12), 0]
                        
                        NavButton:
                            text: "  Dashboard"
                            icon: "view-dashboard"
                            selected: app.current_section == 'dashboard'
                            on_release: app.show_section('dashboard')
                        
                        NavButton:
                            text: "  Active Users"
                            icon: "account-group"
                            selected: app.current_section == 'users'
                            on_release: app.show_section('users')
                        
                        NavButton:
                            text: "  Security Alerts"
                            icon: "shield-alert"
                            selected: app.current_section == 'alerts'
                            on_release: app.show_section('alerts')
                        
                        NavButton:
                            text: "  Blocked Users"
                            icon: "account-cancel"
                            selected: app.current_section == 'blocked'
                            on_release: app.show_section('blocked')
                        
                        NavButton:
                            text: "  Analytics"
                            icon: "chart-line"
                            selected: app.current_section == 'analytics'
                            on_release: app.show_section('analytics')
                        
                        Widget:
                            size_hint_y: None
                            height: dp(32)
                        
                        MDLabel:
                            text: "SYSTEM"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: hex("#6B7280")
                            padding: [dp(12), 0]
                            size_hint_y: None
                            height: dp(32)
                        
                        NavButton:
                            text: "  Settings"
                            icon: "cog"
                            selected: app.current_section == 'settings'
                            on_release: app.show_section('settings')
                
                # Bottom actions
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(140)
                    padding: [dp(12), dp(12)]
                    spacing: dp(12)
                    
                    canvas.before:
                        Color:
                            rgba: hex("#374151")
                        Line:
                            points: [self.x, self.top, self.right, self.top]
                            width: 1
                    
                    MDRaisedButton:
                        text: "  Sign Out"
                        icon: "logout"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(48)
                        md_bg_color: hex("#DC2626")
                        on_release: app.logout()
                    
                    MDLabel:
                        text: f"Uptime: {app.system_uptime}"
                        font_style: "Caption"
                        halign: "center"
                        theme_text_color: "Custom"
                        text_color: hex("#6B7280")
                        size_hint_y: None
                        height: dp(20)
                    
                    MDIconButton:
                        icon: "information"
                        theme_text_color: "Custom"
                        text_color: hex("#9CA3AF")
                        pos_hint: {"center_x": 0.5}
                        on_release: app.show_info()
            
            # ==================== MAIN CONTENT ====================
            BoxLayout:
                orientation: 'vertical'
                
                # Top Bar
                BoxLayout:
                    orientation: 'horizontal'
                    size_hint_y: None
                    height: dp(70)
                    padding: [dp(32), 0]
                    spacing: dp(16)
                    
                    canvas.before:
                        Color:
                            rgba: hex("#1F2937")
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: dp(4)
                        
                        MDLabel:
                            text: "Security Monitoring Dashboard"
                            font_style: "H6"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: hex("#FFFFFF")
                            size_hint_y: None
                            height: dp(28)
                        
                        MDLabel:
                            text: f"Real-time System • {app.active_users_count} Active Users"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: hex("#9CA3AF")
                            size_hint_y: None
                            height: dp(20)
                    
                    Widget:
                    
                    MDIconButton:
                        icon: "refresh"
                        theme_text_color: "Custom"
                        text_color: hex("#4F46E5")
                        on_release: app.refresh_data()
                        size_hint: None, None
                        size: dp(40), dp(40)
                    
                    MDIconButton:
                        icon: "bell"
                        theme_text_color: "Custom"
                        text_color: hex("#9CA3AF")
                        size_hint: None, None
                        size: dp(40), dp(40)
                
                # Content Area
                ScrollView:
                    do_scroll_x: False
                    
                    BoxLayout:
                        id: main_content
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        padding: dp(32)
                        spacing: dp(24)
'''


# ==================== MAIN APPLICATION CLASS ====================
class SecurityRadarAdminApp(MDApp):
    """Main admin panel application with modern UI"""
    
    active_users_count = StringProperty("0")
    total_alerts_count = StringProperty("0")
    blocked_users_count = StringProperty("0")
    system_uptime = StringProperty("0h 0m")
    current_section = StringProperty("dashboard")
    
    users_data = DictProperty({})
    alerts_data = ListProperty([])
    blocked_users = ListProperty([])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logged_in = False
        self.firebase_initialized = False
        self.system_start_time = datetime.now()
        self.users_ref = None
        self.alerts_ref = None
        self.blocked_ref = None
        self.stats_ref = None
        self.refresh_scheduled = False
        
    def build(self):
        """Build the application"""
        self.theme_cls.theme_style = AdminConfig.THEME_STYLE
        self.theme_cls.primary_palette = AdminConfig.PRIMARY_PALETTE
        self.title = "Security Radar - Modern Admin Dashboard"
        
        Window.size = (AdminConfig.MIN_WIDTH, AdminConfig.MIN_HEIGHT)
        Window.minimum_width = AdminConfig.MIN_WIDTH
        Window.minimum_height = AdminConfig.MIN_HEIGHT
        
        self.firebase_initialized = FirebaseConfig.initialize()
        
        if self.firebase_initialized:
            self.setup_firebase_references()
        
        return Builder.load_string(KV)
    
    def on_start(self):
        """Called when app starts"""
        Clock.schedule_interval(self.update_stats, AdminConfig.STATS_REFRESH)
        Clock.schedule_interval(self.update_system_uptime, 1)
        Clock.schedule_interval(self.auto_refresh_current_section, AdminConfig.USERS_REFRESH)
    
    def setup_firebase_references(self):
        """Setup Firebase database references"""
        try:
            self.users_ref = db.reference(FirebaseConfig.USERS_PATH)
            self.alerts_ref = db.reference(FirebaseConfig.ALERTS_PATH)
            self.blocked_ref = db.reference(FirebaseConfig.BLOCKED_PATH)
            self.stats_ref = db.reference(FirebaseConfig.STATS_PATH)
            print("✅ Firebase references configured")
        except Exception as e:
            print(f"❌ Firebase reference error: {e}")
    
    def login(self):
        """Handle login"""
        if not self.root:
            print("❌ Root widget not available")
            return
            
        username = self.root.ids.username_field.text
        password = self.root.ids.password_field.text
        
        if username == AdminConfig.ADMIN_USERNAME and password == AdminConfig.ADMIN_PASSWORD:
            self.logged_in = True
            Clock.schedule_once(lambda dt: self._complete_login(), 0.1)
        else:
            self.show_error_dialog("Invalid credentials", "Please check your username and password")
    
    def _complete_login(self):
        """Complete login process"""
        self.root.current = "dashboard"
        self.refresh_data()
        self.show_section('dashboard')
        print("✅ Login successful")
    
    def logout(self):
        """Handle logout"""
        self.logged_in = False
        self.root.current = 'login'
        self.root.ids.username_field.text = ""
        self.root.ids.password_field.text = ""
        print("✅ Logged out")
    
    def refresh_data(self):
        """Refresh all data from Firebase"""
        if not self.firebase_initialized:
            print("⚠️ Firebase not initialized")
            return
        
        if self.refresh_scheduled:
            return
        
        self.refresh_scheduled = True
        threading.Thread(target=self._load_data_thread, daemon=True).start()
    
    def _load_data_thread(self):
        """Load data in background thread"""
        try:
            users = self.users_ref.get() or {}
            alerts = self.alerts_ref.get() or {}
            blocked = self.blocked_ref.get() or {}
            
            Clock.schedule_once(lambda dt: self._update_data(users, alerts, blocked), 0)
            
            print("✅ Data refreshed")
        except Exception as e:
            print(f"❌ Refresh error: {e}")
        finally:
            self.refresh_scheduled = False
    
    def _update_data(self, users, alerts, blocked):
        """Update data in main thread"""
        self.users_data = dict(users) if users else {}
        self.alerts_data = [v for k, v in alerts.items()] if isinstance(alerts, dict) else []
        self.blocked_users = list(blocked.keys()) if isinstance(blocked, dict) else []
        
        self.update_stats(0)
        
        if self.logged_in:
            self._update_section_content(self.current_section)
    
    def auto_refresh_current_section(self, dt):
        """Auto-refresh current section"""
        if self.logged_in and not self.refresh_scheduled:
            self.refresh_data()
    
    def update_stats(self, dt):
        """Update statistics"""
        active_count = 0
        current_time = datetime.now().timestamp()
        
        for user_id, user_data in self.users_data.items():
            if isinstance(user_data, dict):
                last_seen = user_data.get('last_seen', 0)
                if current_time - last_seen < 30:
                    active_count += 1
        
        self.active_users_count = str(active_count)
        self.total_alerts_count = str(len(self.alerts_data))
        self.blocked_users_count = str(len(self.blocked_users))
    
    def update_system_uptime(self, dt):
        """Update system uptime"""
        uptime = datetime.now() - self.system_start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        self.system_uptime = f"{hours}h {minutes}m"
    
    def show_section(self, section):
        """Show specific section"""
        self.current_section = section
        Clock.schedule_once(lambda dt: self._update_section_content(section), 0)
    
    def _update_section_content(self, section):
        """Update section content"""
        try:
            content = self.root.ids.main_content
            content.clear_widgets()
            
            if section == 'dashboard':
                self.display_dashboard_section()
            elif section == 'users':
                self.display_users_section()
            elif section == 'alerts':
                self.display_alerts_section()
            elif section == 'blocked':
                self.display_blocked_section()
            elif section == 'analytics':
                self.display_analytics_section()
            elif section == 'settings':
                self.display_settings_section()
        except Exception as e:
            print(f"❌ Section update error: {e}")
    
    def display_dashboard_section(self):
        """Display dashboard with metrics"""
        from kivy.utils import get_color_from_hex as hex
        content = self.root.ids.main_content
        
        # Top metrics row
        metrics_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(140),
            spacing=dp(24)
        )
        
        metrics = [
            ("account-multiple", "Active Users", self.active_users_count, hex("#3B82F6")),
            ("bell-ring", "Total Alerts", self.total_alerts_count, hex("#F59E0B")),
            ("account-cancel", "Blocked Users", self.blocked_users_count, hex("#EF4444")),
            ("clock-outline", "System Uptime", self.system_uptime, hex("#10B981"))
        ]
        
        for icon, title, value, color in metrics:
            card = self.create_metric_card(icon, title, value, color)
            metrics_row.add_widget(card)
        
        content.add_widget(metrics_row)
        
        # Recent activity
        activity_card = self.create_card("Recent Security Events", "history")
        
        recent_alerts = sorted(
            self.alerts_data,
            key=lambda x: x.get('timestamp', '') if isinstance(x, dict) else '',
            reverse=True
        )[:8]
        
        if recent_alerts:
            for alert in recent_alerts:
                if isinstance(alert, dict):
                    alert_row = self.create_alert_row(alert)
                    activity_card.add_widget(alert_row)
        else:
            activity_card.add_widget(self.create_label("No recent events", "#9CA3AF"))
        
        content.add_widget(activity_card)
    
    def display_users_section(self):
        """Display active users"""
        from kivy.utils import get_color_from_hex as hex
        content = self.root.ids.main_content
        
        users_card = self.create_card(f"Active Users ({len(self.users_data)} total)", "account-group")
        
        if self.users_data:
            for user_id, user_data in self.users_data.items():
                if isinstance(user_data, dict):
                    user_card = self.create_user_card(user_id, user_data)
                    users_card.add_widget(user_card)
                    users_card.add_widget(Widget(size_hint_y=None, height=dp(12)))
        else:
            users_card.add_widget(self.create_label("No users found", "#9CA3AF"))
        
        content.add_widget(users_card)
    
    def display_alerts_section(self):
        """Display security alerts"""
        content = self.root.ids.main_content
        
        alerts_card = self.create_card(f"Security Alerts ({len(self.alerts_data)} total)", "shield-alert")
        
        sorted_alerts = sorted(
            self.alerts_data,
            key=lambda x: x.get('timestamp', '') if isinstance(x, dict) else '',
            reverse=True
        )[:25]
        
        if sorted_alerts:
            for alert in sorted_alerts:
                if isinstance(alert, dict):
                    alert_card = self.create_alert_card(alert)
                    alerts_card.add_widget(alert_card)
                    alerts_card.add_widget(Widget(size_hint_y=None, height=dp(8)))
        else:
            alerts_card.add_widget(self.create_label("No alerts recorded", "#9CA3AF"))
        
        content.add_widget(alerts_card)
    
    def display_blocked_section(self):
        """Display blocked users"""
        from kivy.utils import get_color_from_hex as hex
        content = self.root.ids.main_content
        
        blocked_card = self.create_card(f"Blocked Users ({len(self.blocked_users)} total)", "account-cancel")
        
        if self.blocked_users:
            for user_id in self.blocked_users:
                user_data = self.users_data.get(user_id, {})
                ip_address = user_data.get('ip_address', user_id.replace('-', '.'))
                
                user_box = MDBoxLayout(
                    orientation='horizontal',
                    padding=dp(20),
                    spacing=dp(20),
                    size_hint_y=None,
                    height=dp(80)
                )
                
                with user_box.canvas.before:
                    Color(rgba=hex("#1F2937"))
                    user_box.bg_rect = RoundedRectangle(pos=user_box.pos, size=user_box.size, radius=[dp(12)])
                
                user_box.bind(pos=self._update_card_bg, size=self._update_card_bg)
                
                icon = MDIcon(
                    icon="account-off",
                    theme_text_color="Custom",
                    text_color=hex("#EF4444"),
                    size_hint_x=None,
                    width=dp(40),
                    font_size=dp(36)
                )
                
                user_label = self.create_label(f"🚫 IP: {ip_address}", "#FFFFFF")
                
                unblock_btn = MDRaisedButton(
                    text="Unblock",
                    size_hint=(None, None),
                    size=(dp(120), dp(44)),
                    md_bg_color=hex("#10B981"),
                    on_release=lambda x, uid=user_id: self.unblock_user(uid)
                )
                
                user_box.add_widget(icon)
                user_box.add_widget(user_label)
                user_box.add_widget(Widget())
                user_box.add_widget(unblock_btn)
                
                blocked_card.add_widget(user_box)
                blocked_card.add_widget(Widget(size_hint_y=None, height=dp(12)))
        else:
            blocked_card.add_widget(self.create_label("No blocked users", "#9CA3AF"))
        
        content.add_widget(blocked_card)
    
    def display_analytics_section(self):
        """Display analytics"""
        from kivy.utils import get_color_from_hex as hex
        content = self.root.ids.main_content
        
        # Metrics row
        metrics_row = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(140),
            spacing=dp(24)
        )
        
        alert_breakdown = defaultdict(int)
        for alert in self.alerts_data:
            if isinstance(alert, dict):
                severity = alert.get('severity', 'UNKNOWN')
                alert_breakdown[severity] += 1
        
        metrics = [
            ("account-group", "Total Users", str(len(self.users_data)), hex("#3B82F6")),
            ("account-check", "Active Now", self.active_users_count, hex("#10B981")),
            ("alert-circle", "High Alerts", str(alert_breakdown.get('HIGH', 0)), hex("#EF4444")),
            ("alert", "Medium Alerts", str(alert_breakdown.get('MEDIUM', 0)), hex("#F59E0B"))
        ]
        
        for icon, title, value, color in metrics:
            card = self.create_metric_card(icon, title, value, color)
            metrics_row.add_widget(card)
        
        content.add_widget(metrics_row)
    
    def display_settings_section(self):
        """Display settings"""
        from kivy.utils import get_color_from_hex as hex
        content = self.root.ids.main_content
        
        settings_card = self.create_card("System Configuration", "cog")
        
        settings = [
            ("Database", "Firebase Realtime Database"),
            ("Auto-refresh", f"{AdminConfig.STATS_REFRESH}s"),
            ("Theme", "Dark Mode"),
            ("Version", "2.0 Modern UI")
        ]
        
        for label, value in settings:
            setting_row = MDBoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(50),
                padding=[dp(16), dp(8)],
                spacing=dp(20)
            )
            
            setting_row.add_widget(self.create_label(label, "#9CA3AF"))
            setting_row.add_widget(Widget())
            setting_row.add_widget(self.create_label(value, "#FFFFFF"))
            
            settings_card.add_widget(setting_row)
        
        # Action buttons
        actions_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(60),
            padding=[dp(16), dp(20)],
            spacing=dp(16)
        )
        
        clear_btn = MDRaisedButton(
            text="Clear All Alerts",
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(48),
            md_bg_color=hex("#EF4444"),
            on_release=lambda x: self.clear_all_alerts()
        )
        
        refresh_btn = MDRaisedButton(
            text="Refresh Data",
            size_hint_x=0.5,
            size_hint_y=None,
            height=dp(48),
            md_bg_color=hex("#4F46E5"),
            on_release=lambda x: self.refresh_data()
        )
        
        actions_box.add_widget(clear_btn)
        actions_box.add_widget(refresh_btn)
        
        settings_card.add_widget(Widget(size_hint_y=None, height=dp(20)))
        settings_card.add_widget(actions_box)
        
        content.add_widget(settings_card)
    
    # ==================== CARD CREATION METHODS ====================
    
    def create_metric_card(self, icon, title, value, icon_color):
        """Create a metric card"""
        from kivy.utils import get_color_from_hex as hex
        
        card = MDBoxLayout(
            orientation='vertical',
            padding=dp(24),
            spacing=dp(12),
            size_hint_y=None,
            height=dp(140)
        )
        
        with card.canvas.before:
            Color(rgba=hex("#1F2937"))
            card.bg_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        icon_widget = MDIcon(
            icon=icon,
            font_size=dp(40),
            theme_text_color="Custom",
            text_color=icon_color,
            size_hint_y=None,
            height=dp(48)
        )
        
        value_label = MDLabel(
            text=str(value),
            font_style="H4",
            bold=True,
            theme_text_color="Custom",
            text_color=hex("#FFFFFF"),
            size_hint_y=None,
            height=dp(48)
        )
        
        title_label = MDLabel(
            text=title,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=hex("#9CA3AF"),
            size_hint_y=None,
            height=dp(20)
        )
        
        card.add_widget(icon_widget)
        card.add_widget(value_label)
        card.add_widget(title_label)
        
        return card
    
    def create_card(self, title, icon):
        """Create a card container"""
        from kivy.utils import get_color_from_hex as hex
        
        card = MDBoxLayout(
            orientation='vertical',
            padding=dp(24),
            spacing=dp(16),
            size_hint_y=None
        )
        card.bind(minimum_height=card.setter('height'))
        
        with card.canvas.before:
            Color(rgba=hex("#1F2937"))
            card.bg_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        # Header
        header = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(16)
        )
        
        icon_widget = MDIcon(
            icon=icon,
            theme_text_color="Custom",
            text_color=hex("#4F46E5"),
            size_hint_x=None,
            width=dp(32),
            font_size=dp(28)
        )
        
        title_label = MDLabel(
            text=title,
            font_style="Subtitle1",
            bold=True,
            theme_text_color="Custom",
            text_color=hex("#FFFFFF")
        )
        
        header.add_widget(icon_widget)
        header.add_widget(title_label)
        
        card.add_widget(header)
        
        # Separator
        sep = Widget(size_hint_y=None, height=dp(1))
        with sep.canvas.before:
            Color(rgba=hex("#374151"))
            sep.line = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, v: setattr(w.line, 'pos', v),
                size=lambda w, v: setattr(w.line, 'size', v))
        card.add_widget(sep)
        
        return card
    
    def create_user_card(self, user_id, user_data):
        """Create user card"""
        from kivy.utils import get_color_from_hex as hex
        
        card = MDBoxLayout(
            orientation='horizontal',
            padding=dp(20),
            spacing=dp(20),
            size_hint_y=None,
            height=dp(90)
        )
        
        with card.canvas.before:
            Color(rgba=hex("#1F2937"))
            card.bg_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
        
        card.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        is_blocked = user_id in self.blocked_users
        last_seen = user_data.get('last_seen', 0)
        is_active = (datetime.now().timestamp() - last_seen) < 30
        alert_count = user_data.get('alert_count', 0)
        ip_address = user_data.get('ip_address', user_id.replace('-', '.'))
        fps = user_data.get('fps', 0)
        
        # Status box
        status_box = MDBoxLayout(
            orientation='vertical',
            size_hint_x=None,
            width=dp(60),
            spacing=dp(4)
        )
        
        avatar = MDIcon(
            icon="account-circle",
            theme_text_color="Custom",
            text_color=hex("#10B981") if is_active else hex("#6B7280"),
            font_size=dp(48),
            halign="center"
        )
        
        status_dot = MDLabel(
            text="🟢" if is_active else "⚫",
            font_style="Caption",
            halign="center",
            size_hint_y=None,
            height=dp(16)
        )
        
        status_box.add_widget(avatar)
        status_box.add_widget(status_dot)
        
        # User info
        info_box = MDBoxLayout(orientation='vertical', spacing=dp(6))
        
        ip_label = MDLabel(
            text=f"IP: {ip_address}",
            font_style="Subtitle2",
            bold=True,
            theme_text_color="Custom",
            text_color=hex("#FFFFFF")
        )
        
        status_text = f"Status: {'Online' if is_active else 'Offline'} • Alerts: {alert_count} • FPS: {fps}"
        status_label = MDLabel(
            text=status_text,
            font_style="Caption",
            theme_text_color="Custom",
            text_color=hex("#9CA3AF")
        )
        
        info_box.add_widget(ip_label)
        info_box.add_widget(status_label)
        
        if is_blocked:
            blocked_label = MDLabel(
                text="🚫 Access Blocked",
                font_style="Caption",
                theme_text_color="Custom",
                text_color=hex("#EF4444")
            )
            info_box.add_widget(blocked_label)
        
        # Action button
        btn_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_x=None,
            width=dp(120),
            spacing=dp(12)
        )
        
        if is_blocked:
            btn = MDRaisedButton(
                text="Unblock",
                size_hint=(None, None),
                size=(dp(100), dp(44)),
                md_bg_color=hex("#10B981"),
                on_release=lambda x: self.unblock_user(user_id)
            )
        else:
            btn = MDRaisedButton(
                text="Block",
                size_hint=(None, None),
                size=(dp(100), dp(44)),
                md_bg_color=hex("#EF4444"),
                on_release=lambda x: self.block_user(user_id)
            )
        
        btn_box.add_widget(btn)
        
        card.add_widget(status_box)
        card.add_widget(info_box)
        card.add_widget(Widget())
        card.add_widget(btn_box)
        
        return card
    
    def create_alert_row(self, alert):
        """Create alert row for dashboard"""
        from kivy.utils import get_color_from_hex as hex
        
        severity = alert.get('severity', 'LOW')
        details = alert.get('details', 'No details')
        timestamp = alert.get('timestamp', 'Unknown')
        ip_address = alert.get('ip_address', alert.get('user_id', 'Unknown'))
        
        severity_config = {
            'HIGH': (hex("#EF4444"), "alert-octagon"),
            'MEDIUM': (hex("#F59E0B"), "alert"),
            'LOW': (hex("#3B82F6"), "information")
        }
        
        color, icon_name = severity_config.get(severity, (hex("#6B7280"), "information"))
        
        alert_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(60),
            spacing=dp(16),
            padding=[dp(12), dp(8)]
        )
        
        icon = MDIcon(
            icon=icon_name,
            theme_text_color="Custom",
            text_color=color,
            size_hint_x=None,
            width=dp(32),
            font_size=dp(24)
        )
        
        info_box = MDBoxLayout(orientation='vertical', spacing=dp(4))
        
        details_label = MDLabel(
            text=f"[{severity}] {details}",
            font_style="Body2",
            theme_text_color="Custom",
            text_color=hex("#FFFFFF"),
            size_hint_y=None,
            height=dp(24)
        )
        
        meta_label = MDLabel(
            text=f"IP: {ip_address} • {timestamp}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=hex("#6B7280"),
            size_hint_y=None,
            height=dp(20)
        )
        
        info_box.add_widget(details_label)
        info_box.add_widget(meta_label)
        
        alert_box.add_widget(icon)
        alert_box.add_widget(info_box)
        
        return alert_box
    
    def create_alert_card(self, alert):
        """Create full alert card"""
        from kivy.utils import get_color_from_hex as hex
        
        severity = alert.get('severity', 'LOW')
        timestamp = alert.get('timestamp', 'Unknown')
        details = alert.get('details', 'No details')
        ip_address = alert.get('ip_address', alert.get('user_id', 'Unknown'))
        
        severity_config = {
            'HIGH': (hex("#EF4444"), "alert-octagon", "🔴"),
            'MEDIUM': (hex("#F59E0B"), "alert", "🟠"),
            'LOW': (hex("#3B82F6"), "information", "🔵")
        }
        
        color, icon_name, emoji = severity_config.get(severity, (hex("#6B7280"), "information", "⚪"))
        
        alert_box = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(80),
            padding=dp(16),
            spacing=dp(16)
        )
        
        with alert_box.canvas.before:
            Color(rgba=hex("#1F2937"))
            alert_box.bg_rect = RoundedRectangle(pos=alert_box.pos, size=alert_box.size, radius=[dp(10)])
        
        alert_box.bind(pos=self._update_card_bg, size=self._update_card_bg)
        
        icon = MDIcon(
            icon=icon_name,
            theme_text_color="Custom",
            text_color=color,
            size_hint_x=None,
            width=dp(32),
            font_size=dp(28)
        )
        
        info_box = MDBoxLayout(orientation='vertical', spacing=dp(4))
        
        details_label = MDLabel(
            text=f"{emoji} [{severity}] {details}",
            font_style="Body2",
            theme_text_color="Custom",
            text_color=hex("#FFFFFF")
        )
        
        meta_label = MDLabel(
            text=f"IP: {ip_address} • {timestamp}",
            font_style="Caption",
            theme_text_color="Custom",
            text_color=hex("#6B7280")
        )
        
        info_box.add_widget(details_label)
        info_box.add_widget(meta_label)
        
        alert_box.add_widget(icon)
        alert_box.add_widget(info_box)
        
        return alert_box
    
    def create_label(self, text, color):
        """Create a styled label"""
        from kivy.utils import get_color_from_hex as hex
        
        label = MDLabel(
            text=text,
            font_style="Body1",
            theme_text_color="Custom",
            text_color=hex(color),
            size_hint_y=None,
            height=dp(32)
        )
        return label
    
    def _update_card_bg(self, instance, value):
        """Update card background"""
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size
    
    # ==================== USER ACTIONS ====================
    
    def block_user(self, user_id):
        """Block a user"""
        try:
            self.blocked_ref.child(user_id).set(True)
            self.users_ref.child(user_id).update({
                'blocked': True,
                'blocked_at': datetime.now().isoformat()
            })
            print(f"✅ User {user_id} blocked")
            Clock.schedule_once(lambda dt: self.refresh_data(), 0.5)
        except Exception as e:
            print(f"❌ Block error: {e}")
            self.show_error_dialog("Block Error", f"Failed to block user: {str(e)}")
    
    def unblock_user(self, user_id):
        """Unblock a user"""
        try:
            self.blocked_ref.child(user_id).delete()
            self.users_ref.child(user_id).update({
                'blocked': False,
                'unblocked_at': datetime.now().isoformat()
            })
            print(f"✅ User {user_id} unblocked")
            Clock.schedule_once(lambda dt: self.refresh_data(), 0.5)
        except Exception as e:
            print(f"❌ Unblock error: {e}")
            self.show_error_dialog("Unblock Error", f"Failed to unblock user: {str(e)}")
    
    def clear_all_alerts(self):
        """Clear all alerts"""
        try:
            self.alerts_ref.delete()
            self.alerts_data = []
            print("✅ All alerts cleared")
            Clock.schedule_once(lambda dt: self.refresh_data(), 0.5)
        except Exception as e:
            print(f"❌ Clear error: {e}")
            self.show_error_dialog("Clear Error", f"Failed to clear alerts: {str(e)}")
    
    def show_error_dialog(self, title, message):
        """Show error dialog"""
        dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDRaisedButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
    
    def show_info(self):
        """Show info dialog"""
        dialog = MDDialog(
            title="Security Radar Admin Panel",
            text="Version 2.0 Modern UI Edition\n\n"
                 "Real-time security monitoring system\n"
                 "powered by Firebase Realtime Database.\n\n"
                 "Features:\n"
                 "• Live user monitoring with IP tracking\n"
                 "• Advanced alert management\n"
                 "• User access control\n"
                 "• Comprehensive analytics\n"
                 "• Modern, responsive UI\n"
                 "• Auto-refresh every 2 seconds\n\n"
                 "© 2024 Security Radar",
            buttons=[
                MDRaisedButton(
                    text="OK",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()


if __name__ == '__main__':

    SecurityRadarAdminApp().run()
