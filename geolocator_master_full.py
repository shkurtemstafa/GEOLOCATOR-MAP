# geolocator_master_full.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from geopy.geocoders import Nominatim
import requests
import webbrowser
import folium
import os
import csv
import pandas as pd
from datetime import datetime


# Optional embed:
try:
    from tkhtmlview import HTMLLabel, HTMLScrolledText
    TKHTML_AVAILABLE = True
except Exception:
    TKHTML_AVAILABLE = False

# PIL for images
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Matplotlib for charts
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# Optional GIS libraries:
try:
    import geopandas as gpd
    import shapely.geometry as geom
    from shapely.geometry import Point, Polygon
    from shapely.ops import transform
    GIS_AVAILABLE = True
except Exception:
    GIS_AVAILABLE = False

try:
    import pyproj
    from pyproj import Transformer, CRS
    PROJ_AVAILABLE = True
except Exception:
    PROJ_AVAILABLE = False

try:
    import gpxpy
    import gpxpy.gpx
    GPX_AVAILABLE = True
except Exception:
    GPX_AVAILABLE = False

import json  # Built-in module, always available
JSON_AVAILABLE = True

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGIS_AVAILABLE = True
except Exception:
    POSTGIS_AVAILABLE = False

# SQLite - Built-in, no installation needed!
import sqlite3
SQLITE_AVAILABLE = True

# -------------------------
# Configuration
# -------------------------
APP_TITLE = "GeoLocator - Advanced GIS/GNSS/PostGIS"
BG_COLOR = "#F5F7FA"  # Light blue-gray background
CARD_BG = "#FFFFFF"  # Pure white cards
PRIMARY_BLUE = "#2196F3"  # Material Blue
SECONDARY_BLUE = "#03A9F4"  # Light Blue
DARK_BLUE = "#1976D2"  # Dark Blue
SUCCESS_GREEN = "#4CAF50"  # Green
WARNING_ORANGE = "#FF9800"  # Orange
ERROR_RED = "#F44336"  # Red
TEXT_COLOR = "#212121"  # Almost black
TEXT_SECONDARY = "#757575"  # Gray

# If you want to use Google Geocoding for more accurate results, set:
# GOOGLE_API_KEY = "YOUR_API_KEY_HERE"
GOOGLE_API_KEY = ""  # optional

# Services
geolocator = Nominatim(user_agent="geo_master_app_v2")
OPEN_ELEVATION_URL = "https://api.open-elevation.com/api/v1/lookup"
IP_API_BASE = "http://ip-api.com/json/"

# PostGIS Connection (optional - set these if using PostGIS)
POSTGIS_HOST = ""
POSTGIS_PORT = "5432"
POSTGIS_DB = ""
POSTGIS_USER = ""
POSTGIS_PASSWORD = ""

# SQLite Database (built-in, no setup needed!)
SQLITE_DB_PATH = "geolocator_data.db"

# Store multiple points for GIS operations
stored_points = []

# Favorite locations
favorite_locations = []

# Theme settings
current_theme = "light"  # or "dark"

# Autocomplete class
class AutocompleteEntry(tk.Entry):
    """Entry widget with autocomplete dropdown"""
    def __init__(self, parent, autocomplete_function=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.autocomplete_function = autocomplete_function
        self.var = self["textvariable"]
        if self.var == '':
            self.var = self["textvariable"] = tk.StringVar()
        
        self.var.trace('w', self.changed)
        self.bind("<Right>", self.selection)
        self.bind("<Up>", self.move_up)
        self.bind("<Down>", self.move_down)
        self.bind("<Return>", self.selection)
        
        self.lb_up = False
        self.lb = None
        self.typing_timer = None  # Add delay timer
    
    def changed(self, name, index, mode):
        # Cancel previous timer
        if self.typing_timer:
            self.after_cancel(self.typing_timer)
        
        if self.var.get() == '':
            if self.lb_up:
                self.lb.destroy()
                self.lb_up = False
        else:
            # Wait 500ms after user stops typing before showing suggestions
            self.typing_timer = self.after(500, self.show_suggestions)
    
    def show_suggestions(self):
        """Show suggestions after delay"""
        words = self.comparison()
        if words:
            if not self.lb_up:
                self.lb = tk.Listbox(self.master, height=5, font=("Segoe UI", 9))
                self.lb.bind("<Double-Button-1>", self.selection)
                self.lb.bind("<Right>", self.selection)
                self.lb.place(x=self.winfo_x(), y=self.winfo_y() + self.winfo_height())
                self.lb_up = True
            
            self.lb.delete(0, tk.END)
            for w in words:
                self.lb.insert(tk.END, w)
        else:
            if self.lb_up:
                self.lb.destroy()
                self.lb_up = False
    
    def selection(self, event):
        if self.lb_up:
            self.var.set(self.lb.get(tk.ACTIVE))
            self.lb.destroy()
            self.lb_up = False
            self.icursor(tk.END)
    
    def move_up(self, event):
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != '0':
                self.lb.selection_clear(first=index)
                index = str(int(index) - 1)
                self.lb.selection_set(first=index)
                self.lb.activate(index)
    
    def move_down(self, event):
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '-1'
            else:
                index = self.lb.curselection()[0]
            if index != tk.END:
                self.lb.selection_clear(first=index)
                index = str(int(index) + 1)
                self.lb.selection_set(first=index)
                self.lb.activate(index)
    
    def comparison(self):
        if self.autocomplete_function:
            return self.autocomplete_function(self.var.get())
        return []

# -------------------------
# Helper utilities
# -------------------------
def safe_get(d, *keys):
    cur = d
    for k in keys:
        if cur and isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

def extract_address_fields(location):
    raw = location.raw.get("address", {}) if hasattr(location, "raw") else {}
    return {
        "display_name": getattr(location, "address", ""),
        "latitude": getattr(location, "latitude", ""),
        "longitude": getattr(location, "longitude", ""),
        "country": safe_get(raw, "country"),
        "state": safe_get(raw, "state") or safe_get(raw, "region"),
        "county": safe_get(raw, "county"),
        "city": safe_get(raw, "city") or safe_get(raw, "town") or safe_get(raw, "village"),
        "postcode": safe_get(raw, "postcode"),
        "road": safe_get(raw, "road"),
        "house_number": safe_get(raw, "house_number"),
        "neighbourhood": safe_get(raw, "neighbourhood"),
        "boundingbox": location.raw.get("boundingbox") if hasattr(location, "raw") else None,
    }

def get_elevation(lat, lon):
    """Query Open-Elevation for altitude (meters)."""
    try:
        resp = requests.get(OPEN_ELEVATION_URL, params={"locations": f"{lat},{lon}"}, timeout=8)
        data = resp.json()
        if "results" in data and len(data["results"]) > 0:
            return data["results"][0].get("elevation")
    except Exception:
        return None
    return None

def get_timezone_info(lat, lon):
    """Get timezone information for coordinates using free API"""
    try:
        # Using TimeAPI.io (free, no key needed)
        url = f"https://timeapi.io/api/TimeZone/coordinate?latitude={lat}&longitude={lon}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'timezone': data.get('timeZone', 'Unknown'),
                'current_time': data.get('currentLocalTime', 'Unknown'),
                'utc_offset': data.get('currentUtcOffset', {}).get('seconds', 0) / 3600
            }
    except:
        pass
    return None

def get_weather_info(lat, lon):
    """Get weather information using free API (Open-Meteo)"""
    try:
        # Open-Meteo is free, no API key needed!
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=celsius"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            weather = data.get('current_weather', {})
            temp = weather.get('temperature')
            windspeed = weather.get('windspeed')
            
            # Weather codes
            weather_codes = {
                0: "☀️ Clear sky", 1: "🌤️ Mainly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
                45: "🌫️ Foggy", 48: "🌫️ Rime fog", 51: "🌦️ Light drizzle", 53: "🌦️ Drizzle",
                55: "🌧️ Heavy drizzle", 61: "🌧️ Light rain", 63: "🌧️ Rain", 65: "🌧️ Heavy rain",
                71: "🌨️ Light snow", 73: "❄️ Snow", 75: "❄️ Heavy snow", 77: "🌨️ Snow grains",
                80: "🌦️ Light showers", 81: "🌧️ Showers", 82: "🌧️ Heavy showers",
                85: "🌨️ Light snow showers", 86: "❄️ Snow showers", 95: "⛈️ Thunderstorm",
                96: "⛈️ Thunderstorm with hail", 99: "⛈️ Heavy thunderstorm"
            }
            
            code = weather.get('weathercode', 0)
            condition = weather_codes.get(code, "Unknown")
            
            return {
                'temperature': f"{temp}°C" if temp is not None else "N/A",
                'condition': condition,
                'windspeed': f"{windspeed} km/h" if windspeed is not None else "N/A"
            }
    except:
        pass
    return None

# Image functions removed - using visual charts instead

def get_address_suggestions(query):
    """Get address suggestions from Nominatim - with caching and delay"""
    if not query or len(query) < 3:  # Require 3 characters minimum
        return []
    
    # Simple cache to avoid repeated API calls
    if not hasattr(get_address_suggestions, 'cache'):
        get_address_suggestions.cache = {}
    
    # Check cache first
    if query in get_address_suggestions.cache:
        return get_address_suggestions.cache[query]
    
    try:
        # Use Nominatim search with limit
        results = geolocator.geocode(query, exactly_one=False, limit=5, timeout=3, addressdetails=True)
        if results:
            suggestions = [loc.address for loc in results]
            get_address_suggestions.cache[query] = suggestions
            return suggestions
        return []
    except:
        return []

def use_google_geocode_address(address):
    """Optional: Google Geocoding (requires API key). Returns dict similar to geopy Location."""
    if not GOOGLE_API_KEY:
        return None
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    r = requests.get(url, params={"address": address, "key": GOOGLE_API_KEY}, timeout=8).json()
    if r.get("status") != "OK":
        return None
    res = r["results"][0]
    loc = res["geometry"]["location"]
    # build a small pseudo-location object
    class P:
        pass
    p = P()
    p.latitude = loc["lat"]
    p.longitude = loc["lng"]
    p.address = res.get("formatted_address")
    p.raw = {"address": {}}
    # parse components into raw["address"] best-effort
    for comp in res.get("address_components", []):
        types = comp.get("types", [])
        if "country" in types:
            p.raw["address"]["country"] = comp.get("long_name")
        if "administrative_area_level_1" in types:
            p.raw["address"]["state"] = comp.get("long_name")
        if "administrative_area_level_2" in types:
            p.raw["address"]["county"] = comp.get("long_name")
        if "locality" in types or "postal_town" in types:
            p.raw["address"]["city"] = comp.get("long_name")
        if "postal_code" in types:
            p.raw["address"]["postcode"] = comp.get("long_name")
        if "route" in types:
            p.raw["address"]["road"] = comp.get("long_name")
        if "street_number" in types:
            p.raw["address"]["house_number"] = comp.get("long_name")
    return p

# -------------------------
# GIS Functions: Coordinate Transformations (Gjeoreferencimi)
# -------------------------
def transform_coordinates(lat, lon, from_crs="EPSG:4326", to_crs="EPSG:3857"):
    """Transform coordinates between different CRS (Coordinate Reference Systems).
    EPSG:4326 = WGS84 (lat/lon), EPSG:3857 = Web Mercator, EPSG:32633 = UTM Zone 33N, etc."""
    if not PROJ_AVAILABLE:
        return None, None
    try:
        transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)
        return x, y
    except Exception as e:
        return None, None

def get_utm_zone(lon):
    """Calculate UTM zone from longitude."""
    return int((lon + 180) / 6) + 1

def convert_to_utm(lat, lon):
    """Convert WGS84 to UTM coordinates."""
    if not PROJ_AVAILABLE:
        return None, None, None
    try:
        zone = get_utm_zone(lon)
        hemisphere = 'north' if lat >= 0 else 'south'
        epsg_code = 32600 + zone if hemisphere == 'north' else 32700 + zone
        x, y = transform_coordinates(lat, lon, "EPSG:4326", f"EPSG:{epsg_code}")
        return x, y, f"UTM Zone {zone}{hemisphere[0].upper()}"
    except Exception:
        return None, None, None

