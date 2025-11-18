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

# -------------------------
# Configuration
# -------------------------
APP_TITLE = "GeoLocator - Advanced GIS/GNSS/PostGIS"
BG_COLOR = "white"
CARD_BG = "#FAFBFD"
PRIMARY_BLUE = "#1E88E5"
DARK_BLUE = "#0D47A1"
TEXT_COLOR = "#222222"

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

# Store multiple points for GIS operations
stored_points = []

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
        INSERT INTO {table_name} (name, description, geom)
        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
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

# -------------------------
# GUI functions: Fill results
# -------------------------
def clear_results():
    for k in result_vars:
        result_vars[k].set("")
    history_listbox.delete(0, tk.END)

def add_to_history(entry):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history.append((timestamp, entry))
    history_listbox.insert(0, f"{timestamp} — {entry}")

def fill_result_panel(data_dict):
    """data_dict keys should map to our result_vars keys"""
    for key, val in data_dict.items():
        if key in result_vars:
            result_vars[key].set("" if val is None else str(val))

# -------------------------
# Address -> Coordinates
# -------------------------
def on_find_coordinates():
    address = address_entry.get().strip()
    if not address:
        messagebox.showerror("Input required", "Please enter an address.")
        return
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
        elevation = get_elevation(data["latitude"], data["longitude"])
        out = {
            "Latitude": data["latitude"],
            "Longitude": data["longitude"],
            "Altitude": f"{elevation} m" if elevation is not None else "N/A",
            "Display Address": data["display_name"],
            "Country": data["country"] or "",
            "Region": data["state"] or "",
            "City": data["city"] or "",
            "Postal Code": data["postcode"] or "",
            "Timezone": "",  # timezone from lat/lon can be fetched via timezone API if needed
            "ISP": "",
            "AS": "",
            "Bounding Box": ", ".join(data["boundingbox"]) if data["boundingbox"] else ""
        }
        fill_result_panel(out)
        add_to_history(f"Address -> {address}")
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
    try:
        location = geolocator.reverse(f"{lat}, {lon}", addressdetails=True, exactly_one=True, timeout=10)
        if not location:
            messagebox.showinfo("Not found", "No address found at these coordinates.")
            return
        data = extract_address_fields(location)
        elevation = get_elevation(lat, lon)
        out = {
            "Latitude": data["latitude"],
            "Longitude": data["longitude"],
            "Altitude": f"{elevation} m" if elevation is not None else "N/A",
            "Display Address": data["display_name"],
            "Country": data["country"] or "",
            "Region": data["state"] or "",
            "City": data["city"] or "",
            "Postal Code": data["postcode"] or "",
            "Timezone": "",
            "ISP": "",
            "AS": "",
            "Bounding Box": ", ".join(data["boundingbox"]) if data["boundingbox"] else ""
        }
        fill_result_panel(out)
        add_to_history(f"Coords -> {lat},{lon}")
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
            "AS": data.get("as") or "",
            "Bounding Box": ""
        }
        fill_result_panel(out)
        add_to_history(f"IP -> {ip}")
    except Exception as e:
        messagebox.showerror("Error", f"IP lookup failed: {e}")

