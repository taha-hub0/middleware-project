# Middleware Tabanlı Veri İşleme Sistemi

Sahte veri üreten producer servisinden gelen log/veri kayıtlarını FastAPI tabanlı middleware üzerinden işleyen, KVKK maskelemesi yapan, kategorilendiren ve çoklu formatta çıktı üreten profesyonel bir veri işleme sistemi.

## İçindekiler
1. [Proje Amacı](#proje-amacı)
2. [Sistem Mimarisi](#sistem-mimarisi)
3. [Teknoloji Yığını](#teknoloji-yığını)
4. [Tasarım Kalıpları](#tasarım-kalıpları)
5. [Dosya Yapısı](#dosya-yapısı)
6. [Kurulum](#kurulum)
7. [Kullanım](#kullanım)
8. [Docker](#docker)
9. [Veri Akışı Örneği](#veri-akışı-örneği)
10. [Stress Test](#stress-test)
11. [Modül Açıklamaları](#modül-açıklamaları)
12. [Çıktı Formatları](#çıktı-formatları)

---

## Proje Amacı

Bu proje, üniversite final projesi kapsamında geliştirilmiş bir middleware sistemidir. Temel görevleri:

- 📊 Sahte log/veri kayıtları üretme (Producer)
- 🔄 Gelen verileri sırayla işleme (Chain of Responsibility)
- 🔒 KVKK maskelemesi uygulaması
- 📁 Veriyi kategorilendiritme ve zenginleştirme
- 📤 Çoklu formatta çıktı üretimi (JSON, CSV, HTML)
- 📝 Merkezi logging sistemi (Observer Pattern)
- ⚡ Stress test ile performans ölçümü

---

## Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCER SERVICE                          │
│  • Faker ile sahte veri üretimi                             │
│  • HTTP POST ile middleware'e gönderimi                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ↓ POST /logs
┌─────────────────────────────────────────────────────────────┐
│              MIDDLEWARE (FastAPI)                            │
│                                                              │
│  1. Log Filter    → DEBUG seviye logları filtrele           │
│  2. KVKK Mask     → Kişisel verileri maskele                │
│  3. Enrichment    → Kategori ve timestamp ekle              │
│  4. Routing       → Channel'a göre yönlendir                │
│                    ↓                                         │
│  5. Formatting    → JSON / CSV / HTML                       │
│  6. Storage       → outputs/ klasörüne yaz                  │
│  7. Observers     → logs/ klasörüne log yazması             │
└─────────────────────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│            OUTPUTS (3 format)                               │
│  • data_<uuid>.json     (JSON formatı)                      │
│  • data_<uuid>.csv      (CSV formatı)                       │
│  • data_<uuid>.html     (HTML tablosu)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Teknoloji Yığını

| Bileşen   | Teknoloji  | Versiyon |
|---------  |----------- |----------|
| Framework | FastAPI    | 0.115.0 |
| Server    | Uvicorn    | 0.30.6 |
| Data Gen  | Faker      | 26.1.0 |
| HTTP Client | requests | 2.32.3 |
| Container | Docker     | - |
| Language | Python      | 3.11+ |

---

## Tasarım Kalıpları

### 1. Chain of Responsibility
**Dosya:** `middleware/pipeline.py`

İşleme adımlarını sırayla zincirlemek için kullanılır. Her adım (filter, mask, enrichment, routing) bir sonraki adıma veri iletir.

```python
Step (Handler) → set_next() → Step → ... → Step
```

### 2. Factory Pattern
**Dosya:** `middleware/formatters.py`

JSON/CSV/HTML formatter seçim ve üretimini merkezileştirir. İstenilen format adı verildiğinde doğru formatter sınıfı oluşturulur.

```python
FormatterFactory().create("json")   # JsonFormatter
FormatterFactory().create("csv")    # CsvFormatter
FormatterFactory().create("html")   # HtmlFormatter
```

### 3. Observer Pattern
**Dosya:** `middleware/observers.py`

Log olaylarını dinleyip farklı hedeflere yazmak için kullanılır. Her event'te tüm observer'lar bilgilendirilir.

```python
EventDispatcher([NormalLogObserver(), CriticalLogObserver()])
```

---

## Dosya Yapısı

```
middleware_project/
├── producer/
│   └── main.py                 # Faker ile sahte veri üretimi
│
├── middleware/
│   ├── main.py                 # FastAPI uygulaması
│   ├── pipeline.py             # Chain of Responsibility akışı
│   ├── steps.py                # İşleme adımları
│   ├── formatters.py           # Factory Pattern formatters
│   ├── observers.py            # Observer Pattern logging
│   ├── logger.py               # Merkezi logging yapılandırması
│   └── storage.py              # Dosya yazma işlemleri
│
├── logs/                       # Runtime log dosyaları
├── outputs/                    # İşlenmiş veri çıktıları
│
├── stress_test.py              # Performans ölçüm scripti
├── requirements.txt            # Python bağımlılıkları
├── Dockerfile                  # Container image tanımı
├── docker-compose.yml          # Multi-container yapılandırması
├── PROJECT_SPEC.md             # Proje özellikleri
└── README.md                   # Bu dosya
```

---

## Kurulum

### Ön Koşullar
- Python 3.11 veya sonrası
- pip paket yöneticisi

### Adım 1: Bağımlılıkları Yükleyin

```bash
python -m pip install -r requirements.txt
```

### Adım 2: Middleware Servisini Başlatın

```bash
python -m uvicorn middleware.main:app --host 0.0.0.0 --port 8000
```

Başarılı başlangıç çıktısı:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Adım 3: Producer'u Çalıştırın (Yeni Terminal)

```bash
python producer/main.py
```

Varsayılan olarak 5 kayıt üretir ve middleware'e gönderir.

---

## Kullanım

### Environment Değişkenleri

**Producer için:**
```bash
export MIDDLEWARE_URL=http://localhost:8000/logs
export PRODUCER_COUNT=10          # Kaç kayıt üretilsin
export PRODUCER_DELAY=0.5         # Kaydın arasındaki gecikme (saniye)
```

**Örnek:**
```bash
PRODUCER_COUNT=100 PRODUCER_DELAY=0.1 python producer/main.py
```

### API Endpoint'leri

#### POST /logs
Log/veri kaydı gönderme

**Request:**
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-05-11T18:00:00Z",
    "level": "INFO",
    "event_type": "login",
    "message": "User logged in",
    "user_name": "Ahmet Yilmaz",
    "email": "ahmet@example.com",
    "phone": "5551234567",
    "ip": "192.168.1.1"
  }'
```

**Response:**
```json
{
  "status": "ok",
  "channel": "general",
  "formats": ["json", "csv", "html"]
}
```

---

## Docker

### Middleware'i Container'da Çalıştırma

```bash
docker compose up --build
```

Middleware Docker içinde 8000 portunda çalışacak.

### Producer'u Host'ta Çalıştırma

```bash
python producer/main.py
```

---

## Veri Akışı Örneği

### 1. Gelen Veri (Producer'dan)
```json
{
  "timestamp": "2026-05-11T18:00:00Z",
  "level": "INFO",
  "event_type": "login",
  "message": "User logged in",
  "user_name": "Ahmet Yilmaz",
  "email": "ahmet@example.com",
  "phone": "5551234567",
  "ip": "192.168.1.1"
}
```

### 2. Log Filter Adımı
- DEBUG seviyesi loglar atılır
- Diğer loglar devam eder

### 3. KVKK Maskelemesi
```json
{
  "user_name": "A*****",
  "email": "a*****@example.com",
  "phone": "********67",
  "ip": "192.168.***.***"
}
```

### 4. Enrichment (Kategorilendirim)
```json
{
  "category": "general",
  "processed_at": "2026-05-11T18:00:00+00:00"
}
```

### 5. Routing
- Category="security" → channel="critical"
- Diğer → channel="general"

### 6. Çıktı Formatları
Aynı veri için 3 dosya oluşturulur:
- `data_550e8400-e29b-41d4-a716-446655440000.json`
- `data_550e8400-e29b-41d4-a716-446655440000.csv`
- `data_550e8400-e29b-41d4-a716-446655440000.html`

---

## Stress Test

Middleware performansını ölçmek için stress test aracı kullanın.

### Çalıştırma

```bash
python stress_test.py
```

### Varsayılan Test Yükü
- 100 istek
- 1.000 istek
- 5.000 istek

### Örnek Çıktı
```
Stress Test Results
----------------------------------------------------------------------
Requests: 100 | Start: 18:00:00 | End: 18:00:02
Duration: 2.45s | Req/s: 40.82 | OK: 100 | Errors: 0
----------------------------------------------------------------------
Requests: 1000 | Start: 18:00:02 | End: 18:00:30
Duration: 28.15s | Req/s: 35.53 | OK: 1000 | Errors: 0
----------------------------------------------------------------------
Requests: 5000 | Start: 18:00:30 | End: 18:03:45
Duration: 135.20s | Req/s: 36.97 | OK: 5000 | Errors: 0
----------------------------------------------------------------------
```

### Özel Test Sayısı

```python
from stress_test import run_tests

# 200, 2000 istek test et
run_tests(counts=[200, 2000])
```

---

## Modül Açıklamaları

### producer/main.py
- Faker kütüphanesiyle sahte veri üretir
- HTTP POST ile middleware'e gönderir
- İsim, email, telefon, IP, level, event_type içerir

### middleware/main.py
- FastAPI uygulaması
- POST /logs endpoint'i
- Pipeline ve Observer entegrasyonu

### middleware/pipeline.py
- Chain of Responsibility pattern
- Step sınıfı ile adım zincirlemesi
- build_chain() fabrika fonksiyonu

### middleware/steps.py
- **log_filter_step**: DEBUG logları filtreler
- **kvkk_mask_step**: Kişisel verileri maskeler
- **enrichment_step**: Kategori ve timestamp ekler
- **routing_step**: Channel'a göre yönlendirir

### middleware/formatters.py
- **JsonFormatter**: JSON formatında çıktı
- **CsvFormatter**: CSV formatında çıktı
- **HtmlFormatter**: HTML tablo formatında çıktı
- **FormatterFactory**: Format seçimi

### middleware/observers.py
- **NormalLogObserver**: Tüm olayları logs/middleware.log'a yazar
- **CriticalLogObserver**: ERROR/CRITICAL olayları logs/critical.log'a yazar

### middleware/logger.py
- Merkezi logging yapılandırması
- get_logger() fonksiyonu
- logs/ klasörüne mutlak path yazma

### middleware/storage.py
- Dosya yazma işlemleri
- UUID kullanarak collision-free dosya adları
- Thread-safe işlem (Lock mekanizması)

---

## Çıktı Formatları

### JSON
```json
{
  "timestamp": "2026-05-11T18:00:00Z",
  "level": "INFO",
  "event_type": "login",
  "message": "User logged in",
  "user_name": "A*****",
  "email": "a*****@example.com",
  "phone": "********67",
  "ip": "192.168.***.***",
  "category": "general",
  "processed_at": "2026-05-11T18:00:00+00:00"
}
```

### CSV
```csv
timestamp,level,event_type,message,user_name,email,phone,ip,category,processed_at
2026-05-11T18:00:00Z,INFO,login,User logged in,A*****,a*****@example.com,********67,192.168.***.***,general,2026-05-11T18:00:00+00:00
```

### HTML
```html
<table>
  <tr><td>timestamp</td><td>2026-05-11T18:00:00Z</td></tr>
  <tr><td>level</td><td>INFO</td></tr>
  <tr><td>event_type</td><td>login</td></tr>
  <tr><td>user_name</td><td>A*****</td></tr>
  ...
</table>
```

---

## Kazanımlar

✅ Tasarım Kalıplarının Pratik Uygulaması  
✅ FastAPI ile Asenkron İşleme  
✅ KVKK Mevzuatına Uygun Maskeleme  
✅ Merkezi Logging Sistemi  
✅ Thread-Safe File Writing  
✅ Docker ile Containerizasyon  
✅ Production-Ready Mimari  

---


## İletişim
Sorularınız için proje dokümantasyonunu inceleyiniz.
