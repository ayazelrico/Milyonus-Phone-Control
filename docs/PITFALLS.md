# Platform Tuzakları (PITFALLS.md)

> Bir backend'e (Android, iOS, Companion, uzak) dokunmadan önce bu dosyayı oku (CLAUDE.md §6).
> Her madde: **Belirti → Neden → Çözüm → Test**. "Test" sütunu `TODO A2.xx` ise ilgili kalemde kilitlenecek.
> Kaynak v0: phone-harness v0.3.2 SKILL.md, install.md ve kaynak kod gözlemleri (Plan.md §4.3). Yeni bir şey öğrendiğinde buraya ekle.

---

## Android (adb)

### android-tree-slow
- **Belirti:** `screen()` yavaş telefonda 2–3 sn sürüyor.
- **Neden:** `uiautomator dump` her çağrıda erişilebilirlik ağacını baştan serileştirir.
- **Çözüm:** Kanıtlanmış adımları tek script'te topla; ekran imzasını kısa süre önbellekle; P7'de Companion hibrit modu (ADR-0010).
- **Test:** TODO A2.05 (gecikme ölçümü), A7.13 (hibrit ≥ 5×).

### android-idle-state
- **Belirti:** `uiautomator dump` "could not get idle state" ile başarısız, ya da uzun süre dönmüyor.
- **Neden:** Ekranda animasyon (video, yükleme göstergesi, bazı Ayarlar sayfaları) var; uiautomator ekran "boşta" olana kadar bekler.
- **Çözüm:** `TREE_UNAVAILABLE` döndür; 10 sn ağacı deneme, `screen.text` OCR'a düşsün (`source: "pixels"`). `ui()`/`tap_ui()` gerçek ağaç ister ve hata vermeye devam eder. Cihaz hazırlığında animasyon ölçekleri 0.5x/kapalı.
- **Test:** TODO A2.05 (fixture), A2.16 test uygulamasında animasyonlu ekran.

### android-silent-success
- **Belirti:** Tap "başarılı" ama hiçbir şey değişmedi.
- **Neden:** adb `input` sonucu bildirmez; boş alana tap da çıkış kodu 0'dır.
- **Çözüm:** Eylem → Doğrula: `wait_for_text` / `wait_for_app` / `wait_stable` + tek `screen()`. Helper'lar hüküm vermez, gözlem döndürür.
- **Test:** SKILL.md yöntemi + agent eval (A3.10).

### android-locked-taps
- **Belirti:** Kilit ekranına dokunuşlar gidiyor; PIN pedi açılıyor; hiçbir hata yok.
- **Neden:** adb kilitli ekrana da girdi gönderir.
- **Çözüm:** Her girdi op'undan önce durum kapısı: `dumpsys power | grep mWakefulness` + `dumpsys window | grep isKeyguardShowing` (2 sn önbellek). Uyku → `KEYCODE_WAKEUP`; kilitli → `DEVICE_LOCKED`, **hiçbir** dokunuş gönderilmez. PIN asla yazılmaz.
- **Test:** `test_backend.py::test_locked_phone_gets_no_touch`, E2E `test_locked_phone_refuses_and_sends_no_touch`.

### android-ascii-only-text
- **Belirti:** `type_text("Çağrı")` boş, bozuk veya hatalı yazıyor.
- **Neden:** `adb shell input text` yalnızca ASCII destekler.
- **Çözüm:** `input.text` `mode=auto` → IME yolu (ADBKeyboard `ADB_INPUT_B64` / Companion IME). ADR-0009.
- **Kanıt:** API 30 ve 34'te `input text 'çağrı'` → `NullPointerException`, çıkış kodu 1 / 255 (`tests/fixtures/android/*/input_text_turkish.*`).
- **Test:** `test_parse_fixtures.py::test_input_text_cannot_type_turkish`, `test_backend.py::test_turkish_text_switches_to_the_ime_and_back`, E2E `test_turkish_text_round_trip`.