# -------------------------
# Map generation (Folium)
# -------------------------
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
    m = folium.Map(location=[latf, lonf], zoom_start=18, tiles=None)  # Zoom më i lartë për saktësi
    
    # Shto layer-e të ndryshme
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='Harta Standard',
        attr='OpenStreetMap contributors'
    ).add_to(m)
    
    if satellite:
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Imazh Satelitor',
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
    
    # Shto kontrollin e layer-ave
    folium.LayerControl().add_to(m)
    
    # Shto një mini-map në qoshe (nëse është e disponueshme)
    try:
        from folium.plugins import MiniMap
        minimap = MiniMap(toggle_display=True)
        m.add_child(minimap)
    except:
        pass  # MiniMap nuk është kritike
    
    # Shto fullscreen button (nëse është e disponueshme)
    try:
        from folium.plugins import Fullscreen
        Fullscreen().add_to(m)
    except:
        pass  # Fullscreen nuk është kritike
    
    # Ruaj dhe hap
    outpath = os.path.join(os.getcwd(), "geolocator_map.html")
    m.save(outpath)
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
        
        progress_label.config(text=f"Duke procesuar {idx}/{total}...")
        progress_bar['value'] = idx
        progress_window.update()
    
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
    """Calculate distance between two points."""
    lat1 = result_vars["Latitude"].get()
    lon1 = result_vars["Longitude"].get()
    if not lat1 or not lon1:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    
    # Open dialog for second point
    dialog = tk.Toplevel(root)
    dialog.title("Calculate Distance")
    dialog.geometry("300x150")
    tk.Label(dialog, text="Point 2 Coordinates:").pack(pady=5)
    tk.Label(dialog, text="Latitude:").pack()
    lat2_entry = tk.Entry(dialog, width=20)
    lat2_entry.pack()
    tk.Label(dialog, text="Longitude:").pack()
    lon2_entry = tk.Entry(dialog, width=20)
    lon2_entry.pack()
    
    def calc():
        try:
            lat2 = float(lat2_entry.get())
            lon2 = float(lon2_entry.get())
            dist = calculate_distance(float(lat1), float(lon1), lat2, lon2)
            bearing = calculate_bearing(float(lat1), float(lon1), lat2, lon2)
            msg = f"Distance: {dist:.2f} meters ({dist/1000:.2f} km)\nBearing: {bearing:.1f}°"
            messagebox.showinfo("Distance Calculation", msg)
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {e}")
    
    tk.Button(dialog, text="Calculate", command=calc).pack(pady=10)

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
    """Configure PostGIS connection."""
    dialog = tk.Toplevel(root)
    dialog.title("PostGIS Connection")
    dialog.geometry("350x250")
    
    tk.Label(dialog, text="PostGIS Database Connection", font=("Segoe UI", 10, "bold")).pack(pady=5)
    
    fields = [
        ("Host:", "host"),
        ("Port:", "port"),
        ("Database:", "db"),
        ("User:", "user"),
        ("Password:", "password")
    ]
    entries = {}
    for i, (label, key) in enumerate(fields):
        tk.Label(dialog, text=label).pack()
        entry = tk.Entry(dialog, width=30, show="*" if key == "password" else "")
        entry.pack(pady=2)
        entries[key] = entry
    
    def save_conn():
        global POSTGIS_HOST, POSTGIS_PORT, POSTGIS_DB, POSTGIS_USER, POSTGIS_PASSWORD
        POSTGIS_HOST = entries["host"].get()
        POSTGIS_PORT = entries["port"].get() or "5432"
        POSTGIS_DB = entries["db"].get()
        POSTGIS_USER = entries["user"].get()
        POSTGIS_PASSWORD = entries["password"].get()
        if connect_postgis():
            messagebox.showinfo("Connected", "PostGIS connection successful!")
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Connection failed. Check credentials and ensure PostGIS is installed.")
    
    tk.Button(dialog, text="Connect", command=save_conn).pack(pady=10)

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
    """Create buffer around current point."""
    lat = result_vars["Latitude"].get()
    lon = result_vars["Longitude"].get()
    if not lat or not lon:
        messagebox.showerror("No coordinates", "No coordinates available.")
        return
    
    dialog = tk.Toplevel(root)
    dialog.title("Create Buffer")
    dialog.geometry("250x100")
    tk.Label(dialog, text="Radius (meters):").pack()
    radius_entry = tk.Entry(dialog, width=20)
    radius_entry.insert(0, "100")
    radius_entry.pack()
    
    def create():
        try:
            radius = float(radius_entry.get())
            buffer_geom = create_buffer(float(lat), float(lon), radius)
            if buffer_geom:
                # Export buffer as GeoJSON
                filename = filedialog.asksaveasfilename(defaultextension=".geojson", filetypes=[("GeoJSON", "*.geojson")])
                if filename:
                    geojson = {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "geometry": buffer_geom,
                            "properties": {"radius_meters": radius}
                        }]
                    }
                    with open(filename, "w", encoding="utf8") as f:
                        json.dump(geojson, f, indent=2)
                    messagebox.showinfo("Success", f"Buffer saved to {filename}")
            else:
                messagebox.showerror("Error", "Buffer creation failed. Install: pip install shapely geopandas")
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
    
    tk.Button(dialog, text="Create", command=create).pack(pady=10)

