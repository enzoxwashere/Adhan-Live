
"""
Adhan Live - Professional Prayer Times Display
A beautiful TUI application for displaying Islamic prayer times
"""

import os
import sys
import json
import time
import argparse
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

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    from rich import box
except ImportError:
    print("Error: 'rich' module not found. Install it with: pip install rich")
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
        "enabled_prayers": ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"],
        "volume": 100,
        "language": "en",
        "mute": False
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "adhan-live"
        self.config_file = self.config_dir / "config.json"
        self.config = self.load()
    
    def load(self) -> Dict:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**self.DEFAULT_CONFIG, **config}
            except Exception:
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save(self):
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set configuration value"""
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
        """Get location from IP"""
        try:
            response = self.session.get(self.LOCATION_API, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'city': data.get('city', 'Unknown'),
                        'country': data.get('country', 'Unknown'),
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'timezone': data.get('timezone')
                    }
        except Exception:
            pass
        return None
    
    def fetch_prayer_times(self, date: Optional[datetime] = None) -> Optional[Dict]:
        """Fetch prayer times from API"""
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
        
        try:
            url = f"{self.BASE_URL}/timings/{date.strftime('%d-%m-%Y')}"
            params = {
                'latitude': lat,
                'longitude': lon,
                'method': self.config.get('calculation_method', 4)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 200:
                    return data['data']
        except Exception:
            pass
        
        return None


# ============================================================================
# Prayer Times Manager
# ============================================================================

class PrayerTimesManager:
    """Manages prayer times and calculations"""
    
    PRAYER_COLORS = {
        'Fajr': 'magenta',
        'Dhuhr': 'yellow',
        'Asr': 'cyan',
        'Maghrib': 'red',
        'Isha': 'blue'
    }
    
    PRAYER_ICONS = {
        'Fajr': '🌅',
        'Dhuhr': '☀️',
        'Asr': '🌤️',
        'Maghrib': '🌆',
        'Isha': '🌙'
    }
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.api = PrayerTimesAPI(config)
        self.prayer_times: Dict[str, datetime] = {}
        self.hijri_date = ""
        self.location_data = None
        self.timezone = None
    
    def update(self) -> bool:
        """Update prayer times from API"""
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
        """Get next prayer name and time"""
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
        """Calculate time remaining until target"""
        now = datetime.now(self.timezone) if self.timezone else datetime.now()
        diff = target_time - now
        
        if diff.total_seconds() < 0:
            return (0, 0, 0)
        
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        seconds = diff.seconds % 60
        
        return (hours, minutes, seconds)
    
    def is_prayer_time(self, prayer: str) -> bool:
        """Check if it's time for a specific prayer"""
        if prayer not in self.prayer_times:
            return False
        
        now = datetime.now(self.timezone) if self.timezone else datetime.now()
        prayer_time = self.prayer_times[prayer]
        
        return abs((now - prayer_time).total_seconds()) < 60


# ============================================================================
# Audio Player
# ============================================================================

