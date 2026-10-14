# ADR-0002: Paket ve workspace yönetimi için uv workspace

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Dokuz Python paketi birlikte geliştirilir, birlikte sürümlenir (tools/bump_version.py) ama ayrı kurulabilir olmalıdır (ör. node host'una gateway kurulmaz). Kurulumun tek komut olması (NFR-12) hedeftir.

## Karar

Kökte `[tool.uv.workspace] members = ["packages/*"]`; kök proje paketlenmez (`package = false`) ve tüm üyelere bağımlıdır. Kilit dosyası `uv.lock` commit'lenir; CI `uv sync --frozen` kullanır. Son kullanıcı kurulumu `uv tool install mphone[...]`.

## Değerlendirilen alternatifler

- **Poetry:** workspace desteği zayıf, yavaş.
- **pip-tools + editable kurulumlar:** çok paketli düzende kırılgan, kilitleme ayrı araç ister.

## Sonuçlar

- (+) Hızlı, tekrarlanabilir kurulum; Python sürümünü de uv yönetir.
- (+) Paketler arası bağımlılık `{ workspace = true }` ile yerel.
- (−) Ekip uv bilmeli; CLAUDE.md §3 komutları uv üzerinden.
