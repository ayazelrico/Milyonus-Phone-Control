# ADR-0011: iOS'ta önce iPhone Mirroring, sonra WebDriverAgent

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

iPhone kontrolünün iki yolu var. iPhone Mirroring Xcode, imzalama veya telefona kurulum gerektirmez ama Mac başına tek iPhone destekler, Apple güncellemeleriyle davranışı değişir ve ağaç vermez (yalnızca OCR). WebDriverAgent ağaç verir ve Mac başına çok cihazı destekler, ama Apple Developer hesabı, imzalama ve sürüm bakımı ister.

## Karar

P4'te iPhone Mirroring backend'i (hızlı değer, tek cihaz), P8'de (opsiyonel, Q10'a bağlı) WDA backend'i. İkisi aynı protokolü uygular; agent tarafı değişmez.

## Değerlendirilen alternatifler

- **Yalnızca WDA:** daha güçlü ama başlangıç maliyeti ve Apple hesabı bağımlılığı yüksek.
- **Yalnızca Mirroring:** filo ölçeğine çıkamaz.

## Sonuçlar

- (+) iPhone desteği erken gelir.
- (−) İki iOS backend'i bakımı; Mirroring kırılganlığı (Plan.md R1).
