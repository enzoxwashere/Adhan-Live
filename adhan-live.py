#!/usr/bin/env python3
"""
Adhan Live Console - Beautiful prayer times display
Live console with countdown timer
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ANSI Color codes
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

class AdhanLive:
    def __init__(self):
        # تحديد مسار ملف التكوين
        if os.path.exists('/etc/adhan-reminder/config.json'):
            self.config_path = '/etc/adhan-reminder/config.json'
        else:
            user_config = os.path.expanduser('~/.config/adhan-reminder/config.json')
            self.config_path = user_config
            
        self.config = self.load_config()
        self.prayer_times = {}
        self.timezone = None
        
    def load_config(self):
        """تحميل ملف التكوين"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return self.create_default_config()
        except Exception:
            return self.create_default_config()
    
    def create_default_config(self):
        """إنشاء تكوين افتراضي"""
        return {
            "audio_file": "/usr/share/adhan-reminder/a1.mp3",
            "calculation_method": 4,
            "auto_detect_location": True,
            "latitude": None,
            "longitude": None,
            "timezone": None,
            "enabled_prayers": ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"],
            "volume": 100
        }
    
    def get_location(self):
        """الحصول على الموقع الجغرافي تلقائياً"""
        try:
            response = requests.get('http://ip-api.com/json/', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    self.config['latitude'] = data['lat']
                    self.config['longitude'] = data['lon']
                    self.config['timezone'] = data['timezone']
                    self.timezone = ZoneInfo(data['timezone'])
                    return data
        except Exception:
            pass
        return None
    
    def fetch_prayer_times(self):
        """جلب أوقات الصلاة من API"""
        if self.config['auto_detect_location']:
            if not self.config['latitude'] or not self.config['longitude']:
                if not self.get_location():
                    return False
        
        try:
            lat = self.config['latitude']
            lon = self.config['longitude']
            method = self.config['calculation_method']
            
            now = datetime.now()
            
            url = f"http://api.aladhan.com/v1/timings/{now.strftime('%d-%m-%Y')}"
            params = {
                'latitude': lat,
                'longitude': lon,
                'method': method
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 200:
                    timings = data['data']['timings']
                    self.prayer_times = {
                        'Fajr': timings['Fajr'],
                        'Dhuhr': timings['Dhuhr'],
                        'Asr': timings['Asr'],
                        'Maghrib': timings['Maghrib'],
                        'Isha': timings['Isha']
                    }
                    return True
        except Exception:
            pass
        
        return False
    
    def play_adhan(self, prayer_name):
        """تشغيل صوت الأذان"""
        audio_file = self.config['audio_file']
        
        if not os.path.exists(audio_file):
            return False
        
        try:
            # إرسال إشعار
            subprocess.run([
                'notify-send',
                '-u', 'critical',
                '-i', 'appointment-soon',
                'وقت الصلاة',
                f'حان الآن وقت صلاة {prayer_name}'
            ], check=False)
            
            # تشغيل الصوت
            players = ['mpg123', 'ffplay', 'mpv']
            for player in players:
                if subprocess.run(['which', player], capture_output=True).returncode == 0:
                    if player == 'mpg123':
                        subprocess.run(['mpg123', '-q', audio_file], check=False)
                    elif player == 'ffplay':
                        subprocess.run(['ffplay', '-nodisp', '-autoexit', audio_file], 
                                     stderr=subprocess.DEVNULL, check=False)
                    elif player == 'mpv':
                        subprocess.run(['mpv', '--no-video', audio_file], check=False)
                    return True
            
            return False
            
        except Exception:
            return False
    
    def get_next_prayer(self):
        """الحصول على الصلاة القادمة"""
        if not self.prayer_times:
            return None, None
        
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        
        prayer_names_ar = {
            'Fajr': 'الفجر',
            'Dhuhr': 'الظهر',
            'Asr': 'العصر',
            'Maghrib': 'المغرب',
            'Isha': 'العشاء'
        }
        
        for prayer in self.config['enabled_prayers']:
            if prayer in self.prayer_times:
                prayer_time = self.prayer_times[prayer]
                if prayer_time > current_time:
                    return prayer, prayer_names_ar.get(prayer, prayer), prayer_time
        
        # الصلاة القادمة هي الفجر غداً
        first_prayer = self.config['enabled_prayers'][0]
        return (first_prayer, 
                prayer_names_ar.get(first_prayer, first_prayer), 
                self.prayer_times.get(first_prayer, ''))
    
    def get_time_until_prayer(self, prayer_time):
        """حساب الوقت المتبقي حتى الصلاة"""
        try:
            now = datetime.now()
            prayer_dt = datetime.strptime(prayer_time, '%H:%M').replace(
                year=now.year, month=now.month, day=now.day
            )
            
            if prayer_dt < now:
                prayer_dt += timedelta(days=1)
            
            diff = prayer_dt - now
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            seconds = diff.seconds % 60
            
            return hours, minutes, seconds
        except Exception:
            return 0, 0, 0
    
    def clear_screen(self):
        """مسح الشاشة"""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def print_header(self, location_data=None):
        """Print beautiful header with colors"""
        c = Colors
        
        # Top border with gradient effect
        print(f"{c.BRIGHT_CYAN}{c.BOLD}")
        print("╔═══════════════════════════════════════════════════════════════╗")
        print(f"║{c.BRIGHT_WHITE}              🕌 ADHAN REMINDER - LIVE CONSOLE{c.BRIGHT_CYAN}              ║")
        print("╚═══════════════════════════════════════════════════════════════╝")
        print(c.RESET)
        print()
        
        if location_data:
            city = location_data.get('city', 'Unknown')
            country = location_data.get('country', 'Unknown')
            lat = location_data.get('lat', 0)
            lon = location_data.get('lon', 0)
            
            print(f"{c.BRIGHT_MAGENTA}📍 Location:{c.RESET} {c.WHITE}{city}, {country}{c.RESET}")
            print(f"{c.BRIGHT_BLUE}🌐 Coords:{c.RESET}   {c.DIM}{lat:.4f}, {lon:.4f}{c.RESET}")
        
        now = datetime.now()
        print(f"{c.BRIGHT_YELLOW}📅 Date:{c.RESET}     {c.WHITE}{now.strftime('%A, %B %d, %Y')}{c.RESET}")
        print(f"{c.BRIGHT_GREEN}⏰ Time:{c.RESET}     {c.BOLD}{c.WHITE}{now.strftime('%H:%M:%S')}{c.RESET}")
        print()
    
    def print_prayer_times(self):
        """Print beautiful prayer times with colors"""
        c = Colors
        
        print(f"{c.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c.RESET}")
        print(f"{c.BOLD}{c.BRIGHT_WHITE}                    ✨ PRAYER TIMES FOR TODAY ✨{c.RESET}")
        print(f"{c.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c.RESET}")
        print()
        
        prayer_data = {
            'Fajr': {'icon': '🌅', 'color': c.BRIGHT_MAGENTA, 'name': 'Fajr'},
            'Dhuhr': {'icon': '☀️', 'color': c.BRIGHT_YELLOW, 'name': 'Dhuhr'},
            'Asr': {'icon': '🌤️', 'color': c.BRIGHT_CYAN, 'name': 'Asr'},
            'Maghrib': {'icon': '🌆', 'color': c.BRIGHT_RED, 'name': 'Maghrib'},
            'Isha': {'icon': '🌙', 'color': c.BRIGHT_BLUE, 'name': 'Isha'}
        }
        
        now = datetime.now().strftime('%H:%M')
        
        for prayer in ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']:
            if prayer in self.prayer_times:
                data = prayer_data[prayer]
                icon = data['icon']
                color = data['color']
                name = data['name']
                time = self.prayer_times[prayer]
                
                # Check if prayer has passed
                if time < now:
                    status = f"{c.BRIGHT_GREEN}✓{c.RESET}"
                    time_color = c.DIM
                else:
                    status = f"{c.BRIGHT_YELLOW}○{c.RESET}"
                    time_color = c.BRIGHT_WHITE
                
                print(f"  {status} {icon}  {color}{c.BOLD}{name:10}{c.RESET} {c.BRIGHT_BLACK}│{c.RESET} {time_color}{time}{c.RESET}")
        
        print()
        print(f"{c.BRIGHT_CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c.RESET}")
        print()
    
    def print_next_prayer(self, prayer, prayer_ar, prayer_time):
        """Print beautiful next prayer box with countdown"""
        c = Colors
        hours, minutes, seconds = self.get_time_until_prayer(prayer_time)
        
        # Prayer-specific colors
        prayer_colors = {
            'Fajr': c.BRIGHT_MAGENTA,
            'Dhuhr': c.BRIGHT_YELLOW,
            'Asr': c.BRIGHT_CYAN,
            'Maghrib': c.BRIGHT_RED,
            'Isha': c.BRIGHT_BLUE
        }
        
        prayer_icons = {
            'Fajr': '🌅',
            'Dhuhr': '☀️',
            'Asr': '🌤️',
            'Maghrib': '🌆',
            'Isha': '🌙'
        }
        
        color = prayer_colors.get(prayer, c.BRIGHT_WHITE)
        icon = prayer_icons.get(prayer, '🕌')
        
        print(f"{color}{c.BOLD}╔═══════════════════════════════════════════════════════════════╗{c.RESET}")
        print(f"{color}║{c.RESET}                  {icon}  {c.BOLD}{c.BRIGHT_WHITE}NEXT PRAYER: {prayer.upper()}{c.RESET}  {icon}                 {color}║{c.RESET}")
        print(f"{color}╠═══════════════════════════════════════════════════════════════╣{c.RESET}")
        print(f"{color}║{c.RESET}                                                               {color}║{c.RESET}")
        print(f"{color}║{c.RESET}  {c.BRIGHT_CYAN}⏰ Time:{c.RESET}      {c.BOLD}{c.BRIGHT_WHITE}{prayer_time}{c.RESET}                                         {color}║{c.RESET}")
        print(f"{color}║{c.RESET}                                                               {color}║{c.RESET}")
        print(f"{color}║{c.RESET}  {c.BRIGHT_YELLOW}⏳ Countdown:{c.RESET} {c.BOLD}{c.BRIGHT_GREEN}{hours:02d}{c.RESET}h {c.BOLD}{c.BRIGHT_GREEN}{minutes:02d}{c.RESET}m {c.BOLD}{c.BRIGHT_GREEN}{seconds:02d}{c.RESET}s                              {color}║{c.RESET}")
        print(f"{color}║{c.RESET}                                                               {color}║{c.RESET}")
        print(f"{color}╚═══════════════════════════════════════════════════════════════╝{c.RESET}")
        print()
    
    def run_live(self):
        """Run live mode with beautiful interface"""
        c = Colors
        
        print(f"{c.BRIGHT_CYAN}{c.BOLD}Starting Adhan Reminder...{c.RESET}")
        
        # Get location
        location_data = self.get_location()
        
        # Fetch prayer times
        if not self.fetch_prayer_times():
            print(f"{c.BRIGHT_RED}❌ Failed to fetch prayer times{c.RESET}")
            return
        
        last_fetch_date = datetime.now().date()
        last_played_prayer = None
        
        print(f"{c.BRIGHT_GREEN}✅ Prayer times fetched successfully!{c.RESET}")
        time.sleep(2)
        
        try:
            while True:
                self.clear_screen()
                
                # التحقق من تغيير اليوم
                current_date = datetime.now().date()
                if last_fetch_date != current_date:
                    self.fetch_prayer_times()
                    last_fetch_date = current_date
                    last_played_prayer = None
                
                # طباعة المعلومات
                self.print_header(location_data)
                self.print_prayer_times()
                
                # الصلاة القادمة
                prayer, prayer_ar, prayer_time = self.get_next_prayer()
                if prayer and prayer_time:
                    self.print_next_prayer(prayer, prayer_ar, prayer_time)
                
                # Check prayer time
                current_time = datetime.now().strftime('%H:%M')
                if current_time in self.prayer_times.values():
                    for p, t in self.prayer_times.items():
                        if t == current_time and p != last_played_prayer:
                            c = Colors
                            print()
                            print(f"{c.BRIGHT_GREEN}{c.BOLD}" + "═"*63 + c.RESET)
                            print(f"{c.BRIGHT_WHITE}{c.BOLD}           🕌 IT'S TIME FOR {p.upper()} PRAYER! 🕌{c.RESET}")
                            print(f"{c.BRIGHT_GREEN}{c.BOLD}" + "═"*63 + c.RESET)
                            print()
                            
                            self.play_adhan(p)
                            last_played_prayer = p
                            time.sleep(60)  # Wait 1 minute to avoid repetition
                
                print(f"{Colors.DIM}Press Ctrl+C to exit{Colors.RESET}")
                time.sleep(1)
                
        except KeyboardInterrupt:
            c = Colors
            print("\n\n")
            print(f"{c.BRIGHT_MAGENTA}{c.BOLD}╔═══════════════════════════════════════════════════════════════╗{c.RESET}")
            print(f"{c.BRIGHT_MAGENTA}║{c.RESET}                  {c.BRIGHT_YELLOW}✨ PROGRAM STOPPED ✨{c.RESET}                     {c.BRIGHT_MAGENTA}║{c.RESET}")
            print(f"{c.BRIGHT_MAGENTA}║{c.RESET}                                                               {c.BRIGHT_MAGENTA}║{c.RESET}")
            print(f"{c.BRIGHT_MAGENTA}║{c.RESET}              {c.BRIGHT_GREEN}May Allah reward you! 🕌{c.RESET}                  {c.BRIGHT_MAGENTA}║{c.RESET}")
            print(f"{c.BRIGHT_MAGENTA}╚═══════════════════════════════════════════════════════════════╝{c.RESET}")
            print()

def main():
    """الدالة الرئيسية"""
    live = AdhanLive()
    live.run_live()

if __name__ == '__main__':
    main()
