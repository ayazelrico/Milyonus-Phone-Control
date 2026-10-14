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
- **Test:** TODO A2.03 (adb çağrı kaydıyla "kilitliyken input komutu yok").

### android-ascii-only-text
- **Belirti:** `type_text("Çağrı")` boş, bozuk veya hatalı yazıyor.
- **Neden:** `adb shell input text` yalnızca ASCII destekler.
- **Çözüm:** `input.text` `mode=auto` → IME yolu (ADBKeyboard `ADB_INPUT_B64` / Companion IME). ADR-0009.
- **Test:** TODO A2.08 (100 Türkçe cümle + emoji).

### android-input-text-escaping
- **Belirti:** Boşluklar kayboluyor, `&`, `;`, `(`, `'` gibi karakterler komutu bozuyor.
- **Neden:** `input text` argümanı cihazdaki shell'den geçer; boşluk `%s` olmalı.
- **Çözüm:** ASCII yolunda kaçış tablosu; şüphede IME yolu.
- **Test:** TODO A2.08.

### android-duplicate-wifi-device
- **Belirti:** "more than one device/emulator" hatası; tek telefon bağlı olmasına rağmen.
- **Neden:** Wi-Fi adb aynı telefonu hem `ip:port` hem mDNS adıyla listeleyebilir.
- **Çözüm:** Her komutta `-s SERIAL`; keşifte `ro.serialno` ile birleştir.
- **Test:** TODO A2.02 (fixture).

### android-wireless-debug-resets
- **Belirti:** Yeniden başlatmadan sonra Wi-Fi telefon bulunamıyor.
- **Neden:** Kablosuz hata ayıklama telefon yeniden başlayınca kendiliğinden kapanır; port değişir.
- **Çözüm:** `doctor` bunu söyler; mDNS ile yeniden keşif; raf cihazlarında USB tercih et.
- **Test:** TODO A2.13.

### android-primary-fallback
- **Belirti:** Agent yanlış telefonda (yanlış hesapta) işlem yaptı.
- **Neden:** Birincil telefon ulaşılamayınca "ilk bulunan" telefona düşmek.
- **Çözüm:** **Kırmızı çizgi:** birincil/kiralanan cihaz yoksa hata (`PrimaryUnreachable` / `DEVICE_OFFLINE`). CLAUDE.md §6.2.
- **Test:** TODO A2.02, A5.22.

### android-scroll-vs-swipe
- **Belirti:** Liste gezerken satırlar atlanıyor.
- **Neden:** `input swipe` kısa sürede flick üretir, liste momentumla kayar.
- **Çözüm:** `scroll` = `input motionevent` DOWN/MOVE/UP, sonda ~80 ms duraklama (fling'i öldürür), her seferinde aynı mesafe. `swipe` yalnızca "sonraki video/sayfa" için.
- **Test:** TODO A2.07 (mesafe ±%5).

### android-motionevent-missing
- **Belirti:** `input motionevent` "Unknown command".
- **Neden:** Eski Android sürümlerinde yok.
- **Çözüm:** Destek tespiti (önbellekli) → yedek: uzun süreli `input swipe`.
- **Test:** TODO A2.07.

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
