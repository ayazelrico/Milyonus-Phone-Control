# Milyonus Phone Control (mphone)

Milyonus Agent'ın gerçek telefonları **bağlı (yerel)** ve **uzaktan** kontrol etmesini sağlayan sistem: Android (adb, Companion App), iPhone (iPhone Mirroring, WebDriverAgent), Gateway (kiralama, politika, onay, audit) ve MCP sunucusu.

| Doküman | İçerik |
|---|---|
| [Plan.md](Plan.md) | Mimari, protokol, bileşenler, güvenlik |
| [Phases.md](Phases.md) | Fazlar ve kilometre taşları |
| [Plan-Actions.md](Plan-Actions.md) | İş kalemleri ve durumları |
| [CLAUDE.md](CLAUDE.md) | Geliştirme kuralları (insanlar ve Claude Code için) |
| [docs/](docs/) | ADR'ler, PITFALLS, runbook'lar, kararlar |

## Geliştirme

```bash
uv sync
uv run pytest tests/unit tests/contract
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run pre-commit install && uv run pre-commit install --hook-type commit-msg
```

Durum: **P0 — Temel ve Kararlar**. Henüz telefon kontrol eden kod yok; ilk gerçek cihaz kontrolü P2'de (Plan-Actions.md §14).