### android-input-text-escaping
- **Belirti:** Boşluklar kayboluyor, `&`, `;`, `(`, `'` gibi karakterler komutu bozuyor.
- **Neden:** `input text` argümanı cihazdaki shell'den geçer; boşluk `%s` olmalı.
- **Çözüm:** ASCII yolunda kaçış tablosu; şüphede IME yolu.
- **Test:** TODO A2.08.

### android-duplicate-wifi-device
- **Belirti:** "more than one device/emulator" hatası; tek telefon bağlı olmasına rağmen.
- **Neden:** Wi-Fi adb aynı telefonu hem `ip:port` hem mDNS adıyla listeleyebilir.
- **Çözüm:** Her komutta `-s SERIAL`; keşifte `ro.serialno` ile birleştir.
- **Test:** `test_backend.py::test_commands_are_pinned_after_resolve`, `test_parse_fixtures.py::test_devices_states_and_transports`.

### android-wireless-debug-resets
- **Belirti:** Yeniden başlatmadan sonra Wi-Fi telefon bulunamıyor.
- **Neden:** Kablosuz hata ayıklama telefon yeniden başlayınca kendiliğinden kapanır; port değişir.
- **Çözüm:** `doctor` bunu söyler; mDNS ile yeniden keşif; raf cihazlarında USB tercih et.
- **Test:** TODO A2.13.

### android-primary-fallback
- **Belirti:** Agent yanlış telefonda (yanlış hesapta) işlem yaptı.
- **Neden:** Birincil telefon ulaşılamayınca "ilk bulunan" telefona düşmek.
- **Çözüm:** **Kırmızı çizgi:** birincil/kiralanan cihaz yoksa hata (`PrimaryUnreachable` / `DEVICE_OFFLINE`). CLAUDE.md §6.2.
- **Test:** `test_backend.py::test_unreachable_primary_is_an_error_not_another_phone`, `test_explicit_serial_is_never_substituted`; uzak: TODO A5.22.

### android-scroll-vs-swipe
- **Belirti:** Liste gezerken satırlar atlanıyor.
- **Neden:** `input swipe` kısa sürede flick üretir, liste momentumla kayar.
- **Çözüm:** `scroll` = `input motionevent` DOWN/MOVE/UP, sonda ~80 ms duraklama (fling'i öldürür), her seferinde aynı mesafe. `swipe` yalnızca "sonraki video/sayfa" için.
- **Test:** `test_backend.py::test_scroll_has_no_momentum_and_moves_the_finger_against_the_content`, E2E `test_scroll_collect_walks_200_rows_in_order`.

### android-motionevent-missing
- **Belirti:** `input motionevent` "Unknown command".
- **Neden:** Eski Android sürümlerinde yok.
- **Çözüm:** Destek tespiti (önbellekli) → yedek: uzun süreli `input swipe`.
- **Kanıt:** API 30 ve 34 `input` yardımında `motionevent` var.
- **Test:** `test_parse_fixtures.py::test_motionevent_is_available`.

### android-screenshot-equals-tap-space
- **Belirti:** —
- **Neden/Bilgi:** `screencap` görüntüsü tap koordinatlarıyla 1:1 (cihaz pikseli). Protokolün koordinat uzayı tanımı budur (Plan.md §6.4). `wm size` override varsa fiziksel değil override boyutunu kullan.
- **Test:** TODO A2.04.

### android-screen-timeout
- **Belirti:** Uzun görevin ortasında telefon kilitleniyor.
- **Neden:** Ekran zaman aşımı.
- **Çözüm:** `device.keep_awake` (ayar değiştirmeden periyodik `KEYCODE_WAKEUP`); raf cihazlarında "şarjda uyanık kal". Kullanıcı cihazında önce kullanıcıya sor.
- **Test:** TODO A2.12.

### android-unauthorized
- **Belirti:** `adb devices` → `unauthorized`.
- **Neden:** Telefonda "USB hata ayıklamaya izin ver?" onaylanmadı.
- **Çözüm:** `DEVICE_UNAUTHORIZED` + "Telefonun kilidini açıp İzin ver'e dokunun (Her zaman izin ver'i işaretleyin)". Görünmüyorsa kabloyu çıkar-tak.
- **Test:** TODO A2.01, A2.13.

### android-miui-restrictions
- **Belirti:** Xiaomi/Redmi'de `input` çalışmıyor veya APK kurulamıyor.
- **Neden:** MIUI/HyperOS'ta ek ayarlar: "USB hata ayıklama (Güvenlik ayarları)", "USB üzerinden yükle" (Mi hesabı ister).
- **Çözüm:** `docs/runbooks/device-prep.md` Xiaomi bölümü; `doctor` marka tespitiyle uyarır.
- **Test:** TODO A2.17 (cihaz matrisi).

### android-flag-secure
- **Belirti:** Bazı uygulamalarda (bankacılık) ekran görüntüsü siyah.
- **Neden:** `FLAG_SECURE`.
- **Çözüm:** Hata değil; `details.secure=true` ile bildir. Ağaç yine okunabilir olabilir.
- **Test:** TODO A2.16 (test uygulamasında secure ekran).

### android-uiautomator-dev-tty
- **Belirti:** Ağaç her zaman boş; çıktı yalnızca `UI hierchary dumped to: /dev/tty`.
- **Neden:** İnternetteki yaygın tarif `uiautomator dump /dev/tty`, etkileşimsiz `adb shell` altında tty olmadığı için XML'i hiç vermiyor (API 30 ve 34'te kanıtlandı, çıkış kodu 0).
- **Çözüm:** Dosyaya dök, oku, sil: `uiautomator dump /sdcard/mphone_ui.xml; cat …; rm -f …`.
- **Test:** `tests/unit/android/test_parse_fixtures.py::test_dev_tty_dump_has_no_xml`, `test_backend.py::test_tree_dumps_to_a_file_never_dev_tty`.

