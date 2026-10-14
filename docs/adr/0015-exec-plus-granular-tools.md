# ADR-0015: Agent'a hem script çalıştırma (phone_exec) hem granüler araçlar

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

phone-harness deneyimi: kanıtlanmış bir alt görevi tek script'te toplamak, her adım için ayrı araç çağrısından çok daha hızlı ve token-verimlidir. Öte yandan hızlı bakış ve tek adımlık işler için script yazmak gereksiz yüktür.

## Karar

MCP iki tür araç sunar: `phone_exec` (helper'lar yüklü Python, her çağrı taze yorumlayıcı) ve granüler araçlar (`phone_screen`, `phone_tap`, `phone_type`, `phone_open_app` …). Skill, "keşif için granüler, kanıtlanmış dizi için exec" yöntemini öğretir.

## Değerlendirilen alternatifler

- **Yalnızca granüler araçlar:** her adım bir LLM turu → yavaş ve pahalı.
- **Yalnızca exec:** basit işler için script yazma yükü, daha fazla hata.

## Sonuçlar

- (+) Hız ve esneklik birlikte.
- (−) İki yüzeyin tutarlı kalması gerekir → granüler araçlar helper'ların ince sarmalayıcısıdır, ayrı mantık içermez.
