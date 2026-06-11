# Akıllı Komponent Yönetim Sistemi (ToolboxDB API)

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-brightgreen)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Redis](https://img.shields.io/badge/Redis-Cache-orange)
![GitHub Actions CI](https://img.shields.io/badge/GitHub%20Actions-CI-white)

## Proje Özeti
**Akıllı Komponent Yönetim Sistemi (ToolboxDB API)**; maker’lar ve IoT geliştiricileri için tasarlanmış, bileşen ömürlerini izlemeye, fatura ve parti bilgilerinin AI/LLM destekli PDF ayrıştırma ile otomatik içeri aktarımına ve sorgu performansını Redis ile hızlandırmaya odaklı bir envanter yönetim hizmetidir. Sistem, doğrulama için fatura verilerini taslak olarak saklar ve ardından güvenli şekilde envantere eşler.

## Temel Özellikler
Aşağıdaki tablo ve maddeler projede öne çıkan yetenekleri özetler:

| Özellik | Açıklama |
|---|---|
| **Automatik PDF Fatura Ayrıştırma (LLM)** | PDF'lerden yapılandırılmış (structured) çıktı üreten LLM destekli işlem hattı (öğe ayırma, miktar, tedarikçi, tarih). |
| **Staging / Taslak Alanı** | Ayrıştırılan faturalar `is_processed = False` ile `Invoice`/`InvoiceItem` modellerinde taslak olarak saklanır; manuel/otomatik doğrulama sonrası envantere eşlenir. |
| **JWT Kimlik Doğrulama** | Endpoint'leri `OAuth2PasswordBearer` ve JWT ile güvenceye alma. Bcrypt şifrelemeli kullanıcı kayıt ve giriş akışı. |
| **Rol Tabanlı Erişim Kontrolü (RBAC)** | 3 farklı yetki seviyesi: `admin` (tam yetki), `user` (sadece okuma + fatura yükleme) ve `chatter` (sadece yapay zeka ile sohbet). |
| **Çok Kiracılı Bileşenler (Multi-Tenant)** | Bileşenler tamamen kullanıcılara özeldir. Tüm CRUD işlemleri `user_id` üzerinden filtrelenir; tam gizlilik ve sahiplik sağlanır. |
| **Modüler Monolit Mimari & ID Tip Güvenliği** | `src/routes` yalnızca HTTP katmanını yönetir; servis mantığı `src/services` içinde. Tür güvenliği: **Components** için `UUID`, **Categories** için `int`. Router path'leri tip olarak zorlanır. |
| **Yüksek-ROI Redis Önbellekleme** | Referans verileri (ör. kategori listesi) Redis'te cache'lenir. Yazma işlemlerinde (POST/PUT/DELETE) cache hemen invalid edilir. Dinamik envanter miktarları asla cache'lenmez. |
| **Prod-ready Operasyonel Özellikler** | **Correlation ID** takibi; `/health` için SQLAlchemy `text("SELECT 1")` kullanılarak DB sağlık kontrolü; Docker tabanlı CI pipeline'ları. |

Öne çıkan maddeler:
- Otomatik fatura -> taslak -> doğrulama -> envanter eşleme iş akışı.
- Güçlü tip güvenliği: router seviyesinde `component_id:uuid`, `category_id:int`.
- Cache invalidation politikasına sıkı uyum.
- Merkezi log/izleme için `X-Correlation-ID` desteği.

## Tech Stack
- Framework & Web:
  - FastAPI (ASGI)
  - Uvicorn (dev/prod runner)
- Veritabanı & ORM:
  - Supabase (PostgreSQL)
  - SQLAlchemy (async/sync destekli)
- Cache:
  - Redis (`redis-py`)
- PDF & LLM:
  - pypdf (PDF parsing)
  - OpenAI / Ollama (LLM sağlayıcı adaptörleri)
- Test & QA:
  - Pytest
  - Black / Flake8 (kod format & linting)
- Diğer:
  - Pydantic v2 (şema doğrulama)

## Proje Yapısı (Öne Çıkanlar)
Aşağıda repo içinde odaklanılması gereken alanlara dair ağaç görselleştirmesi:

```
toolboxdb-api/
├─ main.py
├─ requirements.txt
├─ .github/
│  └─ workflows/
│     └─ ci.yml        # Linting + Test + Redis service container
├─ src/
│  ├─ __init__.py
│  ├─ cache.py
│  ├─ db/
│  │  └─ connector.py
│  ├─ llm/
│  │  └─ ...          # LLM provider adaptörleri (openai, ollama, groq)
│  ├─ middleware/
│  │  └─ middleware.py # Correlation ID, error handling, request validation
│  ├─ pdf/
│  │  └─ pdf_service.py # PDF -> LLM ayrıştırma hattı
│  ├─ routes/
│  │  ├─ category_routes.py
│  │  ├─ component_routes.py
│  │  └─ core_routes.py
│  ├─ services/
│  │  └─ ...          # İş mantığı, veri eşleme, transaction yönetimi
│  ├─ models.py
│  └─ schemas.py
├─ tests/
│  ├─ test_component_routes.py
│  └─ test_pdf_service.py
└─ docks/
   └─ REDIS_SETUP.md
```

Not: Proje, `src/routes` → HTTP katmanı; `src/services` → iş mantığı/kayıt/update; `src/middleware/middleware.py` → global error handling ve correlation-id enjekte edici olarak tasarlanmıştır.

## Kurulum & Yerel Geliştirme (zsh)
Aşağıdaki adımlar macOS + zsh ortamı için hazırlanmıştır.

1. Depoyu klonlayın:
```bash
git clone <REPO_URL> toolboxdb-api
cd toolboxdb-api
```

2. Sanal ortam oluşturun ve aktif edin (`.venv`):
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

3. Bağımlılıkları yükleyin:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Yerel Redis konteynerini başlatın (geliştirme amaçlı):
```bash
docker run -d --name toolboxdb-redis -p 6379:6379 redis:7
```

5. Çevresel değişkenler:
- Proje `.env` veya CI sırlarına göre DB/REDIS/LLM anahtarlarını ayarlayın. Örnek (geliştirme):
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/toolboxdb
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=sk-...
```

6. Uvicorn ile geliştirme sunucusunu başlatın:
```bash
uvicorn main:app --reload
```

Uygulama tipik olarak `http://127.0.0.1:8000`'de çalışır. Swagger UI: `http://127.0.0.1:8000/docs`

## Sağlık Kontrolleri & Güvenlik Notları
- Sistem, standart OAuth2 prosedürleri ile çalışan JWT Kimlik Doğrulaması (Authentication & Authorization) içerir.
- **Tam Koruma**: Uygulamanın tüm temel işlevleri (Kategoriler, Bileşenler, Faturalar, Yapay Zeka Önerileri) router seviyesinde kilitlenmiştir ve Bearer token zorunludur. Sadece `/health` ve giriş yolları halka açıktır.
- `/health` endpoint'i, SQLAlchemy ile DB'ye şu şekilde güvenli bir sorgu atar: `db.execute(text("SELECT 1"))`. (Ham stringler kullanılmaz.)
- Tüm eksik yollar ve hatalar JSON yapılı özel hata cevabı döner; HTML hata sayfaları geri dönmez.
- Arama endpoint'leri boş/yalnızca-boşluk girişlerini hızlıca `[]` ile yanıtlayarak gereksiz DB bağlantısını önler.

## CI/CD (Kısa Açıklama)
- `/.github/workflows/ci.yml` (veya benzeri) GitHub Actions üzerinde:
  - Kod formatlama ve statik kontrol: **Black** ve **Flake8**
  - Testler: **Pytest**
  - Workflow, test aşamasında bir **Redis service container** sağlar; böylece tests Redis'e erişimli çalışır.
  - Pipeline ayrıca Docker tabanlı entegrasyon ve image oluşturma adımlarına kolayca genişletilebilir.

## İleri Okuma ve Operasyonel Öneriler
- **Cache Invalidation**: `POST/PUT/DELETE` ile kategori değişiklikleri yapıldığında ilgili Redis anahtarları hemen invalid edilir.
- **Invoice Staging**: PDFService + LLM sonucunu `Invoice` olarak kaydet; `is_processed=False` ile taslak bırak; manuel doğrulama sonrası `is_processed=True` ve toplu eşleme yap.
- **Tip Güvenliği**: Router seviyesinde path parametre tiplerini açıkça belirtin:
  - `@router.get("/components/{component_id:uuid}")`
  - `@router.get("/categories/{category_id:int}")`

---

Bu README'yi çift dilli (TR/EN) sürüm veya ek geliştirici yardımcı dosyaları (`.env.example`, `Makefile`, `devcontainer`) ile genişletmemi isterseniz bildirin; şu an kök dizine tek dilli Türkçe sürümü ekledim.