### android-dozing-is-asleep
- **Belirti:** Ekran kapalıyken backend telefonu "uyanık" sanıyor; dokunuşlar boşa gidiyor.
- **Neden:** `KEYCODE_SLEEP` sonrası API 30 `mWakefulness=Asleep`, API 34 aynı imajda kimi zaman `Asleep`, kimi zaman `Dozing` diyor. API 34'te `Display Power: state=` satırı da yok.
- **Çözüm:** Yalnızca `Awake` uyanıktır; diğer her değer (Asleep, Dozing, Dreaming, yok) uyandırma gerektirir.
- **Test:** `test_parse_fixtures.py::test_wakefulness`, `test_backend.py::test_asleep_is_woken_then_driven`.

### android-hint-as-text
- **Belirti:** Boş bir metin alanı ağaçta `text="Metin"` gösteriyor; "alan dolu" sanılıyor.
- **Neden:** uiautomator boş EditText için ipucunu (hint) `text` olarak raporluyor (API 30 ve 34).
- **Çözüm:** Alanın değerini doğrularken beklenen değerle karşılaştır; "boş mu" sorusunda ipucunu da boş say.
- **Test:** `test_parse_fixtures.py::test_uiautomator_test_screen`.

### android-ime-async
- **Belirti:** `ime enable` kurulumdan hemen sonra `Unknown input method … cannot be enabled` diyor; hemen ardından `ime list` klavyeyi gösteriyor.
- **Neden:** Giriş yöntemi servisi yeni paketi eşzamansız tarıyor.
- **Çözüm:** Kurulumdan sonra `ime list -a -s` klavyeyi gösterene kadar bekle (en çok 30 sn), sonra etkinleştir.
- **Test:** `tests/e2e_emulator/conftest.py::ime_installed`; capture betiği `ime_wait_seconds`.

