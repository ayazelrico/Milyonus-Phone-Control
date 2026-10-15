# CLAUDE.md — Milyonus Phone Control (mphone)

Bu dosya, bu depoda çalışan Claude Code oturumları (ve insan geliştiriciler) için **çalışma kurallarıdır**. Her oturumun başında okunur. Kurallar ile başka bir doküman çelişirse bu dosya ve ardından [Plan.md](Plan.md) geçerlidir; çelişkiyi fark edersen düzeltmeyi öner.

---

## 0. Hızlı Bakış

- **Ne yapıyoruz:** Milyonus Agent'ın (ve MCP destekli diğer agent'ların) gerçek telefonları **bağlı (yerel)** ve **uzaktan** kontrol etmesini sağlayan sistem. Referans: [ShawnPana/phone-harness](https://github.com/ShawnPana/phone-harness) — baştan yazıyoruz, kod kopyalamıyoruz.
- **Kalbi:** Tek bir op sözlüğü (`send(op, **kw)`) — yerel backend, Node üzerinden uzak cihaz ve Companion App aynı sözleşmeyi konuşur. Helper'lar platform bilmez.
- **Dokümanlar:**
  | Doküman | Ne zaman oku |
  |---|---|
  | [Plan.md](Plan.md) | Mimari, protokol (§7), bileşen detayları (§8), güvenlik (§10). Bir bileşene dokunmadan önce ilgili bölümü oku. |
  | [Phases.md](Phases.md) | Hangi fazdayız, çıkış kriterleri neler. |
  | [Plan-Actions.md](Plan-Actions.md) | Üzerinde çalıştığın kalem (`A<faz>.<no>`), kabul kriteri, bağımlılıklar. |
  | `docs/PITFALLS.md` | Bir backend'e (Android/iOS/Companion) dokunmadan önce **mutlaka**. |
  | `docs/adr/` | Bir teknoloji/kararı sorgulamadan önce. |
  | `docs/decisions.md` | Açık soruların (Q1–Q13) cevapları. |
- **Mevcut faz:** `P1 tamamlandı → P2 — Android ADB` (P0'da insan bekleyen maddeler: H-01, H-02, H-03) (bu satırı faz değiştikçe güncelle).

---

## 1. Dil ve Üslup

- **Kod, tanımlayıcılar, commit mesajları, kod yorumları:** İngilizce.
- **Dokümanlar (`docs/`, Plan*, Phases, SKILL.md):** Türkçe (SKILL.en.md İngilizce kopyadır).
- **Kullanıcıya/operatöre görünen mesajlar** (`user_action`, `doctor` ipuçları, CLI yardım, dashboard): Türkçe varsayılan, İngilizce karşılığı i18n tablosunda (`mphone_core/i18n/`). Yeni bir mesaj eklediğinde ikisini de ekle.
- Kullanıcıyla sohbette kullanıcının dilini kullan (genelde Türkçe).
- Hata mesajları **kullanıcının yapması gereken tek şeyi** söyler: "Telefonun kilidini açın; PIN asla otomatik yazılmaz." — "Bir hata oluştu" değil.

---

## 2. Depo Yapısı (özet — tam hali Plan.md §18)

```
packages/
  mphone-protocol/   # TEK DOĞRULUK KAYNAĞI: schema/ops.v1.json + üretilmiş modeller. Elle model yazma.
  mphone-core/       # Backend taban, connect(), helpers, textnorm (Türkçe), ocr, config, workspace, policy
  mphone-backends/   # android_adb, ios_mirroring, ios_wda, remote, fake
  mphone-cli/        # `mphone` komutu
  mphone-mcp/        # MCP araç tanımları (stdio + gateway HTTP aynı tanımları kullanır)
  mphone-node/       # cihaz düğümü daemon'u
  mphone-gateway/    # FastAPI kontrol düzlemi
  mphone-runner/     # uzak script sandbox'ı
  mphone-sdk/        # Python istemci
apps/android-agent/  # Companion App (Kotlin)
apps/dashboard/      # Next.js
apps/test-app/       # E2E için deterministik Android test uygulaması
skills/phone-control/SKILL.md
packages/mphone-core/src/mphone_core/workspace_default/agent_helpers.py  # agent workspace varsayılanı
packages/mphone-backends/src/mphone_backends/fake/scenarios/              # fake telefon senaryoları
tests/{unit,contract,e2e_fake,e2e_emulator,e2e_device,load,chaos,agent_eval,fixtures}
tools/               # gen_protocol.py, gen_skill_helpers.py, fake_node.py, bump_version.py
```

**Katman kuralı (ihlal etme):**
```
protocol  ←  core  ←  backends  ←  cli / mcp / node / runner / sdk  ←  gateway
```
- `mphone-core` hiçbir backend'i import etmez (backend'ler entry point ile kaydolur).
- `helpers.py` içinde platform adı (`android`, `ios`, `adb`, `Quartz`) **geçmez**. Platforma özgü her şey backend'dedir.
- Gateway, backend'leri import etmez; cihazlarla yalnızca protokol mesajlarıyla konuşur.

---

## 3. Komutlar

> Bir komut çalışmıyorsa düzelt ve bu bölümü güncelle. Sağdaki etiket, komutun hangi kalemle geldiğini gösterir; etiketsiz olanlar bugün çalışır (A0.08'de doğrulandı).

```bash
uv sync                                   # tüm workspace bağımlılıkları (Python 3.12'yi uv kurar)
uv run pytest tests/unit tests/contract   # hızlı test seti (her değişiklikte)
uv run pytest -m "not slow"               # PR öncesi
uv run ruff check --fix . && uv run ruff format .
uv run pyright
uv run pre-commit run --all-files         # yalnızca git'te izlenen/stage'li dosyaları kontrol eder
uv run tools/bump_version.py --check      # tüm paketler aynı sürümde mi
uv run mphone --version

uv run tools/gen_protocol.py              # şemadan modelleri + docs/protocol.md yeniden üret
uv run tools/gen_protocol.py --check      # CI: üretilmiş dosyalar güncel mi
uv run pytest --cov=packages/mphone-core/src --cov=packages/mphone-protocol/src   # çekirdek kapsamı (hedef ≥ %90)
uv run pytest -m ocr                      # [A2.06] OCR korpus kalite testi
uv run pytest tests/e2e_emulator          # [A2.15] açık bir Android emülatörü/cihazı gerekir
uv run mphone doctor android              # [A2.13] bağlı Android zincir teşhisi
uv run mphone run <<'PY'                  # [A3.01]
ensure_device(); print(screen_text()[:20])
PY
uv run pytest tests/e2e_fake              # [A5.22] gateway/runner/mcp zinciri (Docker gerekir)
docker compose -f deploy/docker-compose.yml up -d   # [A5.20] yerel gateway yığını
```

Bu makinede (geliştirme Mac'i) `adb` ve `docker` henüz kurulu değil: P2 için `brew install android-platform-tools`, P5 için Docker Desktop veya OrbStack gerekir.

Pytest işaretleri: `slow`, `ocr`, `device` (gerçek cihaz ister — CI'da atlanır), `emulator`, `macos` (pyobjc ister), `docker`.

Android uygulaması (`apps/android-agent`): `./gradlew test assembleDebug` · Dashboard: `pnpm -C apps/dashboard dev|test|lint`.

---

## 4. Bir Kalem Üzerinde Çalışma Akışı

Kullanıcı "A2.08'i yap" dediğinde (veya bir iş verdiğinde):

1. **Oku:** Plan-Actions.md'de kalemi, bağımlılıklarını ve kabul kriterini; Plan.md'nin ilgili bölümünü; backend işiyse `docs/PITFALLS.md`.
2. **Bağımlılık kontrolü:** Bağımlı kalemler `☑` değilse dur, kullanıcıya söyle (veya açıkça mock'la ve bunu belirt).
3. **Kalemi `◐` yap.**
4. **Önce test:** Kabul kriterini doğrulayan testleri yaz (fake backend / fixture ile; gerçek cihaz gerekiyorsa `@pytest.mark.device`).
5. **Uygula:** Küçük, odaklı değişiklik. Kapsam dışı bir şey bulursan düzeltme; Plan-Actions.md'ye yeni kalem öner.
6. **Doğrula:** ilgili testler + `ruff` + `pyright` + (şema değiştiyse) `gen_protocol --check`.
7. **Dokümanları güncelle:** PITFALLS.md (yeni platform dersi), CHANGELOG.md (`Unreleased`), SKILL.md (agent davranışı değiştiyse), Plan.md (tasarım değiştiyse + ADR), Plan-Actions.md durum `☑`.
8. **Rapor:** Ne yapıldı, nasıl doğrulandı (komut + sonuç), ne yapılamadı/atlandı — dürüstçe. Test başarısızsa çıktısıyla söyle.

Commit/PR yalnızca kullanıcı isterse. Commit mesajı: Conventional Commits + kalem kimliği:
```
feat(android): unicode text input via IME (A2.08)
```
Dal adı: `a2.08-unicode-ime`. PR açıklaması: kalem kimliği, kabul kriterleri kontrol listesi, test kanıtı.

---

## 5. Protokol Kuralları (en kritik bölüm)

Protokol = `packages/mphone-protocol/schema/ops.v1.json`. Her şey buradan türer.

### 5.1 Yeni op ekleme kontrol listesi
1. Gerçekten yeni bir **anlam** mı? Mevcut op + argümanla yapılamıyor mu? Op adları **ne anlama geldiğine** göre (`nav.home`), platformun nasıl yaptığına göre değil (`adb.keyevent` ✗).
2. Şemaya ekle: `args_schema`, `result_schema`, `default_timeout_ms`, `side_effect`, `description_tr/en`.
3. `uv run tools/gen_protocol.py` → modeller, `OP_NAMES`, `docs/protocol.md`.
4. Uyum vektörleri (`tests/fixtures/protocol_vectors/`): ≥ 1 geçerli, ≥ 1 geçersiz.
5. Fake backend'e uygula (her op fake'te olmalı).
6. Destekleyen backend'lere uygula; desteklemeyenlerde **hiçbir şey yapma** (slot tanımlanmazsa otomatik `Unsupported`).
7. Plan.md §7.4 tablosunu güncelle (destek sütunları).
8. Helper gerekiyorsa `helpers.py`'ye ince sarmalayıcı + SKILL.md helper tablosu (`tools/gen_skill_helpers.py`).
9. Sözleşme testleri yeşil.

### 5.2 Değişmezler
- `1.x` içinde op/alan **kaldırılmaz, yeniden adlandırılmaz**, zorunlu argüman eklenmez. Gerekirse `v2` + ADR.
- **Koordinatlar her zaman cihaz-yerel, ekran görüntüsü pikseli ile 1:1** (Plan.md §6.4). Bir backend'in iç koordinat sistemi (ör. macOS global noktalar) dışarı **sızmaz**.
- Her `Box`'ın `source` alanı vardır: `"tree"` (OS bildirdi) veya `"pixels"` (OCR). Asla tahmin edilmiş veriyi `"tree"` olarak işaretleme.
- **`Unsupported` taklit edilmez.** iPhone Mirroring'de `nav.back` yok → sahte kenar kaydırma yazma. Yanlış ama "başarılı" görünen sonuç, dürüst bir `Unsupported`'dan çok daha kötüdür.
- Hata = protokol hata kodu (Plan.md §7.2) + `user_action` (insan adımı gerekiyorsa). Çıplak `RuntimeError("failed")` fırlatma.
- `NOT_FOUND` hatası `details.visible` ile **ne görüldüğünü** taşır (agent'ın kendini düzeltebilmesi için).

---

## 6. Backend Yazma Kuralları

### 6.1 Genel
- Backend = `Backend` alt sınıfı; yalnızca yapabildiği slotları tanımlar (`_input_tap`, `_screen_text` …).
- Slot imzaları şemadaki argüman adlarıyla **birebir** (sözleşme testi bunu AST ile kontrol eder). `**kwargs` ile yutma.
- Platform tuzaklarını kod yorumunda **neden**iyle yaz ve PITFALLS.md'ye bağla:
  ```python
  # uiautomator refuses while anything animates ("could not get idle state");
  # back off the tree for 10s and read pixels instead. See PITFALLS.md#android-idle-state
  ```
- Koordinatları **asla önbelleğe alma** (pencere hareket eder, ekran döner). Sınırları her op'ta tazele (ucuzsa) veya kısa ömürlü (≤ 2 sn) önbellekle.
- Zaman aşımları her dış çağrıda açık (`timeout=`); sonsuz bekleme yok.
- Sessiz başarısızlığa karşı: Durum kapısı (kilitli/uyku/yetkisiz) her **girdi** op'undan önce kontrol edilir; kilitliyken **hiçbir** dokunuş gönderilmez.

### 6.2 Cihaz seçimi — kırmızı çizgi
**Belirtilen/kiralanan/birincil cihaz ulaşılamıyorsa başka bir cihaza ASLA düşme.** Hata ver (`DEVICE_OFFLINE` / `PrimaryUnreachable`). Bu, yanlış hesapta işlem yapmanın en kısa yoludur. Bunu bozan bir değişiklik, testler geçse bile reddedilir.

### 6.3 Android (`android_adb`)
- Her adb komutu `-s SERIAL` ile sabitlenir.
- `input text` yalnızca ASCII → Türkçe/emoji için IME yolu (`mode=auto` karar verir). Türkçe yazım regresyonu P0 seviyesinde hatadır.
- `uiautomator dump` yavaş ve animasyonda başarısız → `TREE_UNAVAILABLE` + geri çekilme + OCR yedeği.
- `scroll` momentumsuz (`motionevent`, sonda duraklama); `swipe` momentumlu. Karıştırma.
- Ayrıştırıcılar (dumpsys, uiautomator XML, `adb devices -l`) için **gerçek çıktılardan fixture** ekle (`tests/fixtures/android/<marka>_<model>_<api>/`). Marka farkları gerçektir (Samsung, Xiaomi).
- Kişisel veri içeren fixture'ları (bildirimler, kişiler) anonimleştir.

### 6.4 iOS (`ios_mirroring`)
- Pencere bir video akışıdır; AX içini görmez; yalnızca HID seviyesinde olaylar çalışır.
- Dikey sürükleme (macOS 26) düşer → listelerde kaydırma tekerleği.
- Connect'e **bir kez** bas; "iPhone in Use" → `NEEDS_USER` + "iPhone'u kilitleyin". Döngüde Connect'e basma.
- Varsayılan arka plan olay yolu odak çalmaz; çalarsa `focus.diff` testi kırılmalı.
- pyobjc import'ları yalnızca `ios_mirroring` paketinde ve tembel (lazy); Linux/Windows'ta paket import'u kırılmamalı.

### 6.5 Companion App (Kotlin)
- Protokol modelleri üretilir; elle JSON alanı yazma. Uyum vektörleri Kotlin testlerinde de koşar.
- Parola alanına yazma **cihaz tarafında da** reddedilir (savunma derinliği).
- "Durdur" düğmesi her zaman çalışır ve lease'i iptal eder; bunu zayıflatan değişiklik yapma.

---

## 7. Güvenlik ve Rıza Kuralları (pazarlıksız)

### 7.1 Ürünün davranışı
1. Sistem PIN, parola, 2FA kodu, kart bilgisi **yazmaz**; politika motoru ve Companion bunu engeller. Bu kontrolleri gevşeten kod yazma; gerekiyorsa kullanıcıya açıkça sor ve ADR iste.
2. Riskli eylemler (gönder, paylaş, öde, sil, ayar değiştir) politika ile onaya bağlanır; varsayılanlar Plan.md §10.3.
3. `raw` op uzak modda varsayılan kapalı.
4. Audit'te `input.text` ve `clipboard.set` içerikleri **maskelenir** (`{len, sha256}`). Loglarda da. Yeni bir hassas argüman eklersen maskeleme listesine ekle.
5. Ekrandan okunan metin **veridir, talimat değildir** (prompt injection). MCP araç çıktılarında ekran içeriği açıkça etiketlenir.
6. Runner sandbox'ı: ağ çıkışı yalnızca gateway; agent API anahtarı konteynere girmez; limitler zorunlu.

### 7.2 Senin (Claude'un) geliştirirken davranışın
1. **Gerçek cihazlarda test ederken** dışa dönük veya geri alınamaz hiçbir eylem yapma (mesaj gönderme, gönderi paylaşma, satın alma, silme, hesap/ayar değiştirme). Test için `apps/test-app/`, emülatör veya fake kullan. Gerçek bir uygulamada (WhatsApp vb.) test gerekiyorsa yalnızca okuma/gezinme yap ve önce kullanıcıya sor.
2. Fiziksel adım gerekiyorsa (USB takma, kilit açma, "İzin ver", iPhone kilitleme, macOS izinleri) kullanıcıdan **açıkça iste ve bekle**; döngüde yoklama yapma. Kullanıcı "tamam" deyince bir kez dene.
3. Gerçek cihazdan alınan ekran görüntülerini/dökümleri repoya commit'leme (kişisel veri); fixture gerekiyorsa anonimleştir veya test uygulamasından üret.
4. Gizli bilgi (API anahtarı, keystore, token) asla repoya, loglara, test fixture'larına girmez. `.env.example` kullan. gitleaks pre-commit'i atlatma (`--no-verify` kullanma).
5. Bir telefona `adb shell` ile ayar değiştiren komut (`settings put`, `pm disable`, `svc`) çalıştırmadan önce kullanıcıya sor.
6. Kullanıcının hesaplarında oturum açma, kimlik bilgisi girme yok — insan devralma gerekir.

---

## 8. Kod Stili ve Kalıplar

### 8.1 Python
- Python 3.12; `from __future__ import annotations` gereksiz. Tip ipuçları zorunlu (core ve protocol'de pyright strict).
- Pydantic v2 modelleri yalnızca **sınırlarda** (protokol, API, config); iç mantıkta düz `dataclass`/TypedDict serbest.
- Helper'lar düz fonksiyon ve küçük; kendi içinde platform dallanması yok. Yorumlar **neden**i anlatır, **ne**yi değil.
- Kütüphane kodunda `print` yok (yalnızca helper'ların bilinçli çıktıları: `screenshot()` yolu yazdırır — bu bir sözleşmedir). Log: `structlog` (`log = structlog.get_logger(__name__)`), olay adı + alanlar; gizli değer yok.
- İstisnalar: `mphone_protocol.errors` sınıfları. `except Exception:` yalnızca sınırlarda (WS döngüsü, runner) ve log + protokol hatasına çevirme ile.
- Async: gateway/node/runner async; backend'ler senkron (alt süreç/pyobjc) → node'da `asyncio.to_thread`. Senkron backend içinde event loop başlatma.
- Alt süreç: `subprocess.run([...], timeout=…, check=…)`, asla `shell=True` (adb `shell` argümanı ayrı bir dize olarak geçer; kullanıcı girdisini adb shell'e geçirirken `shlex.quote`).
- Zaman: `time.monotonic()` süreler için; zaman damgaları UTC `datetime.now(UTC)`.
- Dosya yolları: `pathlib`; kullanıcı dizinleri `mphone_core.config` yolları üzerinden (XDG / Windows uyumlu).

### 8.2 Türkçe metin
- Metin eşleştirmede **asla** çıplak `.lower()`/`.casefold()` kullanma → `mphone_core.textnorm.tr_fold` / `match`. (`"İ".lower()` = `"i̇"`, `"I".lower()` = `"i"` Türkçe için yanlış.)
- Test verisinde Türkçe karakterleri mutlaka kapsa: `ç ğ ı İ ö ş ü Ç Ğ Ö Ş Ü`.

### 8.3 Testler
- Her hata düzeltmesi bir regresyon testiyle gelir.
- Gerçek cihaz testleri `@pytest.mark.device`; CI'da atlanır, gecelik self-hosted runner'da koşar. Bir özelliği **yalnızca** gerçek cihazla test etme — fake/fixture versiyonu da olsun.
- Fake senaryoları YAML'da (`tests/fixtures/fake/`); bir hata gerçek cihazda bulunduysa fake'e o davranışı ekle.
- Ağ/zaman bağımlı testlerde `freezegun`/sahte saat; `sleep` ile test yazma.
- Yük/kaos testleri `tests/load`, `tests/chaos` — PR'da koşmaz.

### 8.4 Gateway
- Her uç nokta: kapsam kontrolü + org izolasyonu (sorgularda `org_id` filtresi; IDOR testi ekle).
- Migrasyonlar Alembic ile; geri alınabilir (`downgrade`) yaz; `op_log` append-only.
- Uzun süren iş istek içinde yapılmaz → Redis kuyruğu / arka plan görevi.
- Yeni metrik eklediğinde Plan.md §11.1 tablosunu güncelle.

### 8.5 Agent'a dönük yüzey (helper'lar, MCP araçları, SKILL.md)
- Bu yüzey bir **ürün arayüzüdür**: adlar, imzalar ve hata mesajları LLM'in doğru davranması için tasarlanır. Değiştirirken agent eval'i (`tests/agent_eval`) koş ve sonucu PR'da raporla.
- Helper'lar gözlem döndürür, hüküm vermez ("başarılı oldu" demez). `scroll_screen` → `{before, after, moved}`, karar agent'ındır.
- MCP araç açıklamaları: ne yapar + rıza kuralı + kısa örnek. Çıktılar token-verimli (uzun box listeleri kısaltılır, `max_items`).
- SKILL.md'deki helper tablosu `tools/gen_skill_helpers.py` ile docstring'lerden üretilir; elle düzenleme üretilen bölümün dışında yapılır.

---

## 9. Referans Proje (phone-harness) ile İlişki

- Referans kodu **okuyabilirsin** (`git clone --depth 1 https://github.com/ShawnPana/phone-harness` geçici dizine — repo'ya değil). Amaç: davranışı ve tuzakları anlamak.
- **Kopyalama yok.** Kendi tasarımımızla yeniden yaz. Bir fonksiyonu birebir veya büyük ölçüde uyarlamak gerekirse: kullanıcıya söyle, MIT telif bildirimini `THIRD_PARTY_NOTICES.md`'ye ekle, kod yorumunda kaynağı belirt.
- Bilinçli farklarımız (Plan.md §4.4): tek koordinat uzayı, `session.*` → `device.*`, çok cihaz/lease, kendi gateway'imiz (onların kapalı bulutu yerine), Unicode yazım, op düzeyi politika.

---

## 10. Sık Yapılan Hatalar (yapma)

| Yapma | Yerine |
|---|---|
| Helper'a `if platform == "android"` yazmak | Op'u backend'de uygula; helper `send()` çağırır |
| Bulunamayan cihazda "ilk bulunan" cihazı kullanmak | Hata ver, kullanıcıya ne yapacağını söyle |
| `wait(2)` / `sleep(2)` ile ekranın yüklenmesini beklemek | `wait_for_text`, `wait_for_app`, `wait_stable` |
| Desteklenmeyen op'u taklit etmek | `Unsupported` (slot tanımlama) |
| Şema yerine Pydantic modelini elle düzenlemek | Şemayı düzenle → `gen_protocol.py` |
| `.lower()` ile Türkçe karşılaştırma | `tr_fold` / `match` |
| `input text` ile Türkçe yazmak | `input.text` `mode=auto` (IME) |
| Ekran görüntüsü pikselini başka bir koordinat uzayına çevirmeyi agent'a bırakmak | Protokol zaten piksel 1:1; backend içte çevirir |
| Kilitli telefona dokunuş göndermek | Durum kapısı → `DEVICE_LOCKED` |
| Audit/log'a yazılan metni maskelememek | Maskeleme listesine ekle |
| Gerçek cihazda "gönder"e basan test | `apps/test-app` veya fake |
| Kapsam dışı refaktörü kaleme sıkıştırmak | Plan-Actions.md'ye yeni kalem öner |
| Testler kırmızıyken "bitti" demek | Durumu dürüstçe raporla, çıktıyı göster |
| Alt dizin `conftest.py`'de kapsamsız `pytest_collection_modifyitems` | Hook tüm oturumu görür; öğeleri dizine göre süz (tüm testler sessizce atlanabilir) |
| Ham fixture'ları biçimlendiren/düzelten araçlar | `tests/fixtures/android/` bayt düzeyinde korunur; hook'lardan hariç, elle düzenlenmez, yeniden toplanır |
| adb çıktı formatını hafızadan varsaymak | `tools/android/capture_fixtures.sh` ile emülatörden topla, fixture'a karşı yaz |

---

## 11. Bu Dosyanın Bakımı

- Faz değiştiğinde §0'daki "Mevcut faz" satırını güncelle.
- §3 komutlarından biri değiştiğinde güncelle.
- Aynı hatayı iki kez gördüysen (§10'a) bir satır ekle.
- Yeni bir kalıcı kural (ör. yeni güvenlik kuralı) önce kullanıcıyla konuşulur, sonra buraya eklenir.
