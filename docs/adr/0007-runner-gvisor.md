# ADR-0007: Uzak script'ler Docker + gVisor sandbox'ında çalışır

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Agent'ın `phone_exec` ile gönderdiği Python script'i keyfi koddur. Uzak modda ne agent makinesinde (bilinmiyor) ne node'da (telefonlara fiziksel erişim, ağ) çalışmalıdır.

## Karar

Her run, kısa ömürlü bir Docker konteynerinde gVisor (`runsc`) çalışma zamanıyla koşar: ağ çıkışı yalnızca gateway iç adresi, salt-okunur kök + tmpfs, CPU/bellek/pids/süre limitleri, yalnızca o lease'e op gönderebilen kısa ömürlü run token'ı; agent API anahtarı konteynere girmez. Yerel modda alt süreç + ortam temizleme.

## Değerlendirilen alternatifler

- **Firecracker microVM:** daha güçlü izolasyon, daha yüksek operasyon maliyeti — P9'da yeniden değerlendirilir.
- **nsjail/firejail:** hafif ama yapılandırması kırılgan.
- **Pyodide/WASM:** güvenli ama Pillow/numpy ve ağ istemcisi kısıtları.

## Sonuçlar

- (+) Üretimde olgun, Docker uyumlu izolasyon.
- (−) gVisor her ortamda kurulmayabilir (geçici yedek: seccomp + ağ kısıtı, Phases.md P5 riskleri).
- (−) Konteyner başlatma ~300–800 ms run gecikmesi ekler (havuz ile azaltılabilir).
