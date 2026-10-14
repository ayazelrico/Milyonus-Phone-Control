# Mimari Karar Kayıtları (ADR)

Her önemli teknik karar burada bir dosyadır. Yeni karar: sıradaki numara, aynı şablon (Durum, Bağlam, Karar, Alternatifler, Sonuçlar). Bir kararı değiştirmek için eskisini silme; yeni ADR yaz ve eskisini `Superseded by ADR-XXXX` yap.

| ADR | Karar | Durum |
|---|---|---|
| [0001](0001-python-core.md) | Çekirdek, node, gateway, runner, MCP: Python 3.12 | Accepted |
| [0002](0002-uv-workspace.md) | uv workspace | Accepted |
| [0003](0003-json-schema-protocol.md) | Protokolün tek kaynağı JSON Schema | Accepted |
| [0004](0004-outbound-websocket.md) | Node/Companion → Gateway dışa doğru WSS | Accepted |
| [0005](0005-fastapi.md) | Gateway: FastAPI | Accepted |
| [0006](0006-postgres-redis.md) | PostgreSQL + Redis | Accepted |
| [0007](0007-runner-gvisor.md) | Runner: Docker + gVisor | Accepted |
| [0008](0008-mcp-python-sdk.md) | Resmi MCP Python SDK | Accepted |
| [0009](0009-ime-unicode-input.md) | Android Unicode yazım: IME | Accepted |
| [0010](0010-android-tree-source.md) | Android ağaç: uiautomator → Companion | Accepted |
| [0011](0011-ios-mirroring-then-wda.md) | iOS: Mirroring → WDA | Accepted |
| [0012](0012-live-view-mjpeg-first.md) | Canlı görüntü: MJPEG → WebRTC | Accepted |
| [0013](0013-server-ocr-rapidocr.md) | Sunucu OCR: RapidOCR | Accepted |
| [0014](0014-dashboard-nextjs.md) | Dashboard: Next.js | Accepted |
| [0015](0015-exec-plus-granular-tools.md) | phone_exec + granüler araçlar | Accepted |
