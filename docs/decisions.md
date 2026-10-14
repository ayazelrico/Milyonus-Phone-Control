# Karar Kaydı (A0.06)

Plan.md §16'daki açık sorular. **Durum:** 2026-10-14 itibarıyla cevaplar gelmedi; proje **varsayılanlarla** ilerliyor (kullanıcı "başlayabilirsin" dedi). Bir cevap geldiğinde: satırı güncelle, "Etkilenen kalemler" sütunundaki işleri gözden geçir, gerekiyorsa ADR yaz.

Durum: `varsayılan` = cevap bekleniyor, varsayılanla ilerleniyor · `kesin` = karar verildi.

| # | Soru | Karar | Durum | Karar veren | Tarih | Etkilenen kalemler |
|---|---|---|---|---|---|---|
| Q1 | Milyonus Agent hangi dil/çatı, MCP istemcisi var mı? | MCP istemcisi var veya eklenebilir; entegrasyon MCP ile | varsayılan | — | 2026-10-14 | A3.09 (köprü gerekebilir), A5.16 SDK önceliği |
| Q2 | Hangi telefonlar: şirket rafı, çalışan, müşteri? | Şirkete ait raf/ofis telefonları | varsayılan | — | 2026-10-14 | KVKK (H-07, A9.07), P7 önceliği |
| Q3 | Platform önceliği? | Android önce | varsayılan | — | 2026-10-14 | Faz sırası (Phases.md §2.2) |
| Q4 | Cihaz sayısı (3 ay / 12 ay)? | 10 / 50 | varsayılan | — | 2026-10-14 | H-03, NFR-04/05 |
| Q5 | Öncelikli kullanım senaryoları? | WhatsApp Business + genel uygulama gezinme | varsayılan | — | 2026-10-14 | Politika varsayılanları, agent eval seti |
| Q6 | Barındırma / veri yerleşimi? | AWS eu-central-1 veya Türkiye'de yerel sağlayıcı | varsayılan | — | 2026-10-14 | A5.20, A9.09 |
| Q7 | SSO kimlik sağlayıcı? | Google Workspace OIDC | varsayılan | — | 2026-10-14 | A6.09 |
| Q8 | Onay bildirim kanalı? | Slack + dashboard | varsayılan | — | 2026-10-14 | A6.06 |
| Q9 | Açık / kapalı kaynak? | Repo **public** (GitHub: ayazelrico/Milyonus-Phone-Control). Lisans şimdilik "All rights reserved" — açık kaynak lisansı (MIT/Apache-2.0) ayrıca karar bekliyor | kesin (repo görünürlüğü) | ayazelrico | 2026-10-14 | LICENSE, A3.11 paket deposu |
| Q10 | Apple Developer hesabı? | Yok → P8 opsiyonel | varsayılan | — | 2026-10-14 | P8 |
| Q11 | Güven seviyeleri ve operatörler? | 2 operatör, mesai saatleri | varsayılan | — | 2026-10-14 | P6, H-15 |
| Q12 | Saklama süreleri? | Ekran görüntüsü 30 gün, meta/audit 1 yıl | varsayılan | — | 2026-10-14 | A5.12, A9.07 |
| Q13 | Donanım bütçesi? | 1 Linux node + 4 Android + 1 Mac mini + 1 iPhone | varsayılan | — | 2026-10-14 | H-03, H-04 |

## Uygulama sırasında alınan kararlar

| Tarih | Karar | Gerekçe |
|---|---|---|
| 2026-10-14 | Python paketleri `hatchling` ile derlenir; kök proje paketlenmez (`tool.uv.package = false`) | ADR-0002; kök yalnızca geliştirme ortamı |
| 2026-10-14 | `ruff format` Markdown dosyalarını biçimlendirmez | Dokümanlardaki kod blokları açıklayıcı örneklerdir; biçimlendirici okunurluğu bozuyordu |
| 2026-10-14 | Tüm yerel durum tek dizinde: `MPHONE_HOME`, yoksa `~/.mphone` (config.toml, cache/, runs/, audit/, locks/, agent-workspace/) — XDG ayrımı yok | Tek yer = kolay destek ve temizlik; Windows'ta aynı davranış |
| 2026-10-14 | Agent workspace varsayılanı paketin içinde (`mphone_core/workspace_default/`); kökteki `agent-workspace/` kaldırıldı | Tek kopya, wheel'e ek ayar gerekmeden girer |
| 2026-10-14 | Fake senaryoları paketin içinde (`mphone_backends/fake/scenarios/`), `tests/fixtures/fake` yerine | `connect("fake:…")` testler dışında da (demo, MCP denemesi) çalışsın |
| 2026-10-14 | `send()` slot'a şemanın **tüm** argümanlarını varsayılanlarıyla geçirir; slot imzaları şemayla birebir olmalı | Varsayılanlar tek yerde (şema); sözleşme testi eksik/fazla parametreyi yakalar |
| 2026-10-14 | `connect(uri)` yeni bir `Phone` döndürür, varsayılanı değiştirmez; varsayılanı `use(...)` seçer | Bir script iki cihazı karıştırmadan tutabilsin |
| 2026-10-14 | Selector şemasına `query` anahtarı eklendi (text / content_desc / resource_id içinde arar) | `tap_ui("Gönder")` etiketsiz ikonları da bulsun |
| 2026-10-14 | Protokol v1'de 39 op (A1.01'deki "40+" tahmini yerine); Plan.md §7.4 tablosunun tamamı | Tablo eksiksiz; sayı tahmindi |
| 2026-10-14 | Fake ekran görüntüleri Türkçe glifli bir sistem fontu kullanır (Arial / DejaVu), yoksa Pillow varsayılanı | Pillow'un yerleşik fontunda ı/ğ/ş yok; görüntüler OCR testine girdi olacak |
| 2026-10-14 | Fake telefon parola alanlarını ağaçta `•` ile maskeler | Gerçek Android davranışı; politika testleri gerçekçi olsun |
