# ADR-0006: Kalıcı durum PostgreSQL, hızlı koordinasyon Redis

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Lease'ler atomik ve hızlı olmalı (50 paralel acquire → tam bir kazanan). Çok örnekli gateway'de op'un, node bağlantısını tutan örneğe iletilmesi gerekir. Audit kayıpsız yazılmalı ama op yolunu yavaşlatmamalı.

## Karar

PostgreSQL 16 doğruluk kaynağıdır (lease, audit, cihaz, politika). Redis 7: lease kilidi (`SET NX PX`), hız sınırı, pub/sub yönlendirme, audit stream'i, run kuyruğu. Tutarsızlıkta Postgres kazanır; uzlaştırıcı iş Redis'i onarır. Postgres'te `leases(device_id) WHERE status='active'` kısmi benzersiz indeksi ikinci güvencedir.

## Değerlendirilen alternatifler

- **Yalnızca Postgres** (advisory lock, LISTEN/NOTIFY): mümkün ama yönlendirme ve hız sınırı için gecikme ve yük daha yüksek.

## Sonuçlar

- (+) Düşük gecikmeli op yolu, kayıpsız audit.
- (−) İki durum deposu → uzlaştırma mantığı ve testleri gerekir.