# -------------------------
# GIS Functions: Spatial Calculations
# -------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula (in meters)."""
    from math import radians, sin, cos, sqrt, atan2
    R = 6371000  # Earth radius in meters
    lat1_rad = radians(float(lat1))
    lat2_rad = radians(float(lat2))
    delta_lat = radians(float(lat2) - float(lat1))
    delta_lon = radians(float(lon2) - float(lon1))
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate initial bearing from point 1 to point 2 (in degrees)."""
    from math import radians, degrees, atan2, sin, cos
    lat1_rad = radians(float(lat1))
    lat2_rad = radians(float(lat2))
    delta_lon = radians(float(lon2) - float(lon1))
    y = sin(delta_lon) * cos(lat2_rad)
    x = cos(lat1_rad) * sin(lat2_rad) - sin(lat1_rad) * cos(lat2_rad) * cos(delta_lon)
    bearing = degrees(atan2(y, x))
    return (bearing + 360) % 360

def create_buffer(lat, lon, radius_meters):
    """Create a circular buffer around a point (returns GeoJSON-like dict)."""
    if not GIS_AVAILABLE:
        return None
    try:
        point = Point(float(lon), float(lat))
        # Approximate: 1 degree lat ≈ 111km, 1 degree lon ≈ 111km * cos(lat)
        buffer_degrees = radius_meters / 111000.0
        buffer_poly = point.buffer(buffer_degrees)
        coords = list(buffer_poly.exterior.coords)
        return {
            "type": "Polygon",
            "coordinates": [[[c[0], c[1]] for c in coords]]
        }
    except Exception:
        return None

# -------------------------
# GIS Functions: GeoJSON Import/Export
# -------------------------
def export_to_geojson(points_list, filename):
    """Export points to GeoJSON format."""
    if not JSON_AVAILABLE:
        return False, "JSON module not available"
    if not points_list:
        return False, "No points to export"
    try:
        features = []
        for i, pt in enumerate(points_list):
            try:
                lat = float(pt.get("lat", 0))
                lon = float(pt.get("lon", 0))
                if lat == 0 and lon == 0:
                    continue  # Skip invalid coordinates
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]  # GeoJSON format: [lon, lat]
                    },
                    "properties": {
                        "name": str(pt.get("name", f"Point {i+1}")),
                        "description": str(pt.get("description", "")),
                        "timestamp": str(pt.get("timestamp", ""))
                    }
                })
            except (ValueError, TypeError) as e:
                print(f"Error processing point {i}: {e}")
                continue
        
        if not features:
            return False, "No valid points to export"
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        return True, f"Exported {len(features)} points"
    except Exception as e:
        return False, f"Export error: {str(e)}"

def import_from_geojson(filename):
    """Import points from GeoJSON file."""
    if not JSON_AVAILABLE:
        return [], "JSON module not available"
    if not filename or not os.path.exists(filename):
        return [], "File not found"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        points = []
        # Handle both FeatureCollection and single Feature
        if data.get("type") == "FeatureCollection":
            features = data.get("features", [])
        elif data.get("type") == "Feature":
            features = [data]
        else:
            return [], "Invalid GeoJSON format: must be Feature or FeatureCollection"
        
        for i, feature in enumerate(features):
            try:
                geom = feature.get("geometry", {})
                if geom.get("type") == "Point":
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        props = feature.get("properties", {})
                        points.append({
                            "lat": float(coords[1]),
                            "lon": float(coords[0]),
                            "name": str(props.get("name", f"Point {i+1}")),
                            "description": str(props.get("description", "")),
                            "timestamp": str(props.get("timestamp", ""))
                        })
            except (ValueError, TypeError, KeyError) as e:
                print(f"Error processing feature {i}: {e}")
                continue
        
        return points, f"Imported {len(points)} points" if points else ([], "No valid points found in file")
    except json.JSONDecodeError as e:
        return [], f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return [], f"Import error: {str(e)}"

# -------------------------
# GNSS Functions: GPX Support
# -------------------------
def export_to_gpx(points_list, filename):
    """Export points to GPX format (GNSS standard)."""
    if not GPX_AVAILABLE:
        return False, "gpxpy not installed. Install: pip install gpxpy"
    if not points_list:
        return False, "No points to export"
    try:
        gpx = gpxpy.gpx.GPX()
        
        # Create a track
        track = gpxpy.gpx.GPXTrack()
        track.name = "Exported Track"
        gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)
        
        valid_points = 0
        for pt in points_list:
            try:
                lat = float(pt.get("lat", 0))
                lon = float(pt.get("lon", 0))
                if lat == 0 and lon == 0:
                    continue
                
                # Add track point
                point = gpxpy.gpx.GPXTrackPoint(
                    lat,
                    lon,
                    elevation=float(pt.get("elevation", 0)) if pt.get("elevation") else None
                )
                if pt.get("timestamp"):
                    try:
                        timestamp_str = str(pt["timestamp"]).replace("Z", "+00:00")
                        point.time = datetime.fromisoformat(timestamp_str)
                    except:
                        pass
                segment.points.append(point)
                
                # Add waypoint
                waypoint = gpxpy.gpx.GPXWaypoint(
                    lat,
                    lon,
                    name=str(pt.get("name", "Waypoint"))
                )
                if pt.get("description"):
                    waypoint.description = str(pt.get("description", ""))
                if pt.get("elevation"):
                    waypoint.elevation = float(pt.get("elevation", 0))
                gpx.waypoints.append(waypoint)
                valid_points += 1
            except (ValueError, TypeError) as e:
                print(f"Error processing point: {e}")
                continue
        
        if valid_points == 0:
            return False, "No valid points to export"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(gpx.to_xml())
        return True, f"Exported {valid_points} points"
    except Exception as e:
        return False, f"Export error: {str(e)}"

def import_from_gpx(filename):
    """Import points from GPX file."""
    if not GPX_AVAILABLE:
        return [], "gpxpy not installed. Install: pip install gpxpy"
    if not filename or not os.path.exists(filename):
        return [], "File not found"
    try:
        with open(filename, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        
        points = []
        # Extract waypoints
        for waypoint in gpx.waypoints:
            try:
                points.append({
                    "lat": float(waypoint.latitude),
                    "lon": float(waypoint.longitude),
                    "name": str(waypoint.name or ""),
                    "description": str(waypoint.description or ""),
                    "elevation": float(waypoint.elevation) if waypoint.elevation else None,
                    "timestamp": waypoint.time.isoformat() if waypoint.time else ""
                })
            except Exception as e:
                print(f"Error processing waypoint: {e}")
                continue
        
        # Extract track points
        for track in gpx.tracks:
            track_name = track.name or "Track"
            for segment in track.segments:
                for point in segment.points:
                    try:
                        points.append({
                            "lat": float(point.latitude),
                            "lon": float(point.longitude),
                            "name": str(track_name),
                            "elevation": float(point.elevation) if point.elevation else None,
                            "timestamp": point.time.isoformat() if point.time else ""
                        })
                    except Exception as e:
                        print(f"Error processing track point: {e}")
                        continue
        
        if points:
            return points, f"Imported {len(points)} points from GPX"
        else:
            return [], "No valid points found in GPX file"
    except gpxpy.gpx.GPXException as e:
        return [], f"Invalid GPX format: {str(e)}"
    except Exception as e:
        return [], f"Import error: {str(e)}"

# -------------------------
# PostGIS Functions: Spatial Database Operations
# -------------------------
def connect_postgis():
    """Connect to PostGIS database."""
    if not POSTGIS_AVAILABLE or not all([POSTGIS_HOST, POSTGIS_DB, POSTGIS_USER]):
        return None
    try:
        conn = psycopg2.connect(
            host=POSTGIS_HOST,
            port=POSTGIS_PORT,
            database=POSTGIS_DB,
            user=POSTGIS_USER,
            password=POSTGIS_PASSWORD
        )
        return conn
    except Exception:
        return None

def query_postgis_spatial(query, params=None):
    """Execute spatial query on PostGIS database."""
    conn = connect_postgis()
    if not conn:
        return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params or [])
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception as e:
        if conn:
            conn.close()
        return None

def insert_point_postgis(table_name, lat, lon, name="", description=""):
    """Insert a point into PostGIS table."""
    conn = connect_postgis()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        query = f"""
        INSERT INTO {table_name} (name, description, geom, search_date)
        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), NOW())
        """
        cur.execute(query, (name, description, float(lon), float(lat)))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return False

def init_sqlite_db():
    """Initialize SQLite database - automatic, no setup needed!"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        
        # Create locations table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            search_type TEXT,
            latitude REAL,
            longitude REAL,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create favorites table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            address TEXT,
            latitude REAL,
            longitude REAL,
            notes TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create statistics table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_date DATE,
            search_count INTEGER DEFAULT 0,
            UNIQUE(stat_date)
        )
        """)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"SQLite init error: {e}")
        return False

def save_to_database(lat, lon, name, search_type):
    """Automatically save search to SQLite database."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        
        # Insert location
        cur.execute("""
        INSERT INTO locations (name, search_type, latitude, longitude)
        VALUES (?, ?, ?, ?)
        """, (name, search_type, float(lat), float(lon)))
        
        # Update statistics
        from datetime import date
        today = date.today().isoformat()
        cur.execute("""
        INSERT INTO statistics (stat_date, search_count)
        VALUES (?, 1)
        ON CONFLICT(stat_date) DO UPDATE SET search_count = search_count + 1
        """, (today,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Save to DB error: {e}")
        pass  # Silently fail
    
    # Also try PostGIS if configured
    if POSTGIS_HOST and POSTGIS_DB:
        try:
            conn = connect_postgis()
            if conn:
                cur = conn.cursor()
                query = """
                INSERT INTO locations (name, search_type, latitude, longitude, geom, search_date)
                VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), NOW())
                """
                cur.execute(query, (name, search_type, float(lat), float(lon), float(lon), float(lat)))
                conn.commit()
                cur.close()
                conn.close()
        except Exception:
            pass

def find_points_within_radius(table_name, lat, lon, radius_meters):
    """Find all points within radius using PostGIS spatial query."""
    conn = connect_postgis()
    if not conn:
        return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = f"""
        SELECT name, description, 
               ST_X(geom) as lon, ST_Y(geom) as lat,
               ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as distance
        FROM {table_name}
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        )
        ORDER BY distance
        """
        cur.execute(query, (float(lon), float(lat), float(lon), float(lat), float(radius_meters)))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception:
        if conn:
            conn.close()
        return []

def create_database_table():
    """Create the locations table if it doesn't exist."""
    conn = connect_postgis()
    if not conn:
        return False, "Not connected to database"
    
    try:
        cur = conn.cursor()
        # Create table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(500),
            search_type VARCHAR(50),
            latitude DOUBLE PRECISION,
            longitude DOUBLE PRECISION,
            geom GEOMETRY(Point, 4326),
            search_date TIMESTAMP DEFAULT NOW()
        );
        """)
        
        # Create spatial index
        cur.execute("""
        CREATE INDEX IF NOT EXISTS locations_geom_idx ON locations USING GIST (geom);
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        return True, "Table created successfully"
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return False, str(e)

# -------------------------
# GUI functions: Fill results
# -------------------------
def clear_results():
    for k in result_vars:
        result_vars[k].set("")
    history_listbox.delete(0, tk.END)

def clear_input_fields():
    """Clear all input fields"""
    address_entry.delete(0, tk.END)
    lat_entry.delete(0, tk.END)
    lon_entry.delete(0, tk.END)
    ip_entry.delete(0, tk.END)

def load_favorites():
    """Load favorites from database"""
    global favorite_locations
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name, address, latitude, longitude, notes FROM favorites ORDER BY name")
        favorite_locations = [{'name': row[0], 'address': row[1], 'lat': row[2], 'lon': row[3], 'notes': row[4]} for row in cur.fetchall()]
        conn.close()
    except:
        favorite_locations = []

def save_favorite(name, address, lat, lon, notes=""):
    """Save location to favorites"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO favorites (name, address, latitude, longitude, notes)
        VALUES (?, ?, ?, ?, ?)
        """, (name, address, float(lat), float(lon), notes))
        conn.commit()
        conn.close()
        load_favorites()
        return True
    except Exception as e:
        print(f"Save favorite error: {e}")
        return False

