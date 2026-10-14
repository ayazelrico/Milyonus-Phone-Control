# ADR-0003: Protokolün tek kaynağı JSON Schema; modeller üretilir

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Aynı op sözleşmesini Python (core, gateway, node), Kotlin (Companion App) ve TypeScript (dashboard) konuşacak. Sözleşme; süreç içi çağrı, WebSocket mesajı ve HTTP isteği olarak taşınacak. MCP JSON tabanlıdır. Agent'lar ve LLM'ler şemayı okuyabilmelidir (`GET /v1/protocol`, `mphone://protocol`).

## Karar

`packages/mphone-protocol/schema/ops.v1.json` (JSON Schema 2020-12) tek doğruluk kaynağıdır. `tools/gen_protocol.py` bundan Pydantic v2 modelleri, `OP_NAMES`, hata sınıfları, `docs/protocol.md`, TypeScript ve Kotlin tiplerini üretir. Üretilmiş dosyalar elle düzenlenmez; CI `--check` ile tazeliği doğrular. Medya (canlı görüntü) ikili WebSocket çerçeveleriyle taşınır, şemanın dışındadır.

## Değerlendirilen alternatifler

- **Protobuf/gRPC:** Güçlü tipler ve ikili verim; ama tarayıcı ve MCP uyumu zayıf, insan/LLM okunurluğu düşük, WS üzerinde ek katman gerekir.
- **Pydantic modellerini kaynak yapmak:** Python dışı dillere üretim dolaylı ve kırılgan.

## Sonuçlar

- (+) Tüm diller aynı sözleşmeden; uyum vektörleri her dilde koşar.
- (+) Şema doğrudan agent'a verilebilir.
- (−) Bir kod üreticisi bakımı (tools/gen_protocol.py) gerekir.
- (−) JSON büyük ekran görüntülerinde verimsiz → artefaktlar S3'e imzalı URL ile (Plan.md §8.3).
