# phone-harness Çalışma Notları (A0.09)

> Kaynak: https://github.com/ShawnPana/phone-harness, v0.3.2, MIT. 2026-10-14'te okundu.
> **Bu dosya davranış ve tasarım notudur, kod değildir.** Referans koddan satır kopyalanmaz (CLAUDE.md §9). Mimari özet Plan.md §4'te; burada uygulama sırasında işe yarayacak ayrıntılar var.

---

## 1. Helper yüzeyi (referanstaki imzalar → bizdeki karşılık)

| Referans | Bizde | Not |
|---|---|---|
| `send(op, **kw)`, `supports(op)`, `ops()` | aynı | Tek dikiş |
| `connection_state()`, `connection_detail()` | `connection_state()`, `device.detail` op'u | `session.*` → `device.*` |
| `ensure_device()` | aynı | Her görevin ilk satırı; Mirroring'de Connect'e bir kez basar |
| `activate()`, `find_window()`, `screen_info()` | — / `screen.bounds` | Pencere kavramı backend içinde kalır (tek koordinat uzayı) |
| `image_point()`, `tap_image_point()` | yalnızca `tap_image_point(x, y, image_size)` | Bizde yalnızca **küçültülmüş** görüntü için ölçek; uzay dönüşümü yok |
| `focus_probe()`, `interruption()` | `focus.probe/diff` op'ları | iOS'ta anlamlı, diğerlerinde no-op |
| `screen(min_confidence)`, `ocr_pixels()` | `screen()`, `screen.text_pixels` | |
| `find_text`, `tap_text` | aynı + Türkçe-farkında eşleşme | |
| `ui()`, `find_nodes(query, exact, clickable_only)`, `tap_node`, `tap_ui` | `ui()`, `find_nodes(**selector)`, `tap_ui(query_or_selector)` | Seçici şeması Plan.md §7.5 |
| `tap, long_press, drag, press, type_text(text, delay, keystrokes)` | `type_text(text, mode=…)` | `keystrokes: bool` → `mode` enum (auto/paste/keystrokes/ime) |
| `swipe(direction, distance, at)`, `scroll(direction, amount, at)` | aynı | Anlam farkı korunur |
| `scroll_screen`, `scroll_until`, `scroll_collect` | aynı | Ayrıntı §2 |
| `home, back, app_switcher` | `home, back, recents` (+ `notifications_panel`) | |
| `open_app, current_app, list_apps` | aynı (+ `stop_app`) | |
| `shell(cmd)` | `send("raw", cmd=…)` | Uzak modda varsayılan kapalı |
| `wait(seconds)` | **yok** | Skill zaten `wait(n)` kullanma diyor; sunmuyoruz |
| `wait_for_text, wait_for_app, wait_stable` | aynı | |
| — | `request_human`, `request_approval`, `note`, `clipboard`, `notifications`, `device_info` | Yeni |

## 2. Kaydırma yardımcılarının ince ayrıntıları (yeniden yazarken koru)

1. **Durum çubuğu ve gezinme şeridi hariç tutulur.** "Ekran değişti mi" karşılaştırması, ekranın üst ~%6'sı (saat, pil) ve alt ~%8'i (gezinme çubuğu) dışındaki metinlerle yapılır. Aksi halde saatin dakika değiştirmesi "hareket" sayılır ve liste sonu tespiti hiç tetiklenmez.
2. **Oturma (settle) tam eşitlikle.** Kaydırmadan sonra iki ardışık okumanın metin kümesi **birebir aynı** olana kadar (veya `settle` süresi dolana kadar) beklenir. Ayarlanacak eşik yok; video gibi hiç durmayan ekran bütçesini kullanır.
3. **`scroll_screen` hüküm vermez.** Eskiden Jaccard benzerliği döndürüyormuş; iki tarafta da okunabilir metin olmayan ekranlarda "tamamen farklı" diyerek yanılmış. Şimdi yalnızca `{before, after, boxes}` döner; karar çağıranındır. Bizde de öyle (+ isteğe bağlı `moved` yalnızca "küme eşit mi" bilgisidir, yorum değil).
4. **`scroll_until`:** önce mevcut ekranda predikatı dener; iki kez **birebir aynı** içerik gelirse sonu kabul eder.
5. **`scroll_collect`:** bitiş koşulu "ekstraktörün `end_after` (3) kez yeni öğe üretmemesi"dir — piksel hareketi değil. Liste (öteleme) ve feed (öğe değiştirme) ikisi de ilerlemedir. `amount < 1.0` ki ekranlar örtüşsün ve satır kaçmasın. Yeni öğe gelmeyince kısa ek bekleme (tembel yükleme için).
6. Dönüş: `{items, stop: "reached-end" | "max-scrolls", scrolls}`.

