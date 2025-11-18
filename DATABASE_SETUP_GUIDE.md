# 💾 Database Setup Guide - Step by Step

## 📋 What You Need:

1. **PostgreSQL** installed on your computer
2. **PostGIS extension** installed
3. **psycopg2** Python package: `pip install psycopg2-binary`

---

## 🚀 Step-by-Step Setup:

### Step 1: Install PostgreSQL

**Windows:**
1. Download from: https://www.postgresql.org/download/windows/
2. Run installer
3. Remember your password!
4. Default port: 5432

**Mac:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Step 2: Install PostGIS Extension

**Windows:**
- PostGIS is included in PostgreSQL installer (check "PostGIS" during installation)

**Mac:**
```bash
brew install postgis
```

**Linux:**
```bash
sudo apt-get install postgis postgresql-14-postgis-3
```

### Step 3: Create Database

Open terminal/command prompt:

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE geolocator;

# Connect to database
\c geolocator

# Enable PostGIS extension
CREATE EXTENSION postgis;

# Verify PostGIS is installed
SELECT PostGIS_Version();

# Exit
\q
```

---

## 🔌 Connect from GeoLocator App:

### Step 1: Open Application
```bash
python geolocator_master_full.py
```

### Step 2: Click "Connect PostGIS"

### Step 3: Enter Connection Details:
```
Host: localhost
Port: 5432
Database: geolocator
User: postgres
Password: [your password]
```

### Step 4: Click "Test Connection"
- Should show: ✅ Connection successful!
- Shows PostGIS version

### Step 5: Click "Create Table"
- Creates `locations` table automatically
- Table structure:
  - id (auto-increment)
  - name (location name)
  - search_type (address_search, coords_search, ip_search)
  - latitude
  - longitude
  - geom (PostGIS geometry)
  - search_date (timestamp)

### Step 6: Done!
- All your searches now save automatically!
- No need to do anything else

---

## 🎯 What Gets Saved Automatically:

Every time you search:
- **Address → Coordinates**: Saves with type "address_search"
- **Coordinates → Address**: Saves with type "coords_search"
- **IP → Location**: Saves with type "ip_search"

---

## 📊 View Your Data:

### Option 1: Using psql
```bash
psql -U postgres -d geolocator

SELECT * FROM locations ORDER BY search_date DESC LIMIT 10;
```

### Option 2: Using pgAdmin
1. Open pgAdmin (comes with PostgreSQL)
2. Connect to server
3. Navigate to: Servers → PostgreSQL → Databases → geolocator → Schemas → public → Tables → locations
4. Right-click → View/Edit Data → All Rows

### Option 3: Using GeoLocator App
1. Click "Spatial Query"
2. Enter table name: locations
3. Enter radius: 1000000 (1000 km)
4. See all nearby locations

---

## 🔍 Useful SQL Queries:

### Count total searches:
```sql
SELECT COUNT(*) FROM locations;
```

### Count by search type:
```sql
SELECT search_type, COUNT(*) 
FROM locations 
GROUP BY search_type;
```

### Recent searches:
```sql
SELECT name, search_type, search_date 
FROM locations 
ORDER BY search_date DESC 
LIMIT 10;
```

### Find locations near a point:
```sql
SELECT name, 
       ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(21.1655, 42.6629), 4326)::geography) as distance_meters
FROM locations
WHERE ST_DWithin(
    geom::geography,
    ST_SetSRID(ST_MakePoint(21.1655, 42.6629), 4326)::geography,
    100000
)
ORDER BY distance_meters;
```

---

## ⚠️ Troubleshooting:

### Problem: "Connection failed"
**Solutions:**
1. Check PostgreSQL is running:
   - Windows: Services → PostgreSQL
   - Mac/Linux: `brew services list` or `systemctl status postgresql`
2. Check password is correct
3. Check port is 5432 (default)

### Problem: "PostGIS extension not found"
**Solution:**
```sql
-- Connect to your database
psql -U postgres -d geolocator

-- Install extension
CREATE EXTENSION postgis;
```

### Problem: "Table doesn't exist"
**Solution:**
- Click "Create Table" button in app
- Or run manually:
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500),
    search_type VARCHAR(50),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    search_date TIMESTAMP DEFAULT NOW()
);

CREATE INDEX locations_geom_idx ON locations USING GIST (geom);
```

### Problem: "psycopg2 not installed"
**Solution:**
```bash
pip install psycopg2-binary
```

---

## 🎉 Benefits of Using Database:

1. **History**: Keep track of all your searches
2. **Analysis**: Analyze search patterns
3. **Spatial Queries**: Find locations within radius
4. **Backup**: Your data is saved permanently
5. **Export**: Export to CSV, GeoJSON, etc.

---

## 💡 Tips:

- Database connection is optional - app works without it
- Searches save silently in background
- No performance impact
- Can disable by disconnecting
- Data persists even if you close the app

---

**That's it! Your database is ready to use! 🎉**
