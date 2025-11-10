#!/usr/bin/env python3
"""
Adhan Live GUI - Professional Prayer Times Display
A beautiful GUI application for displaying Islamic prayer times
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Gdk, Pango
import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Install it with: pip install requests")
    sys.exit(1)


# ============================================================================
# Configuration Manager
# ============================================================================

class ConfigManager:
    """Manages application configuration"""
    
    DEFAULT_CONFIG = {
        "audio_file": "a1.mp3",
        "calculation_method": 4,
        "auto_detect_location": True,
        "latitude": None,
        "longitude": None,
        "timezone": None,
        "city": None,
        "country": None,
        "enabled_prayers": ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"],
        "volume": 100,
        "language": "en",
        "mute": False,
        "theme": "auto",
        "retry_attempts": 3,
        "retry_delay": 2,
        "window_width": 600,
        "window_height": 500
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "adhan-live"
        self.config_file = self.config_dir / "config.json"
        self.config = self.load()
    
    def load(self) -> Dict:
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**self.DEFAULT_CONFIG, **config}
            except Exception:
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        self.config[key] = value
        self.save()


# ============================================================================
# Prayer Times API Client
# ============================================================================

class PrayerTimesAPI:
    """Handles API calls to Aladhan API"""
    
    BASE_URL = "http://api.aladhan.com/v1"
    LOCATION_API = "http://ip-api.com/json/"
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AdhanLive/2.0'})
    
    def get_location(self) -> Optional[Dict]:
        retry_attempts = self.config.get('retry_attempts', 3)
        retry_delay = self.config.get('retry_delay', 2)
        
        for attempt in range(retry_attempts):
            try:
                response = self.session.get(self.LOCATION_API, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                if data.get('status') == 'success':
                    location = {
                        'city': data.get('city', 'Unknown'),
                        'country': data.get('country', 'Unknown'),
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'timezone': data.get('timezone')
                    }
                    self.config.set('city', location['city'])
                    self.config.set('country', location['country'])
                    return location
                    
            except Exception:
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
        
        return None
    
    def fetch_prayer_times(self, date: Optional[datetime] = None) -> Optional[Dict]:
        if date is None:
            date = datetime.now()
        
        if self.config.get('auto_detect_location'):
            location = self.get_location()
            if location:
                self.config.set('latitude', location['lat'])
                self.config.set('longitude', location['lon'])
                self.config.set('timezone', location['timezone'])
        
        lat = self.config.get('latitude')
        lon = self.config.get('longitude')
        
        if not lat or not lon:
            return None
        
        retry_attempts = self.config.get('retry_attempts', 3)
        retry_delay = self.config.get('retry_delay', 2)
        
        for attempt in range(retry_attempts):
            try:
                url = f"{self.BASE_URL}/timings/{date.strftime('%d-%m-%Y')}"
                params = {
                    'latitude': lat,
                    'longitude': lon,
                    'method': self.config.get('calculation_method', 4)
                }
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get('code') == 200:
                    return data['data']
                    
            except Exception:
                if attempt < retry_attempts - 1:
                    time.sleep(retry_delay)
        
        return None


# ============================================================================
# Prayer Times Manager
# ============================================================================

class PrayerTimesManager:
    """Manages prayer times and calculations"""
    
    PRAYER_COLORS = {
        'Fajr': '#E91E63',
        'Dhuhr': '#FFC107',
        'Asr': '#00BCD4',
        'Maghrib': '#F44336',
        'Isha': '#3F51B5'
    }
    
    PRAYER_ICONS = {
        'Fajr': '◗',
        'Dhuhr': '◉',
        'Asr': '◐',
        'Maghrib': '◖',
        'Isha': '◕'
    }
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.api = PrayerTimesAPI(config)
        self.prayer_times: Dict[str, datetime] = {}
        self.hijri_date = ""
        self.location_data = None
        self.timezone = None
    
    def update(self) -> bool:
        data = self.api.fetch_prayer_times()
        if not data:
            return False
        
        tz_name = self.config.get('timezone')
        if tz_name:
            try:
                self.timezone = ZoneInfo(tz_name)
            except Exception:
                self.timezone = None
        
        timings = data.get('timings', {})
        date_obj = datetime.now(self.timezone) if self.timezone else datetime.now()
        
        self.prayer_times = {}
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if prayer in timings:
                time_str = timings[prayer].split()[0]
                try:
                    hour, minute = map(int, time_str.split(':'))
                    prayer_time = date_obj.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    self.prayer_times[prayer] = prayer_time
                except Exception:
                    pass
        
        hijri = data.get('date', {}).get('hijri', {})
        self.hijri_date = f"{hijri.get('day', '')} {hijri.get('month', {}).get('en', '')} {hijri.get('year', '')}"
        
        self.location_data = self.api.get_location()
        
        return True
    
    def get_next_prayer(self) -> Optional[Tuple[str, datetime]]:
        now = datetime.now(self.timezone) if self.timezone else datetime.now()
        
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if prayer in self.prayer_times:
                prayer_time = self.prayer_times[prayer]
                if prayer_time > now:
                    return (prayer, prayer_time)
        
        if 'Fajr' in self.prayer_times:
            fajr_tomorrow = self.prayer_times['Fajr'] + timedelta(days=1)
            return ('Fajr', fajr_tomorrow)
        
        return None
    
    def get_time_remaining(self, target_time: datetime) -> Tuple[int, int, int]:
        now = datetime.now(self.timezone) if self.timezone else datetime.now()
        diff = target_time - now
        
        if diff.total_seconds() < 0:
            return (0, 0, 0)
        
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        seconds = diff.seconds % 60
        
        return (hours, minutes, seconds)
    
    def is_prayer_time(self, prayer: str) -> bool:
        if prayer not in self.prayer_times:
            return False
        
        now = datetime.now(self.timezone) if self.timezone else datetime.now()
        prayer_time = self.prayer_times[prayer]
        
        return abs((now - prayer_time).total_seconds()) < 60


# ============================================================================
# Audio Player
# ============================================================================

class AudioPlayer:
    """Handles audio playback"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.is_playing = False
        self.thread = None
    
    def play(self, audio_file: str):
        if self.config.get('mute', False):
            return
        
        if self.is_playing:
            return
        
        self.thread = threading.Thread(target=self._play_audio, args=(audio_file,), daemon=True)
        self.thread.start()
    
    def _play_audio(self, audio_file: str):
        if not Path(audio_file).exists():
            return
        
        self.is_playing = True
        
        try:
            volume = self.config.get('volume', 100)
            players = [
                (['mpv', '--no-video', '--really-quiet', f'--volume={volume}', audio_file], True),
                (['ffplay', '-nodisp', '-autoexit', '-volume', str(volume * 10), audio_file], True),
                (['mpg123', '-q', audio_file], True)
            ]
            
            for cmd, _ in players:
                try:
                    if subprocess.run(['which', cmd[0]], capture_output=True).returncode == 0:
                        subprocess.run(cmd, check=False, capture_output=True)
                        break
                except Exception:
                    continue
        finally:
            self.is_playing = False
    
    def send_notification(self, title: str, message: str):
        try:
            subprocess.run([
                'notify-send',
                '-u', 'critical',
                '-i', 'appointment-soon',
                title,
                message
            ], check=False, capture_output=True)
        except Exception:
            pass