## 3. Op sözlüğü ve backend deseni

- `Backend.send(op)` → `_` + `op.replace(".", "_")` adlı metot; yoksa `Unsupported`. Yetenek listesi elle tutulmaz.
- `ops()` sonucu sözlükteki adlarla kesiştirilir — iç yardımcı metotlar op gibi görünemez.
- `connect()` bir nesne döndürür (modül global'i değil) → bir script iki cihaz tutabilir; helper'lar varsayılan birini bağlar.
- Sözleşme testi: `helpers.py`'deki `send("op", kw=…)` çağrıları AST ile toplanır, her backend metodunun imzasıyla karşılaştırılır. Bizde A1.14.
- Remote backend: `POST <url>/op` `{"op","kw"}`, `GET <url>/ops`; 400 + `unsupported:true` → `Unsupported`; 404 → oturum yok; host'un hata metnindeki tip öneki (`RuntimeError: …`) çift basılmasın diye ayıklanır. Bizde hata kodları yapılandırılmış olduğundan bu ayıklamaya gerek yok.

## 4. Hermes eklentisinden güvenlik kararları

| Karar | Bizde |
|---|---|
| Her `phone_exec` çağrısı kullanıcı onayı ister; "oturum boyu/her zaman" cevabı `rule_key` ile hatırlanır | MCP istemcisinin onay mekanizması + uzakta op düzeyi politika |
| Sınıflandırıcıyla otomatik çalıştırma **açıkça opt-in**; sınıflandırıcı sezgisel ve atlatılabilir | Bizde AST ön kontrolü yalnızca savunma derinliği; asıl koruma sandbox (ADR-0007) |
| Sınıflandırıcının reddettikleri: helper modülü dışı import, `open/eval/exec/__import__` ve takma adları, `send("raw", …)`, dunder erişimi | Runner AST ön kontrolü (A5.18) aynı listeyle başlar |
| Alt süreç ortamından `*_API_KEY`, `*_TOKEN`, `*_SECRET` temizlenir | Aynı + `*_PASSWORD` (A3.01) |
| Aynı süreçte aynı anda tek script telefonu sürer (120 sn kilit bekleme) | Yerelde dosya kilidi (A3.03), uzakta lease |
| Zaman aşımı varsayılan 300 sn, en az 5, en çok 1800; çıktı 50 KB, stderr 4 KB | Aynı sınırlar |
| Çağrı sırasında kaydedilen ekran görüntüsü sonuca eklenir (model görüntü görebiliyorsa) | MCP image content, en fazla 4 görüntü |

## 5. SKILL.md'den çalışma yöntemi (bizim skill'in iskeleti)

1. Her script `# task:` (kullanıcı isteği, görev boyunca aynı) + `# step:` ile başlar.
2. Kullanıcıya her script öncesi bir satır (ne yapacağım), sonrası bir satır (ne gördüm). Art arda sessiz iki script yok.
3. Ekranı `screen()` ile oku; ekran görüntüsü yalnızca OCR'ın göremediği için (ikon, görsel, durum).
4. Eylem → Doğrula → Uyarla: değişmesi gerekeni adlandır → tek eylem + tek kontrol → kanıtlanmış diziyi tek script'te topla → hata olursa izole et, tek hipotez test et → öğrendiğini `agent_helpers.py`'ye yaz.
5. "Telefonum" = kişisel telefon; çalışan başka bir oturuma asla düşme.
6. Web'de/API'de yapılabiliyorsa telefonu kullanma.
7. Rıza: göndermek, paylaşmak, takip etmek, satın almak, silmek, ayar değiştirmek öncesi sor; PIN/parola/2FA asla.
8. Fiziksel adımlar kullanıcının; mesajı aktar ve dur; "tamam" sonrası bir kez dene.

## 6. Bilinçli olarak almadıklarımız

- Kapalı kaynak bulut CLI'ı (`cloud.py`, ~1900 satır: OAuth, katalog, faturalama) — yerine kendi Gateway + lease.
- Anonim kullanım telemetrisi — yerine OTel + audit (kendi altyapımızda).
- Platforma göre değişen koordinat uzayı — tek uzay (Plan.md §6.4).
- `wait(seconds)` helper'ı.
