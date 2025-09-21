# 🏠 AI Floorplan to 3D Service - Docker

Kompletná Docker služba ktorá spracováva obrázky pôdorysov pomocou AI a generuje 3D modely vo formáte glTF.

## 🎯 Funkcionalita

**Vstup:** PNG/JPG obrázok pôdorysu  
**Výstup:** glTF 3D model

**Workflow:**
1. 📤 Upload obrázka cez API
2. 🤖 AI spracovanie (OpenAI) - odstránenie nábytku, vyčistenie
3. 🏗️ Generovanie 3D modelu (Blender)
4. 📦 Export do glTF formátu
5. 📥 Download výsledku

## 🚀 Rýchle spustenie

### 1. Príprava
```bash
# Klonujte projekt
git clone <repository>
cd floor3Dobj

# Vytvorte .env súbor s OpenAI API kľúčom
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### 2. Spustenie služby
```bash
# Jednoduché spustenie
./docker-start.sh

# Alebo manuálne
docker-compose -f docker-compose.ai.yml up -d
```

### 3. Test služby
```bash
# Otestujte API
python3 test_api.py

# Alebo manuálne
curl -X GET http://localhost:8081/health
```

## 📋 API Endpointy

### Health Check
```bash
GET http://localhost:8081/health
```

### Jednoduché spracovanie (vráti len glTF)
```bash
POST http://localhost:8081/process-simple
Content-Type: multipart/form-data
Body: image=@your_floorplan.png

# Príklad
curl -X POST -F 'image=@Images/Examples/example4.png' \
     http://localhost:8081/process-simple \
     -o result.gltf
```

### Kompletné spracovanie (vráti ZIP s všetkými súbormi)
```bash
POST http://localhost:8081/process-floorplan
Content-Type: multipart/form-data
Body: image=@your_floorplan.png

# Príklad
curl -X POST -F 'image=@Images/Examples/example4.png' \
     http://localhost:8081/process-floorplan \
     -o result.zip
```

## 🔧 Konfigurácia

### Environment Variables (.env)
```bash
# POVINNÉ
OPENAI_API_KEY=your_openai_api_key_here

# VOLITEĽNÉ
BLENDER_PATH=/usr/local/blender/blender
PORT=5000
MAX_FILE_SIZE=16777216  # 16MB
PROCESSING_TIMEOUT=300  # 5 minút
```

### Docker Compose Porty
- **8081** - Nginx reverse proxy (odporúčané)
- **5001** - Priamy prístup k Flask API

## 📊 Monitoring

### Kontrola stavu služby
```bash
# Stav kontajnerov
docker-compose -f docker-compose.ai.yml ps

# Logy
docker-compose -f docker-compose.ai.yml logs -f

# Health check
curl http://localhost:8081/health
```

### Zastavenie služby
```bash
docker-compose -f docker-compose.ai.yml down

# S vyčistením volumes
docker-compose -f docker-compose.ai.yml down -v
```

## 🧪 Testovanie

### Automatické testy
```bash
# Spustite test suite
python3 test_api.py
```

### Manuálne testy
```bash
# Test s example4.png
curl -X POST \
  -F 'image=@Images/Examples/example4.png' \
  http://localhost:8081/process-simple \
  -o test_result.gltf

# Kontrola výsledku
ls -la test_result.gltf
```

## 📁 Štruktúra výstupov

### Simple endpoint
```
result.gltf          # 3D model
```

### Full endpoint (ZIP)
```
result.zip
├── model_12345.gltf      # 3D model
├── model_12345.bin       # Binárne dáta
├── ai_processed_xxx.png  # AI spracovaný obrázok
└── original_xxx.png      # Pôvodný obrázok
```

## ⚡ Výkon a limity

### Podporované formáty
- **Vstup:** PNG, JPG, JPEG
- **Výstup:** glTF 2.0 + BIN

### Limity
- **Max veľkosť súboru:** 16MB
- **Timeout:** 5 minút na spracovanie
- **Súbežné requesty:** Závisí od CPU/RAM

### Typické časy spracovania
- **AI preprocessing:** 10-30s
- **3D generovanie:** 30-60s
- **glTF export:** 5-15s
- **Celkom:** 1-2 minúty

## 🛠️ Troubleshooting

### Časté problémy

**1. Port už používaný**
```bash
# Zmeňte port v docker-compose.ai.yml
ports:
  - "8082:80"  # Namiesto 8081
```

**2. OpenAI API chyby**
```bash
# Skontrolujte .env súbor
cat .env | grep OPENAI_API_KEY

# Skontrolujte logy
docker-compose -f docker-compose.ai.yml logs floorplan-ai-service
```

**3. Blender chyby**
```bash
# Skontrolujte Blender v kontajneri
docker exec -it floorplan-ai-processor /usr/local/blender/blender --version
```

**4. Pamäťové problémy**
```bash
# Zvýšte pamäť pre Docker
# Docker Desktop -> Settings -> Resources -> Memory -> 4GB+
```

### Debug módy
```bash
# Spustenie s debug logmi
FLASK_ENV=development docker-compose -f docker-compose.ai.yml up

# Vstup do kontajnera
docker exec -it floorplan-ai-processor bash
```

## 🏗️ Architektúra

```
Internet → Nginx → Flask API → AI Processing → Blender → glTF Export
    ↓        ↓         ↓            ↓           ↓         ↓
  Port 8081  Port 80  Port 5000   OpenAI    /usr/local  Response
```

### Komponenty
- **Nginx:** Load balancer, file upload handling
- **Flask:** REST API, request handling
- **OpenAI:** AI image preprocessing
- **Blender:** 3D model generation
- **Ubuntu 22.04:** Base system

## 🔐 Bezpečnosť

### Odporúčania
- Používajte `.env` súbor pre API kľúče
- Nespúšťajte ako root (používa sa appuser)
- Limitujte veľkosť uploadov
- Implementujte rate limiting pre produkciu

### Produkčné nastavenia
```yaml
# docker-compose.prod.yml
environment:
  - FLASK_ENV=production
  - MAX_WORKERS=4
  - RATE_LIMIT=10/minute
```

## 📈 Škálovanie

Pre vysokú záťaž:
```yaml
# Viac workerov
services:
  floorplan-ai-service:
    deploy:
      replicas: 3
    
  # Load balancer
  nginx:
    depends_on:
      - floorplan-ai-service
```

---

## 🎉 Hotovo!

Vaša AI Floorplan služba je pripravená na použitie. Pošlite obrázok pôdorysu a dostanete 3D model vo formáte glTF! 🏠✨
