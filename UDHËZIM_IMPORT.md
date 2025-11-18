# 📥 Udhëzim i Detajuar Hap pas Hapi për Import/Export

## 📋 Përmbajtja:
1. [Import/Export GeoJSON](#1-importexport-geojson)
2. [Import/Export GPX](#2-importexport-gpx)
3. [Batch Geocode CSV](#3-batch-geocode-csv)
4. [Export Current to CSV](#4-export-current-to-csv)

---

## 1. Import/Export GeoJSON

### 🎯 Export GeoJSON (Eksporto pika në GeoJSON)

#### Hapi 1: Ruaj pika në aplikacion
1. **Kërko një lokacion** (p.sh. "Tirana, Albania")
   - Shkruaj në fushën "Address"
   - Kliko "Find Coordinates"
   - Shiko rezultatet në panelin e djathtë

2. **Ruaj pikën:**
   - Kliko butonin **"Store Point"** (në seksionin "GIS / Gjeoreferencimi")
   - Do të shfaqet mesazh: "Point stored. Total: 1"

3. **Përsërit për më shumë pika:**
   - Kërko një lokacion tjetër (p.sh. "Prishtina, Kosovo")
   - Kliko "Find Coordinates"
   - Kliko "Store Point" përsëri
   - Do të shfaqet: "Point stored. Total: 2"

#### Hapi 2: Eksporto pikat në GeoJSON
1. **Kliko butonin "Export GeoJSON"** (në seksionin "GeoJSON")
2. **Në dialog që hapet:**
   - Shkruaj emrin e skedarit (p.sh. "pikat_e_mija.geojson")
   - Zgjidh ku të ruhet (p.sh. Desktop ose Downloads)
   - Kliko "Save"
3. **Rezultati:**
   - Do të shfaqet mesazh: "Sukses! Exported X points"
   - Skedari GeoJSON ruhet në lokacionin që zgjodhët

#### 📝 Shembull skedar GeoJSON i krijuar:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [19.8187, 41.3275]
      },
      "properties": {
        "name": "Tirana, Albania",
        "description": "",
        "timestamp": "2024-01-15T10:30:00"
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [21.1655, 42.6629]
      },
      "properties": {
        "name": "Prishtina, Kosovo",
        "description": "",
        "timestamp": "2024-01-15T10:35:00"
      }
    }
  ]
}
```

#### 🔍 Si të testosh skedarin GeoJSON:
1. **Hap në QGIS:**
   - Hap QGIS
   - Layer → Add Layer → Add Vector Layer
   - Zgjidh skedarin GeoJSON
   - Kliko "Add"

2. **Hap në Google Earth:**
   - Hap Google Earth Pro
   - File → Open
   - Zgjidh skedarin GeoJSON
   - Kliko "Open"

3. **Hap në browser:**
   - Vendos skedarin në http://geojson.io
   - Ose drag & drop në hartë

---

### 📥 Import GeoJSON (Importo pika nga GeoJSON)

#### Hapi 1: Krijo skedar GeoJSON (ose përdor një ekzistues)

**Opsioni A: Krijo manualisht**
1. Hap Notepad ose VS Code
2. Shkruaj këtë kod:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [21.1655, 42.6629]
      },
      "properties": {
        "name": "Prishtina",
        "description": "Kryeqyteti i Kosovës"
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [20.7397, 42.2139]
      },
      "properties": {
        "name": "Prizren",
        "description": "Qyteti historik"
      }
    }
  ]
}
```
3. Ruaj si "shembull.geojson" (me encoding UTF-8)

**Opsioni B: Përdor skedarin e shembullit**
- Unë kam krijuar `shembull_kosove.csv` që mund ta përdorësh për batch geocode

#### Hapi 2: Importo në aplikacion
1. **Kliko butonin "Import GeoJSON"** (në seksionin "GeoJSON")
2. **Në dialog që hapet:**
   - Shko te folder-i ku është skedari GeoJSON
   - Zgjidh skedarin (p.sh. "shembull.geojson")
   - Kliko "Open"
3. **Rezultati:**
   - Do të shfaqet mesazh: "Sukses! Imported X points"
   - Pikat shtohen në listën e ruajtura
   - Mund t'i eksportosh më vonë në GPX ose CSV

#### ⚠️ Shënime të rëndësishme:
- **Koordinatat në GeoJSON:** Duhet të jenë `[longitude, latitude]` (jo `[latitude, longitude]`)
- **Encoding:** Skedari duhet të jetë UTF-8
- **Format:** Duhet të jetë valid JSON

---

## 2. Import/Export GPX

### ⚙️ Para se të fillosh:
**Instalo gpxpy:**
```bash
pip install gpxpy
```

### 🎯 Export GPX (Eksporto pika në GPX)

#### Hapi 1: Ruaj pika (si në GeoJSON)
1. Kërko lokacione një nga një
2. Kliko "Store Point" pas çdo kërkimi
3. Ruaj të paktën 2-3 pika për testim

