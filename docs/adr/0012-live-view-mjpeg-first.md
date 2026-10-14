# ADR-0012: Canlı görüntü önce WS üzerinden MJPEG, sonra WebRTC

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Operatörler cihazı canlı izlemeli ve devralabilmeli. Hedef ≥ 10 fps ve < 500 ms gecikme.

## Karar

MVP: node JPEG kareleri üretir, ikili WS çerçeveleriyle gateway'e, oradan izleyicilere aktarır; geri basınçta kare atlanır. v2: WebRTC (aiortc veya LiveKit) ile < 250 ms.

## Değerlendirilen alternatifler

- **Baştan WebRTC:** TURN/STUN, codec müzakeresi, ek altyapı — ihtiyaç kanıtlanmadan karmaşık.

## Sonuçlar

- (+) Basit, mevcut WS altyapısını kullanır.
- (−) Bant genişliği H.264'e göre yüksek; çok izleyicide maliyet.