# ============================================================================
# Settings Dialog
# ============================================================================

class SettingsDialog(Gtk.Dialog):
    """Settings dialog window"""
    
    def __init__(self, parent, config: ConfigManager, prayer_manager: PrayerTimesManager):
        Gtk.Dialog.__init__(
            self,
            title="⚙️ Settings - Adhan Live",
            transient_for=parent,
            flags=0
        )
        
        self.config = config
        self.prayer_manager = prayer_manager
        self.location_changed = False
        
        self.add_buttons(
            "◈ Cancel", Gtk.ResponseType.CANCEL,
            "◈ Save", Gtk.ResponseType.OK
        )
        
        self.set_default_size(500, 600)
        self.set_border_width(10)
        
        # Create notebook for tabs
        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)
        
        # Add tabs
        notebook.append_page(self.create_general_tab(), Gtk.Label(label="◈ General"))
        notebook.append_page(self.create_location_tab(), Gtk.Label(label="◉ Location"))
        notebook.append_page(self.create_audio_tab(), Gtk.Label(label="◵ Audio"))
        notebook.append_page(self.create_appearance_tab(), Gtk.Label(label="◈ Appearance"))
        notebook.append_page(self.create_about_tab(), Gtk.Label(label="◆ About"))
        
        box = self.get_content_area()
        box.add(notebook)
        
        self.show_all()
    
    def create_general_tab(self):
        """Create general settings tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Auto detect location
        self.auto_detect_check = Gtk.CheckButton(label="◉ Auto-detect location via IP")
        self.auto_detect_check.set_active(self.config.get('auto_detect_location', True))
        box.pack_start(self.auto_detect_check, False, False, 0)
        
        # Calculation method
        method_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        method_label = Gtk.Label(label="◆ Calculation Method:")
        method_label.set_halign(Gtk.Align.START)
        method_box.pack_start(method_label, False, False, 0)
        
        self.method_combo = Gtk.ComboBoxText()
        methods = [
            "University of Islamic Sciences, Karachi",
            "Islamic Society of North America",
            "Muslim World League",
            "Umm Al-Qura University, Makkah",
            "Egyptian General Authority of Survey",
            "Institute of Geophysics, University of Tehran",
            "Gulf Region",
            "Kuwait",
            "Qatar",
            "Majlis Ugama Islam Singapura, Singapore",
            "Union Organization islamic de France",
            "Diyanet İşleri Başkanlığı, Turkey",
            "Spiritual Administration of Muslims of Russia"
        ]
        for method in methods:
            self.method_combo.append_text(method)
        
        current_method = self.config.get('calculation_method', 4)
        self.method_combo.set_active(current_method - 1)
        method_box.pack_start(self.method_combo, True, True, 0)
        box.pack_start(method_box, False, False, 0)
        
        # Retry settings
        retry_frame = Gtk.Frame(label="◵ Network Settings")
        retry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        retry_box.set_border_width(10)
        
        # Retry attempts
        retry_attempts_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        retry_attempts_label = Gtk.Label(label="Retry attempts:")
        retry_attempts_label.set_halign(Gtk.Align.START)
        retry_attempts_box.pack_start(retry_attempts_label, False, False, 0)
        
        self.retry_attempts_spin = Gtk.SpinButton()
        self.retry_attempts_spin.set_adjustment(Gtk.Adjustment(
            value=self.config.get('retry_attempts', 3),
            lower=1, upper=10, step_increment=1
        ))
        retry_attempts_box.pack_start(self.retry_attempts_spin, False, False, 0)
        retry_box.pack_start(retry_attempts_box, False, False, 0)
        
        # Retry delay
        retry_delay_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        retry_delay_label = Gtk.Label(label="Retry delay (seconds):")
        retry_delay_label.set_halign(Gtk.Align.START)
        retry_delay_box.pack_start(retry_delay_label, False, False, 0)
        
        self.retry_delay_spin = Gtk.SpinButton()
        self.retry_delay_spin.set_adjustment(Gtk.Adjustment(
            value=self.config.get('retry_delay', 2),
            lower=1, upper=10, step_increment=1
        ))
        retry_delay_box.pack_start(self.retry_delay_spin, False, False, 0)
        retry_box.pack_start(retry_delay_box, False, False, 0)
        
        retry_frame.add(retry_box)
        box.pack_start(retry_frame, False, False, 0)
        
        return box
    
    def create_location_tab(self):
        """Create location settings tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Current location info
        info_frame = Gtk.Frame(label="◉ Current Location")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        info_box.set_border_width(10)
        
        city = self.config.get('city', 'Unknown')
        country = self.config.get('country', 'Unknown')
        lat = self.config.get('latitude', 0)
        lon = self.config.get('longitude', 0)
        tz = self.config.get('timezone', 'Unknown')
        
        info_label = Gtk.Label()
        info_label.set_markup(
            f"<b>City:</b> {city}\n"
            f"<b>Country:</b> {country}\n"
            f"<b>Latitude:</b> {lat:.4f}\n"
            f"<b>Longitude:</b> {lon:.4f}\n"
            f"<b>Timezone:</b> {tz}"
        )
        info_label.set_halign(Gtk.Align.START)
        info_box.pack_start(info_label, False, False, 0)
        
        info_frame.add(info_box)
        box.pack_start(info_frame, False, False, 0)
        
        # Manual location
        manual_frame = Gtk.Frame(label="◆ Manual Location (Optional)")
        manual_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        manual_box.set_border_width(10)
        
        # Latitude
        lat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lat_label = Gtk.Label(label="Latitude:")
        lat_label.set_halign(Gtk.Align.START)
        lat_label.set_size_request(100, -1)
        lat_box.pack_start(lat_label, False, False, 0)
        
        self.lat_entry = Gtk.Entry()
        self.lat_entry.set_text(str(lat))
        self.lat_entry.set_placeholder_text("e.g., 36.7405")
        lat_box.pack_start(self.lat_entry, True, True, 0)
        manual_box.pack_start(lat_box, False, False, 0)
        
        # Longitude
        lon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lon_label = Gtk.Label(label="Longitude:")
        lon_label.set_halign(Gtk.Align.START)
        lon_label.set_size_request(100, -1)
        lon_box.pack_start(lon_label, False, False, 0)
        
        self.lon_entry = Gtk.Entry()
        self.lon_entry.set_text(str(lon))
        self.lon_entry.set_placeholder_text("e.g., 3.1159")
        lon_box.pack_start(self.lon_entry, True, True, 0)
        manual_box.pack_start(lon_box, False, False, 0)
        
        # Timezone
        tz_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tz_label = Gtk.Label(label="Timezone:")
        tz_label.set_halign(Gtk.Align.START)
        tz_label.set_size_request(100, -1)
        tz_box.pack_start(tz_label, False, False, 0)
        
        self.tz_entry = Gtk.Entry()
        self.tz_entry.set_text(str(tz))
        self.tz_entry.set_placeholder_text("e.g., Africa/Algiers")
        tz_box.pack_start(self.tz_entry, True, True, 0)
        manual_box.pack_start(tz_box, False, False, 0)
        
        manual_frame.add(manual_box)
        box.pack_start(manual_frame, False, False, 0)
        
        # Help text
        help_label = Gtk.Label()
        help_label.set_markup(
            '<span size="small" style="italic">'
            'Note: Manual location will override auto-detection.\n'
            'Leave empty to use auto-detected location.'
            '</span>'
        )
        help_label.set_halign(Gtk.Align.START)
        box.pack_start(help_label, False, False, 0)
        
        return box
    
    def create_audio_tab(self):
        """Create audio settings tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Mute
        self.mute_check = Gtk.CheckButton(label="◵ Mute adhan sound")
        self.mute_check.set_active(self.config.get('mute', False))
        box.pack_start(self.mute_check, False, False, 0)
        
        # Volume
        volume_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        volume_label = Gtk.Label(label="◷ Volume:")
        volume_label.set_halign(Gtk.Align.START)
        volume_box.pack_start(volume_label, False, False, 0)
        
        self.volume_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 5
        )
        self.volume_scale.set_value(self.config.get('volume', 100))
        self.volume_scale.set_draw_value(True)
        self.volume_scale.set_value_pos(Gtk.PositionType.RIGHT)
        volume_box.pack_start(self.volume_scale, True, True, 0)
        box.pack_start(volume_box, False, False, 0)
        
        # Audio file
        audio_frame = Gtk.Frame(label="◈ Audio File")
        audio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        audio_box.set_border_width(10)
        
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        self.audio_entry = Gtk.Entry()
        self.audio_entry.set_text(self.config.get('audio_file', '/usr/share/adhan-live/a1.mp3'))
        file_box.pack_start(self.audio_entry, True, True, 0)
        
        browse_btn = Gtk.Button(label="◆ Browse")
        browse_btn.connect("clicked", self.on_browse_audio)
        file_box.pack_start(browse_btn, False, False, 0)
        
        audio_box.pack_start(file_box, False, False, 0)
        
        # Test button
        test_btn = Gtk.Button(label="◵ Test Audio")
        test_btn.connect("clicked", self.on_test_audio)
        audio_box.pack_start(test_btn, False, False, 0)
        
        audio_frame.add(audio_box)
        box.pack_start(audio_frame, False, False, 0)
        
        return box
    
    def create_appearance_tab(self):
        """Create appearance settings tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        
        # Theme
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        theme_label = Gtk.Label(label="◈ Theme:")
        theme_label.set_halign(Gtk.Align.START)
        theme_box.pack_start(theme_label, False, False, 0)
        
        self.theme_combo = Gtk.ComboBoxText()
        self.theme_combo.append_text("Auto (System)")
        self.theme_combo.append_text("Light")
        self.theme_combo.append_text("Dark")
        
        theme = self.config.get('theme', 'auto')
        theme_index = {'auto': 0, 'light': 1, 'dark': 2}.get(theme, 0)
        self.theme_combo.set_active(theme_index)
        theme_box.pack_start(self.theme_combo, True, True, 0)
        box.pack_start(theme_box, False, False, 0)
        
        # Language
        lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lang_label = Gtk.Label(label="◉ Language:")
        lang_label.set_halign(Gtk.Align.START)
        lang_box.pack_start(lang_label, False, False, 0)
        
        self.lang_combo = Gtk.ComboBoxText()
        self.lang_combo.append_text("English")
        self.lang_combo.append_text("العربية (Arabic)")
        
        lang = self.config.get('language', 'en')
        lang_index = 0 if lang == 'en' else 1
        self.lang_combo.set_active(lang_index)
        lang_box.pack_start(self.lang_combo, True, True, 0)
        box.pack_start(lang_box, False, False, 0)
        
        # Note
        note_label = Gtk.Label()
        note_label.set_markup(
            '<span size="small" style="italic">'
            'Note: Some settings require restart to take effect.'
            '</span>'
        )
        note_label.set_halign(Gtk.Align.START)
        box.pack_start(note_label, False, False, 0)
        
        return box
    
    def create_about_tab(self):
        """Create about tab"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        
        # Logo/Title
        title_label = Gtk.Label()
        title_label.set_markup(
            '<span size="xx-large" weight="bold">◈ Adhan Live ◈</span>'
        )
        box.pack_start(title_label, False, False, 10)
        
        # Version
        version_label = Gtk.Label()
        version_label.set_markup('<span size="large">Version 2.0.0</span>')
        box.pack_start(version_label, False, False, 0)
        
        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup(
            '<span size="medium">'
            'Professional Islamic prayer times display\n'
            'with beautiful TUI and GUI interfaces'
            '</span>'
        )
        desc_label.set_justify(Gtk.Justification.CENTER)
        box.pack_start(desc_label, False, False, 10)
        
        # Features
        features_label = Gtk.Label()
        features_label.set_markup(
            '<b>Features:</b>\n'
            '• Auto-detect location via IP\n'
            '• Real-time countdown with progress bar\n'
            '• Desktop notifications\n'
            '• Hijri and Gregorian dates\n'
            '• Multi-language support\n'
            '• Threaded audio playback'
        )
        features_label.set_halign(Gtk.Align.START)
        box.pack_start(features_label, False, False, 10)
        
        # Links
        links_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        github_label = Gtk.Label()
        github_label.set_markup(
            '<a href="https://github.com/enzoxwashere/Adhan-Live">◈ GitHub Repository</a>'
        )
        links_box.pack_start(github_label, False, False, 0)
        
        box.pack_start(links_box, False, False, 10)
        
        # Copyright
        copyright_label = Gtk.Label()
        copyright_label.set_markup(
            '<span size="small">© 2025 Enzo\n'
            'Licensed under MIT License</span>'
        )
        copyright_label.set_justify(Gtk.Justification.CENTER)
        box.pack_start(copyright_label, False, False, 0)
        
        return box
    
    def on_browse_audio(self, button):
        """Browse for audio file"""
        dialog = Gtk.FileChooserDialog(
            title="Select Audio File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        # Add filters
        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio files")
        filter_audio.add_mime_type("audio/*")
        dialog.add_filter(filter_audio)
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.audio_entry.set_text(dialog.get_filename())
        
        dialog.destroy()
    
    def on_test_audio(self, button):
        """Test audio playback"""
        audio_file = self.audio_entry.get_text()
        if not Path(audio_file).exists():
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Audio file not found"
            )
            dialog.format_secondary_text(f"File does not exist: {audio_file}")
            dialog.run()
            dialog.destroy()
            return
        
        # Test play
        try:
            subprocess.run(['mpv', '--no-video', '--really-quiet', audio_file], check=False, capture_output=True)
        except Exception as e:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to play audio"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()
    
    def save_settings(self):
        """Save all settings"""
        # General
        self.config.set('auto_detect_location', self.auto_detect_check.get_active())
        self.config.set('calculation_method', self.method_combo.get_active() + 1)
        self.config.set('retry_attempts', int(self.retry_attempts_spin.get_value()))
        self.config.set('retry_delay', int(self.retry_delay_spin.get_value()))
        
        # Location
        try:
            new_lat = float(self.lat_entry.get_text())
            new_lon = float(self.lon_entry.get_text())
            new_tz = self.tz_entry.get_text()
            
            old_lat = self.config.get('latitude')
            old_lon = self.config.get('longitude')
            
            if new_lat != old_lat or new_lon != old_lon:
                self.location_changed = True
                self.config.set('latitude', new_lat)
                self.config.set('longitude', new_lon)
                self.config.set('timezone', new_tz)
                self.config.set('auto_detect_location', False)
        except ValueError:
            pass
        
        # Audio
        self.config.set('mute', self.mute_check.get_active())
        self.config.set('volume', int(self.volume_scale.get_value()))
        self.config.set('audio_file', self.audio_entry.get_text())
        
        # Appearance
        theme_index = self.theme_combo.get_active()
        theme = ['auto', 'light', 'dark'][theme_index]
        self.config.set('theme', theme)
        
        lang_index = self.lang_combo.get_active()
        lang = 'en' if lang_index == 0 else 'ar'
        self.config.set('language', lang)


# ============================================================================
# Main GUI Window
# ============================================================================

class AdhanLiveWindow(Gtk.Window):
    """Main application window"""
    
    def __init__(self):
        Gtk.Window.__init__(self, title="Adhan Live")
        
        # Initialize components
        self.config = ConfigManager()
        self.prayer_manager = PrayerTimesManager(self.config)
        self.audio_player = AudioPlayer(self.config)
        
        self.last_played_prayer = None
        self.last_update_date = None
        
        # Window settings
        self.set_default_size(
            self.config.get('window_width', 600),
            self.config.get('window_height', 500)
        )
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(10)
        
        # Apply CSS styling
        self.apply_css()
        
        # Create UI
        self.create_ui()
        
        # Initialize data
        self.initialize_data()
        
        # Start update timer (every second)
        GLib.timeout_add(1000, self.update_display)
        
        # Connect signals
        self.connect("destroy", Gtk.main_quit)
        self.connect("size-allocate", self.on_window_resize)
    
    def apply_css(self):
        """Apply custom CSS styling"""
        css_provider = Gtk.CssProvider()
        css = b"""
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 10px;
        }
        
        .prayer-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 5px;
            border-left: 4px solid #667eea;
        }
        
        .prayer-box-completed {
            background: #e9ecef;
            opacity: 0.7;
        }
        
        .next-prayer {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
        }
        
        .prayer-name {
            font-size: 18px;
            font-weight: bold;
        }
        
        .prayer-time {
            font-size: 24px;
            font-weight: bold;
        }
        
        .countdown {
            font-size: 32px;
            font-weight: bold;
        }
        """
        css_provider.load_from_data(css)
        
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def create_ui(self):
        """Create the user interface"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)
        
        # Header
        self.header_box = self.create_header()
        main_box.pack_start(self.header_box, False, False, 0)
        
        # Prayer times list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.prayers_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scrolled.add(self.prayers_box)
        main_box.pack_start(scrolled, True, True, 0)
        
        # Next prayer panel
        self.next_prayer_box = self.create_next_prayer_panel()
        main_box.pack_start(self.next_prayer_box, False, False, 0)
        
        # Control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        button_box.set_halign(Gtk.Align.CENTER)
        
        refresh_btn = Gtk.Button(label="◈ Refresh")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        button_box.pack_start(refresh_btn, False, False, 0)
        
        mute_btn = Gtk.Button(label="◈ Mute/Unmute")
        mute_btn.connect("clicked", self.on_mute_clicked)
        button_box.pack_start(mute_btn, False, False, 0)
        
        settings_btn = Gtk.Button(label="◈ Settings")
        settings_btn.connect("clicked", self.on_settings_clicked)
        button_box.pack_start(settings_btn, False, False, 0)
        
        main_box.pack_start(button_box, False, False, 10)
        
        self.show_all()
    
    def create_header(self):
        """Create header section"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.get_style_context().add_class("header")
        
        # Title
        title = Gtk.Label()
        title.set_markup('<span size="x-large" weight="bold">◈ ADHAN LIVE ◈</span>')
        box.pack_start(title, False, False, 0)
        
        # Location
        self.location_label = Gtk.Label()
        self.location_label.set_markup('<span size="small">Loading location...</span>')
        box.pack_start(self.location_label, False, False, 0)
        
        # Date
        self.date_label = Gtk.Label()
        box.pack_start(self.date_label, False, False, 0)
        
        # Time
        self.time_label = Gtk.Label()
        self.time_label.set_markup('<span size="large" weight="bold">--:--:--</span>')
        box.pack_start(self.time_label, False, False, 0)
        
        return box
    
    def create_next_prayer_panel(self):
        """Create next prayer panel"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.get_style_context().add_class("next-prayer")
        
        # Prayer name
        self.next_prayer_name = Gtk.Label()
        self.next_prayer_name.set_markup('<span size="large" weight="bold">NEXT PRAYER</span>')
        box.pack_start(self.next_prayer_name, False, False, 0)
        
        # Prayer time
        self.next_prayer_time = Gtk.Label()
        self.next_prayer_time.set_markup('<span size="x-large">--:--</span>')
        box.pack_start(self.next_prayer_time, False, False, 0)
        
        # Countdown
        self.countdown_label = Gtk.Label()
        self.countdown_label.set_markup('<span size="xx-large" weight="bold">--:--:--</span>')
        box.pack_start(self.countdown_label, False, False, 0)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        box.pack_start(self.progress_bar, False, False, 5)
        
        return box
    
    def initialize_data(self):
        """Initialize prayer times data"""
        def fetch_data():
            success = self.prayer_manager.update()
            GLib.idle_add(self.on_data_loaded, success)
        
        thread = threading.Thread(target=fetch_data, daemon=True)
        thread.start()
    
    def on_data_loaded(self, success):
        """Called when data is loaded"""
        if success:
            self.update_prayer_list()
            self.update_display()
            self.last_update_date = datetime.now(self.prayer_manager.timezone).date() if self.prayer_manager.timezone else datetime.now().date()
        else:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to load prayer times"
            )
            dialog.format_secondary_text("Please check your internet connection and try again.")
            dialog.run()
            dialog.destroy()
        
        return False
    
    def update_prayer_list(self):
        """Update the prayer times list"""
        # Clear existing prayers
        for child in self.prayers_box.get_children():
            self.prayers_box.remove(child)
        
        now = datetime.now(self.prayer_manager.timezone) if self.prayer_manager.timezone else datetime.now()
        
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if prayer not in self.prayer_manager.prayer_times:
                continue
            
            prayer_time = self.prayer_manager.prayer_times[prayer]
            icon = self.prayer_manager.PRAYER_ICONS.get(prayer, '◆')
            color = self.prayer_manager.PRAYER_COLORS.get(prayer, '#000000')
            
            # Prayer box
            prayer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            prayer_box.get_style_context().add_class("prayer-box")
            
            if prayer_time < now:
                prayer_box.get_style_context().add_class("prayer-box-completed")
            
            # Icon and name
            name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            
            icon_label = Gtk.Label()
            icon_label.set_markup(f'<span size="x-large" foreground="{color}">{icon}</span>')
            name_box.pack_start(icon_label, False, False, 0)
            
            name_label = Gtk.Label()
            name_label.set_markup(f'<span size="large" weight="bold">{prayer}</span>')
            name_label.set_halign(Gtk.Align.START)
            name_box.pack_start(name_label, False, False, 0)
            
            prayer_box.pack_start(name_box, True, True, 0)
            
            # Time
            time_label = Gtk.Label()
            time_label.set_markup(f'<span size="x-large" weight="bold">{prayer_time.strftime("%H:%M")}</span>')
            prayer_box.pack_start(time_label, False, False, 0)
            
            # Status
            if prayer_time < now:
                status_label = Gtk.Label()
                status_label.set_markup('<span foreground="green">✓ Completed</span>')
                prayer_box.pack_start(status_label, False, False, 0)
            else:
                hours, minutes, _ = self.prayer_manager.get_time_remaining(prayer_time)
                remaining_label = Gtk.Label()
                remaining_label.set_markup(f'<span foreground="gray">{hours}h {minutes}m</span>')
                prayer_box.pack_start(remaining_label, False, False, 0)
            
            self.prayers_box.pack_start(prayer_box, False, False, 0)
        
        self.prayers_box.show_all()
    
    def update_display(self):
        """Update the display (called every second)"""
        # Update time - use timezone if available
        now = datetime.now(self.prayer_manager.timezone) if self.prayer_manager.timezone else datetime.now()
        self.time_label.set_markup(f'<span size="large" weight="bold">{now.strftime("%H:%M:%S")}</span>')
        
        # Update date
        date_str = now.strftime("%A, %B %d, %Y")
        hijri_str = self.prayer_manager.hijri_date if self.prayer_manager.hijri_date else ""
        self.date_label.set_markup(f'<span size="small">◆ {date_str}\n◐ {hijri_str}</span>')
        
        # Update location
        city = self.config.get('city', 'Unknown')
        country = self.config.get('country', 'Unknown')
        lat = self.config.get('latitude', 0)
        lon = self.config.get('longitude', 0)
        self.location_label.set_markup(f'<span size="small">◉ {city}, {country} ({lat:.4f}, {lon:.4f})</span>')
        
        # Update next prayer
        next_prayer_data = self.prayer_manager.get_next_prayer()
        if next_prayer_data:
            prayer, prayer_time = next_prayer_data
            icon = self.prayer_manager.PRAYER_ICONS.get(prayer, '◆')
            
            self.next_prayer_name.set_markup(f'<span size="large" weight="bold">{icon} NEXT PRAYER: {prayer.upper()} {icon}</span>')
            self.next_prayer_time.set_markup(f'<span size="x-large">◷ {prayer_time.strftime("%H:%M")}</span>')
            
            hours, minutes, seconds = self.prayer_manager.get_time_remaining(prayer_time)
            self.countdown_label.set_markup(f'<span size="xx-large" weight="bold">◵ {hours:02d}:{minutes:02d}:{seconds:02d}</span>')
            
            # Update progress bar
            total_seconds = (prayer_time - now).total_seconds()
            prev_prayer_time = now.replace(hour=0, minute=0, second=0)
            for p in ['Isha', 'Maghrib', 'Asr', 'Dhuhr', 'Fajr']:
                if p in self.prayer_manager.prayer_times and self.prayer_manager.prayer_times[p] < now:
                    prev_prayer_time = self.prayer_manager.prayer_times[p]
                    break
            
            total_duration = (prayer_time - prev_prayer_time).total_seconds()
            elapsed = (now - prev_prayer_time).total_seconds()
            progress = min(1.0, max(0.0, elapsed / total_duration)) if total_duration > 0 else 0
            
            self.progress_bar.set_fraction(progress)
            self.progress_bar.set_text(f"{progress * 100:.1f}%")
        
        # Check for prayer time
        self.check_prayer_time()
        
        # Check if date changed - use timezone if available
        current_date = datetime.now(self.prayer_manager.timezone).date() if self.prayer_manager.timezone else datetime.now().date()
        if self.last_update_date and self.last_update_date != current_date:
            self.initialize_data()
        
        return True
    
    def check_prayer_time(self):
        """Check if it's prayer time"""
        if not self.prayer_manager.prayer_times:
            return
        
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if self.prayer_manager.is_prayer_time(prayer) and prayer != self.last_played_prayer:
                audio_file = self.config.get('audio_file')
                self.audio_player.play(audio_file)
                
                self.audio_player.send_notification(
                    "◈ Adhan Live",
                    f"It's time for {prayer} prayer!"
                )
                
                self.last_played_prayer = prayer
                break
    
    def on_refresh_clicked(self, button):
        """Refresh button clicked"""
        self.initialize_data()
    
    def on_mute_clicked(self, button):
        """Mute button clicked"""
        current_mute = self.config.get('mute', False)
        self.config.set('mute', not current_mute)
        
        status = "muted" if not current_mute else "unmuted"
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"Sound {status}"
        )
        dialog.run()
        dialog.destroy()
    
    def on_settings_clicked(self, button):
        """Settings button clicked"""
        settings_dialog = SettingsDialog(self, self.config, self.prayer_manager)
        response = settings_dialog.run()
        
        if response == Gtk.ResponseType.OK:
            settings_dialog.save_settings()
            # Refresh prayer times if location changed
            if settings_dialog.location_changed:
                self.initialize_data()
        
        settings_dialog.destroy()
    
    def on_window_resize(self, widget, allocation):
        """Save window size on resize"""
        width = allocation.width
        height = allocation.height
        self.config.set('window_width', width)
        self.config.set('window_height', height)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    win = AdhanLiveWindow()
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
