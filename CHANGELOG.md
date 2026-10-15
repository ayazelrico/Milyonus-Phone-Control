# Changelog

Bu dosya [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) biçimini, sürümler [SemVer](https://semver.org/lang/tr/) kuralını izler.
Protokol sürümü (`ops.v1`) paket sürümünden bağımsızdır (Plan.md §7.6).

## [Unreleased]

### Changed
- Lisans Apache-2.0 (LICENSE, NOTICE); repo public; Q1–Q13 kesinleşti; `main` branch koruması (karar kaydı).

### Added
- P3: `mphone run` — alt süreçte script; gizli ortam değişkenleri temizlenir, zaman aşımı süreç grubunu öldürür, çıktı 50 KB'a kırpılır, her op audit'e (yazılan metin maskeli) (A3.01–A3.02).
- P3: Yerel kiralama (dosya kilidi; sahibini söyler) (A3.03).
- P3: Politika motoru (YAML, en katı karar kazanır): parola alanına yazma ve kod benzeri girdiler reddedilir; gönder/öde/sil onay ister; `--allow KURAL` (A3.04).
- P3: MCP sunucusu (stdio, 15 araç, `mphone://skill`, `mphone://protocol`, `phone_task` istemi); `mphone mcp`, `mphone skill` (A3.05, A3.08).
- P3: `skills/phone-control/SKILL.md`; Milyonus Agent entegrasyon rehberi (A3.06, A3.09).
- P3: Agent değerlendirme düzeneği (7 görev; yarısı doğru durmayı ölçer) (A3.10).
- P2: Android (adb) backend `AndroidAdb`: cihaz seçimi (USB > emülatör > Wi-Fi, birincil telefon asla ikamesiz), kilit/uyku kapısı, dosya tabanlı ağaç, OCR yedeği, momentumsuz kaydırma, uygulama adı çözümleme (TR/EN), bildirimler, dosya aktarımı (A2.01–A2.12).
- P2: `apps/android-ime` — Türkçe/emoji için kendi klavyemiz (Apache-2.0; ADBKeyboard GPL-2.0 olduğu için); yalnızca adb shell/sistem yazdırabilir (DUMP izni). Debug APK'da E2E test ekranı (A2.08, A2.09, A2.16).
- P2: `mphone doctor android [--write-test]`, `mphone android devices|pair|use|ime|awake` (A2.13, A2.14).
- P2: Emülatörden ham adb çıktısı toplayan iş akışı ve bayt düzeyinde fixture'lar (API 30, 34); E2E emülatör iş akışı (A2.15).
- P0: uv workspace iskeleti (9 paket), ruff/pyright/pytest/pre-commit yapılandırması, CI (A0.01–A0.03).
- P0: ADR-0001…0015, PITFALLS.md v0, karar kaydı, cihaz hazırlık rehberi, referans proje notları (A0.04–A0.09).
- P0: `tools/bump_version.py` ve bu değişiklik günlüğü (A0.10).
- P1: Protokol v1 şeması (39 op, 19 hata kodu) ve `tools/gen_protocol.py` (Pydantic modelleri, op tablosu, hata sınıfları, `docs/protocol.md`) (A1.01–A1.02).
- P1: Protokol uyum vektörleri (A1.03).
- P1: `Backend` taban sınıfı + middleware zinciri + `TraceMiddleware`, `connect()` ve cihaz URI'leri, Türkçe-farkında eşleştirme (`tr_fold`, `match`), ağaç yardımcıları, config, agent workspace, OCR arayüzü (A1.04–A1.06, A1.10–A1.11).
- P1: Helper API (`Phone` + modül fonksiyonları): ekran okuma, dokunma, Unicode yazma, kaydırma/toplama, bekleme, ağaç, insan devralma/onay (A1.07–A1.09).
- P1: Fake telefon backend'i (tüm op'lar) ve 5 senaryo (A1.12–A1.13); sözleşme testleri (A1.14).
