# ADR-0013: Sunucu/Linux tarafı OCR için RapidOCR (ONNX)

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Ağacın olmadığı ekranlarda (animasyon, oyun, video) ve Linux node'larda OCR gerekir. Ekran görüntüleri kişisel veri içerir (KVKK); dış servise gönderilmemelidir. Türkçe karakterler doğru okunmalıdır.

## Karar

macOS'ta Apple Vision (`tr-TR`, `en-US`); Linux/Windows/sunucuda RapidOCR (ONNX Runtime, PaddleOCR latin modeli); Companion App'te ML Kit. Hepsi `OcrEngine` arayüzü arkasında; kalite kapısı Türkçe korpusta karakter doğruluğu ≥ %97 (GA).

## Değerlendirilen alternatifler

- **Tesseract:** ekran metninde daha düşük doğruluk, kurulum zahmeti.
- **Bulut OCR (Google Vision vb.):** yüksek doğruluk ama kişisel veri dışarı çıkar.

## Sonuçlar

- (+) Veri yerelde kalır, platformlar arası.
- (−) Model dosyası (~15 MB) dağıtımı; CPU maliyeti.
