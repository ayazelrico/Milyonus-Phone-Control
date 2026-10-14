# ADR-0008: MCP sunucusu için resmi Python SDK

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Milyonus Agent ve Claude Code gibi istemciler araçları MCP ile kullanacak. Yerelde stdio, uzakta Streamable HTTP gerekir; araç tanımları iki taşımada aynı olmalıdır.

## Karar

Resmi `mcp` Python SDK'sı (FastMCP). Araç tanımları `mphone_mcp.tools` içinde bir kez yazılır; stdio sunucusu yerel backend'lere, gateway `/mcp` uç noktası lease/runner hattına bağlanır.

## Değerlendirilen alternatifler

- **Kendi MCP uygulamamız:** spesifikasyon değişikliklerini takip yükü.

## Sonuçlar

- (+) Spesifikasyon uyumu, image content, kaynaklar, istemler.
- (−) SDK sürüm güncellemelerini takip etmek gerekir.
