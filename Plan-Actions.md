# Milyonus Phone Control — Eylem Planı (Plan-Actions.md)

> **Durum:** Taslak v1.0 · **Tarih:** 2026-10-14
> **Bağlı dokümanlar:** [Plan.md](Plan.md) (neyi, neden) · [Phases.md](Phases.md) (ne zaman, hangi kapıyla) · [CLAUDE.md](CLAUDE.md) (nasıl çalışıyoruz)
>
> Bu doküman, planı **uygulanabilir iş kalemlerine** böler. Her kalemin bir kimliği (`A<faz>.<no>`), açıklaması, somut çıktıları (dosya/komut), kabul kriteri, bağımlılıkları, tahmini süresi ve sahibi vardır. Kalemler bir PR'a (veya küçük bir PR dizisine) karşılık gelecek büyüklükte tutulmuştur.

---

## İçindekiler

1. [Nasıl Kullanılır](#1-nasıl-kullanılır)
2. [İnsan Gerektiren Eylemler (H-xx)](#2-insan-gerektiren-eylemler-h-xx)
3. [P0 — Temel ve Kararlar](#p0--temel-ve-kararlar)
4. [P1 — Protokol, Çekirdek, Fake](#p1--protokol-çekirdek-fake)
5. [P2 — Android ADB](#p2--android-adb)
6. [P3 — Agent Arayüzleri → MVP](#p3--agent-arayüzleri--mvp)
7. [P4 — iPhone Mirroring](#p4--iphone-mirroring)
8. [P5 — Uzaktan Kontrol](#p5--uzaktan-kontrol)
9. [P6 — Canlı / Onay / Devralma / Dashboard](#p6--canlı--onay--devralma--dashboard)
10. [P7 — Android Companion App](#p7--android-companion-app)
11. [P8 — iOS WDA](#p8--ios-wda)
12. [P9 — Sertleştirme → GA](#p9--sertleştirme--ga)
13. [Kalem Şablonu ve Claude'a Görev Verme](#13-kalem-şablonu-ve-claudea-görev-verme)
14. [İlk 10 İş Günü — Somut Başlangıç Listesi](#14-ilk-10-iş-günü--somut-başlangıç-listesi)

---

## 1. Nasıl Kullanılır

**Durum etiketleri:** `☐ Yapılacak` · `◐ Devam ediyor` · `☑ Bitti` · `⏸ Bloklu` · `✕ İptal`

**Sahip kodları:**
- **C** — Claude (Claude Code oturumu) uygular; insan PR'ı inceler.
- **İ** — İnsan yapmalı (fiziksel cihaz, hesap, satın alma, karar, hukuki konu).
- **C+İ** — Claude uygular, insan fiziksel doğrulama / karar ile katılır.

**Tahmin birimi:** ideal iş günü (g). 0.5 g = yarım gün.

**Kurallar:**
1. Bir kalem başlamadan önce bağımlılıkları `☑` olmalı (veya açıkça mock'lanmalı).
2. Her kalem bir PR; PR açıklamasında kalem kimliği (`A2.07`) yazılır.
3. "Kabul" sütunu kalemin Definition of Done'ıdır; test veya ölçümle kanıtlanır.
4. Kapsam dışına taşan keşifler yeni kalem olarak eklenir (son numaradan devam), mevcut kalem şişirilmez.
5. Durumlar haftalık güncellenir (Phases.md §7).

---

## 2. İnsan Gerektiren Eylemler (H-xx)

Claude'un yapamayacağı veya yapmaması gereken işler. Fazların zamanında başlaması bunlara bağlıdır.

| ID | Eylem | Gerektiği faz | Bloke ettiği kalemler | Durum |
|---|---|---|---|---|
| H-01 | Plan.md §16 Q1–Q13 sorularını cevapla (özellikle Q1 Milyonus Agent yığını, Q2 hangi telefonlar, Q3 platform önceliği) | P0 | A0.06, A3.09 | ☑ kullanıcı kararları Claude'a bıraktı; docs/decisions.md |
| H-02 | GitHub repo (public: ayazelrico/Milyonus-Phone-Control), branch koruma kuralları (main'e doğrudan push yok, 1 onay, CI zorunlu) | P0 | A0.01 | ☑ |
| H-03 | Donanım satın alma: 1 Linux mini PC, 1 powered USB hub (≥ 7 port, port başına ≥ 2.4 A), 4 Android (Samsung A serisi, Xiaomi/Redmi, Pixel, 1 eski API 28–30), kaliteli kısa USB-C kablolar | P0 | A2.xx gerçek cihaz testleri, A5.xx | ☐ |
| H-04 | Mac mini (M2/M4, 16 GB) + 1 iPhone (iOS 18+) + aynı Apple ID ile iPhone Mirroring eşleştirmesi | P0–P4 | A4.xx | ☐ |
| H-05 | Android telefonları hazırlık checklist'ine göre hazırla (Geliştirici seçenekleri, USB hata ayıklama, "İzin ver" + "Her zaman izin ver") | P2 | A2.12, A2.15 | ☐ |
| H-06 | Mac'te Erişilebilirlik + Ekran Kaydı izinlerini ver (terminal/mphone), iPhone Mirroring'i ilk kez eşleştir | P4 | A4.02+ | ☐ |
| H-07 | KVKK / hukuk görüşmesi: kontrol edilecek telefonların sahipliği, aydınlatma metni, saklama süreleri | P0 başlat, P7 öncesi bitir | A9.07, M4 | ☐ |
| H-08 | Staging için bulut hesabı/VM + alan adı (ör. `phone-staging.milyonus.com`) + DNS | P5 | A5.20 | ☐ |
| H-09 | Slack çalışma alanında onay bildirimleri için kanal + gelen webhook / Slack uygulaması | P6 | A6.06 | ☐ |
| H-10 | SSO (OIDC) istemci kaydı (Google Workspace / Azure AD) | P6 | A6.09 | ☐ |
| H-11 | Android imzalama anahtarı (keystore) oluştur ve güvenli sakla (Companion APK) | P7 | A7.12 | ☐ |
| H-12 | Apple Developer Program üyeliği (ücretli) + cihaz UDID kaydı | P8 | A8.01 | ☐ |
| H-13 | Pentest sağlayıcısı seçimi ve sözleşme | P9 | A9.04 | ☐ |
| H-14 | Prod bulut hesabı, yönetilen Postgres/Redis/S3, gizli bilgi yöneticisi | P9 | A9.09 | ☐ |
| H-15 | Operatörlerin belirlenmesi (onay verecek kişiler), nöbet/mesai kararı | P6 | A6.xx kullanılabilirlik testi | ☐ |

---

## P0 — Temel ve Kararlar

**Hedef hafta:** 1 · **Toplam tahmin:** ~5.5 g · Detay: [Phases.md#P0](Phases.md#p0--temel-ve-kararlar)

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A0.01 | Repo iskeleti (uv workspace) | Kök `pyproject.toml` (`[tool.uv.workspace] members = ["packages/*"]`), Plan.md §18'deki dizinler; her paket için `pyproject.toml` + `src/<pkg>/__init__.py` + `py.typed`; `.gitignore`, `.editorconfig`, `README.md`, `LICENSE` (Apache-2.0, karar Q9), `THIRD_PARTY_NOTICES.md` | `uv sync` hatasız; `uv run python -c "import mphone_core, mphone_protocol"` çalışır | H-02 | 0.5 | C | ☑ |
| A0.02 | Kod kalitesi araçları | `ruff` (lint+format, `line-length=110`, kurallar: E,F,I,UP,B,SIM,RUF,S), `pyright` (strict: protocol, core; basic: diğerleri), `pytest` + `pytest-cov` + `pytest-asyncio`, `.pre-commit-config.yaml` (ruff, pyright, gitleaks, end-of-file, trailing-whitespace, conventional commit mesaj kontrolü) | `pre-commit run --all-files` temiz | A0.01 | 0.5 | C | ☑ |
| A0.03 | CI iş akışı | `.github/workflows/ci.yml`: matris {ubuntu, macos, windows} × py3.12; adımlar: uv kurulum + önbellek, `uv sync --frozen`, ruff, pyright, pytest (unit+contract), kapsam raporu artefaktı; PR'da zorunlu | Boş test seti ile 3 OS yeşil | A0.02 | 0.5 | C | ☑ (ilk CI koşusu: lint + 3 OS yeşil) |
| A0.04 | ADR'ler | `docs/adr/0001-python-core.md` … `0015-exec-plus-granular-tools.md` (Plan.md §14 tablosundan; şablon: Bağlam, Karar, Alternatifler, Sonuçlar, Durum) + `docs/adr/README.md` dizini | 15 ADR `Accepted` | — | 1 | C | ☑ |
| A0.05 | PITFALLS.md v0 | `docs/PITFALLS.md`: Plan.md §4.3'teki tüm dersler; her madde: Platform, Belirti, Neden, Çözüm, Test (henüz yoksa "TODO A2.xx") | Android ≥ 12, iOS ≥ 10, Uzak ≥ 2 madde | — | 0.5 | C | ☑ |
| A0.06 | Karar kaydı | `docs/decisions.md`: Q1–Q13, cevap, karar veren, tarih, etkilenen kalemler | Her soru cevaplı veya "varsayılan kabul" | H-01 | 0.5 | İ (C taslak) | ☑ |
| A0.07 | Cihaz hazırlık rehberi + envanter | `docs/runbooks/device-prep.md` (Android: geliştirici seçenekleri, USB hata ayıklama, animasyon ölçekleri 0.5x, "şarjda uyanık kal" (raf), otomatik güncelleme kapalı, MIUI ek adımları; iPhone: Mirroring eşleştirme, kilit davranışı); `docs/inventory.md` (cihaz, model, OS, seri hash, sahip, konum) | Rehber bir kişi tarafından bir telefonda uygulanıp doğrulandı | H-03 | 0.5 | C+İ | ◐ rehber + envanter hazır; telefonda doğrulama donanım bekliyor (H-03) |
| A0.08 | CLAUDE.md'nin repo'ya yerleşmesi ve doğrulanması | Bu repo'daki CLAUDE.md'nin komutlarının (uv, pytest, ruff) gerçekten çalıştığını kontrol, eksikleri düzelt | CLAUDE.md'deki her komut çalışır | A0.03 | 0.25 | C | ☑ |
| A0.09 | Referans proje çalışma notları | `docs/reference/phone-harness-notes.md`: modül haritası, op sözlüğü, helper imzaları, SKILL.md'deki çalışma yöntemi özeti, Hermes eklentisinin güvenlik kararları (Plan.md §4'ün genişletilmişi). **Kod kopyalanmaz.** | Ekip okudu (PR onayı) | — | 0.5 | C | ☑ |
| A0.10 | Sürüm ve değişiklik günlüğü düzeni | `CHANGELOG.md` (Keep a Changelog), `tools/bump_version.py` (tüm paketlerin sürümünü birlikte artırır), Conventional Commits rehberi | `uv run tools/bump_version.py 0.1.0` tüm paketleri günceller | A0.01 | 0.25 | C | ☑ |

---

## P1 — Protokol, Çekirdek, Fake

**Hedef hafta:** 2 · **Toplam tahmin:** ~7 g (2 kişiyle 1 hafta) · Detay: [Phases.md#P1](Phases.md#p1--protokol-çekirdek-ve-fake-backend)

### P1.a — Protokol

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A1.01 | Op şeması v1 | `packages/mphone-protocol/schema/ops.v1.json`: JSON Schema 2020-12; `$defs`: `Box`, `Node`, `Selector`, `Bounds`, `DeviceInfo`, `ErrorCode` (enum, Plan.md §7.2), `OpRequest`, `OpResult`; her op için `{name, args_schema, result_schema, default_timeout_ms, side_effect: none\|input\|nav\|apps\|device, description_tr, description_en}` (Plan.md §7.4) | Şema `jsonschema` meta-doğrulamasından geçer; Plan.md §7.4'teki tüm op'lar tanımlı (39) | A0.01 | 1.5 | C | ☑ |
| A1.02 | Kod üretici | `tools/gen_protocol.py`: şemadan `mphone_protocol/models.py` (Pydantic v2, `extra="ignore"` yanıtlar, `extra="forbid"` istekler), `ops.py` (`OP_NAMES`, `OP_SPECS`), `errors.py` (istisna sınıfları: `MphoneError` + kod başına alt sınıf; `Unsupported(MphoneError, RuntimeError)`), `docs/protocol.md`; ileride `apps/dashboard/src/protocol.ts` ve Kotlin (P7) | `uv run tools/gen_protocol.py --check` CI'da; üretilen dosyalar elle düzenlenmez (başlıkta uyarı) | A1.01 | 1 | C | ☑ |
| A1.03 | Protokol uyum vektörleri | `tests/fixtures/protocol_vectors/*.json`: her op için geçerli/geçersiz istek ve örnek sonuç; Python testleri bunları doğrular (P7'de Kotlin de kullanır) | Her op için ≥ 1 geçerli + 1 geçersiz vektör | A1.02 | 0.5 | C | ☑ |

### P1.b — Çekirdek

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A1.04 | `Backend` taban sınıfı | `mphone_core/transport.py`: `_slot()`, `send()` (doğrulama → middleware zinciri → slot), `supports()`, `ops()`, `close()`, bağlam yöneticisi; middleware arayüzü `Callable[[OpCall, Next], Any]`; yerleşik `TraceMiddleware` (helper/op izi) | Tanımsız slot → `Unsupported`; `ops()` yalnızca `OP_NAMES` içindekileri döner; geçersiz kw → `INVALID_ARGUMENT` | A1.02 | 0.75 | C | ☑ |
| A1.05 | `connect()` ve URI çözümleme | `mphone_core/connect.py`: Plan.md §8.1.2 sırası; URI ayrıştırıcı (`android:`, `ios-mirror:`, `ios-wda:`, `gw://`, `fake:`); backend kayıt defteri (entry point `mphone.backends`) — çekirdek backend paketlerini import etmeden çalışır | Bulunamayan cihaz → hata, asla yedeğe düşmez (test); URI tablo testleri | A1.04 | 0.5 | C | ☑ |
| A1.06 | Türkçe metin normalizasyonu | `mphone_core/textnorm.py`: `tr_fold(s)` (İ→i, I→ı, sonra lower; NFC), `strip_accents_tr(s)` (ç→c, ğ→g, ı→i, ö→o, ş→s, ü→u), `match(query, text, exact)` → skor (1: tam, 2: tr_fold eşit, 3: içerir, 4: aksansız içerir) | Hypothesis + tablo testleri (≥ 30 vaka, "İSTANBUL", "IĞDIR", "Çağrı", "ŞİŞLİ") | — | 0.5 | C | ☑ |
| A1.07 | Helper'lar — temel | `mphone_core/helpers.py`: `send, supports, ops, connect, ensure_device, connection_state, device_info, screen, screen_text, screenshot, find_text, tap_text, tap, long_press, tap_image_point, type_text, clear_text, press, open_app, current_app, list_apps, stop_app, home, back, recents, notifications_panel, ui, find_nodes, tap_ui, clipboard, set_clipboard, notifications, note` | Fake üzerinde her helper için ≥ 1 test; docstring'ler TR+EN kısa | A1.04, A1.06 | 1.25 | C | ☑ |
| A1.08 | Helper'lar — hareket ve bekleme | `swipe, scroll, scroll_screen, scroll_until, scroll_collect, wait_stable, wait_for_text, wait_for_app`; ekran imzası (metin kümesi hash'i) ile "ekran değişti mi"; `scroll_collect` `extract/key/end_after/on_progress` | `long_list_120` senaryosunda 120 öğe tekrarsız, `stop="reached-end"`; `max_scrolls` sınırı testli | A1.07 | 1 | C | ☑ |
| A1.09 | `request_human` / `request_approval` (yerel) | Yerel modda: stderr'e mesaj + stdin'den "devam/iptal" (TTY değilse `NEEDS_USER` hatası fırlat, MCP katmanı yakalar) | TTY ve TTY-dışı davranış testli | A1.07 | 0.25 | C | ☑ |
| A1.10 | Config + workspace | `mphone_core/config.py` (TOML, XDG, env override, kaynak raporlama), `mphone_core/workspace.py` (yol çözümleme, varsayılandan tohumlama, asla üzerine yazmama, helper'lardan sonra yükleme + çakışma uyarısı) | Mevcut workspace değiştirilmez (test); env override testleri | A1.04 | 0.5 | C | ☑ |
| A1.11 | OCR arayüzü | `mphone_core/ocr/__init__.py`: `OcrEngine` protokolü, `recognize(png, langs)`, motor kayıt defteri, `NullEngine`; box üretim yardımcıları (piksel kutusu → merkez) | Arayüz testleri; motorlar P2'de | A1.04 | 0.25 | C | ☑ |

### P1.c — Fake backend ve testler

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A1.12 | Fake backend motoru | `mphone_backends/fake/`: YAML senaryo yükleyici (ekranlar, box'lar, geçişler `on_tap/on_text/on_key/on_scroll`, uygulamalar, durum, kaydırılabilir listeler), Pillow ile PNG çizimi (box metinleri gerçekten çizilir → OCR testlerinde kullanılabilir), hata/gecikme enjeksiyonu, op kaydı (testlerde doğrulama için) | Tüm v1 op'ları `F` sütunu (Plan.md §7.4) | A1.04 | 1 | C | ☑ |
| A1.13 | Fake senaryolar | `mphone_backends/fake/scenarios/settings_about.yaml`, `notes_turkish.yaml`, `long_list_120.yaml`, `locked_phone.yaml`, `whatsapp_like.yaml` (sohbet listesi + mesaj alanı + Gönder düğmesi — politika testleri için) | 5 senaryo, her biri bir uçtan uca testte kullanılır | A1.12 | 0.5 | C | ☑ |
| A1.14 | Sözleşme testleri | `tests/contract/test_helpers_vs_backends.py` (AST: helper'ların `send("op", kw=…)` çağrıları ↔ her backend slot imzası), `test_ops_schema.py` (her backend'in `ops()` ⊆ şema; fake sonuçları sonuç şemasına uyar) | CI'da çalışır; kasıtlı bozulma testi kırılır | A1.07, A1.12 | 0.5 | C | ☑ |

---

## P2 — Android ADB

**Hedef hafta:** 3–4 · **Toplam tahmin:** ~11 g · Detay: [Phases.md#P2](Phases.md#p2--android-adb-backend-yerel)

### P2.a — adb altyapısı

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A2.01 | adb çalıştırıcı | `android_adb/adb.py`: adb ikilisini bul (config → PATH → bilinen yollar: Homebrew, Android SDK, Windows `%LOCALAPPDATA%`), `run(*args, serial, binary, timeout, check)`, stderr'den hata sınıflandırma (`unauthorized`, `offline`, `device not found`, `more than one device`) → protokol hataları; `exec-out` ikili okuma | Fixture'larla sınıflandırma testleri (≥ 10 gerçek hata metni) | A1.04 | 0.75 | C | ☑ |
| A2.02 | Cihaz keşfi ve seçimi | `android_adb/discovery.py`: `adb devices -l` ayrıştırma (transport: usb/wifi, model, durum), `adb mdns services` ayrıştırma, aynı telefonun çift listelenmesini serial ile birleştirme, `resolve()` (Plan.md §8.2.1 sırası), `PrimaryUnreachable`; `~/.mphone/android/phones.json` (bilinen telefonlar) | Primary ulaşılamazsa başka telefona düşmeme testi; USB > Wi-Fi testi; fixture'larla | A2.01 | 1 | C | ☑ |
| A2.03 | Durum kapısı | `android_adb/state.py`: `awake_locked()` (Android 9–15 farklılıkları: `mWakefulness`, `isKeyguardShowing`, `mDreamingLockscreen`, `dumpsys window policy`), 2 sn önbellek, uyandırma, `device.state`/`device.require`/`device.detail` | Kilitli fixture'da hiçbir `input` komutu çalışmaz (adb çağrı kaydıyla test) | A2.01 | 0.75 | C | ☑ |

### P2.b — Göz: yakalama, ağaç, OCR

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A2.04 | Ekran yakalama ve sınırlar | `screen.capture` (`exec-out screencap -p`, `max_side` küçültme, JPEG seçeneği), `screen.bounds` (`wm size` override'lı/fiziksel, `wm density`, rotasyon) | Görüntü boyutu = bounds; rotasyon testleri (fixture) | A2.01 | 0.5 | C | ☑ |
| A2.05 | Ağaç okuma ve dönüşüm | `tree` (`uiautomator dump --compressed /dev/tty` → olmazsa dosya + `cat`), XML ayrıştırma (`lxml` veya `xml.etree` güvenli), `Node` modeli, "could not get idle state" → `TREE_UNAVAILABLE` + 10 sn geri çekilme; `screen.text` = ağaç → box (görünür, boyut > 0, text ∪ content-desc, `clickable_ancestor`, `password`, `editable`, `focused`); `ui.find` seçici eşleme (Plan.md §7.5) | Samsung, Xiaomi, Pixel ağaç fixture'larıyla testler; `tr_fold` ile seçici | A2.01, A1.06 | 1.25 | C | ☑ |
| A2.06 | OCR motorları | `mphone_core/ocr/vision.py` (macOS, pyobjc Vision, `tr-TR,en-US`, accurate mod, piksel koordinatı → box), `mphone_core/ocr/rapid.py` (rapidocr-onnxruntime, latin modeli); `screen.text_pixels`; ağaç yoksa `screen.text` yedeği | `tests/fixtures/ocr/` korpusu v0 (≥ 50 Türkçe/İngilizce ekran görüntüsü + doğru metin) üzerinde karakter doğruluğu ≥ %95 (v0 eşik; GA'da %97) | A1.11, A2.04 | 1.25 | C+İ (İ: korpus için ekran görüntüsü toplama) | ◐ OCR arayüzü + yedek yol hazır; vision/rapidocr motorları ve Türkçe korpus bekliyor |

### P2.c — El: girdi, gezinme, uygulamalar

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A2.07 | Dokunma/jest op'ları | `input.tap`, `input.press`, `input.drag` (`motionevent` destek tespiti, önbellekli; yedek `input swipe`), `input.scroll` (momentumsuz: DOWN → MOVE adımları → 80 ms bekle → UP; `dy/dx` içerik uzayı → parmak yönü dönüşümü), `input.keys` (keyevent tablosu, tek tuş; kombinasyon → `UNSUPPORTED`) | Emülatörde: kaydırma her seferinde aynı mesafe (±%5), flick yok; komut kaydı testleri | A2.03 | 1 | C | ◐ birim testleri geçiyor; emülatör E2E doğrulaması bekleniyor |
| A2.08 | Unicode yazım (IME) | `input.text` `mode=auto/keystrokes/ime/paste`; ASCII güvenli yol (`input text` kaçış tablosu: boşluk `%s`, `& | ; < > ( ) $ \` ' " \\` kaçışları); IME yolu: ADBKeyboard (`am broadcast -a ADB_INPUT_B64 --es msg …`), mevcut IME'yi kaydet → geçici olarak ADBKeyboard → yaz → geri yükle; `input.clear` (`ADB_CLEAR_TEXT` veya CTRL+A+DEL) | Emülatörde 100 rastgele Türkçe cümle (`tests/fixtures/turkish_sentences.txt`) + emoji: yazılan = okunan (ağaçtan doğrulama) | A2.07 | 1 | C | ◐ birim testleri geçiyor; emülatör E2E doğrulaması bekleniyor |
| A2.09 | IME kurulum komutu | `mphone android ime install|status|uninstall`: APK'yı indir (sabit sürüm + SHA-256 doğrulama) veya repodaki derlenmiş APK; `adb install -r`; `ime enable`; lisans kontrolü ve `THIRD_PARTY_NOTICES.md`; **Yedek plan:** ADBKeyboard uygun değilse `apps/android-ime-mini/` (Kotlin, yalnızca broadcast→commitText) | Temiz emülatörde tek komutla kurulum + `doctor` yeşil | A2.08 | 0.5 | C | ☑ |
| A2.10 | Gezinme op'ları | `nav.home/back/recents` (KEYCODE), `nav.notifications` (`cmd statusbar expand-notifications`) | Emülatör E2E | A2.07 | 0.25 | C | ☑ |
| A2.11 | Uygulama op'ları | `apps.list` (+ etiket önbelleği: `pm list packages -3`, etiket için `dumpsys package <pkg>` / `cmd package dump` ayrıştırma, `~/.mphone/cache/android/<serial>/labels.json`), `apps.launch` (çözümleme sırası: tam paket → etiket tr_fold eşleşme → paket parçası; `cmd package resolve-activity --brief` + `am start -n`, yedek `monkey`; `fresh=True` → `am force-stop` önce), `apps.current` (`topResumedActivity`/`mResumedActivity`), `apps.stop`, `apps.install/uninstall`; eşleşme yoksa `NOT_FOUND` + öneriler | "WhatsApp", "whatsapp", "Ayarlar", "Settings", "com.android.settings", "chrome" çözülür; 5 belirsiz ad testi | A2.01, A1.06 | 1 | C | ☑ |
| A2.12 | Cihaz yardımcı op'ları | `device.info` (getprop'lar, `dumpsys battery`), `device.wake`, `device.keep_awake` (arka plan iş parçacığı / `mphone android awake --bg` ayrı süreç + pidfile), `clipboard.get/set` (Android sürümüne göre; desteklenmiyorsa `UNSUPPORTED`), `notifications.list` (`dumpsys notification --noredact` ayrıştırma), `files.push/pull`, `raw` | Gerçek cihazda manuel doğrulama + fixture testleri | A2.03, H-05 | 0.75 | C+İ | ◐ cihaz bilgisi, uyandırma, keep-awake, bildirim, dosya, raw hazır; pano adb'de dürüstçe Unsupported (Companion'da gelecek); gerçek cihaz doğrulaması bekliyor |

### P2.d — Araçlar, testler, doğrulama

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A2.13 | `mphone doctor android` | Merdiven (Plan.md §8.7): her adım `{ad, ok, ipucu}`; renkli çıktı + `--json`; `--write-test` Türkçe yazım testi | 6 hata senaryosu (adb yok, cihaz yok, yetkisiz, kilitli, IME yok, ağaç yok) için doğru ipucu (fixture/mocks) | A2.02–A2.09 | 0.5 | C | ☑ |
| A2.14 | `mphone android` alt komutları | `pair <code> [--host]` (mDNS `_adb-tls-pairing` keşfi), `connect`, `use <ad>` (primary), `ls`, `awake [--bg]`, `rest`, `ime …` | Wi-Fi eşleştirme gerçek cihazda doğrulandı | A2.02 | 0.5 | C+İ | ◐ devices/pair/use/ime/awake hazır; Wi-Fi eşleştirme gerçek cihazda doğrulanmadı |
| A2.15 | Emülatör E2E CI | `.github/workflows/e2e-emulator.yml`: `reactivecircus/android-emulator-runner` (API 30, 34; KVM'li ubuntu), AVD önbelleği, IME kurulumu, `tests/e2e_emulator/` (Ayarlar senaryosu, Türkçe not (Google Keep yoksa yerleşik bir uygulama — ör. Kişiler'de ad alanı veya kendi test APK'mız `apps/test-app/`), liste toplama, kilit tespiti `adb shell locksettings set-pin` ile) | PR'da hızlı set < 15 dk yeşil | A2.07–A2.11 | 1.25 | C | ◐ iş akışı ve testler yazıldı; ilk emülatör koşusu bekleniyor |
| A2.16 | Test uygulaması (opsiyonel ama önerilir) | `apps/test-app/`: basit Android uygulaması: metin alanı, parola alanı, 200 öğelik liste, "Gönder" düğmesi, animasyonlu ekran (idle sorunu), `FLAG_SECURE` ekran — deterministik E2E için | APK CI'da derlenir ve E2E'de kullanılır | — | 1 | C | ☑ (ayrı uygulama yerine IME debug APK'sındaki test ekranı) |
| A2.17 | Gerçek cihaz doğrulaması + cihaz matrisi | 2+ marka gerçek telefonda E2E setini manuel/yarı otomatik koş; `docs/device-matrix.md` (marka, model, Android, op bazında ✓/✗/not, gecikmeler) | Phases.md P2 çıkış kriterleri (≥ 19/20, gecikme hedefleri) | A2.15, H-05 | 1 | C+İ | ⏸ gerçek telefon bekliyor (H-03, H-05) |
| A2.18 | PITFALLS.md Android güncellemesi | Bu fazda keşfedilen her tuzak; her madde test veya kod yorumuna bağlı | ≥ 15 madde | A2.17 | 0.25 | C | ☑ |

---

## P3 — Agent Arayüzleri → MVP

**Hedef hafta:** 5 · **Toplam tahmin:** ~7 g · Detay: [Phases.md#P3](Phases.md#p3--agent-arayüzleri-cli-skill-mcp--mvp)

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A3.01 | `mphone run` | `packages/mphone-cli/src/mphone_cli/run.py`: stdin/dosya/`-c` kodu; helper'ları global isim alanına bağla; workspace yükle; `# task:/# step:` kontrolü (uyarı); zaman aşımı (alt süreçte çalıştırma, `--timeout`); stdout kuyruğu 50 KB; ortam temizleme (`*_API_KEY`, `*_TOKEN`, `*_SECRET`, `*_PASSWORD`); çıkış kodları (0 ok, 1 script hatası, 2 cihaz/ön koşul hatası, 3 politika/onay, 124 zaman aşımı); hata çıktısı: son 20 satır traceback + protokol hatası ise `user_action` | Fake ve emülatörde 15 test (zaman aşımı, büyük çıktı, istisna, politika) | A1.07, A2.xx | 1 | C | ☐ |
| A3.02 | Yerel izleme + audit | Helper çağrı izi (`helper, args (300 kar.), duration, error`) ve op izi → `~/.mphone/runs/<run_id>/trace.jsonl`; günlük audit `~/.mphone/audit/YYYY-MM-DD.jsonl` (`input.text` içeriği maskeli: uzunluk + sha256) | Parola alanına yazılan metin hiçbir dosyada görünmez (test) | A3.01 | 0.5 | C | ☐ |
| A3.03 | Yerel lease (dosya kilidi) | `mphone_core/locallease.py`: `~/.mphone/locks/<device_key>.lock` (`fcntl`/`msvcrt`), sahip bilgisi (pid, agent adı, amaç, başlangıç), ölü süreç kilidini temizleme, TTL | İki süreç testi: ikincisi `LEASE_CONFLICT` + sahip bilgisi | A1.05 | 0.5 | C | ☐ |
| A3.04 | Yerel politika motoru | `mphone_core/policy/`: YAML yükleyici + şema, kural değerlendirici (op, app_in, target_text_any, target_field.password, text_matches, screen_contains_any, mode, trust_level), hedef box çözümleme (`(x,y)` → en küçük kapsayan box + tıklanabilir ata, önbellekli `screen.text`), karar: allow/deny/approve; yerel "approve" → `request_approval` (TTY) veya MCP onayı; **aynı motor P5/P6'da Gateway'de kullanılır** | `whatsapp_like` fake senaryosunda: parola alanı yazımı deny, "Gönder" approve, arama alanı allow; 20 kural testi | A1.07, A1.13 | 1.25 | C | ☐ |
| A3.05 | MCP sunucusu (stdio) | `packages/mphone-mcp/`: resmi `mcp` SDK (FastMCP); araçlar (Phases.md P3 listesi) — her araç ince: lease kontrolü → helper/runner çağrısı → çıktıyı MCP içeriğine (text + image) dönüştür; `phone_exec` alt süreçte `mphone run` mantığıyla; görüntüler JPEG `max_side=1280`, en fazla 4 ek; kaynaklar `mphone://skill`, `mphone://protocol`; istem `phone_task`; araç açıklamalarında rıza kuralları | MCP Inspector ile tüm araçlar çağrılabilir; fake üzerinde araç başına test (`mcp` SDK test istemcisi) | A3.01, A3.03, A3.04 | 1.5 | C | ☐ |
| A3.06 | SKILL.md (TR + EN) | `skills/phone-control/SKILL.md`: Plan.md §8.11 bölümleri; helper tablosu (imzalarla; `tools/gen_skill_helpers.py` ile helper docstring'lerinden üretilen bölüm — elle yazılan yöntem bölümleriyle birleşir); hata kodu → agent davranışı tablosu; platform bölümleri (Android tam; iOS/Companion yer tutucu); örnek görev script'leri | Agent eval'de skill ile/skill'siz karşılaştırma: skill ile başarı ≥ +%15 | A3.05 | 1 | C | ☐ |
| A3.07 | Varsayılan agent workspace | `agent-workspace/agent_helpers.py`: `tap_icon` (iOS için P4'te doldurulur), `dismiss_common_dialogs()` (Türkçe/İngilizce "İzin ver/Allow", "Tamam/OK", "Şimdi değil/Not now" — **yalnızca izin diyalogları için değil, rıza gerektiren diyaloglarda kullanılmaz** notuyla), `read_list_titles()` örneği | Yükleme testi | A1.10 | 0.25 | C | ☐ |
| A3.08 | CLI tamamlama | `mphone skill`, `mphone mcp`, `mphone devices`, `mphone config …`, `mphone version`; `--json` çıktıları; yardım metinleri TR/EN (`MPHONE_LANG`) | `mphone --help` tüm komutları listeler; komut başına duman testi | A3.01 | 0.5 | C | ☐ |
| A3.09 | Milyonus Agent entegrasyonu | `docs/integration/milyonus-agent.md`: MCP config (stdio komutu, env), sistem istemi eki (skill'i ne zaman kullan), araç izin önerileri; Q1'e göre: (a) MCP doğrudan, veya (b) köprü: agent'ın araç sistemine tek `phone_exec` aracı ekleyen ince adaptör (`integrations/milyonus/`); canlı entegrasyon oturumu | Milyonus Agent'tan en az 1 uçtan uca görev başarıyla | A3.05, H-01 | 1 | C+İ | ☐ |
| A3.10 | Agent eval harness v0 | `tests/agent_eval/`: görev tanımları YAML (`prompt`, `device_scenario`, `success_check` (Python predikat: son ekran / fake durumu / cihazdan okunan değer), `max_steps`); koşucu: bir LLM agent'ı (Claude API, model yapılandırılabilir) MCP üzerinden çalıştırır; rapor: başarı, adım, süre, token, hata türleri (Markdown + JSON) | 10 görev, fake + emülatör; ilk rapor `docs/eval/2026-Wxx.md` | A3.05, A3.06 | 1.25 | C | ☐ |
| A3.11 | Paketleme ve kurulum | Wheel'ler, `mphone` meta-paketi (extras: `[ios]`, `[ocr]`, `[node]`, `[gateway]`); GitHub Releases'a wheel yayını (`release.yml`, etiketle tetiklenir; PyPI ad uygunluğu sonrası); `uv tool install` talimatı; kurulum süresi ölçümü | Temiz makinede kurulum → ilk görev < 15 dk | A3.08 | 0.5 | C+İ | ☐ |
| A3.12 | M1 faz kapısı | Demo kaydı, kontrol listesi, `docs/phase-gates/P3.md` | Phases.md P3 çıkış kriterleri | hepsi | 0.25 | İ | ☐ |

---

## P4 — iPhone Mirroring

**Hedef hafta:** 6–7 · **Toplam tahmin:** ~9 g · Detay: [Phases.md#P4](Phases.md#p4--iphone-mirroring-backend)

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A4.01 | Pencere bulma ve geometri | `ios_mirroring/window.py`: `CGWindowListCopyWindowInfo` ile pencere (sahip adı + bundle `com.apple.ScreenContinuity`), ekran üstü/dışı, çerçeve; içerik alanı (başlık çubuğu/kenar kırpma) hesaplama; Retina ölçeği | Pencere taşınınca/yeniden boyutlanınca doğru içerik alanı (manuel + birim test) | P1, H-04 | 0.75 | C+İ | ☐ |
| A4.02 | Yakalama | `capture.py`: pencere kimliğiyle `CGWindowListCreateImage` (öne almadan), kırpma, PNG/JPEG; boş/siyah kare tespiti → "Ekran Kaydı izni" ipucu | Arka planda (başka pencere üstteyken) yakalama çalışır | A4.01, H-06 | 0.5 | C+İ | ☐ |
| A4.03 | Koordinat dönüşümü | `coords.py`: cihaz-yerel piksel (yakalanan görüntü) ↔ global macOS noktası; her op'ta taze geometri; `screen.bounds` = görüntü boyutu | Özellik tabanlı test (gidiş-dönüş hata < 1 px); gerçek cihazda köşe dokunuşları | A4.01 | 0.5 | C | ☐ |
| A4.04 | Olay gönderimi | `events_bg.py` (SkyLight özel API ile pencere kimliğine fare/klavye olayı; ctypes/pyobjc köprüsü), `events_fg.py` (öne al + CGEvent), seçim `MPHONE_IOS_BACKGROUND`; tap, press, drag (yatay), scroll (tekerlek, kısa öne alma + odak iadesi), keys (kombinasyon: cmd/shift/opt/ctrl), paste (pano kaydet → yaz → Cmd+V → geri yükle), keystrokes | `focus.diff`: arka plan modunda `stole_focus=false` (tap/type); scroll'da `raised` kısa ve geri alınmış | A4.03 | 2 | C+İ | ☐ |
| A4.05 | Durum makinesi | `state.py`: `not-running/launching/interstitial(*)/ready`; AX ile pencere içi etiket/düğme okuma; Connect'e tek basış; "iPhone in Use"/"Timed Out"/"Mac Locked"/kimlik doğrulama → `NEEDS_USER` + Türkçe `user_action`; AX gözlemcisi ile hızlı tespit (≤ 3 sn) | Her interstitial türü için gerçek veya kaydedilmiş AX fixture'ı ile test | A4.01 | 1.25 | C+İ | ☐ |
| A4.06 | Op'lar | `nav.home` (Cmd+1), `nav.recents` (Cmd+2), `apps.launch` (Spotlight Cmd+3 + paste + Enter + `wait_stable`), `screen.text` (Vision tr-TR), `nav.back/apps.current/apps.list/tree` → Unsupported; `device.*` | Sözleşme testleri (macOS CI'da pyobjc ile import) | A4.02–A4.05 | 0.75 | C | ☐ |
| A4.07 | `doctor ios` | İzinler (AX: `AXIsProcessTrusted`, Ekran Kaydı: deneme yakalama), uygulama var mı, pencere, durum; ipuçları + Ayarlar derin bağlantıları | 4 hata senaryosu | A4.05 | 0.5 | C | ☐ |
| A4.08 | `tap_icon` ve iOS helper'ları | Workspace `tap_icon(label)`: etiket box'ından ~35 pt (→ piksel: `35 * scale`) yukarı; doğrulama notu | Hava Durumu, Notlar, Ayarlar ikonları gerçek cihazda açılır | A4.06 | 0.25 | C+İ | ☐ |
| A4.09 | Gerçek cihaz test seti + self-hosted Mac runner | `tests/e2e_device/ios_mirroring/`; gecelik iş akışı (self-hosted Mac); 20 tekrar raporu | Phases.md P4 çıkış kriterleri | A4.06, H-04 | 1 | C+İ | ☐ |
| A4.10 | SKILL.md iPhone bölümü + PITFALLS iOS | Koordinatlar artık tek uzay; scroll vs swipe (dikey swipe çalışmaz); ana ekran etiketleri; paste vs keystrokes; Connect/kilit kuralları | İnceleme | A4.09 | 0.25 | C | ☐ |

---

## P5 — Uzaktan Kontrol

**Hedef hafta:** 6–8 · **Toplam tahmin:** ~24 g (3 hafta, 1.5–2 kişi) · Detay: [Phases.md#P5](Phases.md#p5--uzaktan-kontrol-node--gateway--runner)

### P5.a — Gateway temeli

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A5.01 | Gateway iskeleti | `packages/mphone-gateway/`: FastAPI app factory, ayarlar (`pydantic-settings`), async SQLAlchemy oturumu, Redis istemcisi, S3 istemcisi (`aioboto3`), `structlog`, OTel enstrümantasyonu, `/healthz`, `/readyz`, `/metrics`, hata işleyici (protokol hata zarfı), OpenAPI | `docker compose up` ile ayağa kalkar; `/readyz` DB+Redis+S3 kontrol eder | A1.02 | 1 | C | ☐ |
| A5.02 | Veri modeli + migrasyonlar | SQLAlchemy modelleri (Plan.md §8.4.2), Alembic ilk migrasyon, `op_log` aylık bölümleme, indeksler (`op_log(device_id, created_at)`, `op_log(run_id)`, `leases(device_id) WHERE status='active'` benzersiz kısmi indeks) | `alembic upgrade head` / `downgrade base` temiz; kısmi benzersiz indeks ikinci aktif lease'i engeller (test) | A5.01 | 1 | C | ☐ |
| A5.03 | Kimlik: API anahtarları + kapsamlar | Anahtar üretimi (`mph_live_<prefix>_<secret>`), hash'leme, doğrulama bağımlılığı, kapsam dekoratörü, `last_used_at` (toplu güncelleme), `mphone admin bootstrap` (ilk org + owner + admin anahtarı), `mphone admin agents create|keys create|revoke` | Yanlış kapsam → 403; iptal edilmiş anahtar → 401; anahtar düz metin olarak hiçbir yerde saklanmaz (test: DB dökümü) | A5.02 | 1 | C | ☐ |
| A5.04 | Node enrollment + kimlik | `POST /v1/enrollment-tokens` (admin), `POST /v1/nodes/enroll` (token + Ed25519 public key → node kaydı), node JWT verme/yenileme (imzalı nonce ile), token tek kullanım + 15 dk | Yeniden kullanılan token reddedilir; süresi dolmuş JWT ile WS reddedilir | A5.03 | 1 | C | ☐ |
| A5.05 | Registry | Cihaz upsert (`hello`/`device.update`), durum, ops, etiketler, `GET/PATCH /v1/devices`, filtreleme, `devices:read` kapsamı + `allowed_device_tags` kısıtı | Agent yalnızca izinli etiketli cihazları görür (test) | A5.02 | 0.75 | C | ☐ |

### P5.b — Node

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A5.06 | Node daemon çekirdeği | `packages/mphone-node/`: asyncio; `enroll` komutu (anahtar üretimi, kimlik dosyası 0600 / Keychain); WSS istemcisi (`websockets`), üstel geri çekilme + jitter, `hello/welcome`, ping/pong, mesaj şemaları (Plan.md §8.3 — `mphone_protocol` içinde `node_messages.py`) | Bağlantı kopup geri gelince `hello` yeniden gönderilir; 60 sn içinde toparlanır (toxiproxy testi) | A5.04 | 1.5 | C | ☐ |
| A5.07 | Keşif ve cihaz yöneticisi | Periyodik keşif (android_adb her cihaz için ayrı backend örneği `serial` sabit; ios_mirroring; P8'de wda), cihaz başına `asyncio.Queue` seri yürütücü (backend çağrıları `to_thread`), deadline/iptal, sağlık toplayıcı (pil, sıcaklık, durum) | 4 cihazla eşzamanlı op'lar birbirini bloklamaz; aynı cihaza 2 op sıralı yürür (test) | A5.06, A2.xx | 1.25 | C | ☐ |
| A5.08 | Artefakt yükleme | Node: `screen.capture` sonucu > 256 KB ise `artifact.upload_request` → imzalı URL → `httpx` PUT; ≤ 256 KB inline base64 | 5 MB görüntü WS'yi bloklamadan yüklenir | A5.06, A5.12 | 0.5 | C | ☐ |
| A5.09 | Servis dosyaları | `deploy/systemd/mphone-node.service` (`User=mphone`, `Restart=always`, `ProtectSystem=strict`, `ReadWritePaths`), `deploy/udev/51-android.rules`, `mphone node install-service` komutu; `deploy/launchd/com.milyonus.mphone-node.plist` + `install-agent` | Ubuntu 24.04 VM'de kurulum betiği uçtan uca çalışır; yeniden başlatmada node ayağa kalkar | A5.06 | 0.75 | C+İ | ☐ |
| A5.10 | Node CLI | `mphone node run|status|devices|drain|logs`; `node.allow_raw=false` varsayılanı | Duman testleri | A5.07 | 0.5 | C | ☐ |

### P5.c — Lease, op hattı, audit, artefakt

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A5.11 | Lease servisi | Plan.md §8.4.4: acquire (id/seçici, `wait_s` kuyruk), heartbeat, release, süre dolma işi (her 5 sn), grace (node offline), kuyruk dağıtımı, Redis `SET NX PX` + Postgres kalıcılık + uzlaştırıcı; olaylar (`lease.acquired/released/expired`) | Eşzamanlılık testi: 50 paralel acquire aynı cihaz → tam 1 başarılı; TTL dolması; grace içinde node dönüşü; uzlaştırıcı Redis kaybını onarır | A5.02, A5.05 | 2 | C | ☐ |
| A5.12 | Artefakt servisi | İmzalı PUT/GET URL'leri, `artifacts` kaydı, SSE-KMS/SSE-S3, `expires_at`, `GET /v1/artifacts/{id}` → 302 | Başka org'un artefaktına erişim 404 (IDOR testi) | A5.01 | 0.5 | C | ☐ |
| A5.13 | Router | `OpRequest` → cihazın node'u / companion bağlantısı → istek-yanıt eşleme (`req` → `asyncio.Future`), deadline, iptal; çok örnek: Redis pub/sub (`node:conn:<id>` → örnek kimliği) | Tek örnek ve 2 örnek (compose) testleri; node yok → `DEVICE_OFFLINE` | A5.06, A5.11 | 1.25 | C | ☐ |
| A5.14 | Op API + hat | `POST /v1/devices/{id}/ops`, `WS /v1/leases/{id}/ops-ws`; hat (Plan.md §8.4.5): auth → lease → şema/supports → hız sınırı (Redis kayan pencere) → politika (A3.04 motoru, temel kurallar; `approve` → P5'te deny+mesaj) → router → sonuç → audit → metrik | Yanlış lease → `LEASE_REQUIRED/CONFLICT`; desteklenmeyen op → `UNSUPPORTED`; hız sınırı → `RATE_LIMITED` + `retry_after_ms` | A5.13, A3.04 | 1.5 | C | ☐ |
| A5.15 | Audit | Redis stream'e yaz → arka plan toplu Postgres insert (kayıpsız, en az bir kez + id ile idempotent), `kw` maskeleme (`input.text.s` → `{len, sha256}`; `clipboard.set.text` aynı), `GET /v1/audit` (filtre + imleç sayfalama), `mphone admin audit` CLI; append-only DB rolü (UPDATE/DELETE yok) | Gateway çökmesi sonrası stream'den kayıp yok (test); maskeleme testleri | A5.14 | 1 | C | ☐ |

### P5.d — Runner, SDK, MCP HTTP

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A5.16 | Remote backend + Python SDK | `mphone_backends/remote/` (Plan.md §8.2.5): HTTP + WS op kanalı, `supports` önbelleği, artefakt indirme → yerel dosya, hata → istisna, heartbeat iş parçacığı, `auto_wait_approval` (P6'da etkin); `packages/mphone-sdk/`: `Gateway`, `lease()` bağlam yöneticisi, cihaz nesnesi helper metotları, `exec()`; async varyant | Fake node üzerinden tüm helper testleri remote backend ile de geçer (aynı test seti parametreli) | A5.14 | 1.5 | C | ☐ |
| A5.17 | Runner | `packages/mphone-runner/`: Redis kuyruk tüketicisi, Docker SDK ile konteyner (gVisor `runtime=runsc`), ağ: yalnızca gateway iç adresi (özel Docker ağı + egress kuralı), limitler (CPU/bellek/pids/süre), salt-okunur kök + tmpfs, run token'ı, workspace enjeksiyonu, stdout/stderr akışı → Redis → SSE, sonuç kaydı, temizlik; `Dockerfile.runner` (non-root, yalnızca mphone-core + remote + Pillow/numpy) | Kaçış/izolasyon testleri: dış ağ yok, host FS yok, ortamda agent anahtarı yok, fork bombası limitli, zaman aşımı öldürür | A5.16 | 2 | C | ☐ |
| A5.18 | Runs API | `POST /v1/runs`, `GET /v1/runs/{id}`, `GET /v1/runs/{id}/stream` (SSE), `POST /v1/runs/{id}/cancel`; AST ön kontrolü (uzak modda yasak import'lar); run token üretimi; op izi run kaydına | Uçtan uca: run → op'lar → stdout → sonuç; iptal çalışır | A5.17 | 1 | C | ☐ |
| A5.19 | MCP Streamable HTTP + workspace | Gateway `/mcp`: A3.05 araçlarının uzak uygulamaları (aynı araç tanımları, farklı arka uç — `mphone_mcp.tools` paylaşılır), `phone_workspace_get/update` (sürümlü `agent_workspaces`), `phone_approval_status` yer tutucu | MCP Inspector ile uzak araçlar; Claude Code'dan `claude mcp add --transport http` ile bağlantı | A5.18, A3.05 | 1.25 | C | ☐ |

### P5.e — Dağıtım ve doğrulama

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A5.20 | Yerel yığın + staging | `deploy/docker-compose.yml` (gateway ×2, postgres, redis, minio, runner, caddy), `.env.example`; staging VM kurulum betiği (Docker, gVisor, Caddy TLS), `docs/runbooks/staging.md` | Staging'de `/readyz` yeşil, TLS geçerli | A5.17, H-08 | 1 | C+İ | ☐ |
| A5.21 | Fake node simülatörü + yük testi | `tools/fake_node.py` (N sahte cihaz, fake backend, ayarlanabilir gecikme); `tests/load/locustfile.py` (acquire → 50 op → release döngüsü) | 200 cihaz/50 lease/30 dk, hata < %0.5, op ek yükü p95 < 150 ms | A5.14 | 1 | C | ☐ |
| A5.22 | Fake E2E zinciri | `tests/e2e_fake/`: testcontainers ile compose; senaryolar: mutlu yol, lease çakışması, TTL, node kopması (grace içi/dışı), hız sınırı, politika deny, runner zaman aşımı, "başka cihaza düşmeme" | CI'da < 10 dk yeşil | A5.19, A5.21 | 1.25 | C | ☐ |
| A5.23 | Gerçek uzak doğrulama (M2) | Staging + farklı ağdaki Linux node + 2 Android; 2 agent anahtarı; 50 görevlik koşu; ölçümler; `docs/phase-gates/P5.md` | Phases.md P5 çıkış kriterleri | A5.20, A5.22, H-03 | 1 | C+İ | ☐ |
| A5.24 | Güvenlik ön incelemesi | Auth, kapsamlar, IDOR, runner izolasyonu, node kimliği, audit maskeleme kontrol listesi (`docs/security/review-P5.md`); `semgrep` + `bandit` CI'a | Kritik bulgu 0 | A5.23 | 0.5 | C+İ | ☐ |

---

## P6 — Canlı / Onay / Devralma / Dashboard

**Hedef hafta:** 9–11 · **Toplam tahmin:** ~17 g · Detay: [Phases.md#P6](Phases.md#p6--canlı-izleme-onay-devralma-dashboard)

### P6.a — Arka uç

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A6.01 | Canlı akış — node | `screen.stream.start/stop`: Android: `screencap` JPEG döngüsü (MVP, hedef 10 fps; `screenrecord --output-format=h264` veya scrcpy server + PyAV ile JPEG'e çevirme optimizasyonu), iOS: pencere yakalama döngüsü; uyarlanabilir fps/kalite; ikili çerçeve formatı | Android orta sınıf telefonda ≥ 10 fps 720p | A5.07 | 1.5 | C | ☐ |
| A6.02 | Canlı akış — gateway rölesi | `WS /v1/devices/{id}/live`: izleyici kimliği (`devices:watch`), ilk izleyicide akışı başlat, son izleyici gidince 10 sn sonra durdur; Redis pub/sub ile örnekler arası; geri basınç (yavaş izleyiciye kare atla) | 5 izleyici, < 500 ms gecikme | A6.01, A5.13 | 1 | C | ☐ |
| A6.03 | Politika motoru tam sürüm | A3.04'ü genişlet: uygulama kategorileri (`banking`, `messaging`, `social`, `settings` — `config/app_categories.yaml`), güven seviyeleri, `for_trust_levels`, sonrası (post) kurallar (artefakt maskeleme), politika sürümleme (`policies` tablosu), `POST /v1/policies/simulate` | 20 kural simülasyon testi | A3.04, A5.14 | 1.25 | C | ☐ |
| A6.04 | Onay akışı | `approve` kararı → `approvals` kaydı + tetikleyici ekran görüntüsü (hedef box kırmızı çerçeveli, Pillow) → bildirim → `APPROVAL_REQUIRED{approval_id}`; `GET /v1/approvals/{id}?wait=` uzun yoklama; `POST …/decision`; onaylı yeniden gönderimde op+kw hash + cihaz + lease eşleşmesi, tek kullanım; süre aşımı işi | Hash uyuşmazlığı reddi; tek kullanım; süre aşımı testleri | A6.03 | 1.25 | C | ☐ |
| A6.05 | Remote backend onay bekleme | `auto_wait_approval` etkin: bekler, stdout'a "Onay bekleniyor (apr_…): <özet>" yazar, karar sonrası yeniden gönderir; `APPROVAL_DENIED` istisnası | Fake E2E onay senaryosu | A6.04, A5.16 | 0.5 | C | ☐ |
| A6.06 | Bildirimler + webhook'lar | Webhook sistemi (HMAC-SHA256 imza, yeniden deneme + üstel geri çekilme, teslim kaydı), Slack entegrasyonu (onay mesajı: ekran görüntüsü küçük resmi + "Dashboard'da aç" düğmesi; v1'de Slack'ten doğrudan onay **yok** — dashboard'da yapılır, kimlik doğrulama için) | Onay oluşturulmasından Slack mesajına < 3 sn | A6.04, H-09 | 1 | C+İ | ☐ |
| A6.07 | Devralma | `request_human` uzak sürümü (`POST /v1/devices/{id}/human-requests`), `takeover/handback` API, lease `paused` + TTL dondurma, insan girdileri için `input.*` op'ları (kullanıcı kimliğiyle, politika: insan için yalnızca audit), `handback.note` → agent'a; MCP `phone_request_human` | Devralma sırasında agent op'u `LEASE_PAUSED`; geri vermede not iletilir; insan `input.text` maskeli | A6.04 | 1 | C | ☐ |
| A6.08 | Run replay verisi | Her girdi op'undan sonra otomatik küçük ekran görüntüsü (yapılandırılabilir; 480 px JPEG q60; politika ile kapatılabilir), op ↔ artefakt bağlama, `GET /v1/runs/{id}/timeline` | 20 op'luk run zaman çizelgesi < 2 sn | A5.18 | 0.75 | C | ☐ |

### P6.b — Dashboard

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A6.09 | Dashboard iskeleti + SSO | `apps/dashboard/`: Next.js 15, TS strict, Tailwind, shadcn/ui, TanStack Query; OIDC (NextAuth/Auth.js) → Gateway oturum belirteci; rol bazlı yönlendirme; protokol tipleri (A1.02 üretimi); i18n TR (varsayılan) + EN | SSO ile giriş; `viewer` yönetim sayfalarını göremez | A1.02, H-10 | 1.5 | C+İ | ☐ |
| A6.10 | Cihazlar ekranı + cihaz detayı/canlı | Tablo (filtre, etiket düzenleme), canlı önizleme küçük resimleri; detay: canlı görüntü (canvas, WS ikili çerçeve), op zaman çizelgesi (canlı), cihaz bilgisi, lease sahibi | 50 cihazda akıcı; canlı görüntü ≥ 10 fps | A6.02 | 1.5 | C | ☐ |
| A6.11 | Devralma UI | "Devral" → canvas üzerinde tık (tap), basılı tut (press), sürükle (drag), tekerlek (scroll), klavye girişi (input.text/keys), gezinme düğmeleri; "Geri ver" + not; koordinat dönüşümü (canvas → cihaz pikseli) | Operatör canlı görüntüden telefonu sorunsuz kullanır (manuel test, 2 kişi) | A6.07, A6.10 | 1.25 | C | ☐ |
| A6.12 | Onaylar ekranı | Bekleyen liste (canlı), detay: agent, cihaz, op, maskeli argüman, kural, tetikleyici ekran görüntüsü (vurgulu), "Onayla/Reddet/Devral", not alanı; tarayıcı bildirimi | Onay → agent devamı uçtan uca | A6.04 | 1 | C | ☐ |
| A6.13 | Run'lar ve replay | Liste (filtre), detay: kod (sözdizimi vurgulu), stdout, op zaman çizelgesi + görüntü şeridi (önce/sonra), hatalar | 20 op'luk run akıcı gezinme | A6.08 | 1 | C | ☐ |
| A6.14 | Yönetim ekranları | Audit (filtre + CSV/JSON dışa aktarma), Agent'lar & API anahtarları (oluştur — anahtar bir kez gösterilir, döndür, iptal; workspace sürümleri + diff), Node'lar (durum, drain, enrollment token + kopyalanabilir kurulum komutu), Politikalar (YAML düzenleyici — Monaco, şema doğrulama, simülatör) | Her ekran için duman E2E (Playwright) | A6.03, A5.03, A5.04 | 2 | C | ☐ |
| A6.15 | SKILL.md güncellemesi | Onay ve devralma davranışı, `APPROVAL_REQUIRED` döngüsünde tekrar göndermeme, `request_human` kullanım örnekleri | Agent eval'e onay/devralma görevleri eklendi | A6.07 | 0.25 | C | ☐ |
| A6.16 | M3 doğrulama | Kullanılabilirlik testi (H-15 operatörleri), demo senaryosu, `docs/phase-gates/P6.md` | Phases.md P6 çıkış kriterleri | hepsi | 0.5 | C+İ | ☐ |

---

## P7 — Android Companion App

**Hedef hafta:** 11–13 · **Toplam tahmin:** ~17 g · Detay: [Phases.md#P7](Phases.md#p7--android-companion-app)

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A7.01 | Android proje iskeleti | `apps/android-agent/`: Gradle (Kotlin DSL), minSdk 28, Compose, kotlinx.serialization, OkHttp, ktlint/detekt, birim test + instrumentation test; CI iş akışı (derleme + test + APK artefaktı) | CI'da APK üretilir | P1 | 1 | C | ☐ |
| A7.02 | Protokol modelleri (Kotlin) | `tools/gen_protocol.py`'ye Kotlin hedefi veya `jsonschema2pojo` benzeri üretim; uyum vektörleri (A1.03) ile Kotlin birim testleri | Tüm vektörler Kotlin'de geçer | A1.03, A7.01 | 1 | C | ☐ |
| A7.03 | AccessibilityService — ağaç | Tüm pencereler (`windows`), `AccessibilityNodeInfo` → `Node`/`Box` (Plan.md §7.3 alanları: `isPassword`, `isEditable`, `isClickable`, ata tıklanabilir), sınırlar ekran pikselinde; `tree`, `screen.text`, `ui.find` | 200 düğümlü ekranda < 150 ms | A7.02 | 1.5 | C | ☐ |
| A7.04 | AccessibilityService — jestler | `dispatchGesture`: tap, press, drag, scroll (momentumsuz: sürükle + son noktada kısa duraklama), `performGlobalAction` (HOME, BACK, RECENTS, NOTIFICATIONS), `input.keys` (Enter: `ACTION_IME_ENTER` API 30+ / IME üzerinden) | Test uygulamasında (A2.16) jest doğrulama | A7.03 | 1.5 | C | ☐ |
| A7.05 | Metin yazma | Yol 1: `ACTION_SET_TEXT` (odaklı düzenlenebilir düğüm; mevcut metne ekleme modu), Yol 2: kendi IME'miz (`InputMethodService.commitText`), otomatik seçim; parola alanında **cihaz tarafında red** | 100 Türkçe cümle + emoji %100 | A7.03 | 1.25 | C | ☐ |
| A7.06 | Ekran yakalama | MediaProjection (izin akışı, ön plan servis türü `mediaProjection`), `ImageReader` → PNG/JPEG; yedek: `AccessibilityService.takeScreenshot()` (API 30+); `FLAG_SECURE` tespiti → `details.secure=true` | Android 11, 13, 14, 15 üzerinde çalışır (emülatör + gerçek) | A7.01 | 1.5 | C+İ | ☐ |
| A7.07 | Uygulamalar ve cihaz op'ları | `apps.launch` (`PackageManager.getLaunchIntentForPackage`, etiket eşleme tr_fold — Kotlin portu), `apps.list`, `apps.current` (erişilebilirlik olaylarından), `device.info/state`, `clipboard.get/set` (uygulama ön planda/IME aktifken), `notifications.list` (NotificationListenerService, kullanıcı izniyle) | Op sözleşme testleri | A7.03 | 1 | C | ☐ |
| A7.08 | Gateway bağlantısı | Ön plan servisi + kalıcı bildirim, OkHttp WSS, yeniden bağlanma (ağ değişimi dinleyicisi), heartbeat, OpDispatcher (seri yürütme), artefakt yükleme (imzalı URL); Gateway tarafı `/v1/companion/connect` (A5.13 router'ına `kind=companion` bağlantısı) | Uçak modu 30 sn → otomatik toparlanma; 24 saat stabil | A7.04, A5.13 | 1.5 | C | ☐ |
| A7.09 | Kayıt (enrollment) | Dashboard'da QR (enrollment token + gateway URL), uygulamada QR tarama (CameraX + ML Kit barcode), Keystore'da anahtar çifti, `/v1/companion/enroll`; cihaz etiketleri dashboard'dan | QR'dan `ready`'ye < 2 dk | A7.08, A6.14 | 1 | C | ☐ |
| A7.10 | Güvenlik katmanı | SafetyOverlay (`TYPE_ACCESSIBILITY_OVERLAY` ince çerçeve + "Durdur"), Durdur → lease `revoked` (Gateway'e mesaj) + servis duraklat; uygulama içi aktivite günlüğü (son 50 op) | Durdur < 1 sn'de etkili | A7.08 | 0.75 | C | ☐ |
| A7.11 | Kurulum sihirbazı | Compose ekranları: Erişilebilirlik izni, IME etkinleştirme, ekran yakalama, bildirim erişimi, pil optimizasyonu muafiyeti, üreticiye özel yönergeler (Samsung, Xiaomi, Huawei/Honor, Oppo) | Yeni bir kullanıcı yardımsız < 5 dk kurar | A7.06 | 1 | C | ☐ |
| A7.12 | İmzalama ve dağıtım | Release imzalama (H-11 keystore, CI gizlisi), sürüm adı = mphone sürümü, GitHub Releases (özel), güncelleme kontrolü (Gateway `GET /v1/companion/latest`) | İmzalı APK kurulup güncellenir | A7.01, H-11 | 0.5 | C+İ | ☐ |
| A7.13 | Hibrit mod (node + companion) | `LocalSocketServer` (`localabstract:mphone-agent`), `android_adb` backend'inde tespit (`adb forward`), `tree/screen.text/input.text`'i devretme; yedek: uiautomator | Hibrit `screen()` ≥ 5× hızlı (ölçüm) | A7.03, A2.05 | 1 | C | ☐ |
| A7.14 | Doğrulama (M4) | 3 marka gerçek cihaz (Samsung, Xiaomi, Pixel), 4G testi, agent eval, 24 saat dayanıklılık, `docs/phase-gates/P7.md` | Phases.md P7 çıkış kriterleri | hepsi | 1 | C+İ | ☐ |

---

## P8 — iOS WDA

**Hedef hafta:** 14–16 · **Toplam tahmin:** ~11 g · **Opsiyonel** · Detay: [Phases.md#P8](Phases.md#p8--ios-webdriveragent-filo)

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A8.01 | WDA derleme ve imzalama | `tools/ios/build_wda.sh`: WebDriverAgent (sabit sürüm) klonla, takım kimliği ve bundle id ile imzala, `xcodebuild build-for-testing`; profil bitiş tarihi okuma | Mac node'da tek komutla derleme | H-12 | 1.5 | C+İ | ☐ |
| A8.02 | WDA yaşam döngüsü | Cihaz başına WDA başlatma (`xcodebuild test-without-building` veya `go-ios runwda`), port yönlendirme (`iproxy`/go-ios forward), sağlık kontrolü (`/status`), çökmede yeniden başlatma (watchdog), log toplama | 30 sn içinde toparlanma | A8.01 | 2 | C+İ | ☐ |
| A8.03 | WDA HTTP istemcisi + op'lar | `ios_wda/` backend: oturum, `screen.capture` (`/screenshot`), `tree` (`/source?format=json`), `screen.text` (ağaç → box; ölçek: nokta → piksel), `input.*` (`/wda/tap`, `/wda/touchAndHold`, `/wda/dragfromtoforduration`, `/wda/keys`), `nav.home` (`/wda/homescreen`), `apps.launch/stop/current` (bundleId; ad çözümleme `go-ios apps` önbelleği) | Sözleşme + gerçek cihaz testleri | A8.02 | 2.5 | C | ☐ |
| A8.04 | Node keşfi | `go-ios list` / `idevice_id -l` ile cihaz keşfi, cihaz başına backend örneği | 3 iPhone aynı anda kayıtlı | A8.03, A5.07 | 1 | C | ☐ |
| A8.05 | İmza süresi uyarısı ve doctor | Profil bitişine 14 gün kala dashboard/Slack uyarısı; `mphone doctor ios-wda` | Uyarı testi | A8.04 | 0.75 | C | ☐ |
| A8.06 | Filo doğrulaması (M4.5) | 1 Mac + 3 iPhone, agent eval ≥ %85, çökme toparlanma testi | Phases.md P8 çıkış kriterleri | hepsi | 1.5 | C+İ | ☐ |
| A8.07 | SKILL.md + PITFALLS iOS-WDA | Ağaç var, `back` yok, bundleId'ler, koordinat ölçeği | İnceleme | A8.06 | 0.25 | C | ☐ |

---

## P9 — Sertleştirme → GA

**Hedef hafta:** 14–15 · **Toplam tahmin:** ~13 g · Detay: [Phases.md#P9](Phases.md#p9--sertleştirme-güvenlik-denetimi-ga)

| ID | İş | Detay / Çıktılar | Kabul kriteri | Bağ. | Tahmin | Sahip | Durum |
|---|---|---|---|---|---|---|---|
| A9.01 | Yük testi (tam) | 200 cihaz, 50 lease, canlı izleyiciler, runner yükü, 2 saat; darboğaz analizi + düzeltmeler | SLO'lar yük altında tutar | P6 | 1.5 | C | ☐ |
| A9.02 | Kaos testleri | toxiproxy + betikler: node WS kesme, Redis yeniden başlatma, gateway pod öldürme, Postgres failover, yavaş ağ (300 ms, %5 kayıp); `docs/chaos-report.md` | Veri kaybı yok; lease tutarlılığı; otomatik toparlanma | A9.01 | 1 | C | ☐ |
| A9.03 | Çok örnek + Kubernetes | Helm chart (`deploy/helm/mphone`): gateway Deployment + HPA + PDB, runner düğüm havuzu (gVisor RuntimeClass), dashboard, ingress (WS), ServiceMonitor; drain (SIGTERM → yeni WS kabul etme, mevcutları 60 sn içinde devret) | Rolling update sırasında op kaybı yok (test) | A5.20 | 1.5 | C | ☐ |
| A9.04 | Pentest ve düzeltmeler | Kapsam belgesi (auth, IDOR, runner kaçışı, node/companion taklidi, WS, SSRF, XSS dashboard, politika atlatma); bulgu düzeltmeleri | Kritik/yüksek açık bulgu 0 | H-13 | 2 | C+İ | ☐ |
| A9.05 | Tedarik zinciri güvenliği | `pip-audit`, `npm audit`, Trivy imaj taraması, SBOM (CycloneDX), imzalı imajlar (cosign), Dependabot/Renovate | CI'da zorunlu; kritik açık 0 | — | 0.75 | C | ☐ |
| A9.06 | Gözlemlenebilirlik paketi | Grafana panoları (JSON, `deploy/grafana/`), Prometheus uyarı kuralları (Plan.md §11.4), SLO tanımları + hata bütçesi | Panolar staging'de canlı; uyarılar test tetiklemesiyle doğrulandı | P6 | 1 | C | ☐ |
| A9.07 | KVKK işleri | Saklama işleri (artefakt/audit otomatik silme), veri sahibi talebi prosedürü (dışa aktar/sil), PII maskeleme seçeneği (OCR + regex: TCKN, IBAN, kart no, telefon) artefaktlarda, aydınlatma metni şablonu (hukuk onaylı), erişim kaydı raporu | Hukuk onayı (H-07); silme işi testi | H-07 | 1.25 | C+İ | ☐ |
| A9.08 | Kill switch ve acil durum | `mphone admin freeze [--org|--agent|--device]`: tüm op'ları anında `POLICY_DENIED`'a çeker (Redis bayrağı, < 5 sn); dashboard düğmesi (owner) | Tatbikat < 5 sn | A6.03 | 0.5 | C | ☐ |
| A9.09 | Prod altyapı | Terraform (Q6 bulutuna göre): VPC, yönetilen Postgres (PITR), Redis, S3 (versiyonlama, Object Lock audit arşivi), KMS, gizli yönetici, DNS/TLS; prod dağıtım iş akışı (manuel onaylı) | Prod ortamı ayakta; DR tatbikatı RPO < 5 dk, RTO < 1 saat | H-14, A9.03 | 2 | C+İ | ☐ |
| A9.10 | Runbook'lar | `docs/runbooks/`: node arızası, cihaz unauthorized/kilitli, toplu cihaz kopması (hub), gateway olayı, API anahtarı sızıntısı, politika acil değişikliği, yedekten dönüş, yeni node/cihaz ekleme, Companion kurulumu | Her runbook bir kez tatbik edildi | A9.09 | 1 | C+İ | ☐ |
| A9.11 | Dokümantasyon | Operatör kullanıcı rehberi (TR), geliştirici rehberi (yeni op/backend ekleme), agent entegrasyon rehberi son sürüm, API referansı (OpenAPI'den) | İnceleme | — | 1 | C | ☐ |
| A9.12 | Pilot ve GA kararı | 2 haftalık pilot (gerçek iş süreçleri, sınırlı agent/cihaz), SLO ölçümü, geri bildirim, `docs/phase-gates/P9.md` | Phases.md P9 çıkış kriterleri | hepsi | 0.5 (+ 2 hafta pilot takvimi) | İ | ☐ |

---

## 13. Kalem Şablonu ve Claude'a Görev Verme

### 13.1 Yeni kalem şablonu

```markdown
| A<faz>.<no> | <kısa iş adı> | <ne yapılacak; hangi dosyalar/komutlar oluşacak> | <test/ölçümle doğrulanabilir kabul> | <bağımlı kalemler / H-xx> | <g> | <C/İ/C+İ> | ☐ |
```

### 13.2 Claude Code'a bir kalemi verme kalıbı

Bir Claude Code oturumunda bir kalemi başlatırken şu kalıp kullanılır (CLAUDE.md bu kalıbı bilir):

```text
Plan-Actions.md'deki A2.08 kalemini uygula.
- Önce CLAUDE.md, Plan.md §8.2.1 ve §7.4 (input.text satırı) ve docs/PITFALLS.md Android bölümünü oku.
- Bağımlılıklar (A2.07) bitti mi kontrol et; değilse dur ve söyle.
- Kabul kriterini karşılayan testleri ÖNCE yaz, sonra uygula.
- Bitince: testler + ruff + pyright yeşil; PITFALLS.md'ye yeni öğrendiğini ekle;
  Plan-Actions.md'de durumu ◐ → ☑ yap; PR açıklaması taslağını yaz (kalem kimliğiyle).
```

### 13.3 İnsan doğrulaması gereken kalemlerde (C+İ)

Claude, fiziksel adımı **açıkça** ister ve bekler:
> "A2.17 için gerçek cihaz gerekiyor. Lütfen Samsung telefonu USB ile bağlayın, kilidini açın ve 'USB hata ayıklamaya izin ver' sorusunu onaylayın. Hazır olunca 'tamam' yazın; `mphone doctor android` çalıştıracağım."

---

## 14. İlk 10 İş Günü — Somut Başlangıç Listesi

| Gün | Yapılacaklar | Kalemler | Çıktı |
|---|---|---|---|
| 1 | Kararlar toplantısı (Q1–Q13), repo oluşturma, donanım siparişi | H-01, H-02, H-03, A0.06 | `docs/decisions.md` taslağı |
| 1 | Repo iskeleti, araçlar, CI | A0.01, A0.02, A0.03 | Yeşil CI |
| 2 | ADR'ler, PITFALLS v0, referans notları, sürüm düzeni | A0.04, A0.05, A0.09, A0.10 | `docs/` dolu |
| 2 | Cihaz hazırlık rehberi + ilk Android'in hazırlanması | A0.07, H-05 | 1 hazır telefon |
| 3 | Op şeması v1 (gözden geçirme için PR) | A1.01 | Şema PR'ı |
| 4 | Şema gözden geçirmesi (2 kişi) + üretici + uyum vektörleri | A1.02, A1.03 | Üretilmiş modeller |
| 4 | `Backend`, `connect`, `textnorm` | A1.04, A1.05, A1.06 | Çekirdek |
| 5 | Helper'lar, config/workspace, OCR arayüzü | A1.07–A1.11 | Helper API |
| 6 | Fake backend + senaryolar + sözleşme testleri → **P1 kapısı** | A1.12–A1.14 | P1 bitti |
| 7 | adb çalıştırıcı, keşif, durum kapısı | A2.01–A2.03 | Telefon bulunuyor, kilit tespiti |
| 8 | Yakalama, ağaç, OCR | A2.04–A2.06 | `screen()` gerçek telefonda |
| 9 | Jestler, Unicode yazım, IME kurulumu | A2.07–A2.09 | Türkçe yazım çalışıyor |
| 10 | Gezinme, uygulamalar, cihaz op'ları; emülatör CI başlangıcı | A2.10–A2.12, A2.15 | İlk uçtan uca script gerçek telefonda |

**10. günün sonunda beklenen:** Gerçek bir Android'de şu script çalışıyor:

```bash
mphone run <<'PY'
# task: Android sürümünü oku ve Türkçe not yaz
# step: Ayarlar → Telefon hakkında
ensure_device()
open_app("Ayarlar"); wait_stable()
scroll_until(lambda boxes: any("Telefon hakkında" in b["text"] for b in boxes))
tap_text("Telefon hakkında"); wait_stable()
print([b["text"] for b in screen() if "Android" in b["text"]])
PY
```
