# Karar Kaydı (A0.06)

Plan.md §16'daki açık sorular. **Durum:** 2026-10-14'te kullanıcı tüm kararları Claude'a bıraktı ("en mantıklı seçimleri yap"); hepsi kesinleşti. Değiştirmek isteyen satırı güncellesin ve etkilenen kalemleri gözden geçirsin. Bir cevap geldiğinde: satırı güncelle, "Etkilenen kalemler" sütunundaki işleri gözden geçir, gerekiyorsa ADR yaz.

Durum: `varsayılan` = cevap bekleniyor, varsayılanla ilerleniyor · `kesin` = karar verildi.

| # | Soru | Karar | Durum | Karar veren | Tarih | Etkilenen kalemler |
|---|---|---|---|---|---|---|
| Q1 | Milyonus Agent hangi dil/çatı, MCP istemcisi var mı? | MCP birincil entegrasyon; MCP yoksa `integrations/milyonus/` altında ince köprü (tek `phone_exec` aracı) + Python SDK | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | A3.09, A5.16 |
| Q2 | Hangi telefonlar? | Şirkete ait raf/ofis telefonları. Çalışan/kişisel telefonlar ancak P7 + KVKK onayı sonrası | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | H-07, A9.07, P7 |
| Q3 | Platform önceliği? | Android önce (Türkiye pazar payı, adb ile sıfır kurulum, CI'da emülatör) | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | Phases.md §2 |
| Q4 | Cihaz sayısı? | 3 ay: 10, 12 ay: 50 | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | H-03, NFR-04/05 |
| Q5 | Öncelikli senaryolar? | WhatsApp Business + genel uygulama gezinme; bankacılık varsayılan olarak politikayla kapalı | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | Politika varsayılanları, agent eval |
| Q6 | Barındırma? | Staging: tek VM + docker compose (A5.20). Prod: AWS eu-central-1 (Frankfurt); KVKK gereği Türkiye bölgesi şart çıkarsa yerel sağlayıcıya taşınabilir şekilde Terraform | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | A5.20, A9.09 |
| Q7 | SSO? | Google Workspace OIDC (Auth.js sağlayıcısı değiştirilebilir) | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | A6.09 |
| Q8 | Onay bildirimi? | Dashboard + Slack webhook | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | A6.06 |
| Q9 | Açık / kapalı kaynak? | Repo **public** (kullanıcı kararı), lisans **Apache-2.0**: MIT kadar serbest + açık patent lisansı ve patent davası koruması; şirket projesi için daha güvenli. Dağıtım: GitHub Releases + git URL; PyPI ad uygunluğu sonrası | kesin | kullanıcı (public) + Claude (lisans) | 2026-10-14 | LICENSE, NOTICE, A3.11 |
| Q10 | Apple Developer hesabı? | Yok → P8 (WDA) opsiyonel; iOS yalnızca iPhone Mirroring ile (P4) | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | P8 |
| Q11 | Operatörler? | Başlangıçta repo sahibi tek operatör; mesai saatleri; P6'da ikinci operatör eklenir | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | P6, H-15 |
| Q12 | Saklama? | Ekran görüntüsü 30 gün, audit/meta 1 yıl, run kodu 1 yıl | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | A5.12, A9.07 |
| Q13 | Donanım? | Başlangıç: 1 Linux mini PC + powered hub + 4 Android + (P4 için) 1 Mac mini + 1 iPhone. **Bu geliştirme Mac'inde emülatör yok** (disk %98 dolu, 8 GB RAM); emülatör testleri GitHub Actions'ta | kesin | Claude (kullanıcı yetkisiyle) | 2026-10-14 | H-03, H-04, A2.15 |

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
| 2026-10-14 | Branch koruma: `main`'e 4 CI kontrolü zorunlu (lint + 3 OS test, `strict`), force-push ve silme yasak, doğrusal geçmiş; PR onayı zorunlu **değil**, admin istisnası açık | Tek geliştirici + Claude: onay zorunluluğu akışı kilitler; CI asıl kapı. Ekip büyüyünce 1 onay eklenir |
| 2026-10-14 | Çalışma akışı: her iş dalda + PR; CI yeşilse squash merge | Doğrusal geçmiş, her PR = bir veya birkaç Plan-Actions kalemi |
| 2026-10-15 | Gateway P5'te SQLite (geliştirme/test) + Postgres (üretim, `mphone-gateway[postgres]`) aynı SQLAlchemy modelleriyle; Redis yok, node yönlendirmesi tek örnekte bellekte | Geliştirme Mac'inde Docker yok (8 GB RAM); tek örnek P5 için yeterli. Redis + çok örnek A9.03'te |
| 2026-10-15 | Node kimliği P5'te: tek kullanımlık enrollment token → node secret (yalnızca SHA-256 saklanır, Bearer + TLS). ADR-0004'teki Ed25519 + kısa ömürlü JWT P9 güvenlik sertleştirmesine kaldı | Aynı tehdit modelini daha az parçayla karşılıyor; anahtar rotasyonu P9'da |
| 2026-10-15 | Ekran görüntüleri P5'te op sonucunda base64 olarak taşınır; imzalı URL'li artefakt deposu (A5.12) sonraya | Yerel ağda ve tek örnekte yeterli; büyük kurulumlarda WS'yi tıkamamak için S3 gerekecek |
| 2026-10-15 | Uzak modda politika aynı motorla gateway'de çalışır; olgular (uygulama, ekran) node'dan op ile okunur; onay `allow=[kural]` ile (yereldeki --allow ile aynı sözleşme). Dashboard onay kuyruğu P6 | Tek politika kodu, iki mod |
