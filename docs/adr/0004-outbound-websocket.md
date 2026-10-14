# ADR-0004: Node ve Companion App, Gateway'e dışa doğru WSS ile bağlanır

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Telefonlar ofis raflarında, çalışan evlerinde veya 4G'de olabilir; bunların önünde NAT ve güvenlik duvarı vardır. Gateway'in node'lara gelen bağlantı açması pratik değildir. Op'lar düşük gecikmeli, çift yönlü bir kanal ister (istek/yanıt + olaylar + canlı kareler).

## Karar

Node daemon'u ve Companion App, Gateway'e tek kalıcı WSS bağlantısı açar (`/v1/nodes/connect`, `/v1/companion/connect`). Kimlik: Ed25519 anahtar çifti + kısa ömürlü JWT. Kopmada üstel geri çekilme + jitter ile yeniden bağlanma. Büyük artefaktlar WS yerine imzalı S3 URL'sine yüklenir.

## Değerlendirilen alternatifler

- **Gateway'den node'a HTTP:** gelen port, port yönlendirme, dinamik IP sorunları.
- **VPN (Tailscale/WireGuard) + gelen HTTP:** her host'a VPN istemcisi, ek operasyon; ileride ek güvenlik katmanı olarak kullanılabilir.
- **MQTT:** ek broker, istek/yanıt deseni doğal değil.

## Sonuçlar

- (+) Sıfır ağ yapılandırması: host'un yalnızca HTTPS çıkışı yeterli.
- (+) Tek kanal: op, olay, sağlık, canlı kare.
- (−) Çok örnekli gateway'de bağlantının hangi örnekte olduğu bilinmeli → Redis yönlendirme (ADR-0006).
- (−) Uzun ömürlü bağlantılar dağıtımda drain ister (Plan.md §13.2).
