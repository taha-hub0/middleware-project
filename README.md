# Middleware Tabanlı Veri İşleme Sistemi

Bu proje, sahte log/veri üretip FastAPI tabanlı middleware üzerinden işleyen, KVKK maskelemesi yapan ve çıktıları dosyaya yazan sade bir veri işleme sistemidir.

## 1. Proje Amacı
Üretilecek log/veri kayıtlarını tek bir middleware servisinde filtrelemek, maskelemek, zenginleştirmek ve istenen formatta çıktı üretmek.

## 2. Sistem Mimarisi
```
Producer
  └─> POST /logs (FastAPI)
        └─> Chain of Responsibility (filter → kvkk → enrichment → routing)
              └─> Formatter (JSON/CSV/HTML)
                    └─> outputs/
        └─> Observer (logging) → logs/
```

## 3. Kullanılan Teknolojiler
- Python
- FastAPI
- Faker
- requests
- Docker

## 4. Kullanılan Tasarım Kalıpları
- **Chain of Responsibility**: İşleme adımlarını sırayla çalıştırır.
- **Factory Pattern**: JSON/CSV/HTML formatter seçiminde kullanılır.
- **Observer Pattern**: Normal ve kritik logları merkezi logging yapısına yönlendirir.

## 5. Klasör Yapısı
```
project/
├── producer/
│   └── main.py
├── middleware/
│   ├── main.py
│   ├── pipeline.py
│   ├── steps.py
│   ├── formatters.py
│   ├── observers.py
│   └── logger.py
├── logs/
├── outputs/
├── stress_test.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 6. Kurulum Adımları
```bash
python -m pip install -r requirements.txt
```

Middleware servisini çalıştırma:
```bash
python -m uvicorn middleware.main:app --host 0.0.0.0 --port 8000
```

Producer çalıştırma:
```bash
python producer/main.py
```

> `logs/` ve `outputs/` klasörleri otomatik oluşturulur.

## 7. Docker ile Çalıştırma
```bash
docker compose up --build
```

Producer’u ayrı bir terminalde çalıştırabilirsiniz:
```bash
python producer/main.py
```

## 8. Stress Test Sonuçları
Stress testi çalıştırma:
```bash
python stress_test.py
```

Örnek çıktı formatı (gerçek değerler ortama göre değişir):
```
Requests: 100 | Duration: <...>s | Req/s: <...> | OK: <...> | Errors: <...>
Requests: 1000 | Duration: <...>s | Req/s: <...> | OK: <...> | Errors: <...>
Requests: 5000 | Duration: <...>s | Req/s: <...> | OK: <...> | Errors: <...>
```

## 9. Örnek Veri Akışı
**Gelen veri:**
```json
{
  "timestamp": "2026-05-08T21:11:33Z",
  "level": "INFO",
  "event_type": "login",
  "message": "User logged in",
  "user_name": "Ahmet Yilmaz",
  "email": "ahmet@example.com",
  "phone": "555-123-4567",
  "ip": "10.1.2.3",
  "departman": "DEV"
}
```

**İşlenmiş çıktı (JSON):**
```json
{
  "timestamp": "2026-05-08T21:11:33Z",
  "level": "INFO",
  "event_type": "login",
  "message": "User logged in",
  "user_name": "A*****",
  "email": "a*****@example.com",
  "phone": "********67",
  "ip": "10.1.***.***",
  "departman": "DEV",
  "category": "general",
  "processed_at": "2026-05-08T21:11:33+00:00"
}
```

## 10. Sonuç ve Kazanımlar
Bu proje; sade bir mimariyle veri işleme hattı kurmayı, tasarım kalıplarını doğru yerde kullanmayı ve FastAPI tabanlı bir middleware servisinin uçtan uca çalışmasını göstermektedir.