class AudioPlayer:
    """Handles audio playback in separate thread"""
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.is_playing = False
        self.thread = None
    
    def play(self, audio_file: str):
        """Play audio file in separate thread"""
        if self.config.get('mute', False):
            return
        
        if self.is_playing:
            return
        
        self.thread = threading.Thread(target=self._play_audio, args=(audio_file,), daemon=True)
        self.thread.start()
    
    def _play_audio(self, audio_file: str):
        """Internal method to play audio"""
        if not Path(audio_file).exists():
            return
        
        self.is_playing = True
        
        try:
            players = [
                (['mpv', '--no-video', '--really-quiet', audio_file], True),
                (['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', audio_file], True),
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
        """Send desktop notification"""
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
# UI Renderer
# ============================================================================

class UIRenderer:
    """Renders the TUI using Rich library"""
    
    def __init__(self, prayer_manager: PrayerTimesManager):
        self.prayer_manager = prayer_manager
        self.console = Console()
    
    def create_header(self) -> Panel:
        """Create header panel"""
        pm = self.prayer_manager
        
        title = Text("🕌 ADHAN LIVE - PRAYER TIMES", style="bold cyan", justify="center")
        
        info_lines = []
        
        if pm.location_data:
            city = pm.location_data.get('city', 'Unknown')
            country = pm.location_data.get('country', 'Unknown')
            lat = pm.location_data.get('lat', 0)
            lon = pm.location_data.get('lon', 0)
            
            info_lines.append(f"📍 Location: {city}, {country}")
            info_lines.append(f"🌐 Coordinates: {lat:.4f}, {lon:.4f}")
        
        now = datetime.now()
        info_lines.append(f"📅 Date: {now.strftime('%A, %B %d, %Y')}")
        
        if pm.hijri_date:
            info_lines.append(f"🌙 Hijri: {pm.hijri_date}")
        
        info_lines.append(f"⏰ Time: {now.strftime('%H:%M:%S')}")
        
        content = "\n".join(info_lines)
        
        return Panel(content, title=title, border_style="cyan", box=box.DOUBLE)
    
    def create_prayer_table(self) -> Table:
        """Create prayer times table"""
        pm = self.prayer_manager
        
        table = Table(
            title="✨ PRAYER TIMES FOR TODAY ✨",
            title_style="bold white",
            border_style="cyan",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("", style="bold", width=3)
        table.add_column("", width=3)
        table.add_column("Prayer", style="bold", width=12)
        table.add_column("Time", style="bold", width=10)
        table.add_column("Status", style="dim", width=15)
        
        now = datetime.now(pm.timezone) if pm.timezone else datetime.now()
        
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if prayer not in pm.prayer_times:
                continue
            
            prayer_time = pm.prayer_times[prayer]
            color = pm.PRAYER_COLORS.get(prayer, 'white')
            icon = pm.PRAYER_ICONS.get(prayer, '🕌')
            
            if prayer_time < now:
                status = "✓"
                status_style = "green"
                time_style = "dim"
                remaining = "Completed"
            else:
                status = "○"
                status_style = "yellow"
                time_style = "bright_white"
                
                hours, minutes, _ = pm.get_time_remaining(prayer_time)
                remaining = f"{hours}h {minutes}m"
            
            table.add_row(
                f"[{status_style}]{status}[/]",
                icon,
                f"[{color}]{prayer}[/]",
                f"[{time_style}]{prayer_time.strftime('%H:%M')}[/]",
                f"[dim]{remaining}[/]"
            )
        
        return table
    
    def create_next_prayer_panel(self) -> Optional[Panel]:
        """Create next prayer panel with progress bar"""
        pm = self.prayer_manager
        
        next_prayer_data = pm.get_next_prayer()
        if not next_prayer_data:
            return None
        
        prayer, prayer_time = next_prayer_data
        hours, minutes, seconds = pm.get_time_remaining(prayer_time)
        
        color = pm.PRAYER_COLORS.get(prayer, 'white')
        icon = pm.PRAYER_ICONS.get(prayer, '🕌')
        
        lines = []
        lines.append(f"{icon}  [bold {color}]NEXT PRAYER: {prayer.upper()}[/]  {icon}")
        lines.append("")
        lines.append(f"⏰ Time: [bold white]{prayer_time.strftime('%H:%M')}[/]")
        lines.append("")
        lines.append(f"⏳ Countdown: [bold green]{hours:02d}[/]h [bold green]{minutes:02d}[/]m [bold green]{seconds:02d}[/]s")
        
        now = datetime.now(pm.timezone) if pm.timezone else datetime.now()
        total_seconds = (prayer_time - now).total_seconds()
        
        prev_prayer_time = now.replace(hour=0, minute=0, second=0)
        for p in ['Isha', 'Maghrib', 'Asr', 'Dhuhr', 'Fajr']:
            if p in pm.prayer_times and pm.prayer_times[p] < now:
                prev_prayer_time = pm.prayer_times[p]
                break
        
        total_duration = (prayer_time - prev_prayer_time).total_seconds()
        elapsed = (now - prev_prayer_time).total_seconds()
        progress_percent = min(100, max(0, (elapsed / total_duration) * 100)) if total_duration > 0 else 0
        
        bar_width = 40
        filled = int((progress_percent / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append("")
        lines.append(f"[{color}]{bar}[/] {progress_percent:.1f}%")
        
        content = "\n".join(lines)
        
        return Panel(
            content,
            border_style=color,
            box=box.DOUBLE,
            padding=(1, 2)
        )
    
    def create_footer(self) -> Text:
        """Create footer text"""
        return Text("Press Ctrl+C to exit", style="dim", justify="center")
    
    def render_live_view(self) -> Layout:
        """Create complete live view layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=9),
            Layout(name="table", size=12),
            Layout(name="next", size=10),
            Layout(name="footer", size=1)
        )
        
        layout["header"].update(self.create_header())
        layout["table"].update(self.create_prayer_table())
        
        next_panel = self.create_next_prayer_panel()
        if next_panel:
            layout["next"].update(next_panel)
        
        layout["footer"].update(self.create_footer())
        
        return layout
    
    def print_today(self):
        """Print today's prayer times (static)"""
        self.console.print(self.create_header())
        self.console.print()
        self.console.print(self.create_prayer_table())
    
    def print_next(self):
        """Print next prayer only (static)"""
        next_panel = self.create_next_prayer_panel()
        if next_panel:
            self.console.print(next_panel)
        else:
            self.console.print("[yellow]No upcoming prayer found[/]")


# ============================================================================
# Main Application
# ============================================================================

class AdhanLiveApp:
    """Main application controller"""
    
    def __init__(self, args):
        self.args = args
        self.config = ConfigManager()
        
        if args.mute:
            self.config.set('mute', True)
        
        self.prayer_manager = PrayerTimesManager(self.config)
        self.audio_player = AudioPlayer(self.config)
        self.ui = UIRenderer(self.prayer_manager)
        self.console = Console()
        
        self.last_played_prayer = None
        self.last_update_date = None
    
    def initialize(self) -> bool:
        """Initialize application and fetch prayer times"""
        self.console.print("[cyan]Fetching prayer times...[/]")
        
        if not self.prayer_manager.update():
            self.console.print("[red]Failed to fetch prayer times from API[/]")
            return False
        
        self.console.print("[green]Prayer times fetched successfully![/]")
        time.sleep(1)
        
        return True
    
    def check_prayer_time(self):
        """Check if it's prayer time and play adhan"""
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if self.prayer_manager.is_prayer_time(prayer) and prayer != self.last_played_prayer:
                audio_file = self.config.get('audio_file')
                self.audio_player.play(audio_file)
                
                title = "🕌 Adhan Live"
                message = f"It's time for {prayer} prayer!"
                self.audio_player.send_notification(title, message)
                
                self.last_played_prayer = prayer
                break
    
    def update_if_needed(self):
        """Update prayer times if date changed"""
        current_date = datetime.now().date()
        if self.last_update_date != current_date:
            self.prayer_manager.update()
            self.last_update_date = current_date
            self.last_played_prayer = None
    
    def run_live(self):
        """Run live view with auto-refresh"""
        if not self.initialize():
            return
        
        self.last_update_date = datetime.now().date()
        
        try:
            with Live(self.ui.render_live_view(), refresh_per_second=1, console=self.console) as live:
                while True:
                    self.update_if_needed()
                    self.check_prayer_time()
                    live.update(self.ui.render_live_view())
                    time.sleep(1)
        except KeyboardInterrupt:
            self.console.print()
            self.console.print(Panel(
                "[green]May Allah accept your prayers! 🕌[/]",
                title="[yellow]✨ Program Stopped ✨[/]",
                border_style="magenta",
                box=box.DOUBLE
            ))
            self.console.print()
    
    def run_today(self):
        """Show today's prayer times only"""
        if not self.initialize():
            return
        self.ui.print_today()
    
    def run_next(self):
        """Show next prayer only"""
        if not self.initialize():
            return
        self.ui.print_next()


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Adhan Live - Professional Prayer Times Display",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--today', action='store_true', help='Show today\'s prayer times only')
    parser.add_argument('--next', action='store_true', help='Show next prayer only')
    parser.add_argument('--mute', action='store_true', help='Mute adhan sound')
    parser.add_argument('--version', action='version', version='Adhan Live 2.0.0')
    
    args = parser.parse_args()
    
    app = AdhanLiveApp(args)
    
    if args.today:
        app.run_today()
    elif args.next:
        app.run_next()
    else:
        app.run_live()


if __name__ == '__main__':
    main()