### android-emulator-lockscreen-disabled
- **Belirti:** Emülatörde PIN koyup ekranı kapatıp açınca kilit ekranı gelmiyor; `isKeyguardShowing=false`.
- **Neden:** (1) Güvenli kilit, ekran kapandıktan `lock_screen_lock_after_timeout` (varsayılan 5 sn) sonra devreye giriyor; (2) emülatör imajlarında kilit ekranı sistem düzeyinde kapalı gelebiliyor.
- **Çözüm:** Testte `locksettings set-disabled false`, gecikmeyi 0 yap, uyut, ≥ 7 sn bekle, keyguard'ı yokla; sonra eski değerleri geri yükle. Gerçek telefonlarda bu ayarlara dokunulmaz.
- **Test:** `tests/e2e_emulator/test_android_e2e.py::test_locked_phone_refuses_and_sends_no_touch`.

### android-ime-first-bind
- **Belirti:** Android 14'te ilk Türkçe `type_text` alanı boş bırakıyor; sonraki çağrılar çalışıyor (E2E, API 34).
- **Neden:** `ime set` sonrası klavye servisi eşzamansız oluşturuluyor; broadcast o anda gönderilirse dinleyen yok (`result=0`).
- **Çözüm:** mphone klavyesi sıralı yayına sonuç kodu döner (1 yazıldı, 2 odaklı alan yok); backend 0 geldikçe 5 sn'ye kadar yeniden dener, 2'de `NotFound` verir. Metin sessizce kaybolmaz.
- **Test:** `test_backend.py::test_ime_not_listening_yet_is_retried`, `test_ime_reports_no_focused_field`; E2E `test_typing_without_a_focused_field_is_an_error_not_silence`.

### scroll-overshoot
- **Belirti:** `scroll_collect` bir listede 2 satırı atladı (Öğe 85, 86) — API 34 E2E.
- **Neden:** `motionevent` ile momentumsuz kaydırma bile bir kez fırladı: parmak kalkmadan önceki bekleme hız ölçeri sıfırlamaya yetmedi.
- **Çözüm:** (1) Android: kaldırmadan önce aynı noktada iki durağan MOVE. (2) Platformdan bağımsız: `scroll_collect`, yeni ekranın öğeleri öncekiyle hiç örtüşmüyorsa yarım adım geri gidip örtüşen ekrandan devam eder — öğeler eksiksiz ve sıralı kalır. Sabit başlıklar örtüşme sayılmasın diye kontrol ekstraktörün öğeleri üzerinden yapılır.
- **Test:** `test_helpers_fake.py::test_scroll_collect_recovers_rows_skipped_by_a_fling` (fake `overshoot`), E2E `test_scroll_collect_walks_200_rows_in_order`.

## OCR

### ocr-comma-below
- **Belirti:** OCR'ın okuduğu "titreşim" ekrandakiyle aynı görünüyor ama `tap_text("titreşim", exact=True)` bulamıyor.
- **Neden:** Apple Vision Türkçe **ş** (U+015F, çengelli) harfini Romence **ș** (U+0219, virgüllü) olarak okudu (rendered "Ses ve titreşim"). Ayrıca "Ağ" → "Ag" (breve kaçtı).
- **Çözüm:** Her OCR kutusu `ocr.normalize_text` ile ș→ş, Ș→Ş, ț→ţ'ye çevrilir. Kaçan aksanları `textnorm.match` 4. seviyesi (aksansız) tolere eder.
- **Test:** `tests/unit/test_ocr_registry.py::test_comma_below_lookalikes_become_turkish`, `tests/unit/ocr/test_vision.py`.

## iOS — iPhone Mirroring

### ios-video-stream
- **Belirti:** AppleScript `click at` ya da AX ile pencere içine tıklama işe yaramıyor.
- **Neden:** Pencere bir video akışıdır; macOS erişilebilirliği içini görmez.
- **Çözüm:** Yalnızca HID seviyesinde CGEvent / SkyLight olay kaydı.
- **Test:** TODO A4.04.

### ios-vertical-drag-dropped
- **Belirti:** `swipe("up")` listede hiçbir şey kaydırmıyor (macOS 26).
- **Neden:** macOS 26'da Mirroring dikey dokunmatik sürüklemeyi düşürüyor; yatay çalışıyor.
- **Çözüm:** Dikey hareket için kaydırma tekerleği olayı (`input.scroll`); `swipe` yalnızca yatay (ana ekran sayfaları, carousel).
- **Test:** TODO A4.09.

