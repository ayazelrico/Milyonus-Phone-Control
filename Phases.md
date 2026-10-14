# Milyonus Phone Control — Fazlar ve Kilometre Taşları (Phases.md)

> **Durum:** Taslak v1.0 · **Tarih:** 2026-10-14
> **Bağlı dokümanlar:** [Plan.md](Plan.md) (mimari ve tasarım) · [Plan-Actions.md](Plan-Actions.md) (her fazın iş kalemleri, `A<faz>.<no>` kimlikleriyle) · [CLAUDE.md](CLAUDE.md)
>
> Bu doküman **ne zaman, hangi sırayla ve hangi kapıdan geçerek** ilerlediğimizi tanımlar. Her fazın: hedefi, kapsamı, kapsam dışı, teslimatları, çıkış kriterleri (Definition of Done), demo senaryosu, metrikleri, riskleri ve go/no-go kararı vardır. Bir faz, çıkış kriterleri **tamamen** sağlanmadan "bitti" sayılmaz.

---

## İçindekiler

1. [Genel Bakış](#1-genel-bakış)
2. [Zaman Çizelgesi](#2-zaman-çizelgesi)
3. [Kilometre Taşları](#3-kilometre-taşları)
4. [Faz Detayları](#4-faz-detayları)
   - [P0 — Temel ve Kararlar](#p0--temel-ve-kararlar)
   - [P1 — Protokol, Çekirdek ve Fake Backend](#p1--protokol-çekirdek-ve-fake-backend)
   - [P2 — Android ADB Backend (Yerel)](#p2--android-adb-backend-yerel)
   - [P3 — Agent Arayüzleri (CLI, Skill, MCP) → MVP](#p3--agent-arayüzleri-cli-skill-mcp--mvp)
   - [P4 — iPhone Mirroring Backend](#p4--iphone-mirroring-backend)
   - [P5 — Uzaktan Kontrol: Node + Gateway + Runner](#p5--uzaktan-kontrol-node--gateway--runner)
   - [P6 — Canlı İzleme, Onay, Devralma, Dashboard](#p6--canlı-izleme-onay-devralma-dashboard)
   - [P7 — Android Companion App](#p7--android-companion-app)
   - [P8 — iOS WebDriverAgent (Filo)](#p8--ios-webdriveragent-filo)
   - [P9 — Sertleştirme, Güvenlik Denetimi, GA](#p9--sertleştirme-güvenlik-denetimi-ga)
5. [Fazlar Arası Bağımlılıklar](#5-fazlar-arası-bağımlılıklar)
6. [Faz Kapısı (Go/No-Go) Süreci](#6-faz-kapısı-gono-go-süreci)
7. [Fazlar Boyunca Sürekli İşler](#7-fazlar-boyunca-sürekli-işler)
8. [Faz Sonrası (v2 Yol Haritası)](#8-faz-sonrası-v2-yol-haritası)

---

## 1. Genel Bakış

| Faz | Ad | Süre | Kilometre taşı | Kritik yol? | Ana çıktı |
|---|---|---|---|---|---|
| **P0** | Temel ve Kararlar | 1 hafta | M0 | ✓ | Repo, CI, kararlar (Q1–Q13), donanım siparişi, ADR'ler |
| **P1** | Protokol, Çekirdek, Fake | 1 hafta | — | ✓ | Op şeması, `Backend`, helper'lar, fake telefon, sözleşme testleri |
| **P2** | Android ADB (yerel) | 2 hafta | — | ✓ | Gerçek Android kontrolü, Türkçe yazım, `doctor` |
| **P3** | Agent arayüzleri → MVP | 1 hafta | **M1 — MVP** | ✓ | `mphone run`, SKILL.md, MCP stdio; Milyonus Agent masadaki Android'i kullanır |
| **P4** | iPhone Mirroring | 2 hafta | M1.5 | — | iPhone (Mac başına 1) kontrolü |
| **P5** | Uzaktan kontrol | 3 hafta | **M2 — Remote** | ✓ | Node, Gateway, lease, auth, audit, runner, remote backend, MCP HTTP |
| **P6** | Canlı/Onay/Devralma/Dashboard | 2.5 hafta | **M3 — Gözetimli operasyon** | ✓ | Dashboard, canlı görüntü, onay kuyruğu, devralma, run replay, politika UI |
| **P7** | Android Companion App | 3 hafta | **M4 — Host'suz uzak telefon** | — | Kotlin uygulaması, hızlı ağaç, IME, doğrudan Gateway bağlantısı |
| **P8** | iOS WDA (opsiyonel) | 2.5 hafta | M4.5 | — | Mac başına çoklu iPhone |
| **P9** | Sertleştirme → GA | 2 hafta | **M5 — GA** | ✓ | Yük/kaos/pentest, runbook'lar, prod dağıtımı |

**Toplam:** Tek iş kolu (1 geliştirici + Claude) ≈ **20 hafta**; iki iş kolu (2 geliştirici veya geliştirici + Android geliştirici) ≈ **14–15 hafta**.

---

## 2. Zaman Çizelgesi

### 2.1 İki iş kolu (önerilen)

```
Hafta:        1    2    3    4    5    6    7    8    9   10   11   12   13   14   15
              ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
Kol A (Core)  [P0 ][P1 ][P2 ═════][P3 ][P5 ═════════════][P6 ══════════][P9 ═════]
                                    ▲M1                 ▲M2           ▲M3       ▲M5
Kol B (Platf) [P0 ]          ......[P4 ═════]......[P7 ═════════════][P8 ══════════]
                                            ▲M1.5                    ▲M4        ▲M4.5
```

- **Kol A**: çekirdek, Android ADB, MCP, Gateway, Dashboard, sertleştirme.
- **Kol B**: P0'da donanım/kurulum; P1–P3 sırasında Kol A'ya destek (testler, fixture'lar, OCR korpusu); sonra iPhone Mirroring, Companion App, WDA.

### 2.2 Tek iş kolu sırası

`P0 → P1 → P2 → P3 (M1) → P5 (M2) → P6 (M3) → P4 → P7 (M4) → P9 (M5) → P8`

Gerekçe: Uzaktan kontrol (P5) ve gözetim (P6), iPhone'dan daha büyük iş değeri taşır (varsayılan: Android öncelikli — Plan.md Q3). Q3'ün cevabı "iPhone önce" ise P4, P5'in önüne alınır.

---

## 3. Kilometre Taşları

| KT | Ad | Hedef hafta (2 kol) | Kanıt (demo) | Paydaş onayı |
|---|---|---|---|---|
| **M0** | Proje hazır | 1 | CI yeşil, repo iskeleti, kararlar dokümante, donanım sipariş edildi | Teknik lider |
| **M1** | **MVP — Bağlı Android** | 5 | Milyonus Agent (veya Claude Code) MCP ile masadaki Android'de "Ayarlar → Telefon hakkında → Android sürümü" ve "Notlar'a Türkçe not yaz" görevlerini ≥ %95 başarıyla yapar | Ürün + teknik |
| **M1.5** | iPhone (Mirroring) | 7 | Aynı görevler Mac'e bağlı iPhone'da | Teknik |
| **M2** | **Uzaktan kontrol** | 8 | Agent, başka şehirdeki/odadaki node'a bağlı Android'i Gateway üzerinden lease ile kontrol eder; iki agent iki telefonu çakışmadan kullanır; tüm op'lar audit'te | Ürün + teknik + güvenlik |
| **M3** | **Gözetimli operasyon** | 11 | Operatör dashboard'da canlı izler; "Gönder" onaya düşer, onaylanır; 2FA için devralma yapılır; run replay izlenir | Ürün + operasyon |
| **M4** | Host'suz uzak Android | 13 | Companion App yüklü, 4G'deki bir telefon QR ile kaydolur ve agent tarafından kontrol edilir; `screen()` < 400 ms; Türkçe yazım | Ürün |
| **M4.5** | iPhone filosu | 15 | Bir Mac'e bağlı 3 iPhone eşzamanlı kontrol | Teknik |
| **M5** | **GA (Genel Kullanım)** | 15 | Prod ortamında 10+ cihaz, SLO'lar 2 hafta tutuldu, pentest bulguları kapatıldı, runbook'lar hazır | Yönetim |

---

## 4. Faz Detayları

---

### P0 — Temel ve Kararlar

**Süre:** 1 hafta · **Kol:** A + B · **Önkoşul:** yok

#### Hedef
Projenin "nasıl" yapılacağına dair tüm belirsizlikleri kapatmak, geliştirme ortamını ve CI'ı kurmak, donanım tedarikini başlatmak.

#### Kapsam
- Plan.md §16 açık sorularının (Q1–Q13) cevaplanması veya varsayılanların resmen kabulü.
- Monorepo iskeleti (uv workspace, paket dizinleri, boş modüller, `pyproject.toml`'lar).
- Kod kalitesi araçları: ruff (lint + format), pyright (strict, çekirdek paketlerde), pytest, pre-commit, gitleaks, Conventional Commits.
- CI: GitHub Actions — lint, typecheck, unit test (macOS + Linux + Windows matrisi çekirdek için).
- ADR-001 … ADR-015 dosyaları (`docs/adr/`), Plan.md §14'teki özetlerden.
- Donanım siparişi ve test rafı planı; Android cihaz hazırlık checklist'i.
- Referans proje okuması: ekip, phone-harness SKILL.md + transport.py + android.py'yi okur; `docs/PITFALLS.md` ilk sürümü (Plan.md §4.3'ten).
- KVKK/hukuk ön görüşmesi başlatılır (Q2, Q12).

#### Kapsam Dışı
- Herhangi bir backend kodu.

#### Teslimatlar
| # | Teslimat | Konum |
|---|---|---|
| D0.1 | Repo iskeleti + çalışan `uv sync` | kök |
| D0.2 | CI iş akışı (yeşil) | `.github/workflows/ci.yml` |
| D0.3 | ADR'ler | `docs/adr/` |
| D0.4 | Karar kaydı (Q1–Q13 cevapları) | `docs/decisions.md` |
| D0.5 | PITFALLS.md v0 | `docs/PITFALLS.md` |
| D0.6 | Donanım sipariş listesi + cihaz hazırlık checklist'i | `docs/runbooks/device-prep.md` |
| D0.7 | CLAUDE.md (bu repo için) | kök |

#### Çıkış Kriterleri (DoD)
- [ ] `uv sync && uv run pytest` boş test setiyle üç işletim sisteminde yeşil.
- [ ] `pre-commit run --all-files` temiz.
- [ ] Q1–Q13'ün her biri için ya cevap ya "varsayılan kabul edildi" kaydı var.
- [ ] Donanım siparişi verildi (veya mevcut cihazlar envantere alındı); en az 1 Android geliştirici masasında hazır.
- [ ] ADR'ler `Accepted` durumunda.

#### Demo
Boş repo üzerinde PR açılır → CI tüm kontrolleri çalıştırır → yeşil.

#### Riskler
- Kararların gecikmesi → varsayılanlarla ilerle, karar gelince ADR güncelle.

#### Go/No-Go
M0: Teknik lider onayı. No-Go durumu: CI kurulamadıysa veya Q3 (platform önceliği) belirsizse P1 başlamaz.

---

### P1 — Protokol, Çekirdek ve Fake Backend

**Süre:** 1 hafta · **Kol:** A (B destek: fake senaryolar, fixture'lar) · **Önkoşul:** P0

#### Hedef
Tüm sistemin dayandığı **sözleşmeyi** (op sözlüğü + zarf + hata kodları) ve platformdan bağımsız **helper katmanını** telefonsuz, tamamen test edilmiş hale getirmek.

#### Kapsam
- `mphone-protocol`: `schema/ops.v1.json` (Plan.md §7.4 tablosu), zarf (`OpRequest/OpResult`), hata kodları (§7.2), Box (§7.3), seçici (§7.5). Şemadan Pydantic modelleri üretimi (`tools/gen_protocol.py`), `docs/protocol.md` üretimi.
- `mphone-core`: `Backend` taban sınıfı (slot dispatch, `supports`, `ops`, argüman doğrulama), istisna hiyerarşisi, `connect()` + URI çözümleme (§8.1.2), helper'lar (§8.1.3 tablosunun tamamı; P1'de `request_human`/`request_approval` yerel terminal sürümüyle), `textnorm.tr_fold`, config, workspace, OCR arayüzü (motor yok, yalnızca soyutlama + `null` motor).
- `mphone-backends/fake`: YAML senaryo motoru, PNG üretimi, hata/gecikme enjeksiyonu; en az 4 senaryo: `settings_about`, `notes_turkish`, `long_list_120`, `locked_phone`.
- Sözleşme testleri (AST + şema).

#### Kapsam Dışı
- Gerçek cihaz backend'leri, CLI, MCP.

#### Teslimatlar
| # | Teslimat |
|---|---|
| D1.1 | `ops.v1.json` + üretilmiş modeller + `docs/protocol.md` |
| D1.2 | `mphone_core` (Backend, connect, helpers, textnorm, config, workspace, errors) |
| D1.3 | Fake backend + 4 senaryo |
| D1.4 | Birim + sözleşme test seti (çekirdekte satır kapsamı ≥ %90) |

#### Çıkış Kriterleri
- [ ] Helper tablosundaki (Plan.md §8.1.3) her helper uygulanmış ve fake üzerinde testli.
- [ ] `scroll_collect` fake `long_list_120` senaryosunda 120 öğeyi tekrarsız toplar, `stop="reached-end"`.
- [ ] `tap_text` bulunamazsa `NOT_FOUND` + `details.visible` döner.
- [ ] `tr_fold` testleri: `"İSTANBUL"↔"istanbul"`, `"IĞDIR"↔"ığdır"`, `"ç"≠"c"` (exact), aksansız ikincil eşleşme çalışır.
- [ ] Sözleşme testi: helper'ların gönderdiği her kwarg fake backend imzasında var.
- [ ] Şema değişikliği → üretilmiş kod değişmezse CI kırılır (üretim tazeliği kontrolü).
- [ ] Pyright strict temiz (`mphone-protocol`, `mphone-core`).

#### Demo
```bash
uv run python -c "
from mphone_core.helpers import *
use('fake:settings_about')
ensure_device(); open_app('Ayarlar'); tap_text('Telefon hakkında')
print([b['text'] for b in screen()])"
```

#### Metrikler
Çekirdek kapsamı ≥ %90; test süresi < 30 sn.

#### Riskler
- Şemanın aşırı mühendisliği → P1'de yalnızca §7.4 tablosu; "belki lazım olur" alanları eklenmez.

#### Go/No-Go
Çıkış kriterlerinin tamamı. Şema gözden geçirmesi (2 kişi) yapılmadan P2 başlamaz — şema sonradan değişirse tüm backend'ler etkilenir.

---

### P2 — Android ADB Backend (Yerel)

**Süre:** 2 hafta · **Kol:** A · **Önkoşul:** P1, en az 1 gerçek Android + emülatör

#### Hedef
Masadaki bir Android telefonu (USB ve Wi-Fi) protokolün tamamıyla, Türkçe yazım dahil, güvenilir şekilde kontrol etmek.

#### Kapsam
- `android_adb` backend: Plan.md §8.2.1'in tamamı — cihaz seçimi (primary, USB > Wi-Fi > mDNS, `-s` sabitleme), durum kapısı (uyku/kilit/yetkisiz), tüm op'lar, `uiautomator dump` ağaç + "idle state" geri çekilmesi, ağaç → box dönüşümü (clickable ancestor, password bayrağı), `motionevent` kaydırma, keyevent eşlemesi, uygulama adı çözümleme + etiket önbelleği, bildirimler, keep-awake.
- **Unicode yazım:** ADBKeyboard entegrasyonu (`mphone android ime install` APK kurulumu — APK lisansı kontrol edilir; alternatif: P2'de minimal kendi IME APK'mız) ve `mode=auto` mantığı.
- OCR motorları: `vision` (macOS), `rapidocr` (diğer) — `screen.text_pixels` için.
- `mphone doctor android` (Plan.md §8.7 merdiveni).
- `mphone android pair|connect|use|awake|rest|ime install`.
- Fixture tabanlı birim testleri (gerçek `adb` çıktıları, ağaç XML'leri — farklı markalardan).
- Emülatör E2E CI iş akışı (API 30 ve 34).
- PITFALLS.md Android bölümü güncellemesi.

#### Kapsam Dışı
- scrcpy canlı akış (P5/P6'da), Companion App (P7).

#### Teslimatlar
| # | Teslimat |
|---|---|
| D2.1 | `mphone_backends.android_adb` |
| D2.2 | Unicode IME yolu + kurulum komutu |
| D2.3 | OCR motorları (vision, rapidocr) + Türkçe OCR korpusu v0 (≥ 50 görüntü) |
| D2.4 | `doctor android`, `android` alt komutları (CLI'ın ilk parçası) |
| D2.5 | Emülatör E2E iş akışı |
| D2.6 | Cihaz matrisi raporu (`docs/device-matrix.md`): hangi marka/model/sürümde ne çalıştı |

#### Çıkış Kriterleri
- [ ] Emülatör E2E (API 30, 34) yeşil: Ayarlar senaryosu, Türkçe not, 100 öğelik liste toplama, kilit tespiti.
- [ ] En az 2 farklı markada (ör. Samsung + Pixel/Xiaomi) gerçek cihaz üzerinde aynı senaryolar ≥ 19/20 başarı.
- [ ] `type_text("Çağrı ışığı söndü; İğdır'a gidiyoruz! 🚀")` metni doğru yazar (emoji IME ile; emoji desteklenmiyorsa açık hata).
- [ ] Kilitli telefonda her girdi op'u `DEVICE_LOCKED` döner ve **hiçbir dokunuş gönderilmez** (testle doğrulanmış).
- [ ] `primary` ayarlı ve ulaşılamazken başka telefon kullanılmaz (testli).
- [ ] Gecikme (USB, orta sınıf telefon): `tap` p95 < 250 ms, `screenshot` p95 < 900 ms, `screen()` p95 < 3 sn.
- [ ] `doctor android` her kırık adımda doğru tek eylemi söyler (6 hata senaryosu test edildi: adb yok, cihaz yok, yetkisiz, kilitli, IME yok, ağaç yok).
- [ ] PITFALLS.md Android bölümü ≥ 15 madde, her biri bir test veya kod yorumuyla bağlantılı.

#### Demo
Gerçek telefonda canlı: `mphone run <<'PY' ... PY` ile WhatsApp'ı aç → arama → Türkçe metin yaz (göndermeden) → ekranı oku.

#### Metrikler
Op başarı oranı (emülatör E2E, 100 tekrar) ≥ %99.

#### Riskler
- MIUI/HyperOS kısıtları → cihaz matrisinde belgelenir, `doctor` uyarısı.
- ADBKeyboard lisans/bakım sorunu → kendi minimal IME'miz (Kotlin, ~200 satır) yedek plan; P7'de zaten tam IME var.

#### Go/No-Go
Çıkış kriterleri + Türkçe yazımın kanıtı. Türkçe yazım çözülmeden M1 ilan edilmez.

---

### P3 — Agent Arayüzleri (CLI, Skill, MCP) → MVP

**Süre:** 1 hafta · **Kol:** A · **Önkoşul:** P2

#### Hedef
Milyonus Agent'ın (ve Claude Code gibi MCP istemcilerinin) masadaki Android'i **kendi başına, güvenli ve verimli** kullanabilmesi. **M1 — MVP.**

#### Kapsam
- `mphone run`: stdin'den Python; helper'lar önceden yüklü; `# task:/# step:` uyarısı; zaman aşımı; stdout kuyruğu (50 KB); ortam temizleme (`*_API_KEY/_TOKEN/_SECRET`); helper çağrı izi (JSONL); yerel audit (JSONL).
- Yerel lease: dosya kilidi (aynı makinede iki agent çakışmasın).
- Yerel politika: `~/.mphone/policy.yaml` (Plan.md §10.3 kurallarının yerel alt kümesi: `never-type-secrets`, `secret-looking-text`, `outward-send` → yerelde "approve" = MCP istemcisine/terminale onay sorusu).
- `mphone-mcp` stdio: Plan.md §8.6 araç tablosunun **yerel** alt kümesi: `phone_list_devices`, `phone_acquire`, `phone_release`, `phone_exec`, `phone_screen`, `phone_screenshot`, `phone_tap`, `phone_type`, `phone_scroll`, `phone_swipe`, `phone_nav`, `phone_open_app`, `phone_wait_for`, `phone_request_human`, `phone_device_info`; kaynaklar: `mphone://skill`, `mphone://protocol`; istem: `phone_task`.
- `skills/phone-control/SKILL.md` (TR) + `SKILL.en.md` — Plan.md §8.11.
- Milyonus Agent entegrasyon rehberi (`docs/integration/milyonus-agent.md`): MCP config örneği, sistem istemi eki, araç izinleri.
- Agent değerlendirme harness'ı v0 (`tests/agent_eval/`): 10 görev, fake + emülatör üzerinde, başarı/adım/süre/token raporu.
- `mphone skill`, `mphone mcp`, `mphone devices`, `mphone config`.
- Paketleme: `uv tool install` ile kurulabilir wheel (özel paket deposu veya git URL).

#### Kapsam Dışı
- Uzak mod araçları (`phone_approval_status`, workspace sürümleme) — P5.

#### Teslimatlar
| # | Teslimat |
|---|---|
| D3.1 | `mphone` CLI (run, skill, mcp, devices, config, doctor, android) |
| D3.2 | `mphone-mcp` stdio sunucusu |
| D3.3 | SKILL.md (TR/EN) |
| D3.4 | Entegrasyon rehberi + örnek config |
| D3.5 | Agent eval harness v0 + ilk rapor |
| D3.6 | Kurulabilir paket |

#### Çıkış Kriterleri (M1)
- [ ] Temiz bir makinede: `uv tool install …` → `mphone doctor android` → MCP'yi agent'a ekle → ilk görev, **15 dakikadan kısa** sürede (kurulum süresi ölçülür).
- [ ] Agent eval (emülatör + 1 gerçek cihaz, 10 görev × 3 tekrar): başarı ≥ %90; "Android sürümünü oku" ve "Türkçe not" görevleri ≥ %95.
- [ ] `phone_exec` görüntü eki çalışıyor (MCP image content), görüntü başına ≤ 250 KB.
- [ ] Politika: parola alanına `type_text` reddedilir; "Gönder" tıklaması onay sorusu üretir (testli).
- [ ] Aynı makinede iki MCP istemcisi aynı telefonu kiralamaya çalışınca ikincisi `LEASE_CONFLICT` alır.
- [ ] Milyonus Agent ile (Q1 cevabına göre: MCP veya SDK/subprocess köprüsü) en az bir uçtan uca görev canlı gösterildi.

#### Demo (M1)
Milyonus Agent'a doğal dilde: *"Masadaki telefonda Ayarlar'dan Android sürümünü bul, sonra Notlar'a 'Toplantı Çarşamba 14:00, Şişli ofis' notunu ekle."* → agent bunu yapar, kullanıcıya her adımı bir satırla bildirir.

#### Metrikler
Görev başarı oranı, görev başına `phone_exec` sayısı (< 6), ortalama görev süresi, token/görev.

#### Riskler
- Milyonus Agent'ın MCP desteği yok → geçici köprü: agent'ın `mphone run` alt sürecini çağıran tek araç (Hermes eklentisi modeli).

#### Go/No-Go
M1 ürün + teknik onayı. **No-Go** ise (başarı < %85): P5'e geçmeden skill/helper iyileştirme turu (en fazla 1 hafta).

---

### P4 — iPhone Mirroring Backend

**Süre:** 2 hafta · **Kol:** B · **Önkoşul:** P1 (P3 tamamlanmış olması tercih edilir — CLI/MCP'yi yeniden kullanır), Mac (macOS 15+) + iPhone (iOS 18+)

#### Hedef
Mac'e iPhone Mirroring ile bağlı iPhone'u aynı protokol ve helper'larla kontrol etmek.

#### Kapsam
- Plan.md §8.2.2'nin tamamı: pencere bulma, yakalama (öne almadan), cihaz-yerel koordinat dönüşümü (**kritik karar** — Plan.md §6.4), arka plan olay gönderimi (SkyLight) + ön plan yedeği, kaydırma tekerleği, klavye/yapıştırma, Spotlight ile uygulama açma, durum makinesi (Connect'e bir kez bas, interstitial okuma, "iPhone in Use" → `NEEDS_USER`), Vision OCR (`tr-TR`).
- `focus.probe/diff` gerçek uygulaması (kullanıcının Mac'teki işini bozuyor muyuz?).
- `mphone doctor ios` (Erişilebilirlik, Ekran Kaydı izinleri, pencere, durum).
- Varsayılan `agent_helpers.py`'ye `tap_icon` (ana ekran etiketinin ~35 pt üstü) — **cihaz-yerel piksele** çevrilmiş haliyle (ölçek ile).
- SKILL.md iPhone bölümü.
- Gerçek iPhone ile manuel + yarı otomatik test seti (CI'da çalışmaz; self-hosted Mac runner gecelik).

#### Kapsam Dışı
- Çoklu iPhone (P8), uzak node üzerinden iPhone (P5 sonrası otomatik gelir: node macOS'ta da çalışır).

#### Çıkış Kriterleri (M1.5)
- [ ] "Ayarlar → Genel → Hakkında → iOS sürümü" ve "Notlar'a Türkçe not" görevleri 20 tekrarda ≥ 18 başarı.
- [ ] Ekran görüntüsündeki bir noktaya `tap(x, y)` doğrudan dokunur (koordinat dönüşümü testli; pencere taşınınca da doğru).
- [ ] Arka plan modunda dokunma/yazma, kullanıcının Mac'teki ön plan uygulamasından odağı **çalmaz** (`focus.diff` testli).
- [ ] iPhone kilit açıldığında ("iPhone in Use") tüm girdi op'ları `NEEDS_USER` + doğru talimatla durur; Connect döngüsü yok.
- [ ] `back()`, `current_app()`, `ui()` → açık `UNSUPPORTED`.
- [ ] PITFALLS.md iOS bölümü.

#### Demo
Mac'te iPhone Mirroring açık; Milyonus Agent aynı MCP araçlarıyla iPhone'da görev yapar; kullanıcı Mac'te başka uygulamada yazarken odak bozulmaz.

#### Riskler
- macOS güncellemesi davranışı değiştirir (R1) → node'larda macOS sürümünü sabitle; davranış testleri.
- SkyLight özel API'si → yedek ön plan yolu her zaman çalışır durumda tutulur.

#### Go/No-Go
Teknik onay. Başarı < %80 ise iOS'u "beta" etiketiyle sun, P8 (WDA) önceliğini artır.

---

### P5 — Uzaktan Kontrol: Node + Gateway + Runner

**Süre:** 3 hafta · **Kol:** A · **Önkoşul:** P3 (M1)

#### Hedef
Agent'ların, fiziksel olarak başka yerdeki telefonları Gateway üzerinden **güvenli, çakışmasız, izlenebilir** şekilde kontrol etmesi. **M2.**

#### Kapsam
**Hafta 1 — Gateway temeli ve Node:**
- Gateway iskeleti (FastAPI, ayarlar, DB oturumu, Alembic, Redis, S3 istemcisi, yapılandırılmış log, OTel).
- Veri modeli (Plan.md §8.4.2) + migrasyonlar.
- Kimlik: API anahtarları (oluştur/doğrula/kapsam), node enrollment + JWT, admin bootstrap komutu.
- Node daemon: enroll, WS bağlantısı + yeniden bağlanma, keşif döngüsü, cihaz başına seri op kuyruğu, `hello/device.update/op.request/op.response/health` mesajları (Plan.md §8.3).
- Router: tek Gateway örneği için doğrudan; çok örnek için Redis pub/sub (hafta 3).

**Hafta 2 — Lease, op API, audit, remote backend:**
- Lease servisi (Plan.md §8.4.4): acquire (id/seçici), heartbeat, release, TTL süresi dolma işi, kuyruk, node kopması grace.
- `POST /v1/devices/{id}/ops` + `ops-ws`, op işleme hattı (§8.4.5) — politika P5'te temel kurallarla (`no-raw-remote`, `never-type-secrets`, `secret-looking-text`, hız sınırı); `approve` kararı P5'te **deny + mesaj** olarak davranır (onay akışı P6).
- Audit yazımı (Redis stream → Postgres toplu), `GET /v1/audit`.
- Artefaktlar: önceden imzalı yükleme (node → S3), `GET /v1/artifacts/{id}`.
- `remote` backend (SDK ile ortak istemci), `mphone-sdk` Python istemcisi.

**Hafta 3 — Runner, MCP HTTP, çok örnek, sağlamlaştırma:**
- Runner: kuyruk, Docker + gVisor konteyneri, run token'ı, workspace indirme, stdout SSE, artefakt toplama, limitler.
- `POST /v1/runs` + `GET /v1/runs/{id}` + `/stream`.
- MCP Streamable HTTP (`/mcp`) — P3'teki araçlar + `phone_approval_status` (P6 için yer tutucu) + `phone_workspace_get/update`.
- Agent workspace sürümleme.
- Çok Gateway örneği (Redis yönlendirme), `docker compose` yerel yığını, tek VM staging dağıtımı (Caddy TLS).
- Node: systemd unit, udev kuralları, macOS LaunchAgent (P4 ile iPhone uzaktan da çalışır).
- Fake node simülatörü (yük testleri için: N sahte cihaz).

#### Kapsam Dışı
- Dashboard UI (P6) — P5'te yönetim işlemleri CLI/API ile (`mphone admin …`).
- Onay akışı ve devralma (P6). Canlı görüntü (P6).

#### Teslimatlar
| # | Teslimat |
|---|---|
| D5.1 | `mphone-gateway` (API, auth, registry, leases, router, policy-temel, audit, artifacts, runs, mcp_http, workspaces) |
| D5.2 | `mphone-node` + servis dosyaları |
| D5.3 | `mphone-runner` + sandbox imajı |
| D5.4 | `mphone-sdk` + `remote` backend |
| D5.5 | `deploy/docker-compose.yml`, staging dağıtımı |
| D5.6 | Runbook: node kurulumu, cihaz ekleme, API anahtarı verme |

#### Çıkış Kriterleri (M2)
- [ ] Fake E2E: MCP(HTTP) → Gateway → Runner → Remote → Gateway → fake node → fake backend tam zinciri CI'da yeşil; lease çakışması, TTL dolması, node kopması (grace içinde dönüş + dönmeme), hız sınırı senaryoları testli.
- [ ] Gerçek: staging Gateway + farklı ağdaki Linux node + 2 Android; iki farklı agent anahtarıyla iki telefon eşzamanlı; 50 görevlik koşu, lease çakışması 0.
- [ ] Op ek yükü (gateway+node) p95 < 150 ms (aynı bölge); `tap` uçtan uca p95 < 800 ms.
- [ ] Her op audit'te: agent, lease, run, op, kw (maskeli), sonuç, süre, trace_id.
- [ ] Runner: sandbox'tan internete çıkış engelli (test: `urllib` ile dış istek başarısız), agent API anahtarı konteyner ortamında yok, zaman aşımı ve çıktı limiti çalışıyor.
- [ ] Node 60 sn içinde otomatik yeniden bağlanır; cihazlar kaybolmaz.
- [ ] Hiçbir senaryoda op başka cihaza yönlendirilmez (testli).
- [ ] Yük testi: 200 sahte cihaz, 50 eşzamanlı lease, 30 dk; hata oranı < %0.5.

#### Demo (M2)
Ofisteki raf node'una bağlı telefonu, uzaktaki bir dizüstünde çalışan Milyonus Agent kontrol eder; aynı anda ikinci agent ikinci telefonda çalışır; `mphone admin audit --device …` ile tüm op'lar listelenir.

#### Riskler
- gVisor kurulumu staging'de zorlanırsa → geçici olarak Docker `--network` kısıtlı + seccomp, P9'da gVisor zorunlu.
- WS yönlendirme karmaşıklığı → P5'te tek Gateway örneği ile M2, çok örnek P9'a kayabilir (çıkış kriteri değil).

#### Go/No-Go
M2 ürün + teknik + güvenlik ön onayı (güvenlik: auth, sandbox, audit gözden geçirmesi).

---

### P6 — Canlı İzleme, Onay, Devralma, Dashboard

**Süre:** 2.5 hafta · **Kol:** A (frontend için ek kaynak önerilir) · **Önkoşul:** P5

#### Hedef
İnsanların sistemi **gözetebilmesi ve gerektiğinde müdahale edebilmesi**: canlı ekran, onay kuyruğu, devralma, run tekrar oynatma, politika yönetimi. **M3.**

#### Kapsam
- **Canlı görüntü:** node tarafında Android için scrcpy (H.264 → node'da MJPEG'e çevirme veya JPEG `screencap` döngüsü — MVP), iOS için pencere yakalama döngüsü; ikili WS çerçeveleri; Gateway rölesi (`/v1/devices/{id}/live`), izleyici sayısına göre akış başlat/durdur; FPS/çözünürlük uyarlaması.
- **Onay akışı:** politika `approve` kararı → `approvals` kaydı + tetikleyici ekran görüntüsü (hedef box vurgulu) → bildirim (dashboard WS, Slack webhook) → `APPROVAL_REQUIRED` → `auto_wait_approval` (remote backend) → karar → aynı op'un `approval_id` ile yürütülmesi (op+kw hash doğrulaması) → süre aşımı (`expired`).
- **Politika motoru tam sürüm:** Plan.md §10.3 YAML biçimi, hedef box çözümleme, uygulama kategorileri, güven seviyeleri; politika simülatörü API'si.
- **Devralma:** `request_human` → takeover isteği; `takeover/handback` API; lease `paused`; insan girdileri (`input.*` op'ları insan kimliğiyle), `input.text` maskeleme.
- **Dashboard (Next.js):** Plan.md §8.10'daki ekranlar 1–9; OIDC SSO; rol kontrolü.
- **Run replay:** op zaman çizelgesi + ekran görüntüsü şeridi (her girdi op'undan sonra otomatik küçük ekran görüntüsü — yapılandırılabilir, varsayılan açık, 480 px JPEG).
- **Webhook'lar:** `lease.*`, `approval.*`, `device.*`, `run.*` olayları, HMAC imzalı.
- SKILL.md güncellemesi: onay ve devralma davranışı.

#### Kapsam Dışı
- WebRTC (v2), mobil dashboard uygulaması.

#### Çıkış Kriterleri (M3)
- [ ] Canlı görüntü: ≥ 10 fps, < 500 ms gecikme (aynı bölge), 5 eşzamanlı izleyici.
- [ ] "Gönder" senaryosu: onaya düşer → Slack + dashboard bildirimi < 3 sn → onay → mesaj gönderilir; red → script `APPROVAL_DENIED` ile durur ve agent kullanıcıya bildirir. Onaylanan op'un argümanı değiştirilmeye çalışılırsa (hash uyuşmazlığı) reddedilir (testli).
- [ ] Devralma: operatör 2FA kodunu girer, audit'te `user_id` ile ve **maskeli**; geri verince agent notu alır ve devam eder.
- [ ] Run replay: her girdi op'u için önce/sonra küçük görüntü; 20 op'luk run 2 sn'de yüklenir.
- [ ] Politika simülatörü: "bu op bu ekranda ne karar alır" doğru sonuç verir (20 kural testi).
- [ ] Dashboard erişilebilirlik ve rol testleri: `viewer` onay veremez, devralamaz.
- [ ] Operasyon ekibinden 2 kişi, dokümansız 15 dk içinde onay + devralma yapabildi (kullanılabilirlik testi).

#### Demo (M3)
Agent WhatsApp Business'ta müşteri yanıtı hazırlar → "Gönder" onaya düşer → operatör Slack'ten dashboard'a geçer, ekran görüntüsünü görür, onaylar → gönderilir. Ardından Instagram girişinde 2FA → operatör devralır, kodu girer, geri verir → agent devam eder. Sonra run replay izlenir.

#### Riskler
- Frontend iş yükü → hazır bileşen kütüphanesi (shadcn/ui), ekran sayısını önceliklendir (1, 2, 3, 4 zorunlu; 5–9 M3 sonrası 1 hafta içinde).
- Hedef box çözümlemesinin ek `screen.text` maliyeti → yalnızca uygulama eşleşmesi olan durumlarda; önbellek.

#### Go/No-Go
M3 ürün + operasyon onayı. Bu kapıdan sonra **gerçek iş süreçlerinde pilot kullanım** başlayabilir (sınırlı agent, sınırlı cihaz).

---

### P7 — Android Companion App

**Süre:** 3 hafta · **Kol:** B · **Önkoşul:** P1 (protokol), P5 (Gateway companion uç noktaları — paralel geliştirilebilir), Android geliştirme deneyimi

#### Hedef
Host bilgisayar olmadan, internetteki herhangi bir Android telefonu kontrol edebilmek; ayrıca node'a bağlı telefonlarda ağaç okumayı ve Türkçe yazımı hızlandırmak. **M4.**

#### Kapsam
- Plan.md §8.9'un tamamı: AccessibilityService (ağaç, jestler, global eylemler, ACTION_SET_TEXT), IME, ekran yakalama (MediaProjection + `takeScreenshot` yedeği), ön plan servisi, WSS bağlantısı, OpDispatcher, LocalSocketServer (hibrit), QR enrollment, Keystore kimliği, SafetyOverlay + "Durdur", ML Kit OCR.
- Gateway: `/v1/companion/enroll`, `/v1/companion/connect`; companion cihazları registry'de `kind=companion`.
- `android_adb` hibrit modu: Companion App varsa `tree`/`screen.text`/`input.text` yerel soketten.
- İzin kurulum sihirbazı (uygulama içi: Erişilebilirlik, IME, pil optimizasyonu muafiyeti, bildirim izni, ekran yakalama).
- Dağıtım: imzalı APK, sürümleme, güncelleme bildirimi; MDM uyumluluğu notu.
- Protokol uyum testi: Kotlin tarafında JSON Schema'dan üretilmiş modeller + paylaşılan uyum test vektörleri (`tests/fixtures/protocol_vectors/`).

#### Kapsam Dışı
- iOS companion (mümkün değil — iOS başka uygulamaları kontrol etmeye izin vermez).
- Play Store yayını.

#### Çıkış Kriterleri (M4)
- [ ] 4G'deki bir telefon (host yok) QR ile 2 dk içinde kaydolur, Gateway'de `ready` görünür.
- [ ] Agent eval görev seti companion cihazda ≥ %90 başarı.
- [ ] `screen()` p95 < 400 ms; Türkçe + emoji yazım %100 (100 rastgele Türkçe cümle testi).
- [ ] Hibrit mod: node'a bağlı telefonda `screen()` süresi uiautomator'a göre ≥ 5× hızlı.
- [ ] Telefondaki "Durdur" düğmesi lease'i < 1 sn'de `revoked` yapar, agent `LEASE_EXPIRED/REVOKED` alır.
- [ ] Bağlantı koptuğunda (uçak modu 30 sn) otomatik yeniden bağlanır; uygulama 24 saat arka planda öldürülmeden çalışır (Samsung + Xiaomi + Pixel).
- [ ] Parola alanına yazma cihaz tarafında da reddedilir.
- [ ] `FLAG_SECURE` ekranlar `details.secure=true` ile açıkça bildirilir.

#### Demo (M4)
Satış temsilcisinin sahadaki telefonu (Companion yüklü), ofisteki Milyonus Agent tarafından kontrol edilir; temsilci ekranda çerçeveyi görür, istediği an "Durdur"a basar.

#### Riskler
- Üretici arka plan kısıtları (R10) → marka bazlı kurulum rehberi + `dontkillmyapp` önerileri.
- MediaProjection kısıtları (R4) → `takeScreenshot` yedeği.
- Play Protect uyarıları (erişilebilirlik kullanan yan yüklenmiş uygulama) → MDM ile dağıtım, kullanıcı rehberi.

#### Go/No-Go
M4 ürün onayı + KVKK onayı (çalışan telefonları söz konusuysa — Q2).

---

### P8 — iOS WebDriverAgent (Filo)

**Süre:** 2.5 hafta · **Kol:** B · **Önkoşul:** P5, Apple Developer hesabı (Q10), Mac mini + ≥ 2 iPhone · **Durum:** Opsiyonel (Q3/Q4'e bağlı)

#### Hedef
Bir Mac'e birden fazla iPhone bağlayıp ağaç tabanlı, güvenilir kontrol (iPhone Mirroring'in tek cihaz ve kırılganlık sınırlarını aşmak).

#### Kapsam
- Plan.md §8.2.3: WDA derleme/imzalama betikleri, cihaz başına WDA yaşam döngüsü (başlat, sağlık, çökmede yeniden başlat), port yönlendirme, WDA HTTP istemcisi, tüm desteklenen op'lar, ağaç → box (`source="tree"`), bundleId çözümleme.
- Node keşfine `ios_wda` cihazları.
- İmza süresi takibi ve uyarı (profil bitişine 14 gün kala).
- `doctor ios-wda`.

#### Çıkış Kriterleri (M4.5)
- [ ] 1 Mac'te 3 iPhone eşzamanlı, agent eval ≥ %85.
- [ ] WDA çökmesinde 30 sn içinde otomatik toparlanma.
- [ ] `screen()` ağaçtan, p95 < 1.5 sn.

#### Go/No-Go
Teknik onay. Apple hesabı yoksa faz ertelenir; iOS yalnızca Mirroring ile devam eder.

---

### P9 — Sertleştirme, Güvenlik Denetimi, GA

**Süre:** 2 hafta · **Kol:** A (+ B P8 bittiyse) · **Önkoşul:** P6 (M3); P7 tercihen

#### Hedef
Prod'a çıkış: ölçek, dayanıklılık, güvenlik, operasyonel hazırlık. **M5 — GA.**

#### Kapsam
- **Yük ve kaos:** Plan.md §12 yük (200 cihaz/50 lease/2 saat) ve kaos (node kesme, Redis restart, gateway pod öldürme, yavaş ağ) testleri; bulguların düzeltilmesi.
- **Çok örnekli Gateway** (P5'te kaldıysa), HPA, PodDisruptionBudget, drain.
- **Güvenlik:** harici pentest (veya iç kırmızı takım): auth, kapsam yükseltme, runner kaçışı, node taklidi, IDOR (başka org'un cihazı), SSRF (artefakt URL'leri), WS kimlik; bulguların kapatılması. Bağımlılık ve imaj taraması temiz. Gizli bilgi rotasyonu prosedürü.
- **KVKK:** saklama işleri (otomatik silme), dışa aktarma/silme talebi prosedürü, aydınlatma metni, erişim kayıtları.
- **Gözlemlenebilirlik:** Grafana panoları, uyarı kuralları (Plan.md §11.4), SLO tanımları (op başarı %99, gateway erişilebilirlik %99.5, tap p95 < 800 ms).
- **Runbook'lar:** node arızası, cihaz `unauthorized`, toplu kilitlenme, gateway olay müdahalesi, API anahtarı sızıntısı, politika acil değişikliği ("tüm onayları zorunlu yap" anahtarı = kill switch), yedekten geri dönüş.
- **Prod dağıtımı:** Helm chart, Terraform (Q6'ya göre), yedekleme (Postgres PITR, S3 versiyonlama), felaket kurtarma tatbikatı.
- **Dokümantasyon:** kullanıcı rehberi (operatörler), geliştirici rehberi (yeni backend/op ekleme), agent entegrasyon rehberi son sürüm.
- **Pilot → GA:** 2 hafta pilot verisiyle SLO doğrulaması.

#### Çıkış Kriterleri (M5)
- [ ] Pentest kritik/yüksek bulgu = 0 açık.
- [ ] SLO'lar 14 gün boyunca tutuldu (pilot).
- [ ] Felaket kurtarma tatbikatı: RPO < 5 dk, RTO < 1 saat.
- [ ] Kill switch testi: tek komutla tüm agent op'ları durur (< 5 sn).
- [ ] Tüm runbook'lar bir kez tatbik edildi.
- [ ] Prod'da ≥ 10 cihaz, ≥ 2 node, ≥ 2 agent.

#### Go/No-Go
Yönetim onayı. GA sonrası değişiklik yönetimi: sürüm notları, haftalık sürüm treni.

---

## 5. Fazlar Arası Bağımlılıklar

```
P0 ──► P1 ──► P2 ──► P3 (M1) ──► P5 (M2) ──► P6 (M3) ──► P9 (M5)
        │             │            │   │                   ▲
        │             └──► P4 ─────┘   └──► P8 ────────────┤ (opsiyonel)
        │                  (M1.5)            (M4.5)        │
        └──────────────────────► P7 (protokol P1'den; Gateway uçları P5'ten) ──► (M4)
```

| Bağımlılık | Neden |
|---|---|
| P2 → P1 | Backend, protokol ve `Backend` taban sınıfını kullanır |
| P3 → P2 | MVP gerçek cihaz ister |
| P4 → P1 (+P3 tercihen) | Aynı protokol; CLI/MCP yeniden kullanılır |
| P5 → P3 | Uzak mod, yerelde kanıtlanmış helper/MCP/skill'i taşır |
| P6 → P5 | Onay/devralma lease ve op hattına bağlı |
| P7 → P1, P5 | Protokol + companion uç noktaları |
| P8 → P5 | Node keşfi ve uzaktan erişim |
| P9 → P6 | GA, gözetim olmadan yapılmaz |

---

## 6. Faz Kapısı (Go/No-Go) Süreci

Her faz sonunda 45 dakikalık **faz kapısı toplantısı**:

1. **Demo** (canlı, kayıt alınır) — fazın demo senaryosu.
2. **Çıkış kriterleri kontrol listesi** — her madde kanıtıyla (test çıktısı, metrik paneli, video).
3. **Metrikler** — hedef vs gerçekleşen.
4. **Riskler** — yeni riskler, kapanan riskler (Plan.md §15 güncellenir).
5. **Plan sapması** — süre, kapsam; Plan-Actions.md durum güncellemesi.
6. **Karar:** `GO` / `GO (koşullu: …)` / `NO-GO (düzeltme planı + yeni tarih)`.
7. **Kayıt:** `docs/phase-gates/P<n>.md` (karar, katılımcılar, kanıt bağlantıları).

**Koşullu GO kuralları:** Yalnızca "Kritik olmayan" kriterler ertelenebilir; ertelenen her madde bir sonraki fazın ilk haftasına kalem olarak eklenir. Güvenlik, Türkçe yazım, "başka cihaza düşmeme", lease özelliği ve audit kriterleri **asla** ertelenmez.

---

## 7. Fazlar Boyunca Sürekli İşler

| İş | Sıklık | Sorumlu |
|---|---|---|
| PITFALLS.md güncellemesi (her yeni platform keşfinde) | Sürekli | Keşfeden |
| Agent eval koşusu + rapor | Haftalık (P3'ten itibaren) | Kol A |
| Gerçek cihaz gecelik testleri | Gecelik (P2'den itibaren) | Kol B |
| Bağımlılık güncellemeleri (Renovate/Dependabot) | Haftalık | Dönüşümlü |
| ADR yazımı (her önemli karar) | Karar anında | Karar sahibi |
| CHANGELOG | Her PR | PR sahibi |
| Güvenlik incelemesi (auth/sandbox/politika dokunan PR'lar) | PR bazında | İkinci göz zorunlu |
| Plan-Actions.md durum sütunu | Haftalık | Teknik lider |

---

## 8. Faz Sonrası (v2 Yol Haritası)

GA sonrası değerlendirilecek (öncelik sırası Q5 ve pilot geri bildirimine göre):

1. **WebRTC canlı görüntü** (< 250 ms, düşük bant genişliği).
2. **Çoklu dokunma** (Companion: pinch/rotate `dispatchGesture` çoklu stroke).
3. **Görsel öğe tespiti** (ikonlar için küçük bir dedektör modeli; etiketsiz düğmeleri box olarak döndürme, `source="vision"`).
4. **Kayıt → yeniden oynatma** (insanın devraldığı adımları kaydedip agent helper'ına dönüştürme — "teach mode").
5. **Görev şablonları / iş akışları** (sık görevler için doğrulanmış script kütüphanesi, agent workspace'ten terfi).
6. **Üçüncü taraf cihaz bulutları** (`remote` backend üzerinden).
7. **TypeScript SDK** ve Milyonus iç servisleri için olay tabanlı entegrasyon.
8. **Cihaz havuzu otomasyonu:** USB port güç döngüsü, otomatik yeniden başlatma, uygulama sürümü sabitleme.
9. **SMS/çağrı olayları** (Companion: gelen SMS'i agent'a olay olarak — yalnızca açık rıza ve politika ile; 2FA kodlarının otomatik okunması **yapılmaz** v2'de bile, ayrı güvenlik incelemesi gerektirir).
