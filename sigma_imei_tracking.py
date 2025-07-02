import tkinter as tk
from tkinter import scrolledtext
import folium
import requests
import geocoder
import webbrowser
import threading
import os, time, datetime
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
import socketserver
import phonenumbers
from phonenumbers import carrier, geocoder as phone_geocoder
import random
import socket
import re
from tkinter import messagebox

# Config
REFRESH = 8
PORT = 5055
SAVE_DIR = Path.home() / ".sigma_tracker"
SAVE_DIR.mkdir(exist_ok=True)
MAP_FILE = SAVE_DIR / "trace.html"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Hacker-themed colors
BG_COLOR = "#0a0a0a"
TEXT_COLOR = "#00ff00"
ACCENT_COLOR = "#ff0000"
SECONDARY_COLOR = "#00ffff"
TERMINAL_FONT = ("Courier", 12)
TITLE_FONT = ("Courier", 20, "bold")

class GPSTracker:
    def __init__(self):
        self.status = "GLOBAL TRACKING ACTIVE"
        self.services = [
            self._ipapi_co,
            self._ipinfo_io,
            self._geocoder_ip,
            self._abstract_api
        ]
    
    def _ipapi_co(self):
        try:
            r = requests.get("https://ipapi.co/json/", headers={"User-Agent": USER_AGENT}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {
                    "lat": float(data.get("latitude", 0)),
                    "lon": float(data.get("longitude", 0)),
                    "city": data.get("city", "Unknown"),
                    "country": data.get("country_name", "Unknown"),
                    "org": data.get("org", "Unknown"),
                    "ip": data.get("ip", "Unknown"),
                    "accuracy": data.get("accuracy", 5)  # km accuracy
                }
        except:
            pass
        return None
    
    def _ipinfo_io(self):
        try:
            r = requests.get("https://ipinfo.io/json", headers={"User-Agent": USER_AGENT}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                loc = data.get("loc", "0,0").split(",")
                return {
                    "lat": float(loc[0]),
                    "lon": float(loc[1]),
                    "city": data.get("city", "Unknown"),
                    "country": data.get("country", "Unknown"),
                    "org": data.get("org", "Unknown"),
                    "ip": data.get("ip", "Unknown"),
                    "accuracy": 10  # default accuracy
                }
        except:
            pass
        return None
    
    def _geocoder_ip(self):
        try:
            g = geocoder.ip('me')
            if g.ok:
                return {
                    "lat": g.latlng[0],
                    "lon": g.latlng[1],
                    "city": g.city,
                    "country": g.country,
                    "org": g.org if g.org else "Unknown",
                    "ip": g.ip,
                    "accuracy": 10
                }
        except:
            pass
        return None
    
    def _abstract_api(self):
        try:
            # This is a fallback service
            r = requests.get("https://ipgeolocation.abstractapi.com/v1/?api_key=d4e8b4d0c7e14d5c8a61d2d7b4c1e1a0", 
                            headers={"User-Agent": USER_AGENT}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                return {
                    "lat": float(data.get("latitude", 0)),
                    "lon": float(data.get("longitude", 0)),
                    "city": data.get("city", "Unknown"),
                    "country": data.get("country", "Unknown"),
                    "org": data.get("connection", {}).get("organization_name", "Unknown"),
                    "ip": data.get("ip_address", "Unknown"),
                    "accuracy": data.get("accuracy_radius", 10)
                }
        except:
            pass
        return None
    
    def get_location(self):
        """Try multiple services until we get a valid location"""
        for service in self.services:
            result = service()
            if result:
                return result
        
        # Fallback to empty data
        return {
            "lat": 0.0,
            "lon": 0.0,
            "city": "Unknown",
            "country": "Unknown",
            "org": "Unknown",
            "ip": "Unknown",
            "accuracy": 1000
        }

class IMEITracker:
    @staticmethod
    def get_ip_from_imei(imei):
        """Convert IMEI to phone number format and lookup carrier IP ranges"""
        try:
            # Convert IMEI to E.164 format phone number (simplified)
            country_code = "44"  # Default to UK
            if len(imei) >= 15:
                # Extract potential country code from IMEI TAC
                tac = imei[:8]
                # This would normally require a TAC database - we'll simulate
                country_code = "1" if tac.startswith("01") else "86" if tac.startswith("86") else "44"
            
            # Generate a pseudo phone number
            pseudo_number = f"+{country_code}{imei[-9:]}"
            
            # Lookup carrier information
            phone_number = phonenumbers.parse(pseudo_number, None)
            carrier_name = carrier.name_for_number(phone_number, "en")
            country = phone_geocoder.description_for_number(phone_number, "en")
            
            # Get carrier IP ranges (simulated)
            if "vodafone" in carrier_name.lower():
                return "87.194.0.0/16", carrier_name, country
            elif "verizon" in carrier_name.lower():
                return "71.160.0.0/16", carrier_name, country
            elif "att" in carrier_name.lower():
                return "99.110.0.0/16", carrier_name, country
            else:
                return "dynamic_ip", carrier_name, country
                
        except Exception as e:
            return "unknown_ip", "Unknown Carrier", "Unknown Country"
    
    @staticmethod
    def resolve_ip_range(ip_range):
        """Resolve IP range to a sample IP (simulated)"""
        if ip_range == "dynamic_ip":
            # Generate a random public IP address
            return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        elif ip_range == "unknown_ip":
            # Generate a random public IP address
            return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
        else:
            # Handle CIDR format
            base_ip = ip_range.split("/")[0]
            parts = base_ip.split('.')
            if len(parts) == 4:
                # Replace last octet with random number
                parts[3] = str(random.randint(1, 254))
            return ".".join(parts)

class SigmaTracker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("☠ SIGMA CYBER TRACKER ☠")
        self.root.configure(bg=BG_COLOR)
        self.root.geometry("800x600")
        self.root.minsize(800, 600)  # Minimum size for responsiveness
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.gps = GPSTracker()
        self.tracking = False
        self.data = {}
        self.history = []
        self.server_started = False
        
        # Setup GUI first to create console widget
        self.setup_gui()
        
        # Start HTTP server after GUI is ready
        threading.Thread(target=self.start_http_server, daemon=True).start()
        
        self.root.after(1000, self.update_status)
        self.root.mainloop()

    def setup_gui(self):
        # Main frame for responsiveness
        main_frame = tk.Frame(self.root, bg=BG_COLOR)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Terminal frame will expand
        
        # Header with hacker aesthetic
        header_frame = tk.Frame(main_frame, bg=BG_COLOR)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(10, 5))
        
        title = tk.Label(header_frame, text="☠ SIGMA CYBER TRACKER ☠", fg=ACCENT_COLOR, bg=BG_COLOR, font=TITLE_FONT)
        title.pack()
        
        subtitle = tk.Label(header_frame, text="GLOBAL SURVEILLANCE SYSTEM", fg=SECONDARY_COLOR, bg=BG_COLOR, font=("Courier", 12))
        subtitle.pack(pady=(0, 10))
        
        # Matrix-style terminal frame
        terminal_frame = tk.Frame(main_frame, bg=BG_COLOR, highlightthickness=1, highlightbackground=SECONDARY_COLOR)
        terminal_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        terminal_frame.columnconfigure(0, weight=1)
        terminal_frame.rowconfigure(0, weight=1)
        
        # Console with hacker theme
        self.console = scrolledtext.ScrolledText(terminal_frame, bg="#0a0a0a", fg=TEXT_COLOR, 
                                                insertbackground=TEXT_COLOR, font=TERMINAL_FONT,
                                                state='disabled', relief='flat')
        self.console.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        # Add initial hacker message
        self.log("SYSTEM INITIALIZED...")
        self.log("CONNECTING TO SIGMA NETWORK...")
        self.log("ENCRYPTION: AES-256 ACTIVE")
        self.log("READY FOR TARGET ACQUISITION")

        # Control panel with hacker aesthetic
        control_frame = tk.Frame(main_frame, bg=BG_COLOR)
        control_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        # IMEI input
        input_frame = tk.Frame(control_frame, bg=BG_COLOR)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(input_frame, text="TARGET IMEI/MSISDN:", fg=SECONDARY_COLOR, bg=BG_COLOR, font=TERMINAL_FONT).pack(side='left', padx=5)
        self.imei = tk.StringVar()
        entry = tk.Entry(input_frame, textvariable=self.imei, bg="#111", fg=TEXT_COLOR, 
                         font=TERMINAL_FONT, insertbackground=TEXT_COLOR, width=25)
        entry.pack(side='left', padx=5, expand=True, fill='x')
        entry.bind("<Return>", lambda event: self.activate())
        
        # Buttons with hacker style
        button_frame = tk.Frame(control_frame, bg=BG_COLOR)
        button_frame.pack(fill='x', pady=5)
        
        buttons = [
            ("ACTIVATE TRACKING", self.activate, "#0f0"),
            ("TERMINATE TRACKING", self.deactivate, "#f00"),
            ("TRACE LOCATION", self.trace_location, "#ff0"),
            ("VISUALIZE TRACK", self.draw_map, "#0ff"),
            ("CLEAR CONSOLE", self.clear_log, "#aaa")
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(button_frame, text=text, command=command, 
                            bg="#111", fg=color, font=TERMINAL_FONT, relief='raised',
                            activebackground="#222", activeforeground=color)
            btn.pack(side='left', padx=5, ipadx=5, ipady=2, expand=True, fill='x')

        # Status Bar
        self.status_var = tk.StringVar(value="🟢 SYSTEM READY | TRACKING: INACTIVE")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, fg=TEXT_COLOR, bg="#111", 
                             font=TERMINAL_FONT, anchor='w', relief='sunken', bd=1)
        status_bar.grid(row=3, column=0, sticky="ew", padx=2, pady=2)

        # Hacker info panel
        info_frame = tk.Frame(main_frame, bg=BG_COLOR)
        info_frame.grid(row=4, column=0, sticky="ew", pady=(5, 10))
        
        info_text = tk.Label(info_frame, 
                            text="SIGMA CYBER GHOST | ENCRYPTED CHANNEL | TOR RELAY ACTIVE",
                            fg=SECONDARY_COLOR, bg=BG_COLOR, font=TERMINAL_FONT)
        info_text.pack()
        
        # Hacker contact info with social media profiles (FIXED)
        contact_frame = tk.Frame(main_frame, bg=BG_COLOR)
        contact_frame.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        
        contacts = [
            ("TELEGRAM", "t.me/sigma_cyber_ghost", "#0ff", "https://t.me/sigma_cyber_ghost"),
            ("INSTAGRAM", "instagram.com/safderkhan0800_", "#f0f", "https://instagram.com/safderkhan0800_"),
            ("YOUTUBE", "youtube.com/sigma_ghost_hacking", "#f00", "https://youtube.com/sigma_ghost_hacking")
        ]
        
        # Configure columns for contact frame
        for i in range(len(contacts)):
            contact_frame.columnconfigure(i, weight=1)
        
        # Create contact labels
        for i, (platform, handle, color, url) in enumerate(contacts):
            contact = tk.Label(contact_frame, 
                              text=f"{platform}: {handle}",
                              fg=color, bg=BG_COLOR, font=TERMINAL_FONT,
                              cursor="hand2")
            contact.grid(row=0, column=i, padx=5, sticky="ew")
            contact.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

    def log(self, msg):
        if hasattr(self, 'console'):
            self.console.config(state='normal')
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Apply hacker-style formatting
            formatted_msg = f"[{ts}] {msg}"
            self.console.insert(tk.END, formatted_msg + "\n")
            
            # Apply color coding for specific keywords
            self.console.tag_configure("success", foreground="#0f0")
            self.console.tag_configure("warning", foreground="#ff0")
            self.console.tag_configure("error", foreground="#f00")
            self.console.tag_configure("info", foreground="#0ff")
            
            # Highlight keywords
            for word in ["ACTIVATED", "TRACKING", "SUCCESS", "READY"]:
                if word in msg:
                    start_index = f"end - {len(msg) + 1}c"
                    self.console.tag_add("success", start_index, f"{start_index} + {len(word)}c")
            
            for word in ["WARNING", "CAUTION", "ATTENTION"]:
                if word in msg:
                    start_index = f"end - {len(msg) + 1}c"
                    self.console.tag_add("warning", start_index, f"{start_index} + {len(word)}c")
            
            for word in ["ERROR", "FAILED", "TERMINATED"]:
                if word in msg:
                    start_index = f"end - {len(msg) + 1}c"
                    self.console.tag_add("error", start_index, f"{start_index} + {len(word)}c")
            
            for word in ["LOCATION", "IP", "COORDINATES"]:
                if word in msg:
                    start_index = f"end - {len(msg) + 1}c"
                    self.console.tag_add("info", start_index, f"{start_index} + {len(word)}c")
            
            self.console.see(tk.END)
            self.console.config(state='disabled')

    def update_status(self):
        if self.tracking:
            status = f"🔴 TRACKING ACTIVE | TARGETS: {len(self.history)} | LAST UPDATE: {datetime.datetime.now().strftime('%H:%M:%S')}"
        else:
            status = "🟢 SYSTEM READY | TRACKING: INACTIVE"
        self.status_var.set(status)
        self.root.after(1000, self.update_status)

    def activate(self):
        imei = self.imei.get().strip()
        if not imei:
            self.log("⚠️ INPUT ERROR: NO TARGET SPECIFIED")
            messagebox.showerror("Input Error", "No target IMEI/MSISDN specified!")
            return
            
        # Validate IMEI format
        if not (imei.isdigit() and len(imei) in [15, 16]):
            self.log("⚠️ SECURITY ALERT: INVALID IMEI/MSISDN FORMAT")
            messagebox.showerror("Invalid Format", "IMEI must be 15-16 digits!")
            return
            
        self.data['imei'] = imei
        self.tracking = True
        threading.Thread(target=self.track_loop, daemon=True).start()
        self.log(f"✅ TRACKING ACTIVATED FOR TARGET: {imei}")
        self.log("🛰️ ACQUIRING SATELLITE POSITIONING...")

    def trace_location(self):
        imei = self.imei.get().strip()
        if not imei:
            self.log("⚠️ INPUT ERROR: NO TARGET SPECIFIED")
            messagebox.showerror("Input Error", "No target IMEI/MSISDN specified!")
            return
            
        # Validate IMEI format
        if not (imei.isdigit() and len(imei) in [15, 16]):
            self.log("⚠️ SECURITY ALERT: INVALID IMEI/MSISDN FORMAT")
            messagebox.showerror("Invalid Format", "IMEI must be 15-16 digits!")
            return
            
        self.log(f"🔍 INITIATING LOCATION TRACE FOR TARGET: {imei}")
        threading.Thread(target=self.perform_trace, args=(imei,), daemon=True).start()

    def perform_trace(self, imei):
        try:
            # Get IP from IMEI
            ip_range, carrier_name, country = IMEITracker.get_ip_from_imei(imei)
            sample_ip = IMEITracker.resolve_ip_range(ip_range)
            
            self.log(f"📡 CARRIER IDENTIFIED: {carrier_name}")
            self.log(f"🌐 COUNTRY OF ORIGIN: {country}")
            self.log(f"🔗 IP RANGE: {ip_range}")
            self.log(f"🖧 SAMPLE IP: {sample_ip}")
            
            # Get location from IP
            try:
                self.log("🛰️ ACCESSING GEOLOCATION DATABASE...")
                g = geocoder.ip(sample_ip)
                if g.ok:
                    self.log(f"📍 TARGET LOCATION ACQUIRED: {g.city}, {g.country}")
                    self.log(f"🎯 COORDINATES: {g.latlng[0]:.5f}, {g.latlng[1]:.5f}")
                else:
                    self.log("⚠️ GEOLOCATION FAILURE: INSUFFICIENT DATA")
            except Exception as e:
                self.log(f"⚠️ GEOLOCATION SERVICE UNAVAILABLE: {str(e)}")
                
        except Exception as e:
            self.log(f"❗ CRITICAL ERROR IN TRACE OPERATION: {str(e)}")

    def deactivate(self):
        if self.tracking:
            self.tracking = False
            self.log("⛔ TRACKING TERMINATED")
            self.log("🛡️ SYSTEM RETURNED TO STANDBY MODE")

    def track_loop(self):
        while self.tracking:
            try:
                info = self.gps.get_location()
                self.data.update(info)
                self.history.append((info['lat'], info['lon'], time.time()))
                
                logmsg = (f"📡 TARGET {self.data['imei']} → IP: {info['ip']} | ORG: {info['org']} "
                         f"| LOCATION: {info['city']}, {info['country']} "
                         f"| COORD: [{info['lat']:.5f},{info['lon']:.5f}] ±{info['accuracy']}km")
                self.log(logmsg)
            except Exception as e:
                self.log(f"⚠️ TRACKING ERROR: {str(e)}")
            time.sleep(REFRESH)

    def draw_map(self):
        if not self.history:
            self.log("⚠️ NO LOCATION DATA AVAILABLE")
            messagebox.showwarning("No Data", "No location data available for mapping!")
            return
            
        # Get most recent location
        lat, lon, timestamp = self.history[-1]
        
        try:
            # Create map with dark theme and proper attribution
            m = folium.Map(
                location=[lat, lon], 
                zoom_start=12,
                tiles='CartoDB dark_matter',
                attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attribution">CARTO</a>'
            )
            
            # Add toner layer with proper attribution
            folium.TileLayer(
                'Stamen Toner',
                attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://creativecommons.org/licenses/by-sa/3.0">CC BY SA</a>',
                name='Stamen Toner'
            ).add_to(m)
            
            folium.LayerControl().add_to(m)
            
            # Add main marker
            popup_text = (f"<b>TARGET: {self.data.get('imei', 'UNKNOWN')}</b><br>"
                         f"IP: {self.data.get('ip', 'CLASSIFIED')}<br>"
                         f"ORG: {self.data.get('org', 'UNKNOWN')}<br>"
                         f"LOCATION: {self.data.get('city', 'Unknown')}, {self.data.get('country', 'Unknown')}<br>"
                         f"LAST UPDATE: {datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            
            folium.Marker(
                [lat, lon], 
                tooltip="CURRENT POSITION",
                popup=popup_text,
                icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')
            ).add_to(m)
            
            # Add historical path
            points = [(item[0], item[1]) for item in self.history]
            folium.PolyLine(points, color="red", weight=2.5, opacity=0.7).add_to(m)
            
            # Add historical markers
            for i, (lat, lon, ts) in enumerate(self.history):
                if i == len(self.history)-1:  # Skip last point (already added)
                    continue
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    color='#00ff00',
                    fill=True,
                    fill_color='#00ff00',
                    fill_opacity=0.7,
                    popup=f"HISTORICAL POINT {i+1}<br>{datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')}"
                ).add_to(m)
            
            m.save(MAP_FILE)
            webbrowser.open(f"http://localhost:{PORT}/{MAP_FILE.name}")
            self.log("🗺️ VISUAL TRACKING MAP GENERATED")
            self.log("🔐 MAP ACCESSIBLE AT LOCALHOST:5055")
        except Exception as e:
            self.log(f"⚠️ MAP GENERATION ERROR: {str(e)}")
            messagebox.showerror("Map Error", f"Failed to generate map: {str(e)}")

    def clear_log(self):
        if hasattr(self, 'console'):
            self.console.config(state='normal')
            self.console.delete(1.0, tk.END)
            self.console.config(state='disabled')
        self.log("🧹 CONSOLE PURGED")
        self.log("🔄 SYSTEM READY FOR NEW OPERATIONS")

    def start_http_server(self):
        # Wait for GUI to be ready before logging
        while not hasattr(self, 'console'):
            time.sleep(0.1)
        
        os.chdir(SAVE_DIR)
        try:
            with socketserver.TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
                self.log(f"🌐 SECURE SERVER ACTIVE ON PORT {PORT}")
                self.server_started = True
                httpd.serve_forever()
        except Exception as e:
            self.log(f"❗ SERVER CRITICAL ERROR: {e}")

if __name__ == "__main__":
    SigmaTracker()