### ios-home-labels-not-targets
- **Belirti:** `tap_text("Hava Durumu")` ana ekranda uygulamayı açmıyor.
- **Neden:** Etiket dokunma hedefi değil; ikon ~35 pt yukarıda.
- **Çözüm:** `tap_icon()` (agent workspace) — cihaz-yerel pikselde `35 * scale` yukarı. Uygulama içi düğmelerde `tap_text` çalışır.
- **Test:** TODO A4.08.

### ios-type-autocorrect
- **Belirti:** Yazılan "Thu" → "thru" oluyor.
- **Neden:** Tuş vuruşu yolu iOS otomatik düzeltmesinden geçer.
- **Çözüm:** Varsayılan yapıştırma (Mac panosu + Cmd+V, önceki pano geri yüklenir); `mode=keystrokes` yalnızca gerçek tuş olayı isteyen alanlarda.
- **Test:** TODO A4.04.

### ios-connect-needs-locked-phone
- **Belirti:** "iPhone in Use", "Timed Out", Connect düğmesi işe yaramıyor.
- **Neden:** Mirroring yalnızca iPhone kilitliyken bağlanır; kullanıcı telefonu açarsa oturum durur.
- **Çözüm:** Connect'e **bir kez** bas; sonra `NEEDS_USER` + "iPhone'u kilitleyin". Döngüde basma, pencereye tıklama. Kullanıcı "tamam" deyince bir kez daha dene.
- **Test:** TODO A4.05.

### ios-unfocused-input-swallowed
- **Belirti:** Kaydırma "çalışmıyor" ya da liste "bitti" gibi görünüyor.
- **Neden:** Ön plan olay yolunda odaksız pencereye giden olaylar sessizce yutulur; kaydırma tekerleği imleç altındaki pencereye gider.
- **Çözüm:** Arka plan yolu (pencere kimliğine olay); kaydırmada kısa öne alma + odak iadesi. Bir hareket hiçbir şeyi değiştirmediyse önce odağı kontrol et.
- **Test:** TODO A4.04 (`focus.diff`).

### ios-window-moves
- **Belirti:** Dokunuşlar yanlış yere gidiyor.
- **Neden:** Kullanıcı pencereyi taşıdı/yeniden boyutlandırdı.
- **Çözüm:** Geometriyi her op'ta yeniden sorgula; protokol koordinatları cihaz-yerel pikseldir, backend çevirir (Plan.md §6.4).
- **Test:** TODO A4.03.

### ios-one-iphone-per-mac
- **Bilgi:** Mirroring Mac başına tek iPhone; Mac GUI oturumu açık olmalı (headless olmaz), Erişilebilirlik + Ekran Kaydı izinleri gerekir. Ekran Kaydı izni terminal yeniden başlatılınca etkili olur. Filo için WDA (ADR-0011).

### ios-no-back-no-tree
- **Bilgi:** Sistem Geri düğmesi, ağaç, ön plandaki uygulama, uygulama listesi yok → `UNSUPPORTED`. Taklit edilmez.

### ios-login-prompt
- **Bilgi:** Pencerede bazen görünen Mac oturum/Touch ID istemine asla yazılmaz → `NEEDS_USER`.

## Uzak / Gateway

### remote-no-device-substitution
- **Belirti:** Oturum/lease bitti, sonraki script başka bir telefonda koştu.
- **Neden:** "Varsayılan cihaz"a düşmek.
- **Çözüm:** Lease belirli `device_id`'ye bağlı; bitince `LEASE_EXPIRED`; yeni lease agent'ın açık isteğiyle. Paralel agent'lar ortak varsayılanı değiştirmez, kendi lease'ini taşır.
- **Test:** TODO A5.22.

### remote-shared-default-race
- **Belirti:** İki agent birbirinin telefonunu sürüyor.
- **Neden:** Süreçler arası paylaşılan "attached session" değişkeni.
- **Çözüm:** Her op `lease_id` taşır; global varsayılan yok.
- **Test:** TODO A5.11.
