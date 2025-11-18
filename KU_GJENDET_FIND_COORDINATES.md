# 🔍 Ku gjendet "Find Coordinates" dhe si të përdoret

## 📍 Lokacioni i butonit:

Butoni **"Find Coordinates"** gjendet në:
- **Panel i majtë** (në fillim të aplikacionit)
- **Nën seksionin "Address → Coordinates"**
- **Në të djathtë të fushës së tekstit "Address:"**

## 🎯 Si të përdoret:

1. **Hap aplikacionin**
2. **Shiko panelin e majtë** - duhet të shohësh një kuti me titull "Address → Coordinates"
3. **Në këtë kuti do të shohësh:**
   ```
   [Address:] [Fusha për të shkruar adresën] [Find Coordinates]
   ```
4. **Shkruaj adresën** në fushën e bardhë (p.sh. "Prishtina, Kosovo")
5. **Kliko butonin "Find Coordinates"** (buton blu në të djathtë)

## ⚠️ Nëse nuk e shikon butonin:

### Problemi 1: Scrollbar
- **Zgjidhja:** Përdor mousewheel ose scrollbar për të lëvizur lart-poshtë
- Butoni mund të jetë jashtë ekranit nëse nuk ke scrolluar

### Problemi 2: Aplikacioni është i vogël
- **Zgjidhja:** Zmadho dritaren e aplikacionit
- Ose përdor scrollbar për të parë të gjithë përmbajtjen

### Problemi 3: Butoni është i fshehur
- **Zgjidhja:** Kontrollo që aplikacioni është i hapur plotësisht
- Provoni të rihapni aplikacionin

## 📸 Struktura e panelit:

```
┌─────────────────────────────────────────┐
│ Address → Coordinates                   │
├─────────────────────────────────────────┤
│ Address: [Fusha e tekstit] [Find       │
│          Coordinates]                    │
└─────────────────────────────────────────┘
```

## ✅ Test i shpejtë:

1. Shkruaj në fushën "Address": `Tirana, Albania`
2. Kliko butonin blu "Find Coordinates"
3. Duhet të shfaqen rezultatet në panelin e djathtë:
   - Latitude
   - Longitude
   - Display Address
   - Country, Region, City, etj.

## 🔄 Alternativë:

Nëse vërtet nuk e shikon butonin, mund të përdorësh:
- **Batch Geocode CSV** - për adresa të shumta njëherësh
- Ose kontakto mua për të rregulluar problemin