# -------------------------
# Build GUI
# -------------------------
root = tk.Tk()
root.title(APP_TITLE)
root.geometry("1100x900")  # Increased size for new features
root.configure(bg=BG_COLOR)

history = []

# Title
title_lbl = tk.Label(root, text=APP_TITLE, font=("Segoe UI", 18, "bold"), bg=BG_COLOR, fg=TEXT_COLOR)
title_lbl.pack(pady=(10,6))

main_frame = tk.Frame(root, bg=BG_COLOR)
main_frame.pack(fill="both", expand=True, padx=10, pady=6)

# Left: inputs and controls with scrollbar (both vertical and horizontal)
left_container = tk.Frame(main_frame, bg=BG_COLOR)
left_container.pack(side="left", fill="both", padx=(0,12))

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

addr_card = tk.LabelFrame(left, text="Address → Coordinates", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
addr_card.pack(fill="x", pady=6)
tk.Label(addr_card, text="Address:", bg=CARD_BG).grid(row=0, column=0, sticky="w")
address_entry = tk.Entry(addr_card, width=35, font=("Segoe UI", 10))  # Reduced width to fit
address_entry.grid(row=0, column=1, padx=6, pady=4)
tk.Button(addr_card, text="Find Coordinates", bg=PRIMARY_BLUE, fg="white", command=on_find_coordinates).grid(row=0, column=2, padx=6)

coord_card = tk.LabelFrame(left, text="Coordinates → Address", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
coord_card.pack(fill="x", pady=6)
tk.Label(coord_card, text="Latitude:", bg=CARD_BG).grid(row=0, column=0, sticky="w")
lat_entry = tk.Entry(coord_card, width=22, font=("Segoe UI", 10))
lat_entry.grid(row=0, column=1, padx=6, pady=4)
tk.Label(coord_card, text="Longitude:", bg=CARD_BG).grid(row=1, column=0, sticky="w")
lon_entry = tk.Entry(coord_card, width=22, font=("Segoe UI", 10))
lon_entry.grid(row=1, column=1, padx=6, pady=4)
tk.Button(coord_card, text="Find Address", bg=PRIMARY_BLUE, fg="white", command=on_find_address).grid(row=0, column=2, rowspan=2, padx=6)

ip_card = tk.LabelFrame(left, text="IP → Location", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
ip_card.pack(fill="x", pady=6)
tk.Label(ip_card, text="IP Address:", bg=CARD_BG).grid(row=0, column=0, sticky="w")
ip_entry = tk.Entry(ip_card, width=30, font=("Segoe UI", 10))
ip_entry.grid(row=0, column=1, padx=6, pady=4)
tk.Button(ip_card, text="Locate IP", bg=PRIMARY_BLUE, fg="white", command=on_find_ip).grid(row=0, column=2, padx=6)

batch_card = tk.LabelFrame(left, text="Batch / Export", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
batch_card.pack(fill="x", pady=6)
tk.Button(batch_card, text="Batch Geocode CSV", bg=PRIMARY_BLUE, fg="white", command=batch_geocode_from_csv).grid(row=0, column=0, padx=6, pady=4)
tk.Button(batch_card, text="Export Current → CSV", bg=DARK_BLUE, fg="white", command=export_current_to_csv).grid(row=0, column=1, padx=6, pady=4)

maps_card = tk.LabelFrame(left, text="Maps", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
maps_card.pack(fill="x", pady=6)
tk.Button(maps_card, text="Open Map (Browser)", bg=DARK_BLUE, fg="white", command=lambda: open_map_in_browser(False)).grid(row=0, column=0, padx=6, pady=4)
tk.Button(maps_card, text="Open Satellite (Browser)", bg=PRIMARY_BLUE, fg="white", command=lambda: open_map_in_browser(True)).grid(row=0, column=1, padx=6, pady=4)
tk.Button(maps_card, text="Embed Map (Optional)", bg=PRIMARY_BLUE, fg="white", command=embed_map_inside_app).grid(row=0, column=2, padx=6, pady=4)

# GIS Features (Gjeoreferencimi & Spatial Analysis)
gis_card = tk.LabelFrame(left, text="GIS / Gjeoreferencimi", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
gis_card.pack(fill="x", pady=6)
tk.Button(gis_card, text="Transform to UTM", bg="#4CAF50", fg="white", command=on_transform_coordinates).grid(row=0, column=0, padx=4, pady=3)
tk.Button(gis_card, text="Calculate Distance", bg="#4CAF50", fg="white", command=on_calculate_distance).grid(row=0, column=1, padx=4, pady=3)
tk.Button(gis_card, text="Create Buffer", bg="#4CAF50", fg="white", command=on_create_buffer).grid(row=0, column=2, padx=4, pady=3)
tk.Button(gis_card, text="Store Point", bg="#8BC34A", fg="white", command=on_store_point).grid(row=1, column=0, padx=4, pady=3)

# GNSS Features (GPX Support)
gnss_card = tk.LabelFrame(left, text="GNSS / GPX", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
gnss_card.pack(fill="x", pady=6)
tk.Button(gnss_card, text="Import GPX", bg="#FF9800", fg="white", command=on_import_gpx).grid(row=0, column=0, padx=4, pady=3)
tk.Button(gnss_card, text="Export GPX", bg="#FF9800", fg="white", command=on_export_gpx).grid(row=0, column=1, padx=4, pady=3)

# GeoJSON Import/Export
geojson_card = tk.LabelFrame(left, text="GeoJSON", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
geojson_card.pack(fill="x", pady=6)
tk.Button(geojson_card, text="Import GeoJSON", bg="#9C27B0", fg="white", command=on_import_geojson).grid(row=0, column=0, padx=4, pady=3)
tk.Button(geojson_card, text="Export GeoJSON", bg="#9C27B0", fg="white", command=on_export_geojson).grid(row=0, column=1, padx=4, pady=3)

# PostGIS / Spatial Database
postgis_card = tk.LabelFrame(left, text="PostGIS / Databazat Gjeohapsinore", bg=CARD_BG, padx=8, pady=8, font=("Segoe UI", 10))
postgis_card.pack(fill="x", pady=6)
tk.Button(postgis_card, text="Connect PostGIS", bg="#F44336", fg="white", command=on_postgis_connect).grid(row=0, column=0, padx=4, pady=3)
tk.Button(postgis_card, text="Insert Point", bg="#F44336", fg="white", command=on_postgis_insert).grid(row=0, column=1, padx=4, pady=3)
tk.Button(postgis_card, text="Spatial Query", bg="#F44336", fg="white", command=on_postgis_query).grid(row=0, column=2, padx=4, pady=3)

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
right.pack(side="left", fill="both", expand=True)

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
    "ISP": tk.StringVar(),
    "AS": tk.StringVar(),
    "Bounding Box": tk.StringVar(),
    "Altitude": tk.StringVar(),
}

info_card = tk.LabelFrame(right, text="Location Info (Result)", bg=CARD_BG, padx=12, pady=10, font=("Segoe UI", 11))
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
    ("ISP / Org:", "ISP"),
    ("AS:", "AS"),
    ("Bounding Box:", "Bounding Box"),
]:
    lbl = tk.Label(info_card, text=label_text, anchor="w", bg=CARD_BG, width=14)
    lbl.grid(row=row, column=0, sticky="w", padx=(2,6), pady=4)
    ent = tk.Entry(info_card, textvariable=result_vars[var_key], width=60, font=("Segoe UI", 10))
    ent.grid(row=row, column=1, sticky="w", padx=(2,8), pady=4)
    row += 1

controls = tk.Frame(right, bg=BG_COLOR)
controls.pack(fill="x", pady=8)
tk.Button(controls, text="Clear Results", bg="#9E9E9E", fg="white", command=clear_results).pack(side="right", padx=8)
tk.Button(controls, text="Copy Coordinates", bg=PRIMARY_BLUE, fg="white",
          command=lambda: root.clipboard_append(f"{result_vars['Latitude'].get()},{result_vars['Longitude'].get()}")).pack(side="right", padx=8)

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

root.mainloop()
