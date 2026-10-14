# ADR-0009: Android'de Unicode metin IME ile yazılır

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

`adb shell input text` yalnızca ASCII yazar; ç, ğ, ı, İ, ö, ş, ü ve emoji yazılamaz. Türkiye pazarında bu, sistemi kullanılamaz kılar. Android 10+ arka planda pano erişimini kısıtladığı için yapıştırma yolu güvenilir değildir.

## Karar

`input.text` `mode=auto`: saf ASCII ve güvenli karakterlerse `input text`; aksi halde IME yolu. P2'de ADBKeyboard (`ADB_INPUT_B64` broadcast) — lisans uygun değilse kendi minimal IME'miz; P7'de Companion App'in IME'si ve `ACTION_SET_TEXT`. Önceki IME yazımdan sonra geri yüklenir.

## Değerlendirilen alternatifler

- **Pano + yapıştır:** Android 10+ kısıtları, kullanıcının panosunu ezer.
- **`input text` kaçış hileleri:** Unicode için çalışmaz.

## Sonuçlar

- (+) Her alanda Türkçe ve emoji.
- (−) Cihaza bir APK kurulumu gerekir (`mphone android ime install`).
- (−) IME geçişi kısa bir klavye değişimi olarak görünür.
