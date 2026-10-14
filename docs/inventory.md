# Cihaz Envanteri

Hazırlanan her cihaz buraya eklenir ([device-prep.md](runbooks/device-prep.md) §4). **Seri numarasının kendisini yazma** — `sha256(serial)[:12]` yaz (`adb shell getprop ro.serialno | shasum -a 256 | cut -c1-12`).

| Etiket | Tür (raf/kişisel) | Platform | Marka / Model | OS sürümü | Seri hash | Sahip | Konum / Node | Bağlantı | Hazırlık tarihi | Not |
|---|---|---|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — | — | — | Donanım siparişi bekleniyor (H-03, H-04) |
