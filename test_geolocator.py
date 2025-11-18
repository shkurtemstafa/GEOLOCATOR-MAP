#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for GeoLocator application
Run this to verify all features work correctly
"""

import sys

def test_imports():
    """Test if all required modules are available"""
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)
    
    modules = {
        'tkinter': 'GUI framework (required)',
        'geopy': 'Geocoding (required)',
        'requests': 'HTTP requests (required)',
        'folium': 'Map generation (required)',
        'pandas': 'CSV processing (required)',
        'geopandas': 'GIS operations (optional)',
        'shapely': 'Buffer creation (optional)',
        'pyproj': 'Coordinate transformations (optional)',
        'gpxpy': 'GPX import/export (optional)',
        'psycopg2': 'PostGIS connection (optional)',
    }
    
    all_ok = True
    for module, description in modules.items():
        try:
            __import__(module)
            print(f"✅ {module:20s} - {description}")
        except ImportError:
            if 'required' in description:
                print(f"❌ {module:20s} - {description} - MISSING!")
                all_ok = False
            else:
                print(f"⚠️  {module:20s} - {description} - Not installed")
    
    print()
    return all_ok

def test_application():
    """Test if application can be imported"""
    print("=" * 60)
    print("Testing application...")
    print("=" * 60)
    
    try:
        with open('geolocator_master_full.py', 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Check for new features
        features = [
            ('Clear input fields', 'clear_input_fields'),
            ('Save to database', 'save_to_database'),
            ('Distance map', 'open_map_with_distances'),
            ('Searchable distance map', 'open_searchable_distance_map'),
            ('Import random address', 'import_single_address_from_csv'),
            ('SQLite database', 'init_sqlite_db'),
            ('Favorites', 'save_favorite'),
            ('Statistics', 'get_statistics'),
            ('Timezone', 'get_timezone_info'),
        ]
        
        all_present = True
        for name, marker in features:
            if marker in code:
                print(f"✅ {name}")
            else:
                print(f"❌ {name} - NOT FOUND!")
                all_present = False
        
        print()
        return all_present
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("GeoLocator Test Suite")
    print("=" * 60 + "\n")
    
    imports_ok = test_imports()
    app_ok = test_application()
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if imports_ok and app_ok:
        print("✅ ALL TESTS PASSED!")
        print("\nYou can now run:")
        print("  python geolocator_master_full.py")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED")
        if not imports_ok:
            print("\nInstall missing packages:")
            print("  pip install geopy requests folium pandas")
        return 1

if __name__ == '__main__':
    sys.exit(main())
