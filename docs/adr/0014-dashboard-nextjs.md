# ADR-0014: Dashboard için Next.js + TypeScript

- **Durum:** Accepted
- **Tarih:** 2026-10-14
- **İlgili:** Plan.md §14

## Bağlam

Dashboard; canlı görüntü (canvas + ikili WS), devralma girdisi (tıklama, sürükleme, klavye), gerçek zamanlı onay kuyruğu ve politika düzenleyici içerir.

## Karar

Next.js 15 (App Router), TypeScript strict, Tailwind, shadcn/ui, TanStack Query, Auth.js (OIDC). Protokol tipleri şemadan üretilir.

## Değerlendirilen alternatifler

- **Streamlit/Reflex (Python):** hızlı prototip ama düşük gecikmeli canvas etkileşimi ve ince UI kontrolü zor.

## Sonuçlar

- (+) Zengin istemci, geniş ekosistem.
- (−) İkinci bir dil/araç zinciri (pnpm, Node).