def delete_favorite(name):
    """Delete favorite location"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM favorites WHERE name = ?", (name,))
        conn.commit()
        conn.close()
        load_favorites()
        return True
    except:
        return False

def get_statistics():
    """Get search statistics"""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        
        # Total searches
        cur.execute("SELECT COUNT(*) FROM locations")
        total = cur.fetchone()[0]
        
        # By type
        cur.execute("SELECT search_type, COUNT(*) FROM locations GROUP BY search_type")
        by_type = dict(cur.fetchall())
        
        # Recent searches
        cur.execute("SELECT name, search_date FROM locations ORDER BY search_date DESC LIMIT 10")
        recent = cur.fetchall()
        
        # Today's searches
        from datetime import date
        today = date.today().isoformat()
        cur.execute("SELECT search_count FROM statistics WHERE stat_date = ?", (today,))
        result = cur.fetchone()
        today_count = result[0] if result else 0
        
        conn.close()
        
        return {
            'total': total,
            'by_type': by_type,
            'recent': recent,
            'today': today_count
        }
    except:
        return {'total': 0, 'by_type': {}, 'recent': [], 'today': 0}

def add_to_history(entry):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.append((timestamp, entry))
    history_listbox.insert(0, f"{timestamp} — {entry}")

def fill_result_panel(data_dict):
    """data_dict keys should map to our result_vars keys"""
    for key, val in data_dict.items():
        if key in result_vars:
            result_vars[key].set("" if val is None else str(val))
    
    # Create a formatted exact location string
    location_parts = []
    if data_dict.get("City"):
        location_parts.append(data_dict["City"])
    if data_dict.get("Region") and data_dict.get("Region") != data_dict.get("City"):
        location_parts.append(data_dict["Region"])
    if data_dict.get("Country"):
        location_parts.append(data_dict["Country"])
    
    if location_parts:
        exact_location = " → ".join(location_parts)
        # Update Display Address to show both full address and formatted location
        current_address = data_dict.get("Display Address", "")
        if current_address and exact_location not in current_address:
            result_vars["Display Address"].set(f"{current_address}\n📍 {exact_location}")

# -------------------------
# Address -> Coordinates
# -------------------------
def on_find_coordinates():
    address = address_entry.get().strip()
    if not address:
        messagebox.showerror("Input required", "Please enter an address.")
        return
    
    # Clear other input fields
    lat_entry.delete(0, tk.END)
    lon_entry.delete(0, tk.END)
    ip_entry.delete(0, tk.END)
    
    try:
        # Optionally try Google first if configured
        location = None
        if GOOGLE_API_KEY:
            location = use_google_geocode_address(address)
        if not location:
            location = geolocator.geocode(address, addressdetails=True, exactly_one=True, timeout=10)
        if not location:
            messagebox.showinfo("Not found", "Address not found.")
            return
        data = extract_address_fields(location)
        
        # Show basic results immediately
        out = {
            "Latitude": data["latitude"],
            "Longitude": data["longitude"],
            "Altitude": "Loading...",
            "Display Address": data["display_name"],
            "Country": data["country"] or "",
            "Region": data["state"] or "",
            "City": data["city"] or "",
            "Postal Code": data["postcode"] or "",
            "Timezone": "Loading...",
            "Weather": "Loading...",
            "ISP": "",
            "Bounding Box": ", ".join(data["boundingbox"]) if data["boundingbox"] else ""
        }
        fill_result_panel(out)
        add_to_history(f"Address -> {address}")
        root.update()  # Update UI immediately
        
        # Load extra info in background
        elevation = get_elevation(data["latitude"], data["longitude"])
        result_vars["Altitude"].set(f"{elevation} m" if elevation is not None else "N/A")
        
        tz_info = get_timezone_info(data["latitude"], data["longitude"])
        timezone_str = ""
        if tz_info:
            timezone_str = f"{tz_info['timezone']} (UTC{tz_info['utc_offset']:+.1f}) - {tz_info['current_time']}"
        result_vars["Timezone"].set(timezone_str)
        
        weather_info = get_weather_info(data["latitude"], data["longitude"])
        weather_str = ""
        if weather_info:
            weather_str = f"{weather_info['condition']} {weather_info['temperature']}, Wind: {weather_info['windspeed']}"
        result_vars["Weather"].set(weather_str)
        
        # Save to database if connected
        save_to_database(data["latitude"], data["longitude"], data["display_name"], "address_search")
    except Exception as e:
        messagebox.showerror("Error", f"Geocoding failed: {e}")

# -------------------------
# Coordinates -> Address
# -------------------------
def on_find_address():
    lat = lat_entry.get().strip()
    lon = lon_entry.get().strip()
    if not lat or not lon:
        messagebox.showerror("Input required", "Please enter both latitude and longitude.")
        return
    
    # Clear other input fields
    address_entry.delete(0, tk.END)
    ip_entry.delete(0, tk.END)
    
    try:
        location = geolocator.reverse(f"{lat}, {lon}", addressdetails=True, exactly_one=True, timeout=10)
        if not location:
            messagebox.showinfo("Not found", "No address found at these coordinates.")
            return
        data = extract_address_fields(location)
        
        # Show basic results immediately
        out = {
            "Latitude": data["latitude"],
            "Longitude": data["longitude"],
            "Altitude": "Loading...",
            "Display Address": data["display_name"],
            "Country": data["country"] or "",
            "Region": data["state"] or "",
            "City": data["city"] or "",
            "Postal Code": data["postcode"] or "",
            "Timezone": "Loading...",
            "Weather": "Loading...",
            "ISP": "",
            "Bounding Box": ", ".join(data["boundingbox"]) if data["boundingbox"] else ""
        }
        fill_result_panel(out)
        add_to_history(f"Coords -> {lat},{lon}")
        root.update()  # Update UI immediately
        
        # Load extra info in background
        elevation = get_elevation(lat, lon)
        result_vars["Altitude"].set(f"{elevation} m" if elevation is not None else "N/A")
        
        tz_info = get_timezone_info(lat, lon)
        if tz_info:
            result_vars["Timezone"].set(f"{tz_info['timezone']} (UTC{tz_info['utc_offset']:+.1f}) - {tz_info['current_time']}")
        
        weather_info = get_weather_info(lat, lon)
        if weather_info:
            result_vars["Weather"].set(f"{weather_info['condition']} {weather_info['temperature']}, Wind: {weather_info['windspeed']}")
        
        # Save to database if connected
        save_to_database(lat, lon, data["display_name"], "coords_search")
    except Exception as e:
        messagebox.showerror("Error", f"Reverse geocoding failed: {e}")

# -------------------------
# IP -> Geo
# -------------------------
def on_find_ip():
    ip = ip_entry.get().strip()
    if not ip:
        messagebox.showerror("Input required", "Please enter an IP address.")
        return
    
    # Clear other input fields
    address_entry.delete(0, tk.END)
    lat_entry.delete(0, tk.END)
    lon_entry.delete(0, tk.END)
    
    try:
        url = f"{IP_API_BASE}{ip}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        r = requests.get(url, timeout=8)
        data = r.json()
        if data.get("status") == "fail":
            messagebox.showerror("IP Error", f"IP lookup failed: {data.get('message')}")
            return
        elevation = get_elevation(data.get("lat"), data.get("lon"))
        out = {
            "Latitude": data.get("lat"),
            "Longitude": data.get("lon"),
            "Altitude": f"{elevation} m" if elevation is not None else "N/A",
            "Display Address": f"IP: {data.get('query')}",
            "Country": data.get("country") or "",
            "Region": data.get("regionName") or "",
            "City": data.get("city") or "",
            "Postal Code": data.get("zip") or "",
            "Timezone": data.get("timezone") or "",
            "ISP": data.get("isp") or data.get("org") or "",
            "Bounding Box": ""
        }
        fill_result_panel(out)
        add_to_history(f"IP -> {ip}")
        
        # Save to database if connected
        save_to_database(data.get("lat"), data.get("lon"), f"IP: {ip}", "ip_search")
    except Exception as e:
        messagebox.showerror("Error", f"IP lookup failed: {e}")

# -------------------------
# Map generation (Folium)
# -------------------------
def open_map_with_distances():
    """Create map showing distances to major world cities."""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "Please search for a location first.")
        return
    
    try:
        latf = float(lat)
        lonf = float(lon)
    except:
        messagebox.showerror("Invalid", "Invalid coordinates.")
        return
    
    # Major world cities
    major_cities = [
        ("New York, USA", 40.7128, -74.0060),
        ("London, UK", 51.5074, -0.1278),
        ("Paris, France", 48.8566, 2.3522),
        ("Tokyo, Japan", 35.6762, 139.6503),
        ("Beijing, China", 39.9042, 116.4074),
        ("Moscow, Russia", 55.7558, 37.6173),
        ("Dubai, UAE", 25.2048, 55.2708),
        ("Sydney, Australia", -33.8688, 151.2093),
        ("São Paulo, Brazil", -23.5505, -46.6333),
        ("Cairo, Egypt", 30.0444, 31.2357),
        ("Mumbai, India", 19.0760, 72.8777),
        ("Berlin, Germany", 52.5200, 13.4050),
        ("Rome, Italy", 41.9028, 12.4964),
        ("Madrid, Spain", 40.4168, -3.7038),
        ("Istanbul, Turkey", 41.0082, 28.9784),
    ]
    
    # Create map
    m = folium.Map(location=[latf, lonf], zoom_start=3, tiles='OpenStreetMap')
    
    # Add current location
    folium.Marker(
        [latf, lonf],
        popup=f"<b>Your Location</b><br>{result_vars['Display Address'].get() or 'Current Location'}",
        tooltip="Your Location",
        icon=folium.Icon(color='red', icon='star', prefix='glyphicon')
    ).add_to(m)
    
    # Add lines and markers to major cities
    for city_name, city_lat, city_lon in major_cities:
        # Calculate distance
        dist = calculate_distance(latf, lonf, city_lat, city_lon)
        dist_km = dist / 1000
        
        # Add line
        folium.PolyLine(
            locations=[[latf, lonf], [city_lat, city_lon]],
            color='blue',
            weight=2,
            opacity=0.6,
            popup=f"{city_name}<br>Distance: {dist_km:.0f} km"
        ).add_to(m)
        
        # Add city marker
        folium.CircleMarker(
            location=[city_lat, city_lon],
            radius=5,
            popup=f"<b>{city_name}</b><br>Distance: {dist_km:.0f} km ({dist/1609.34:.0f} miles)",
            tooltip=f"{city_name}: {dist_km:.0f} km",
            color='blue',
            fillColor='lightblue',
            fillOpacity=0.7
        ).add_to(m)
    
    # Add title
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; width: auto; background-color: white;
                border: 2px solid #2196F3; border-radius: 5px; z-index: 9999; padding: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-family: Arial, sans-serif;">
        <h4 style="margin: 0 0 5px 0; color: #2196F3;">📍 Distances from Your Location</h4>
        <p style="margin: 0; font-size: 12px;">{result_vars['Display Address'].get() or 'Current Location'}</p>
        <p style="margin: 5px 0 0 0; font-size: 11px; color: #666;">
            Blue lines show distances to major world cities
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Save and open
    outpath = os.path.join(os.getcwd(), "geolocator_distances.html")
    m.save(outpath)
    webbrowser.open("file://" + os.path.abspath(outpath))
    messagebox.showinfo("Map Opened", "Distance map opened in browser!\n\nBlue lines show distances to 15 major world cities.")

def open_searchable_distance_map():
    """Create interactive map where you can search and add multiple cities to see distances."""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "Please search for a location first.")
        return
    
    try:
        latf = float(lat)
        lonf = float(lon)
    except:
        messagebox.showerror("Invalid", "Invalid coordinates.")
        return
    
    # Create dialog for searching cities
    dialog = tk.Toplevel(root)
    dialog.title("Search Cities for Distance Map")
    dialog.geometry("500x600")
    dialog.configure(bg=BG_COLOR)
    
    # Title
    tk.Label(dialog, text="🗺️ Create Custom Distance Map", 
             font=("Segoe UI", 14, "bold"), bg=BG_COLOR, fg=PRIMARY_BLUE).pack(pady=10)
    
    # Info
    info_text = f"Your location: {result_vars['Display Address'].get() or 'Current Location'}\nLat: {latf:.4f}, Lon: {lonf:.4f}"
    tk.Label(dialog, text=info_text, font=("Segoe UI", 9), bg=BG_COLOR, fg=TEXT_SECONDARY).pack(pady=5)
    
    # Search frame
    search_frame = tk.LabelFrame(dialog, text="Search and Add Cities", bg=CARD_BG, padx=10, pady=10)
    search_frame.pack(fill="x", padx=20, pady=10)
    
    tk.Label(search_frame, text="Enter city/country name:", bg=CARD_BG, font=("Segoe UI", 10)).pack(anchor="w")
    search_entry = AutocompleteEntry(search_frame, autocomplete_function=get_address_suggestions, width=40, font=("Segoe UI", 11))
    search_entry.pack(fill="x", pady=5)
    
    # List of added cities
    cities_list = []
    
    listbox_frame = tk.LabelFrame(dialog, text="Added Cities (click to remove)", bg=CARD_BG, padx=10, pady=10)
    listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    cities_listbox = tk.Listbox(listbox_frame, height=15, font=("Segoe UI", 9))
    cities_listbox.pack(side="left", fill="both", expand=True)
    
    scrollbar = tk.Scrollbar(listbox_frame, command=cities_listbox.yview)
    scrollbar.pack(side="right", fill="y")
    cities_listbox.config(yscrollcommand=scrollbar.set)
    
    def add_city():
        city_name = search_entry.get().strip()
        if not city_name:
            messagebox.showerror("Error", "Please enter a city name")
            return
        
        try:
            # Geocode the city
            location = geolocator.geocode(city_name, exactly_one=True, timeout=10)
            if not location:
                messagebox.showerror("Not found", f"City not found: {city_name}")
                return
            
            # Calculate distance
            dist = calculate_distance(latf, lonf, location.latitude, location.longitude)
            dist_km = dist / 1000
            
            # Add to list
            city_data = {
                'name': location.address,
                'lat': location.latitude,
                'lon': location.longitude,
                'distance_km': dist_km,
                'distance_miles': dist / 1609.34
            }
            cities_list.append(city_data)
            
            # Add to listbox
            cities_listbox.insert(tk.END, f"{location.address} - {dist_km:.0f} km ({dist/1609.34:.0f} mi)")
            
            # Clear search
            search_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add city: {e}")
    
    def remove_city():
        selection = cities_listbox.curselection()
        if selection:
            idx = selection[0]
            cities_listbox.delete(idx)
            cities_list.pop(idx)
    
    def create_map():
        if not cities_list:
            messagebox.showerror("Error", "Please add at least one city")
            return
        
        # Create map
        m = folium.Map(location=[latf, lonf], zoom_start=2, tiles='OpenStreetMap')
        
        # Add current location (red star)
        folium.Marker(
            [latf, lonf],
            popup=f"<b>📍 Your Location</b><br>{result_vars['Display Address'].get() or 'Current Location'}<br>Lat: {latf:.4f}, Lon: {lonf:.4f}",
            tooltip="Your Location",
            icon=folium.Icon(color='red', icon='star', prefix='glyphicon')
        ).add_to(m)
        
        # Color palette for different cities
        colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 
                  'darkgreen', 'cadetblue', 'darkpurple', 'pink', 'lightblue', 'lightgreen', 'gray']
        
        # Add lines and markers for each city
        for idx, city in enumerate(cities_list):
            color = colors[idx % len(colors)]
            
            # Add line
            folium.PolyLine(
                locations=[[latf, lonf], [city['lat'], city['lon']]],
                color=color,
                weight=3,
                opacity=0.7,
                popup=f"<b>{city['name']}</b><br>Distance: {city['distance_km']:.0f} km ({city['distance_miles']:.0f} miles)"
            ).add_to(m)
            
            # Add city marker
            folium.Marker(
                location=[city['lat'], city['lon']],
                popup=f"<b>{city['name']}</b><br>Distance: {city['distance_km']:.0f} km<br>({city['distance_miles']:.0f} miles)",
                tooltip=f"{city['name']}: {city['distance_km']:.0f} km",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
        
        # Add legend/title
        legend_html = f'''
        <div style="position: fixed; top: 10px; left: 50px; width: 300px; background-color: white;
                    border: 2px solid #2196F3; border-radius: 5px; z-index: 9999; padding: 15px;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-family: Arial, sans-serif;">
            <h4 style="margin: 0 0 10px 0; color: #2196F3;">📍 Custom Distance Map</h4>
            <p style="margin: 0; font-size: 11px;"><b>From:</b> {result_vars['Display Address'].get() or 'Current Location'}</p>
            <p style="margin: 5px 0; font-size: 11px;"><b>Cities:</b> {len(cities_list)}</p>
            <hr style="margin: 10px 0;">
            <div style="max-height: 200px; overflow-y: auto; font-size: 10px;">
        '''
        
        for idx, city in enumerate(cities_list):
            color = colors[idx % len(colors)]
            legend_html += f'<p style="margin: 3px 0;"><span style="color: {color};">●</span> {city["name"].split(",")[0]}: {city["distance_km"]:.0f} km</p>'
        
        legend_html += '''
            </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Save and open
        outpath = os.path.join(os.getcwd(), "geolocator_custom_distances.html")
        m.save(outpath)
        webbrowser.open("file://" + os.path.abspath(outpath))
        
        messagebox.showinfo("Success", f"Custom distance map created with {len(cities_list)} cities!\n\nMap opened in browser.")
        dialog.destroy()
    
    # Buttons
    btn_frame = tk.Frame(search_frame, bg=CARD_BG)
    btn_frame.pack(fill="x", pady=5)
    
    tk.Button(btn_frame, text="Add City", bg=SUCCESS_GREEN, fg="white", 
              command=add_city, font=("Segoe UI", 9)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Remove Selected", bg=ERROR_RED, fg="white", 
              command=remove_city, font=("Segoe UI", 9)).pack(side="left", padx=5)
    
    # Bind Enter key to add city
    search_entry.bind('<Return>', lambda e: add_city())
    cities_listbox.bind('<Delete>', lambda e: remove_city())
    
    # Bottom buttons
    bottom_frame = tk.Frame(dialog, bg=BG_COLOR)
    bottom_frame.pack(fill="x", padx=20, pady=10)
    
    tk.Button(bottom_frame, text="Create Map", bg=PRIMARY_BLUE, fg="white", 
              command=create_map, font=("Segoe UI", 10, "bold"), width=20).pack(side="left", padx=5)
    tk.Button(bottom_frame, text="Cancel", bg=TEXT_SECONDARY, fg="white", 
              command=dialog.destroy, font=("Segoe UI", 10), width=10).pack(side="right", padx=5)

def open_map_in_browser(satellite=False):
    """Krijon një hartë HTML të bukur dhe të saktë me informacione të detajuara"""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("Nuk ka koordinata", "Ju lutem kërkoni një lokacion fillimisht.")
        return
    try:
        latf = float(lat)
        lonf = float(lon)
    except Exception:
        messagebox.showerror("Koordinata të pavlefshme", "Koordinatat nuk janë numra të vlefshëm.")
        return

    # Krijon hartën me zoom më të saktë
    # Start with satellite if requested, otherwise standard map
    if satellite:
        m = folium.Map(location=[latf, lonf], zoom_start=18, tiles=None)
        # Add satellite layer first (will be default)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='🛰️ Satellite View (Esri)',
            overlay=False,
            control=True
        ).add_to(m)
        # Add standard map as alternative
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='🗺️ Standard Map (OSM)',
            attr='OpenStreetMap contributors',
            overlay=False,
            control=True
        ).add_to(m)
    else:
        m = folium.Map(location=[latf, lonf], zoom_start=18, tiles=None)
        # Add standard map first (will be default)
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='🗺️ Standard Map (OSM)',
            attr='OpenStreetMap contributors',
            overlay=False,
            control=True
        ).add_to(m)
        # Add satellite as alternative
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='🛰️ Satellite View (Esri)',
            overlay=False,
            control=True
        ).add_to(m)
    
    # Marker më i bukur dhe i saktë me informacione të detajuara
    popup_html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 200px;">
        <h3 style="margin: 5px 0; color: #1E88E5;">📍 Lokacioni</h3>
        <hr style="margin: 5px 0;">
        <p style="margin: 3px 0;"><strong>Adresa:</strong><br>{result_vars['Display Address'].get() or 'Nuk dihet'}</p>
        <p style="margin: 3px 0;"><strong>Koordinata:</strong><br>Lat: {latf:.6f}°<br>Lon: {lonf:.6f}°</p>
        <p style="margin: 3px 0;"><strong>Vendndodhja:</strong><br>
        {result_vars['City'].get() or ''}, {result_vars['Region'].get() or ''}<br>
        {result_vars['Country'].get() or ''}</p>
        <p style="margin: 3px 0;"><strong>Lartësia:</strong> {result_vars['Altitude'].get() or 'N/A'}</p>
        <p style="margin: 3px 0; font-size: 10px; color: #666;">Saktësia: ~10-50m (varësisht nga burimi)</p>
    </div>
    """
    
    # Përdor CircleMarker për saktësi më të madhe
    folium.CircleMarker(
        location=[latf, lonf],
        radius=8,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"Lat: {latf:.6f}, Lon: {lonf:.6f}",
        color='#1E88E5',
        fillColor='#1E88E5',
        fillOpacity=0.8,
        weight=2
    ).add_to(m)
    
    # Shto një marker kryesor më të madh
    folium.Marker(
        location=[latf, lonf],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip="Kliko për detaje",
        icon=folium.Icon(color='blue', icon='info-sign', prefix='glyphicon')
    ).add_to(m)
    
    # Shto kontrollin e layer-ave (top right corner)
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Add title/info box
    map_type = "Satellite View (Esri World Imagery)" if satellite else "Standard Map (OpenStreetMap)"
    title_html = f'''
    <div style="position: fixed; 
                top: 10px; 
                left: 50px; 
                width: auto;
                height: auto;
                background-color: white;
                border: 2px solid #1E88E5;
                border-radius: 5px;
                z-index: 9999;
                padding: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif;">
        <h4 style="margin: 0 0 5px 0; color: #1E88E5;">📍 GeoLocator Map</h4>
        <p style="margin: 0; font-size: 12px;"><strong>Default View:</strong> {map_type}</p>
        <p style="margin: 5px 0 0 0; font-size: 11px; color: #666;">
            Use layer control (top-right) to switch between map types
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Shto një mini-map në qoshe (nëse është e disponueshme)
    try:
        from folium.plugins import MiniMap
        minimap = MiniMap(toggle_display=True, position='bottomleft')
        m.add_child(minimap)
    except:
        pass  # MiniMap nuk është kritike
    
    # Shto fullscreen button (nëse është e disponueshme)
    try:
        from folium.plugins import Fullscreen
        Fullscreen(position='topleft').add_to(m)
    except:
        pass  # Fullscreen nuk është kritike
    
    # Shto scale bar
    try:
        from folium.plugins import MeasureControl
        m.add_child(MeasureControl(primary_length_unit='meters', secondary_length_unit='kilometers'))
    except:
        pass
    
    # Ruaj dhe hap
    outpath = os.path.join(os.getcwd(), "geolocator_map.html")
    m.save(outpath)
    
    # Show info message
    view_type = "🛰️ Satellite" if satellite else "🗺️ Standard Map"
    messagebox.showinfo("Map Opened", 
        f"{view_type} opened in browser!\n\n"
        f"📍 Location: {result_vars['Display Address'].get() or 'Unknown'}\n"
        f"📏 Coordinates: {latf:.6f}, {lonf:.6f}\n"
        f"🗺️ Source: {'Esri World Imagery' if satellite else 'OpenStreetMap'}\n\n"
        f"💡 Tip: Use the layer control (top-right) to switch between map types")
    
    webbrowser.open("file://" + os.path.abspath(outpath))

def embed_map_inside_app():
    if not TKHTML_AVAILABLE:
        messagebox.showinfo("Not available", "tkhtmlview not installed. Install with: pip install tkhtmlview")
        return
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available — search first.")
        return
    try:
        latf = float(lat); lonf = float(lon)
    except:
        messagebox.showerror("Invalid", "Coordinates invalid.")
        return
    m = folium.Map(location=[latf, lonf], zoom_start=16)
    folium.Marker([latf, lonf], popup=result_vars["Display Address"].get() or "Location").add_to(m)
    html_path = os.path.join(os.getcwd(), "geolocator_embed.html")
    m.save(html_path)
    with open(html_path, "r", encoding="utf8") as f:
        html_content = f.read()
    # show in a new Toplevel with HTMLScrolledText
    top = tk.Toplevel(root)
    top.title("Embedded Map View")
    top.geometry("800x600")
    scr = HTMLScrolledText(top, html=html_content)
    scr.pack(fill="both", expand=True)

# -------------------------
# CSV Export & Batch
# -------------------------
def export_current_to_csv():
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No data", "No result to export.")
        return
    filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], title="Save result as CSV")
    if not filename:
        return
    data = {k: result_vars[k].get() for k in result_vars}
    with open(filename, "w", newline="", encoding="utf8") as f:
        writer = csv.writer(f)
        writer.writerow(["Field", "Value"])
        for k, v in data.items():
            writer.writerow([k, v])
    messagebox.showinfo("Saved", f"Result exported to {filename}")

def import_single_address_from_csv():
    """Import a random address from CSV and search it."""
    file = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv")],
        title="Select CSV file with addresses"
    )
    
    if not file:
        return
    
    try:
        df = pd.read_csv(file, encoding='utf-8')
    except:
        try:
            df = pd.read_csv(file, encoding='latin-1')
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read CSV: {e}")
            return
    
    # Find address column
    address_col = None
    for col in df.columns:
        if col.lower() in ['address', 'adresa', 'adresë', 'location', 'lokacion']:
            address_col = col
            break
    
    if not address_col:
        messagebox.showerror("Error", "CSV must have a column named 'address' or 'adresa'")
        return
    
    # Get random address
    import random
    addresses = df[address_col].dropna().tolist()
    if not addresses:
        messagebox.showerror("Error", "No addresses found in CSV")
        return
    
    random_address = random.choice(addresses)
    
    # Set it in the address field and search
    address_entry.delete(0, tk.END)
    address_entry.insert(0, str(random_address))
    
    messagebox.showinfo("Random Address", f"Imported random address:\n{random_address}\n\nClick 'Find Coordinates' to search.")

def batch_geocode_from_csv():
    """Geokodim në masë nga CSV - merr adresa dhe kthen koordinata"""
    file = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv")],
        title="Zgjidhni skedarin CSV me adresa (kolona 'address')"
    )
    
    if not file:
        return
    
    try:
        df = pd.read_csv(file, encoding='utf-8')
    except Exception as e:
        try:
            df = pd.read_csv(file, encoding='latin-1')
        except:
            messagebox.showerror("Gabim", f"Nuk mund të lexohet skedari CSV: {e}")
            return
    
    # Kontrollo kolonat e disponueshme
    cols_lower = [c.lower() for c in df.columns]
    address_col = None
    for col in df.columns:
        if col.lower() in ['address', 'adresa', 'adresë', 'location', 'lokacion']:
            address_col = col
            break
    
    if not address_col:
        messagebox.showerror("Format CSV", "CSV duhet të ketë një kolonë me emrin 'address' ose 'adresa'.")
        return
    
    # Procesimi me progress
    total = len(df)
    out_rows = []
    
    progress_window = tk.Toplevel(root)
    progress_window.title("Duke procesuar...")
    progress_window.geometry("400x100")
    progress_label = tk.Label(progress_window, text=f"Duke procesuar 0/{total}...", font=("Segoe UI", 10))
    progress_label.pack(pady=10)
    progress_bar = ttk.Progressbar(progress_window, length=350, mode='determinate', maximum=total)
    progress_bar.pack(pady=5)
    progress_window.update()
    
    for idx, addr in enumerate(df[address_col].astype(str).tolist(), 1):
        if pd.isna(addr) or str(addr).strip() == '':
            out_rows.append({"address": str(addr), "lat": "", "lon": "", "status": "Bosh"})
        else:
            try:
                loc = geolocator.geocode(str(addr).strip(), addressdetails=True, exactly_one=True, timeout=10)
                if loc:
                    out_rows.append({
                        "address": str(addr),
                        "lat": loc.latitude,
                        "lon": loc.longitude,
                        "status": "Sukses"
                    })
                else:
                    out_rows.append({"address": str(addr), "lat": "", "lon": "", "status": "Nuk u gjet"})
            except Exception as e:
                out_rows.append({"address": str(addr), "lat": "", "lon": "", "status": f"Gabim: {str(e)[:30]}"})
        
        try:
            progress_label.config(text=f"Duke procesuar {idx}/{total}...")
            progress_bar['value'] = idx
            progress_window.update()
        except:
            pass  # Window might be closed
    
    progress_window.destroy()
    
    # Ruaj rezultatet
    savepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Ruani rezultatet e geokodimit"
    )
    if not savepath:
        return
    
    try:
        result_df = pd.DataFrame(out_rows)
        result_df.to_csv(savepath, index=False, encoding='utf-8-sig')  # utf-8-sig për Excel
        success_count = len([r for r in out_rows if r.get("status") == "Sukses"])
        messagebox.showinfo("Përfunduar", f"Geokodim i përfunduar!\n\nTotal: {total}\nSukses: {success_count}\nRuajtur në: {savepath}")
    except Exception as e:
        messagebox.showerror("Gabim", f"Nuk mund të ruhet skedari: {e}")

# -------------------------
# GIS/GNSS/PostGIS GUI Handlers
# -------------------------
def on_transform_coordinates():
    """Transform coordinates between CRS."""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    try:
        latf = float(lat)
        lonf = float(lon)
        # Convert to UTM
        utm_x, utm_y, zone = convert_to_utm(latf, lonf)
        if utm_x and utm_y:
            msg = f"UTM Coordinates:\nZone: {zone}\nX (Easting): {utm_x:.2f}\nY (Northing): {utm_y:.2f}"
            messagebox.showinfo("Coordinate Transformation", msg)
        else:
            messagebox.showwarning("Transform", "pyproj not available. Install: pip install pyproj")
    except Exception as e:
        messagebox.showerror("Error", f"Transformation failed: {e}")

def on_calculate_distance():
    """Calculate distance between two points - with option to enter address or coordinates."""
    lat1 = result_vars["Latitude"].get()
    lon1 = result_vars["Longitude"].get()
    if not lat1 or not lon1:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    
    # Open dialog for second point
    dialog = tk.Toplevel(root)
    dialog.title("Calculate Distance / Llogarit Distancën")
    dialog.geometry("400x280")
    
    tk.Label(dialog, text="Point 1 (Current):", font=("Segoe UI", 10, "bold")).pack(pady=5)
    tk.Label(dialog, text=f"Lat: {lat1}, Lon: {lon1}", font=("Segoe UI", 9)).pack()
    tk.Label(dialog, text=result_vars["Display Address"].get() or "Unknown location", 
             font=("Segoe UI", 8), wraplength=350).pack(pady=(0,10))
    
    tk.Label(dialog, text="Point 2 - Choose input method:", font=("Segoe UI", 10, "bold")).pack(pady=5)
    
    # Radio buttons for input method
    input_method = tk.StringVar(value="address")
    tk.Radiobutton(dialog, text="Enter Address/City (e.g., 'Berlin, Germany')", 
                   variable=input_method, value="address").pack(anchor="w", padx=20)
    tk.Radiobutton(dialog, text="Enter Coordinates (Lat, Lon)", 
                   variable=input_method, value="coords").pack(anchor="w", padx=20)
    
    # Address entry
    address_frame = tk.Frame(dialog)
    address_frame.pack(pady=5, fill="x", padx=20)
    tk.Label(address_frame, text="Address/City:").pack(anchor="w")
    address_entry = tk.Entry(address_frame, width=40)
    address_entry.pack(fill="x")
    
    # Coordinates entry
    coords_frame = tk.Frame(dialog)
    coords_frame.pack(pady=5, fill="x", padx=20)
    tk.Label(coords_frame, text="Latitude:").pack(anchor="w")
    lat2_entry = tk.Entry(coords_frame, width=20)
    lat2_entry.pack(fill="x")
    tk.Label(coords_frame, text="Longitude:").pack(anchor="w")
    lon2_entry = tk.Entry(coords_frame, width=20)
    lon2_entry.pack(fill="x")
    
    def calc():
        try:
            lat2, lon2 = None, None
            point2_name = ""
            
            if input_method.get() == "address":
                # Geocode the address
                addr = address_entry.get().strip()
                if not addr:
                    messagebox.showerror("Error", "Please enter an address or city.")
                    return
                
                location = geolocator.geocode(addr, addressdetails=True, exactly_one=True, timeout=10)
                if not location:
                    messagebox.showerror("Not found", f"Address not found: {addr}")
                    return
                
                lat2 = location.latitude
                lon2 = location.longitude
                point2_name = getattr(location, "address", addr)
            else:
                # Use coordinates
                lat2 = float(lat2_entry.get())
                lon2 = float(lon2_entry.get())
                point2_name = f"Lat: {lat2}, Lon: {lon2}"
            
            # Calculate distance and bearing
            dist = calculate_distance(float(lat1), float(lon1), lat2, lon2)
            bearing = calculate_bearing(float(lat1), float(lon1), lat2, lon2)
            
            # Format result message
            msg = f"📍 Point 1: {result_vars['Display Address'].get() or 'Current location'}\n"
            msg += f"📍 Point 2: {point2_name}\n\n"
            msg += f"📏 Distance: {dist:.2f} meters\n"
            msg += f"   = {dist/1000:.3f} km\n"
            msg += f"   = {dist/1609.34:.3f} miles\n\n"
            msg += f"🧭 Bearing: {bearing:.1f}°\n"
            
            # Add cardinal direction
            directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            idx = int((bearing + 22.5) / 45) % 8
            msg += f"   Direction: {directions[idx]}"
            
            messagebox.showinfo("Distance Calculation / Llogaritja e Distancës", msg)
            dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Error", "Invalid coordinates. Please enter valid numbers.")
        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {e}")
    
    tk.Button(dialog, text="Calculate / Llogarit", bg=PRIMARY_BLUE, fg="white", 
              command=calc, font=("Segoe UI", 10)).pack(pady=15)

def on_store_point():
    """Store current point for GIS operations."""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    stored_points.append({
        "lat": float(lat),
        "lon": float(lon),
        "name": result_vars["Display Address"].get() or f"Point {len(stored_points)+1}",
        "timestamp": datetime.now().isoformat()
    })
    messagebox.showinfo("Stored", f"Point stored. Total: {len(stored_points)}")

def on_export_geojson():
    """Export stored points to GeoJSON."""
    if not stored_points:
        messagebox.showerror("Nuk ka pika", "Nuk ka pika të ruajtura. Ruaj pika fillimisht me butonin 'Store Point'.")
        return
    
    filename = filedialog.asksaveasfilename(
        defaultextension=".geojson",
        filetypes=[("GeoJSON files", "*.geojson"), ("JSON files", "*.json")],
        title="Ruaj pikat si GeoJSON"
    )
    
    if not filename:
        return
    
    try:
        success, message = export_to_geojson(stored_points, filename)
        if success:
            messagebox.showinfo("Eksportuar", f"Sukses! {message}\nRuajtur në: {filename}")
        else:
            messagebox.showerror("Gabim", f"Eksportimi dështoi:\n{message}")
    except Exception as e:
        messagebox.showerror("Gabim", f"Gabim gjatë eksportimit:\n{str(e)}")

def on_import_geojson():
    """Import points from GeoJSON."""
    filename = filedialog.askopenfilename(
        filetypes=[("GeoJSON files", "*.geojson"), ("JSON files", "*.json")],
        title="Zgjidhni skedarin GeoJSON për import"
    )
    
    if not filename:
        return
    
    try:
        points, message = import_from_geojson(filename)
        if points:
            stored_points.extend(points)
            messagebox.showinfo("Importuar", f"Sukses! {message}\nTotal pika të ruajtura: {len(stored_points)}")
        else:
            messagebox.showerror("Gabim", f"Importimi dështoi:\n{message}")
    except Exception as e:
        messagebox.showerror("Gabim", f"Gabim gjatë importimit:\n{str(e)}")

def on_export_gpx():
    """Export stored points to GPX (GNSS format)."""
    if not stored_points:
        messagebox.showerror("Nuk ka pika", "Nuk ka pika të ruajtura. Ruaj pika fillimisht me butonin 'Store Point'.")
        return
    
    if not GPX_AVAILABLE:
        messagebox.showerror("Nuk është e disponueshme", "gpxpy nuk është instaluar.\n\nInstalo me: pip install gpxpy")
        return
    
    filename = filedialog.asksaveasfilename(
        defaultextension=".gpx",
        filetypes=[("GPX files", "*.gpx")],
        title="Ruaj pikat si GPX"
    )
    
    if not filename:
        return
    
    try:
        success, message = export_to_gpx(stored_points, filename)
        if success:
            messagebox.showinfo("Eksportuar", f"Sukses! {message}\nRuajtur në: {filename}")
        else:
            messagebox.showerror("Gabim", f"Eksportimi dështoi:\n{message}")
    except Exception as e:
        messagebox.showerror("Gabim", f"Gabim gjatë eksportimit:\n{str(e)}")

def on_import_gpx():
    """Import points from GPX (GNSS format)."""
    if not GPX_AVAILABLE:
        messagebox.showerror("Nuk është e disponueshme", "gpxpy nuk është instaluar.\n\nInstalo me: pip install gpxpy")
        return
    
    filename = filedialog.askopenfilename(
        filetypes=[("GPX files", "*.gpx")],
        title="Zgjidhni skedarin GPX për import"
    )
    
    if not filename:
        return
    
    try:
        points, message = import_from_gpx(filename)
        if points:
            stored_points.extend(points)
            messagebox.showinfo("Importuar", f"Sukses! {message}\nTotal pika të ruajtura: {len(stored_points)}")
        else:
            messagebox.showerror("Gabim", f"Importimi dështoi:\n{message}")
    except Exception as e:
        messagebox.showerror("Gabim", f"Gabim gjatë importimit:\n{str(e)}")

def on_postgis_connect():
    """Configure PostGIS connection with better feedback."""
    dialog = tk.Toplevel(root)
    dialog.title("PostGIS Connection / Lidhja me PostGIS")
    dialog.geometry("450x400")
    
    tk.Label(dialog, text="PostGIS Database Connection", font=("Segoe UI", 12, "bold")).pack(pady=10)
    
    # Info text
    info_text = """
PostGIS is a spatial database extension for PostgreSQL.
PostGIS është një shtesë hapësinore për PostgreSQL.

Required: PostgreSQL + PostGIS extension installed
Kërkohet: PostgreSQL + shtesa PostGIS e instaluar
    """
    tk.Label(dialog, text=info_text, font=("Segoe UI", 8), fg="#666", 
             justify="left", wraplength=400).pack(pady=5)
    
    # Current status
    status_frame = tk.Frame(dialog, bg="#F0F0F0", padx=10, pady=5)
    status_frame.pack(fill="x", padx=10, pady=5)
    
    current_status = "Not connected / Nuk është i lidhur"
    if POSTGIS_HOST and POSTGIS_DB:
        current_status = f"Current: {POSTGIS_USER}@{POSTGIS_HOST}/{POSTGIS_DB}"
        if connect_postgis():
            current_status += " ✅ Connected"
        else:
            current_status += " ❌ Not connected"
    
    tk.Label(status_frame, text=f"Status: {current_status}", font=("Segoe UI", 8), 
             bg="#F0F0F0").pack()
    
    # Input fields
    input_frame = tk.Frame(dialog)
    input_frame.pack(pady=10, padx=20, fill="both")
    
    fields = [
        ("Host:", "host", "localhost or IP address"),
        ("Port:", "port", "5432 (default)"),
        ("Database:", "db", "database name"),
        ("User:", "user", "postgres"),
        ("Password:", "password", "")
    ]
    entries = {}
    
    for i, (label, key, placeholder) in enumerate(fields):
        tk.Label(input_frame, text=label, font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w", pady=3)
        entry = tk.Entry(input_frame, width=30, show="*" if key == "password" else "")
        entry.grid(row=i, column=1, pady=3, padx=5)
        
        # Set current values if available
        if key == "host" and POSTGIS_HOST:
            entry.insert(0, POSTGIS_HOST)
        elif key == "port":
            entry.insert(0, POSTGIS_PORT or "5432")
        elif key == "db" and POSTGIS_DB:
            entry.insert(0, POSTGIS_DB)
        elif key == "user" and POSTGIS_USER:
            entry.insert(0, POSTGIS_USER)
        elif key == "password" and POSTGIS_PASSWORD:
            entry.insert(0, POSTGIS_PASSWORD)
        
        entries[key] = entry
        
        # Placeholder hint
        if placeholder:
            tk.Label(input_frame, text=f"({placeholder})", font=("Segoe UI", 7), 
                    fg="#999").grid(row=i, column=2, sticky="w", padx=5)
    
    def test_connection():
        """Test connection without saving."""
        global POSTGIS_HOST, POSTGIS_PORT, POSTGIS_DB, POSTGIS_USER, POSTGIS_PASSWORD
        
        # Temporarily set values
        old_values = (POSTGIS_HOST, POSTGIS_PORT, POSTGIS_DB, POSTGIS_USER, POSTGIS_PASSWORD)
        
        POSTGIS_HOST = entries["host"].get().strip()
        POSTGIS_PORT = entries["port"].get().strip() or "5432"
        POSTGIS_DB = entries["db"].get().strip()
        POSTGIS_USER = entries["user"].get().strip()
        POSTGIS_PASSWORD = entries["password"].get()
        
        if not all([POSTGIS_HOST, POSTGIS_DB, POSTGIS_USER]):
            messagebox.showerror("Error", "Please fill in Host, Database, and User fields.")
            POSTGIS_HOST, POSTGIS_PORT, POSTGIS_DB, POSTGIS_USER, POSTGIS_PASSWORD = old_values
            return
        
        conn = connect_postgis()
        if conn:
            try:
                cur = conn.cursor()
                # Test PostGIS extension
                cur.execute("SELECT PostGIS_Version();")
                version = cur.fetchone()
                cur.close()
                conn.close()
                
                msg = f"✅ Connection successful!\n\n"
                msg += f"Host: {POSTGIS_HOST}:{POSTGIS_PORT}\n"
                msg += f"Database: {POSTGIS_DB}\n"
                msg += f"User: {POSTGIS_USER}\n"
                if version:
                    msg += f"\nPostGIS Version: {version[0]}"
                
                messagebox.showinfo("Connection Test", msg)
            except Exception as e:
                conn.close()
                messagebox.showwarning("Connected but...", 
                    f"Connected to database but PostGIS extension may not be installed.\n\n"
                    f"Error: {e}\n\n"
                    f"Install PostGIS extension:\nCREATE EXTENSION postgis;")
        else:
            messagebox.showerror("Connection Failed", 
                f"❌ Could not connect to database.\n\n"
                f"Possible issues:\n"
                f"• PostgreSQL is not running\n"
                f"• Wrong credentials\n"
                f"• Database does not exist\n"
                f"• Firewall blocking connection\n"
                f"• psycopg2 not installed (pip install psycopg2-binary)")
            
            # Restore old values
            POSTGIS_HOST, POSTGIS_PORT, POSTGIS_DB, POSTGIS_USER, POSTGIS_PASSWORD = old_values
    
    def save_conn():
        """Save connection and close dialog."""
        global POSTGIS_HOST, POSTGIS_PORT, POSTGIS_DB, POSTGIS_USER, POSTGIS_PASSWORD
        
        POSTGIS_HOST = entries["host"].get().strip()
        POSTGIS_PORT = entries["port"].get().strip() or "5432"
        POSTGIS_DB = entries["db"].get().strip()
        POSTGIS_USER = entries["user"].get().strip()
        POSTGIS_PASSWORD = entries["password"].get()
        
        if not all([POSTGIS_HOST, POSTGIS_DB, POSTGIS_USER]):
            messagebox.showerror("Error", "Please fill in Host, Database, and User fields.")
            return
        
        if connect_postgis():
            messagebox.showinfo("Saved", "✅ Connection saved successfully!\n\nYou can now use PostGIS features.")
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Connection failed. Please test connection first.")
    
    # Buttons
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=15)
    
    tk.Button(btn_frame, text="Test Connection", bg="#FF9800", fg="white", 
              command=test_connection, font=("Segoe UI", 9)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Save & Connect", bg="#4CAF50", fg="white", 
              command=save_conn, font=("Segoe UI", 9)).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", bg="#9E9E9E", fg="white", 
              command=dialog.destroy, font=("Segoe UI", 9)).pack(side="left", padx=5)

def on_postgis_insert():
    """Insert current point into PostGIS."""
    if not POSTGIS_AVAILABLE:
        messagebox.showerror("Not available", "psycopg2 not installed. Install: pip install psycopg2-binary")
        return
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    
    dialog = tk.Toplevel(root)
    dialog.title("Insert to PostGIS")
    dialog.geometry("300x150")
    tk.Label(dialog, text="Table name:").pack()
    table_entry = tk.Entry(dialog, width=25)
    table_entry.pack()
    
    def insert():
        table = table_entry.get()
        if not table:
            messagebox.showerror("Error", "Table name required")
            return
        if insert_point_postgis(table, float(lat), float(lon), 
                               result_vars["Display Address"].get() or "Point", ""):
            messagebox.showinfo("Success", "Point inserted to PostGIS")
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Insert failed. Check connection and table exists.")
    
    tk.Button(dialog, text="Insert", command=insert).pack(pady=10)

def on_add_to_favorites():
    """Add current location to favorites"""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    address = result_vars["Display Address"].get()
    
    if not lat or not lon:
        messagebox.showerror("Error", "No location to save. Search for a location first.")
        return
    
    # Dialog to enter name
    dialog = tk.Toplevel(root)
    dialog.title("Add to Favorites")
    dialog.geometry("400x250")
    dialog.configure(bg=BG_COLOR)
    
    tk.Label(dialog, text="⭐ Add to Favorites", font=("Segoe UI", 12, "bold"), bg=BG_COLOR).pack(pady=10)
    
    tk.Label(dialog, text="Location:", bg=BG_COLOR).pack(anchor="w", padx=20)
    tk.Label(dialog, text=address[:60] + "..." if len(address) > 60 else address, 
             bg=BG_COLOR, fg=TEXT_SECONDARY, wraplength=350).pack(anchor="w", padx=20, pady=5)
    
    tk.Label(dialog, text="Favorite Name:", bg=BG_COLOR).pack(anchor="w", padx=20, pady=(10,0))
    name_entry = tk.Entry(dialog, width=40)
    name_entry.pack(padx=20, pady=5)
    name_entry.insert(0, address.split(",")[0] if "," in address else address[:30])
    
    tk.Label(dialog, text="Notes (optional):", bg=BG_COLOR).pack(anchor="w", padx=20, pady=(10,0))
    notes_entry = tk.Entry(dialog, width=40)
    notes_entry.pack(padx=20, pady=5)
    
    def save():
        name = name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a name")
            return
        
        notes = notes_entry.get().strip()
        if save_favorite(name, address, lat, lon, notes):
            messagebox.showinfo("Success", f"✅ '{name}' added to favorites!")
            dialog.destroy()
            update_favorites_dropdown()
        else:
            messagebox.showerror("Error", "Failed to save favorite")
    
    tk.Button(dialog, text="Save", bg=SUCCESS_GREEN, fg="white", command=save, width=15).pack(pady=15)

def on_load_favorite():
    """Load favorite location"""
    if not favorite_locations:
        messagebox.showinfo("No Favorites", "No favorite locations saved yet.\n\nSearch for a location and click 'Add to Favorites'.")
        return
    
    # Dialog to select favorite
    dialog = tk.Toplevel(root)
    dialog.title("Load Favorite Location")
    dialog.geometry("500x400")
    dialog.configure(bg=BG_COLOR)
    
    tk.Label(dialog, text="⭐ Your Favorite Locations", font=("Segoe UI", 12, "bold"), bg=BG_COLOR).pack(pady=10)
    
    # Listbox
    frame = tk.Frame(dialog, bg=BG_COLOR)
    frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    listbox = tk.Listbox(frame, font=("Segoe UI", 9), height=15)
    listbox.pack(side="left", fill="both", expand=True)
    
    scrollbar = tk.Scrollbar(frame, command=listbox.yview)
    scrollbar.pack(side="right", fill="y")
    listbox.config(yscrollcommand=scrollbar.set)
    
    # Populate listbox
    for fav in favorite_locations:
        listbox.insert(tk.END, f"{fav['name']} - {fav['address'][:50]}")
    
    def load():
        selection = listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a favorite")
            return
        
        fav = favorite_locations[selection[0]]
        dialog.destroy()
        
        # Use the quick load function
        load_favorite_quick(fav)
    
    def delete():
        selection = listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a favorite to delete")
            return
        
        fav = favorite_locations[selection[0]]
        if messagebox.askyesno("Confirm", f"Delete '{fav['name']}' from favorites?"):
            if delete_favorite(fav['name']):
                listbox.delete(selection[0])
                messagebox.showinfo("Deleted", "Favorite deleted")
                update_favorites_dropdown()
    
    # Buttons
    btn_frame = tk.Frame(dialog, bg=BG_COLOR)
    btn_frame.pack(pady=10)
    
    tk.Button(btn_frame, text="Load", bg=PRIMARY_BLUE, fg="white", command=load, width=12).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Delete", bg=ERROR_RED, fg="white", command=delete, width=12).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", bg=TEXT_SECONDARY, fg="white", command=dialog.destroy, width=12).pack(side="left", padx=5)

def show_location_details():
    """Show location details with visual graphs"""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    address = result_vars["Display Address"].get()
    city = result_vars["City"].get()
    country = result_vars["Country"].get()
    altitude = result_vars["Altitude"].get()
    weather = result_vars["Weather"].get()
    timezone = result_vars["Timezone"].get()
    
    if not lat or not lon:
        messagebox.showerror("Error", "No location to show. Search for a location first.")
        return
    
    # Create dialog
    dialog = tk.Toplevel(root)
    dialog.title("📊 Location Overview")
    dialog.geometry("700x650")
    dialog.configure(bg=BG_COLOR)
    
    # Title
    tk.Label(dialog, text="📊 Location Overview", font=("Segoe UI", 18, "bold"), 
             bg=BG_COLOR, fg=PRIMARY_BLUE).pack(pady=15)
    
    # Main info card
    info_frame = tk.LabelFrame(dialog, text="📍 Location Information", bg=CARD_BG, 
                               padx=20, pady=15, font=("Segoe UI", 12, "bold"))
    info_frame.pack(fill="x", padx=20, pady=10)
    
    # Address
    tk.Label(info_frame, text=address[:70], font=("Segoe UI", 11, "bold"), 
             bg=CARD_BG, wraplength=650).pack(anchor="w", pady=5)
    
    # City, Country
    if city and country:
        tk.Label(info_frame, text=f"📍 {city}, {country}", font=("Segoe UI", 10), 
                bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=3)
    elif country:
        tk.Label(info_frame, text=f"📍 {country}", font=("Segoe UI", 10), 
                bg=CARD_BG, fg=TEXT_SECONDARY).pack(anchor="w", pady=3)
    
    # Coordinates
    tk.Label(info_frame, text=f"🌐 Coordinates: {lat}, {lon}", font=("Segoe UI", 10), 
            bg=CARD_BG).pack(anchor="w", pady=3)
    
    # Altitude
    if altitude and altitude != "Loading...":
        tk.Label(info_frame, text=f"⛰️ Altitude: {altitude}", font=("Segoe UI", 10), 
                bg=CARD_BG).pack(anchor="w", pady=3)
    
    # Weather
    if weather and weather != "Loading...":
        tk.Label(info_frame, text=f"🌤️ Weather: {weather}", font=("Segoe UI", 10), 
                bg=CARD_BG).pack(anchor="w", pady=3)
    
    # Timezone
    if timezone and timezone != "Loading...":
        tz_short = timezone.split(' - ')[0] if ' - ' in timezone else timezone
        tk.Label(info_frame, text=f"🕐 Timezone: {tz_short}", font=("Segoe UI", 10), 
                bg=CARD_BG).pack(anchor="w", pady=3)
    
    # Visual chart if matplotlib available
    if MATPLOTLIB_AVAILABLE:
        chart_frame = tk.LabelFrame(dialog, text="📊 Visual Data", bg=CARD_BG, 
                                    padx=10, pady=10, font=("Segoe UI", 11, "bold"))
        chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        try:
            # Create figure with subplots
            fig = Figure(figsize=(6, 3.5), facecolor=CARD_BG)
            
            # Parse data for visualization
            try:
                lat_val = float(lat)
                lon_val = float(lon)
                alt_val = float(altitude.replace(' m', '').replace('N/A', '0')) if altitude else 0
                
                # Create bar chart
                ax = fig.add_subplot(111)
                
                categories = ['Latitude', 'Longitude', 'Altitude\n(m)']
                values = [lat_val, lon_val, alt_val/10]  # Scale altitude for visibility
                colors = [PRIMARY_BLUE, SUCCESS_GREEN, WARNING_ORANGE]
                
                bars = ax.bar(categories, values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
                
                # Add value labels on bars
                for bar, val in zip(bars, [lat_val, lon_val, alt_val]):
                    height = bar.get_height()
                    label = f'{val:.2f}' if val < 1000 else f'{val:.0f}'
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           label, ha='center', va='bottom', fontsize=10, fontweight='bold')
                
                ax.set_ylabel('Value', fontsize=11, fontweight='bold')
                ax.set_title('Location Data Visualization', fontsize=12, fontweight='bold', pad=10)
                ax.grid(axis='y', alpha=0.3, linestyle='--')
                ax.axhline(y=0, color='black', linewidth=0.8)
                
                # Embed chart
                canvas = FigureCanvasTkAgg(fig, master=chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                
            except Exception as e:
                tk.Label(chart_frame, text=f"Could not create chart: {e}", 
                        font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_SECONDARY).pack(pady=20)
        except Exception as e:
            tk.Label(chart_frame, text="Chart unavailable", 
                    font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_SECONDARY).pack(pady=20)
    else:
        # Show text summary if no matplotlib
        summary_frame = tk.LabelFrame(dialog, text="📋 Summary", bg=CARD_BG, 
                                     padx=20, pady=15, font=("Segoe UI", 11, "bold"))
        summary_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(summary_frame, text="Install matplotlib for visual charts:", 
                font=("Segoe UI", 9, "italic"), bg=CARD_BG, fg=TEXT_SECONDARY).pack(pady=5)
        tk.Label(summary_frame, text="pip install matplotlib", 
                font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=PRIMARY_BLUE).pack()
    
    # Close button
    tk.Button(dialog, text="Close", bg=PRIMARY_BLUE, fg="white", 
              command=dialog.destroy, font=("Segoe UI", 11, "bold"), width=15).pack(pady=15)

def on_show_statistics():
    """Show statistics dashboard with visual chart"""
    stats = get_statistics()
    
    # Dialog
    dialog = tk.Toplevel(root)
    dialog.title("Statistics Dashboard")
    dialog.geometry("700x650")
    dialog.configure(bg=BG_COLOR)
    
    tk.Label(dialog, text="📊 Statistics Dashboard", font=("Segoe UI", 16, "bold"), 
             bg=BG_COLOR, fg=PRIMARY_BLUE).pack(pady=10)
    
    # Stats frame
    stats_frame = tk.LabelFrame(dialog, text="Search Statistics", bg=CARD_BG, padx=20, pady=15, 
                                font=("Segoe UI", 11, "bold"))
    stats_frame.pack(fill="x", padx=20, pady=10)
    
    tk.Label(stats_frame, text=f"Total Searches: {stats['total']}", font=("Segoe UI", 12, "bold"), 
             bg=CARD_BG, fg=SUCCESS_GREEN).pack(anchor="w", pady=5)
    tk.Label(stats_frame, text=f"Today: {stats['today']}", font=("Segoe UI", 11), bg=CARD_BG).pack(anchor="w", pady=2)
    
    # Visual chart if matplotlib available
    if MATPLOTLIB_AVAILABLE and stats['by_type']:
        chart_frame = tk.LabelFrame(dialog, text="📊 Search Types Chart", bg=CARD_BG, padx=10, pady=10,
                                    font=("Segoe UI", 11, "bold"))
        chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create bar chart
        fig = Figure(figsize=(6, 3), facecolor=CARD_BG)
        ax = fig.add_subplot(111)
        
        types = list(stats['by_type'].keys())
        counts = list(stats['by_type'].values())
        colors = [PRIMARY_BLUE, SUCCESS_GREEN, WARNING_ORANGE, ERROR_RED][:len(types)]
        
        ax.bar(types, counts, color=colors, alpha=0.8)
        ax.set_ylabel('Number of Searches', fontsize=10)
        ax.set_title('Searches by Type', fontsize=11, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Embed chart in tkinter
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
    elif stats['by_type']:
        # Text-based if no matplotlib
        type_frame = tk.LabelFrame(dialog, text="By Type", bg=CARD_BG, padx=20, pady=15)
        type_frame.pack(fill="x", padx=20, pady=10)
        for search_type, count in stats['by_type'].items():
            tk.Label(type_frame, text=f"  • {search_type}: {count}", font=("Segoe UI", 10), bg=CARD_BG).pack(anchor="w", pady=2)
    
    # Recent searches
    recent_frame = tk.LabelFrame(dialog, text="Recent Searches", bg=CARD_BG, padx=20, pady=15,
                                 font=("Segoe UI", 10, "bold"))
    recent_frame.pack(fill="x", padx=20, pady=10)
    
    if stats['recent']:
        for name, date in stats['recent'][:5]:
            tk.Label(recent_frame, text=f"• {name[:60]} - {date}", font=("Segoe UI", 9), bg=CARD_BG).pack(anchor="w", pady=2)
    else:
        tk.Label(recent_frame, text="No searches yet", font=("Segoe UI", 9), bg=CARD_BG, fg=TEXT_SECONDARY).pack()
    
    tk.Button(dialog, text="Close", bg=PRIMARY_BLUE, fg="white", command=dialog.destroy, 
              font=("Segoe UI", 10), width=15).pack(pady=15)

def update_favorites_dropdown():
    """Update favorites dropdown if it exists"""
    load_favorites()
    # Update dropdown menu if it exists
    try:
        if 'favorites_menu' in globals():
            favorites_menu.delete(0, tk.END)
            if favorite_locations:
                for fav in favorite_locations:
                    favorites_menu.add_command(label=fav['name'], 
                                              command=lambda f=fav: load_favorite_quick(f))
            else:
                favorites_menu.add_command(label="No favorites yet", state="disabled")
    except:
        pass

def load_favorite_extra_info(lat, lon):
    """Load extra info for favorite location"""
    try:
        # Get reverse geocode for full details
        location = geolocator.reverse(f"{lat}, {lon}", addressdetails=True, exactly_one=True, timeout=10)
        if location:
            data = extract_address_fields(location)
            result_vars["Country"].set(data["country"] or "")
            result_vars["Region"].set(data["state"] or "")
            result_vars["City"].set(data["city"] or "")
            result_vars["Postal Code"].set(data["postcode"] or "")
            result_vars["Bounding Box"].set(", ".join(data["boundingbox"]) if data["boundingbox"] else "")
        
        # Load weather, timezone, elevation
        elevation = get_elevation(lat, lon)
        result_vars["Altitude"].set(f"{elevation} m" if elevation is not None else "N/A")
        
        tz_info = get_timezone_info(lat, lon)
        if tz_info:
            result_vars["Timezone"].set(f"{tz_info['timezone']} (UTC{tz_info['utc_offset']:+.1f}) - {tz_info['current_time']}")
        
        weather_info = get_weather_info(lat, lon)
        if weather_info:
            result_vars["Weather"].set(f"{weather_info['condition']} {weather_info['temperature']}, Wind: {weather_info['windspeed']}")
    except:
        pass

def load_favorite_quick(fav):
    """Quick load favorite - use saved address directly"""
    # Clear all fields first
    address_entry.delete(0, tk.END)
    lat_entry.delete(0, tk.END)
    lon_entry.delete(0, tk.END)
    ip_entry.delete(0, tk.END)
    
    # Fill in the saved data directly
    result_vars["Latitude"].set(str(fav['lat']))
    result_vars["Longitude"].set(str(fav['lon']))
    result_vars["Display Address"].set(fav['address'])
    result_vars["Altitude"].set("Loading...")
    result_vars["Timezone"].set("Loading...")
    result_vars["Weather"].set("Loading...")
    result_vars["ISP"].set("")
    
    # Also fill coordinate fields so user can see them
    lat_entry.insert(0, str(fav['lat']))
    lon_entry.insert(0, str(fav['lon']))
    
    # Load additional info in background
    root.after(100, lambda: load_favorite_extra_info(fav['lat'], fav['lon']))

def toggle_theme():
    """Toggle between light and dark theme"""
    global current_theme, BG_COLOR, CARD_BG, TEXT_COLOR, TEXT_SECONDARY
    
    if current_theme == "light":
        # Switch to dark theme
        current_theme = "dark"
        BG_COLOR = "#1E1E1E"
        CARD_BG = "#2D2D2D"
        TEXT_COLOR = "#FFFFFF"
        TEXT_SECONDARY = "#B0B0B0"
    else:
        # Switch to light theme
        current_theme = "light"
        BG_COLOR = "#F5F7FA"
        CARD_BG = "#FFFFFF"
        TEXT_COLOR = "#212121"
        TEXT_SECONDARY = "#757575"
    
    # Update all widgets
    root.configure(bg=BG_COLOR)
    main_frame.configure(bg=BG_COLOR)
    left_container.configure(bg=BG_COLOR)
    scroll_frame.configure(bg=BG_COLOR)
    left_canvas.configure(bg=BG_COLOR)
    left_scrollable_frame.configure(bg=BG_COLOR)
    right.configure(bg=BG_COLOR)
    title_lbl.configure(bg=BG_COLOR, fg=TEXT_COLOR)
    footer.configure(bg=BG_COLOR, fg=TEXT_SECONDARY)
    
    # Update all cards
    for widget in left_scrollable_frame.winfo_children():
        if isinstance(widget, tk.LabelFrame):
            widget.configure(bg=CARD_BG)
            for child in widget.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=CARD_BG, fg=TEXT_COLOR)
    
    info_card.configure(bg=CARD_BG)
    for child in info_card.winfo_children():
        if isinstance(child, tk.Label):
            child.configure(bg=CARD_BG, fg=TEXT_COLOR)
    
    messagebox.showinfo("Theme Changed", f"Switched to {current_theme.title()} theme!")

def on_create_table():
    """Create the locations table in PostGIS."""
    if not POSTGIS_AVAILABLE:
        messagebox.showerror("Not available", "psycopg2 not installed.")
        return
    
    if not POSTGIS_HOST or not POSTGIS_DB:
        messagebox.showerror("Not connected", "Please connect to PostGIS first.")
        return
    
    success, message = create_database_table()
    if success:
        messagebox.showinfo("Success", f"✅ {message}\n\nTable 'locations' is ready to store your searches automatically!")
    else:
        messagebox.showerror("Error", f"Failed to create table:\n{message}")

def on_postgis_query():
    """Query PostGIS for points within radius."""
    if not POSTGIS_AVAILABLE:
        messagebox.showerror("Not available", "psycopg2 not installed.")
        return
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    
    dialog = tk.Toplevel(root)
    dialog.title("PostGIS Spatial Query")
    dialog.geometry("300x150")
    tk.Label(dialog, text="Table name:").pack()
    table_entry = tk.Entry(dialog, width=25)
    table_entry.pack()
    tk.Label(dialog, text="Radius (meters):").pack()
    radius_entry = tk.Entry(dialog, width=25)
    radius_entry.insert(0, "1000")
    radius_entry.pack()
    
    def query():
        table = table_entry.get()
        radius = float(radius_entry.get())
        results = find_points_within_radius(table, float(lat), float(lon), radius)
        if results is not None:
            msg = f"Found {len(results)} points within {radius}m:\n\n"
            for r in results[:10]:  # Show first 10
                msg += f"{r.get('name', 'Unnamed')}: {r.get('distance', 0):.1f}m\n"
            if len(results) > 10:
                msg += f"\n... and {len(results)-10} more"
            messagebox.showinfo("Query Results", msg)
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Query failed.")
    
    tk.Button(dialog, text="Query", command=query).pack(pady=10)

def on_create_buffer():
    """Create buffer around current point with explanation and visualization."""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    
    dialog = tk.Toplevel(root)
    dialog.title("Create Buffer / Krijo Zonë Rrethore")
    dialog.geometry("450x320")
    
    # Explanation
    explanation = """
📍 What is a Buffer? / Çfarë është një Buffer?

A buffer creates a circular zone (polygon) around a point.
Një buffer krijon një zonë rrethore (poligon) rreth një pike.

🎯 Use cases / Përdorimet:
• Coverage areas (e.g., 500m radius around a store)
• Impact zones (e.g., noise pollution area)
• Service areas (e.g., delivery radius)
• GIS analysis (spatial queries, intersections)

The buffer will be exported as a GeoJSON polygon that you can:
• Import in QGIS, ArcGIS, or other GIS software
• Visualize on maps
• Use for spatial analysis
    """
    
    tk.Label(dialog, text=explanation, justify="left", font=("Segoe UI", 8), 
             wraplength=420, bg="#F0F0F0", padx=10, pady=10).pack(pady=10, padx=10, fill="both")
    
    # Input frame
    input_frame = tk.Frame(dialog)
    input_frame.pack(pady=10)
    
    tk.Label(input_frame, text="Center Point:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)
    tk.Label(input_frame, text=f"Lat: {lat}, Lon: {lon}", font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=2, sticky="w")
    tk.Label(input_frame, text=result_vars["Display Address"].get() or "Unknown", 
             font=("Segoe UI", 8), wraplength=350).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0,10))
    
    tk.Label(input_frame, text="Radius (meters):", font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", padx=5)
    radius_entry = tk.Entry(input_frame, width=15, font=("Segoe UI", 10))
    radius_entry.insert(0, "500")
    radius_entry.grid(row=3, column=1, padx=5)
    
    tk.Label(input_frame, text="Examples: 100m, 500m, 1000m, 5000m", 
             font=("Segoe UI", 7), fg="#666").grid(row=4, column=0, columnspan=2, pady=5)
    
    def create():
        try:
            radius = float(radius_entry.get())
            if radius <= 0:
                messagebox.showerror("Error", "Radius must be greater than 0")
                return
            
            buffer_geom = create_buffer(float(lat), float(lon), radius)
            if buffer_geom:
                # Export buffer as GeoJSON
                filename = filedialog.asksaveasfilename(
                    defaultextension=".geojson", 
                    filetypes=[("GeoJSON", "*.geojson"), ("JSON", "*.json")],
                    title="Save Buffer as GeoJSON"
                )
                if filename:
                    geojson = {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "geometry": buffer_geom,
                            "properties": {
                                "radius_meters": radius,
                                "center_lat": float(lat),
                                "center_lon": float(lon),
                                "location": result_vars["Display Address"].get() or "Unknown",
                                "created": datetime.now().isoformat()
                            }
                        }]
                    }
                    with open(filename, "w", encoding="utf8") as f:
                        json.dump(geojson, f, indent=2, ensure_ascii=False)
                    
                    msg = f"✅ Buffer created successfully!\n\n"
                    msg += f"📍 Center: {result_vars['Display Address'].get() or 'Unknown'}\n"
                    msg += f"📏 Radius: {radius} meters ({radius/1000:.2f} km)\n"
                    msg += f"💾 Saved to: {filename}\n\n"
                    msg += f"You can now:\n"
                    msg += f"• Import in QGIS/ArcGIS\n"
                    msg += f"• View on geojson.io\n"
                    msg += f"• Use for spatial analysis"
                    
                    messagebox.showinfo("Success", msg)
                    dialog.destroy()
            else:
                messagebox.showerror("Error", "Buffer creation failed.\n\nInstall required packages:\npip install shapely geopandas")
        except ValueError:
            messagebox.showerror("Error", "Invalid radius. Please enter a valid number.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
    
    tk.Button(dialog, text="Create Buffer / Krijo Buffer", bg="#4CAF50", fg="white", 
              command=create, font=("Segoe UI", 10)).pack(pady=10)

# -------------------------
# Build GUI
# -------------------------
root = tk.Tk()
root.title(APP_TITLE)
root.geometry("1400x950")  # Bigger window
root.configure(bg=BG_COLOR)

# Larger default font
default_font = ("Segoe UI", 10)
root.option_add("*Font", default_font)

history = []

# Title
title_lbl = tk.Label(root, text=APP_TITLE, font=("Segoe UI", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR)
title_lbl.pack(pady=(12,8))

main_frame = tk.Frame(root, bg=BG_COLOR)
main_frame.pack(fill="both", expand=True, padx=10, pady=6)

# Configure main_frame to use grid for better control
main_frame.grid_columnconfigure(0, weight=3)  # Left side gets 60% width
main_frame.grid_columnconfigure(1, weight=2)  # Right side gets 40% width

# Left: inputs and controls with scrollbar (both vertical and horizontal)
left_container = tk.Frame(main_frame, bg=BG_COLOR)
left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

# Create a frame for scrollbars and canvas
scroll_frame = tk.Frame(left_container, bg=BG_COLOR)
scroll_frame.pack(fill="both", expand=True)

# Krijon canvas për scroll (vertical dhe horizontal)
left_canvas = tk.Canvas(scroll_frame, bg=BG_COLOR, highlightthickness=0)
left_scrollbar_v = tk.Scrollbar(scroll_frame, orient="vertical", command=left_canvas.yview)
left_scrollbar_h = tk.Scrollbar(scroll_frame, orient="horizontal", command=left_canvas.xview)
left_scrollable_frame = tk.Frame(left_canvas, bg=BG_COLOR)

# Create window in canvas - store reference globally
canvas_window = left_canvas.create_window((0, 0), window=left_scrollable_frame, anchor="nw")
left_canvas.configure(yscrollcommand=left_scrollbar_v.set, xscrollcommand=left_scrollbar_h.set)

# Update canvas width, height dhe scroll region
def configure_scroll_region(event):
    # Update scroll region për të dy drejtimet
    bbox = left_canvas.bbox("all")
    if bbox:
        left_canvas.configure(scrollregion=bbox)
    # Update canvas window width - don't restrict height, let it grow
    canvas_width = left_canvas.winfo_width()
    if canvas_width > 1:  # Make sure width is valid
        left_canvas.itemconfig(canvas_window, width=canvas_width)

def configure_canvas(event):
    # Update canvas window width when canvas is resized
    canvas_width = event.width
    if canvas_width > 1:
        left_canvas.itemconfig(canvas_window, width=canvas_width)
    # Update scroll region
    bbox = left_canvas.bbox("all")
    if bbox:
        left_canvas.configure(scrollregion=bbox)

left_scrollable_frame.bind("<Configure>", configure_scroll_region)
left_canvas.bind("<Configure>", configure_canvas)

# Pack scrollbars dhe canvas - IMPORTANT: pack in correct order
left_canvas.grid(row=0, column=0, sticky="nsew")
left_scrollbar_v.grid(row=0, column=1, sticky="ns")
left_scrollbar_h.grid(row=1, column=0, sticky="ew")

# Configure grid weights
scroll_frame.grid_rowconfigure(0, weight=1)
scroll_frame.grid_columnconfigure(0, weight=1)

# Bind mousewheel për scroll vertical - Works on Windows
def on_mousewheel_vertical(event):
    # Check if mouse is over canvas or scrollable frame
    widget = event.widget
    if widget == left_canvas or widget == left_scrollable_frame or left_canvas.winfo_containing(event.x_root, event.y_root):
        # Windows uses delta, Linux uses num
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            left_canvas.yview_scroll(-1, "units")
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            left_canvas.yview_scroll(1, "units")
    return "break"

# Bind mousewheel + Shift për scroll horizontal
def on_mousewheel_horizontal(event):
    widget = event.widget
    if widget == left_canvas or widget == left_scrollable_frame or left_canvas.winfo_containing(event.x_root, event.y_root):
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            left_canvas.xview_scroll(-1, "units")
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            left_canvas.xview_scroll(1, "units")
    return "break"

# Bind mousewheel events - Windows and Linux compatible
left_canvas.bind("<MouseWheel>", on_mousewheel_vertical)
left_canvas.bind("<Button-4>", on_mousewheel_vertical)  # Linux
left_canvas.bind("<Button-5>", on_mousewheel_vertical)  # Linux
left_canvas.bind("<Shift-MouseWheel>", on_mousewheel_horizontal)
left_canvas.bind("<Shift-Button-4>", on_mousewheel_horizontal)  # Linux
left_canvas.bind("<Shift-Button-5>", on_mousewheel_horizontal)  # Linux
left_canvas.bind("<Control-MouseWheel>", on_mousewheel_horizontal)
left_canvas.bind("<Control-Button-4>", on_mousewheel_horizontal)  # Linux
left_canvas.bind("<Control-Button-5>", on_mousewheel_horizontal)  # Linux

# Also bind to the scrollable frame for better coverage
left_scrollable_frame.bind("<MouseWheel>", on_mousewheel_vertical)
left_scrollable_frame.bind("<Button-4>", on_mousewheel_vertical)
left_scrollable_frame.bind("<Button-5>", on_mousewheel_vertical)
left_scrollable_frame.bind("<Shift-MouseWheel>", on_mousewheel_horizontal)
left_scrollable_frame.bind("<Shift-Button-4>", on_mousewheel_horizontal)
left_scrollable_frame.bind("<Shift-Button-5>", on_mousewheel_horizontal)
left_scrollable_frame.bind("<Control-MouseWheel>", on_mousewheel_horizontal)
left_scrollable_frame.bind("<Control-Button-4>", on_mousewheel_horizontal)
left_scrollable_frame.bind("<Control-Button-5>", on_mousewheel_horizontal)

# Bind to all child widgets in the scrollable frame
def bind_mousewheel_to_children(parent):
    for child in parent.winfo_children():
        try:
            child.bind("<MouseWheel>", on_mousewheel_vertical)
            child.bind("<Button-4>", on_mousewheel_vertical)
            child.bind("<Button-5>", on_mousewheel_vertical)
            child.bind("<Shift-MouseWheel>", on_mousewheel_horizontal)
            child.bind("<Control-MouseWheel>", on_mousewheel_horizontal)
            bind_mousewheel_to_children(child)  # Recursive for nested widgets
        except:
            pass

left = left_scrollable_frame  # Përdor këtë frame për të gjitha widgets

addr_card = tk.LabelFrame(left, text="Address → Coordinates", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 11, "bold"))
addr_card.pack(fill="x", pady=6)
tk.Label(addr_card, text="Address:", bg=CARD_BG, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
address_entry = AutocompleteEntry(addr_card, autocomplete_function=get_address_suggestions, width=40, font=("Segoe UI", 11))
address_entry.grid(row=0, column=1, padx=6, pady=4)
tk.Button(addr_card, text="Find Coordinates", bg=PRIMARY_BLUE, fg="white", command=on_find_coordinates, font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=6)

coord_card = tk.LabelFrame(left, text="Coordinates → Address", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 11, "bold"))
coord_card.pack(fill="x", pady=6)
tk.Label(coord_card, text="Latitude:", bg=CARD_BG, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
lat_entry = tk.Entry(coord_card, width=25, font=("Segoe UI", 11))
lat_entry.grid(row=0, column=1, padx=6, pady=4)
tk.Label(coord_card, text="Longitude:", bg=CARD_BG, font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w")
lon_entry = tk.Entry(coord_card, width=25, font=("Segoe UI", 11))
lon_entry.grid(row=1, column=1, padx=6, pady=4)
tk.Button(coord_card, text="Find Address", bg=PRIMARY_BLUE, fg="white", command=on_find_address, font=("Segoe UI", 10, "bold")).grid(row=0, column=2, rowspan=2, padx=6)

ip_card = tk.LabelFrame(left, text="IP → Location", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 11, "bold"))
ip_card.pack(fill="x", pady=6)
tk.Label(ip_card, text="IP Address:", bg=CARD_BG, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
ip_entry = tk.Entry(ip_card, width=35, font=("Segoe UI", 11))
ip_entry.grid(row=0, column=1, padx=6, pady=4)
tk.Button(ip_card, text="Locate IP", bg=PRIMARY_BLUE, fg="white", command=on_find_ip, font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=6)

# Favorites & Quick Access
favorites_card = tk.LabelFrame(left, text="⭐ Favorites & Quick Access", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
favorites_card.pack(fill="x", pady=6)
tk.Button(favorites_card, text="Add to Favorites", bg="#FFD700", fg="black", command=on_add_to_favorites, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
tk.Button(favorites_card, text="Load Favorite", bg="#FFA500", fg="white", command=on_load_favorite, font=("Segoe UI", 9)).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
tk.Button(favorites_card, text="📊 Statistics", bg="#9C27B0", fg="white", command=on_show_statistics, font=("Segoe UI", 9)).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
tk.Button(favorites_card, text="🎨 Theme", bg="#607D8B", fg="white", command=toggle_theme, font=("Segoe UI", 9)).grid(row=1, column=0, columnspan=3, padx=4, pady=4, sticky="ew")
favorites_card.grid_columnconfigure(0, weight=1)
favorites_card.grid_columnconfigure(1, weight=1)
favorites_card.grid_columnconfigure(2, weight=1)

batch_card = tk.LabelFrame(left, text="Batch / Export / Import", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
batch_card.pack(fill="x", pady=6)
tk.Button(batch_card, text="Batch Geocode CSV", bg=PRIMARY_BLUE, fg="white", command=batch_geocode_from_csv).grid(row=0, column=0, padx=4, pady=4)
tk.Button(batch_card, text="Export Current → CSV", bg=DARK_BLUE, fg="white", command=export_current_to_csv).grid(row=0, column=1, padx=4, pady=4)
tk.Button(batch_card, text="Import Random Address", bg=SECONDARY_BLUE, fg="white", command=import_single_address_from_csv).grid(row=0, column=2, padx=4, pady=4)

maps_card = tk.LabelFrame(left, text="Maps", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 11, "bold"))
maps_card.pack(fill="x", pady=6)
tk.Button(maps_card, text="Open Map (Browser)", bg=DARK_BLUE, fg="white", command=lambda: open_map_in_browser(False), font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
tk.Button(maps_card, text="Open Satellite (Browser)", bg=PRIMARY_BLUE, fg="white", command=lambda: open_map_in_browser(True), font=("Segoe UI", 10)).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
tk.Button(maps_card, text="Distances to 15 Cities", bg=SUCCESS_GREEN, fg="white", command=open_map_with_distances, font=("Segoe UI", 10)).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
tk.Button(maps_card, text="🔍 Search & Add Cities", bg=WARNING_ORANGE, fg="white", command=open_searchable_distance_map, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, columnspan=3, padx=4, pady=4, sticky="ew")
maps_card.grid_columnconfigure(0, weight=1)
maps_card.grid_columnconfigure(1, weight=1)
maps_card.grid_columnconfigure(2, weight=1)

# GIS Features (Gjeoreferencimi & Spatial Analysis)
gis_card = tk.LabelFrame(left, text="GIS / Gjeoreferencimi", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
gis_card.pack(fill="x", pady=6)
tk.Button(gis_card, text="Transform to UTM", bg=SUCCESS_GREEN, fg="white", command=on_transform_coordinates).grid(row=0, column=0, padx=4, pady=3)
tk.Button(gis_card, text="Calculate Distance", bg=SUCCESS_GREEN, fg="white", command=on_calculate_distance).grid(row=0, column=1, padx=4, pady=3)
tk.Button(gis_card, text="Create Buffer", bg=SUCCESS_GREEN, fg="white", command=on_create_buffer).grid(row=0, column=2, padx=4, pady=3)
tk.Button(gis_card, text="Store Point", bg=SUCCESS_GREEN, fg="white", command=on_store_point).grid(row=1, column=0, columnspan=3, padx=4, pady=3, sticky="ew")

# GNSS Features (GPX Support)
gnss_card = tk.LabelFrame(left, text="GNSS / GPX", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
gnss_card.pack(fill="x", pady=6)
tk.Button(gnss_card, text="Import GPX", bg=WARNING_ORANGE, fg="white", command=on_import_gpx).grid(row=0, column=0, padx=4, pady=3, sticky="ew")
tk.Button(gnss_card, text="Export GPX", bg=WARNING_ORANGE, fg="white", command=on_export_gpx).grid(row=0, column=1, padx=4, pady=3, sticky="ew")
gnss_card.grid_columnconfigure(0, weight=1)
gnss_card.grid_columnconfigure(1, weight=1)

# GeoJSON Import/Export
geojson_card = tk.LabelFrame(left, text="GeoJSON", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 11, "bold"))
geojson_card.pack(fill="x", pady=6)
tk.Button(geojson_card, text="Import GeoJSON", bg="#9C27B0", fg="white", command=on_import_geojson, font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, pady=3, sticky="ew")
tk.Button(geojson_card, text="Export GeoJSON", bg="#9C27B0", fg="white", command=on_export_geojson, font=("Segoe UI", 10)).grid(row=0, column=1, padx=4, pady=3, sticky="ew")
geojson_card.grid_columnconfigure(0, weight=1)
geojson_card.grid_columnconfigure(1, weight=1)

# PostGIS section removed - SQLite is used automatically instead

# History
hist_card = tk.LabelFrame(left, text="Search History", bg=CARD_BG, padx=6, pady=6, font=("Segoe UI", 10))
hist_card.pack(fill="both", pady=6, expand=False)
history_listbox = tk.Listbox(hist_card, height=8, width=50)
history_listbox.pack(side="left", fill="both", expand=True)
hist_scroll = tk.Scrollbar(hist_card, command=history_listbox.yview)
hist_scroll.pack(side="right", fill="y")
history_listbox.config(yscrollcommand=hist_scroll.set)

# Right: results
right = tk.Frame(main_frame, bg=BG_COLOR)
right.grid(row=0, column=1, sticky="nsew", padx=(15, 0))

# Result variables
result_vars = {
    "Latitude": tk.StringVar(),
    "Longitude": tk.StringVar(),
    "Display Address": tk.StringVar(),
    "Country": tk.StringVar(),
    "Region": tk.StringVar(),
    "City": tk.StringVar(),
    "Postal Code": tk.StringVar(),
    "Timezone": tk.StringVar(),
    "Weather": tk.StringVar(),
    "ISP": tk.StringVar(),
    "Bounding Box": tk.StringVar(),
    "Altitude": tk.StringVar(),
}

info_card = tk.LabelFrame(right, text="Location Info (Result)", bg=CARD_BG, padx=12, pady=10, font=("Segoe UI", 12, "bold"))
info_card.pack(fill="both", expand=True, pady=6)

row = 0
for label_text, var_key in [
    ("Latitude:", "Latitude"),
    ("Longitude:", "Longitude"),
    ("Altitude:", "Altitude"),
    ("Display Address:", "Display Address"),
    ("Country:", "Country"),
    ("Region/State:", "Region"),
    ("City:", "City"),
    ("Postal Code:", "Postal Code"),
    ("Timezone:", "Timezone"),
    ("Weather:", "Weather"),
    ("ISP / Org:", "ISP"),
    ("Bounding Box:", "Bounding Box"),
]:
    lbl = tk.Label(info_card, text=label_text, anchor="w", bg=CARD_BG, width=14, font=("Segoe UI", 10, "bold"))
    lbl.grid(row=row, column=0, sticky="w", padx=(2,6), pady=5)
    ent = tk.Entry(info_card, textvariable=result_vars[var_key], width=50, font=("Segoe UI", 11))
    ent.grid(row=row, column=1, sticky="w", padx=(2,8), pady=5)
    row += 1

controls = tk.Frame(right, bg=BG_COLOR)
controls.pack(fill="x", pady=8)
tk.Button(controls, text="📊 Show Overview", bg=SUCCESS_GREEN, fg="white", command=show_location_details, font=("Segoe UI", 10, "bold")).pack(side="left", padx=8)
tk.Button(controls, text="Copy Coordinates", bg=PRIMARY_BLUE, fg="white",
          command=lambda: root.clipboard_append(f"{result_vars['Latitude'].get()},{result_vars['Longitude'].get()}"), font=("Segoe UI", 10)).pack(side="right", padx=8)
tk.Button(controls, text="Clear Results", bg="#9E9E9E", fg="white", command=clear_results, font=("Segoe UI", 10)).pack(side="right", padx=8)

footer_text = "✨ Veçori të Avancuara: GIS (GeoJSON, buffers, distanca), GNSS (GPX import/export), Gjeoreferencimi (transformime UTM/CRS), PostGIS (databaza hapësinore). "
footer_text += "Paketa opsionale: geopandas, shapely, pyproj, gpxpy, psycopg2-binary | "
footer_text += "Scroll: Mousewheel (lart-poshtë), Shift+Mousewheel ose Ctrl+Mousewheel (majtas-djathtas), ose përdor scrollbars."
footer = tk.Label(root, text=footer_text, bg=BG_COLOR, fg="#555555", font=("Segoe UI", 8), wraplength=1000, justify="left")
footer.pack(side="bottom", pady=6)

# Force update scroll region after everything is created
def update_scroll_region():
    try:
        left_canvas.update_idletasks()
        # Force update of scroll region
        bbox = left_canvas.bbox("all")
        if bbox:
            # Expand bbox slightly to ensure everything is scrollable
            left_canvas.configure(scrollregion=(0, 0, max(bbox[2], left_canvas.winfo_width()), max(bbox[3], left_canvas.winfo_height())))
        # Ensure canvas window width is correct
        canvas_width = left_canvas.winfo_width()
        if canvas_width > 1:
            left_canvas.itemconfig(canvas_window, width=canvas_width)
        # Scroll to top-left to ensure first card is visible
        left_canvas.yview_moveto(0)
        left_canvas.xview_moveto(0)
        # Force scrollbars to update
        left_canvas.update_idletasks()
    except Exception as e:
        print(f"Update scroll region error: {e}")  # Debug

# Multiple updates to ensure it works
def finalize_scrolling():
    update_scroll_region()
    # Bind mousewheel to all widgets after they're created
    bind_mousewheel_to_children(left_scrollable_frame)

root.after(50, finalize_scrolling)
root.after(200, finalize_scrolling)
root.after(500, finalize_scrolling)
root.after(1000, finalize_scrolling)  # Final check

# Initialize SQLite database (automatic, no setup needed!)
init_sqlite_db()
load_favorites()

root.mainloop()