#### Hapi 2: Eksporto në GPX
1. **Kliko butonin "Export GPX"** (në seksionin "GNSS / GPX")
2. **Në dialog:**
   - Shkruaj emrin (p.sh. "track_i_mi.gpx")
   - Zgjidh ku të ruhet
   - Kliko "Save"
3. **Rezultati:**
   - Mesazh: "Sukses! Exported X points"
   - Skedari GPX ruhet

#### 📱 Si të përdorësh skedarin GPX:
1. **Në GPS device:**
   - Kopjo skedarin GPX në GPS device
   - Importo në aplikacionin e GPS-it

2. **Në Google Earth:**
   - Hap Google Earth Pro
   - File → Open
   - Zgjidh skedarin GPX

3. **Në Garmin:**
   - Hap Garmin BaseCamp
   - File → Import
   - Zgjidh skedarin GPX

---

### 📥 Import GPX (Importo pika nga GPX)

#### Hapi 1: Merr skedar GPX

**Opsioni A: Nga GPS device**
1. Lidh GPS device me kompjuter
2. Kopjo skedarin .gpx në kompjuter

**Opsioni B: Krijo manualisht**
1. Hap Notepad
2. Shkruaj këtë kod:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1">
  <wpt lat="42.6629" lon="21.1655">
    <name>Prishtina</name>
    <desc>Kryeqyteti i Kosovës</desc>
  </wpt>
  <wpt lat="42.2139" lon="20.7397">
    <name>Prizren</name>
    <desc>Qyteti historik</desc>
  </wpt>
  <trk>
    <name>Track 1</name>
    <trkseg>
      <trkpt lat="42.6629" lon="21.1655">
        <ele>652</ele>
        <time>2024-01-15T10:30:00Z</time>
      </trkpt>
      <trkpt lat="42.2139" lon="20.7397">
        <ele>400</ele>
        <time>2024-01-15T11:00:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
