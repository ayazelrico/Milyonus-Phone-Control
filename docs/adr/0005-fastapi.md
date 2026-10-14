# ADR-0005: Gateway API'si için FastAPI

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Gateway; REST, WebSocket (node, companion, canlı görüntü, op kanalı), SSE (run çıktısı) ve MCP Streamable HTTP sunacak. Pydantic modelleri protokolden üretiliyor (ADR-0003).

## Karar

FastAPI + Uvicorn; async SQLAlchemy 2, `pydantic-settings`, OpenAPI otomatik. MCP HTTP uç noktası aynı uygulamaya monte edilir.

## Değerlendirilen alternatifler

- **Litestar:** benzer yetenek, daha küçük ekosistem.
- **Django + Channels:** ağır, async desteği daha az doğal.

## Sonuçlar

- (+) Pydantic yerel, WS ve SSE desteği, otomatik API dokümanı.
- (−) Arka plan işleri için ayrı mekanizma (Redis kuyruğu / görev döngüleri) gerekir.
