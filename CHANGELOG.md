# Changelog

Bu dosya [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) biçimini, sürümler [SemVer](https://semver.org/lang/tr/) kuralını izler.
Protokol sürümü (`ops.v1`) paket sürümünden bağımsızdır (Plan.md §7.6).

## [Unreleased]

### Changed
- Lisans Apache-2.0 (LICENSE, NOTICE); repo public; Q1–Q13 kesinleşti; `main` branch koruması (karar kaydı).

### Added
- P0: uv workspace iskeleti (9 paket), ruff/pyright/pytest/pre-commit yapılandırması, CI (A0.01–A0.03).
- P0: ADR-0001…0015, PITFALLS.md v0, karar kaydı, cihaz hazırlık rehberi, referans proje notları (A0.04–A0.09).
- P0: `tools/bump_version.py` ve bu değişiklik günlüğü (A0.10).
- P1: Protokol v1 şeması (39 op, 19 hata kodu) ve `tools/gen_protocol.py` (Pydantic modelleri, op tablosu, hata sınıfları, `docs/protocol.md`) (A1.01–A1.02).
- P1: Protokol uyum vektörleri (A1.03).
- P1: `Backend` taban sınıfı + middleware zinciri + `TraceMiddleware`, `connect()` ve cihaz URI'leri, Türkçe-farkında eşleştirme (`tr_fold`, `match`), ağaç yardımcıları, config, agent workspace, OCR arayüzü (A1.04–A1.06, A1.10–A1.11).
- P1: Helper API (`Phone` + modül fonksiyonları): ekran okuma, dokunma, Unicode yazma, kaydırma/toplama, bekleme, ağaç, insan devralma/onay (A1.07–A1.09).
- P1: Fake telefon backend'i (tüm op'lar) ve 5 senaryo (A1.12–A1.13); sözleşme testleri (A1.14).
