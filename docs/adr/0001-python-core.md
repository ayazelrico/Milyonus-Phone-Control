# ADR-0001: Çekirdek, node, gateway, runner ve MCP için Python 3.12

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

iPhone Mirroring backend'i macOS Vision (OCR), Quartz (pencere yakalama, CGEvent) ve özel SkyLight API'lerine erişmek zorunda; bunların olgun bağlayıcısı pyobjc'dir. Agent'lar telefonu Python script'leriyle sürüyor (phone-harness'ta kanıtlanmış yaklaşım; LLM'ler Python'u iyi yazar). Protokol modellerinin tek dilde tutulması sözleşme kaymasını önler.

## Karar

Çekirdek kütüphane, backend'ler, node daemon'u, gateway, runner, MCP sunucusu ve SDK Python 3.12 ile yazılır. Companion App Kotlin, dashboard TypeScript'tir; ikisi de protokol tiplerini JSON Schema'dan üretir (ADR-0003).

## Değerlendirilen alternatifler

- **Go:** Node ve gateway için daha düşük bellek ve tek ikili dağıtım; ama iOS backend'i yine Python gerektirir → iki dil, iki protokol modeli.
- **TypeScript:** MCP ekosistemi güçlü; pyobjc karşılığı yok, agent script dili ayrışır.

## Sonuçlar

- (+) Tek dil: helper'lar, backend'ler, gateway aynı Pydantic modellerini paylaşır.
- (+) Agent script'leri, runner ve yerel CLI aynı yorumlayıcıda çalışır.
- (−) Gateway'de yüksek eşzamanlılık için async disiplini şart (senkron backend çağrıları `asyncio.to_thread`).
- (−) Node dağıtımı Python çalışma zamanı ister → `uv tool install` ile çözülür.
