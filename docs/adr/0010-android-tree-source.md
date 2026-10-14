# ADR-0010: Android ağacı önce uiautomator, sonra Companion AccessibilityService

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Ekranı ağaçtan okumak OCR'dan kesin ve dokunmaya hazırdır, ama `uiautomator dump` yavaştır (2–3 sn) ve animasyonlu ekranlarda ("could not get idle state") başarısız olur.

## Karar

P2: sıfır kurulum için `uiautomator dump`; başarısızlıkta `TREE_UNAVAILABLE` + 10 sn geri çekilme + OCR yedeği. P7: Companion App yüklüyse hibrit mod — ağaç ve metin, `adb forward` ile yerel soketten AccessibilityService'ten (< 150 ms).

## Değerlendirilen alternatifler

- **uiautomator2 (atx) sunucusu:** hızlı, ama ek APK + bakım; P2'de gerekirse ara çözüm.
- **Appium:** ağır bağımlılık zinciri.

## Sonuçlar

- (+) MVP ek kurulum istemez; hız ihtiyacı P7'de karşılanır.
- (−) P7'ye kadar `screen()` yavaş → batch script kültürü ve önbellek önemli.