```
3. Ruaj si "shembull.gpx" (me encoding UTF-8)

#### Hapi 2: Importo në aplikacion
1. **Kliko butonin "Import GPX"** (në seksionin "GNSS / GPX")
2. **Zgjidh skedarin GPX**
3. **Rezultati:**
   - Mesazh: "Sukses! Imported X points"
   - Pikat shtohen në listën e ruajtura

---

## 3. Batch Geocode CSV

### 🎯 Si të përdorësh Batch Geocode CSV

#### Hapi 1: Krijo skedar CSV me adresa

**Shembull 1 - Me kolonë "address":**
1. Hap Excel ose Notepad
2. Shkruaj:
```csv
address
Tirana, Albania
Prishtina, Kosovo
Prizren, Kosovo
Peja, Kosovo
Skopje, North Macedonia
```
3. Ruaj si "adresat.csv" (me encoding UTF-8)

**Shembull 2 - Me kolonë "adresa":**
```csv
adresa
Rruga Dëshmorët e Kombit, Tirana
Bulevardi Nënë Tereza, Prishtina
Qendra e Prizrenit
```

**Shembull 3 - Me kolona të shumta:**
```csv
id,name,address
1,Qyteti 1,Tirana, Albania
2,Qyteti 2,Prishtina, Kosovo
3,Qyteti 3,Prizren, Kosovo
```
(Aplikacioni do të gjejë automatikisht kolonën me adresa)

#### Hapi 2: Importo dhe geocode
1. **Kliko butonin "Batch Geocode CSV"** (në seksionin "Batch / Export")
2. **Zgjidh skedarin CSV** (p.sh. "adresat.csv")
3. **Shiko progress bar:**
   - Do të shfaqet dritare me progress bar
   - Do të shohësh "Duke procesuar 1/5...", "Duke procesuar 2/5...", etj.
   - Pres pak deri sa të përfundojë
4. **Zgjidh ku të ruhen rezultatet:**
   - Shkruaj emrin (p.sh. "rezultatet.csv")
   - Zgjidh ku të ruhet
   - Kliko "Save"
5. **Rezultati:**
   - Mesazh: "Geokodim i përfunduar!"
   - Do të shohësh: Total, Sukses, dhe lokacionin e ruajtjes

#### 📊 Format i rezultateve:
```csv
address,lat,lon,status
Tirana, Albania,41.3275,19.8187,Sukses
Prishtina, Kosovo,42.6629,21.1655,Sukses
Prizren, Kosovo,42.2139,20.7397,Sukses
Lokacion i pavlefshëm,,,Nuk u gjet
```

#### ⚠️ Shënime:
- CSV duhet të ketë kolonë me emrin: `address`, `adresa`, `adresë`, `location`, ose `lokacion`
- Encoding: UTF-8 (për karaktere shqipe)
- Skedari rezultat do të ketë kolonë "status" që tregon: Sukses, Nuk u gjet, Gabim, ose Bosh

#### ✅ Test i plotë:
1. Krijo CSV me 3 adresa
2. Kliko "Batch Geocode CSV"
3. Zgjidh skedarin
4. Shiko progress bar
5. Zgjidh ku të ruhen rezultatet
6. Hap rezultatet në Excel dhe kontrollo koordinatat

---

## 4. Export Current to CSV

### 🎯 Si të eksportosh rezultatin aktual në CSV

#### Hapi 1: Kërko një lokacion
1. Shkruaj adresën (p.sh. "Tirana, Albania")
2. Kliko "Find Coordinates"
3. Shiko rezultatet në panelin e djathtë:
   - Latitude, Longitude
   - Display Address
   - Country, Region, City
   - etj.

#### Hapi 2: Eksporto rezultatin
1. **Kliko butonin "Export Current → CSV"** (në seksionin "Batch / Export")
2. **Në dialog:**
   - Shkruaj emrin (p.sh. "tirana_rezultati.csv")
   - Zgjidh ku të ruhet
   - Kliko "Save"
3. **Rezultati:**
   - Mesazh: "Result exported to ..."
   - Skedari CSV ruhet me të gjitha informacionet

#### 📊 Format i rezultateve:
```csv
Field,Value
Latitude,41.3275
Longitude,19.8187
Altitude,110 m
Display Address,Tirana, Albania
Country,Albania
Region,Tirana
City,Tirana
Postal Code,1001
Timezone,
ISP,
AS,
Bounding Box,41.3275, 41.3275, 19.8187, 19.8187
```

#### ✅ Test:
1. Kërko "Tirana, Albania"
2. Kliko "Export Current → CSV"
3. Ruaj si "test.csv"
4. Hap në Excel dhe kontrollo të gjitha fushat

---

## 🔄 Workflow i plotë - Shembull praktik

### Senaryo: Krijo hartë me qytete të Kosovës

#### Hapi 1: Krijo CSV me adresa
```csv
address
Prishtina, Kosovo
Prizren, Kosovo
Peja, Kosovo
Gjakova, Kosovo
Mitrovica, Kosovo
```

#### Hapi 2: Batch geocode
1. Kliko "Batch Geocode CSV"
2. Zgjidh CSV-në
3. Ruaj rezultatet si "kosove_koordinatat.csv"

#### Hapi 3: Importo pikat në aplikacion
1. Hap "kosove_koordinatat.csv" në Excel
2. Krijo GeoJSON manualisht nga koordinatat (ose përdor tool online)
3. Ruaj si "kosove.geojson"
4. Kliko "Import GeoJSON"
5. Zgjidh "kosove.geojson"

#### Hapi 4: Eksporto në GPX
1. Kliko "Export GPX"
2. Ruaj si "kosove_track.gpx"
3. Hap në Google Earth ose GPS device

---

## ❌ Troubleshooting

### Problemi: "No points stored"
**Zgjidhja:**
- Duhet të ruash pika fillimisht me "Store Point"
- Importo nga CSV/GeoJSON/GPX fillimisht

### Problemi: "gpxpy not installed"
**Zgjidhja:**
```bash
pip install gpxpy
```

### Problemi: CSV nuk lexohet
**Zgjidhja:**
- Kontrollo që encoding është UTF-8
- Kontrollo që ka kolonë me emrin "address" ose "adresa"
- Provoni të hapni në Excel dhe të rishruani si CSV UTF-8

### Problemi: GeoJSON nuk importohet
**Zgjidhja:**
- Kontrollo që koordinatat janë `[lon, lat]` (jo `[lat, lon]`)
- Kontrollo që është valid JSON (përdor jsonlint.com për kontroll)
- Kontrollo që ka "type": "FeatureCollection"

### Problemi: GPX nuk importohet
**Zgjidhja:**
- Kontrollo që është valid XML
- Kontrollo që ka waypoints ose tracks
- Instalo gpxpy: `pip install gpxpy`

---

## 📝 Checklist për testim

- [ ] Testo Export GeoJSON: Ruaj 2 pika → Export GeoJSON → Kontrollo skedarin
- [ ] Testo Import GeoJSON: Krijo/kopjo GeoJSON → Import → Kontrollo që pikat u shtuan
- [ ] Testo Export GPX: Ruaj 2 pika → Export GPX (pas instalimit të gpxpy) → Kontrollo skedarin
- [ ] Testo Import GPX: Krijo/kopjo GPX → Import → Kontrollo që pikat u shtuan
- [ ] Testo Batch CSV: Krijo CSV me 3 adresa → Batch Geocode → Kontrollo rezultatet
- [ ] Testo Export Current CSV: Kërko lokacion → Export Current → Kontrollo skedarin

---

**Udhëzime shtesë:** Nëse ke probleme, kontrollo mesazhet e gabimit në aplikacion ose në terminal për më shumë detaje.
