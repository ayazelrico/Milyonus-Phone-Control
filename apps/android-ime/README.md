# mphone IME

Türkçe ve emoji yazımı için tuşsuz klavye (ADR-0009, Plan-Actions A2.08–A2.09). `adb shell input text` yalnızca ASCII yazabildiği için mphone, ASCII dışı metni bu klavyeye base64 broadcast ile gönderir.

| Broadcast | Etki |
|---|---|
| `com.milyonus.mphone.ime.INPUT_B64 --es msg <base64>` | Odaklı alana metin ekler |
| `com.milyonus.mphone.ime.CLEAR` | Odaklı alanı temizler |
| `com.milyonus.mphone.ime.ENTER` | Alanın eylemini (Ara/Gönder/İleri) veya Enter'ı gönderir |

**Güvenlik:** Alıcı, göndericiden `android.permission.DUMP` ister. Bu izne adb shell ve sistem sahiptir, sıradan uygulamalar sahip olamaz; yani yüklü başka bir uygulama bu klavyeye metin yazdıramaz. Klavye açıkken ekranın altında "mphone klavyesi etkin" bandı görünür.

Derleme (CI'da yapılır): `gradle -p apps/android-ime assembleDebug` → `app/build/outputs/apk/debug/app-debug.apk`. Kurulum: `mphone android ime install`.
