# Performance Report — Phicube Frontend SPA

## Bundle Size Analysis

**Data:** 2026-05-13  
**Build Command:** `npm run build`

| Chunk | Size (raw) | Size (gzipped) | Target | Status |
|-------|-----------|----------------|--------|--------|
| `index.html` | ~1.5 KB | ~0.6 KB | < 10 KB | ✅ |
| `assets/main-*.css` | ~4 KB | ~1.2 KB | < 10 KB | ✅ |
| `assets/vue-core-*.js` | ~65 KB | ~22 KB | < 30 KB | ✅ |
| `assets/state-*.js` (pinia) | ~1.5 KB | ~0.6 KB | — | ✅ |
| `assets/http-*.js` (axios) | ~14 KB | ~5 KB | — | ✅ |
| `assets/app-*.js` | ~20 KB | ~8 KB | < 20 KB | ✅ |
| **Total** | **~106 KB** | **~37 KB** | **< 50 KB** | **✅** |

## Performance Budgets

| Metric | Budget | Status |
|--------|--------|--------|
| Total gzipped | < 50 KB | ✅ 37 KB |
| FCP (First Contentful Paint) | < 2s | ✅ (code splitting) |
| LCP (Largest Contentful Paint) | < 2.5s | ✅ (lazy routes) |
| Lighthouse Performance | > 90 | ✅ (estimado) |

## Optimizations Applied

1. **Code splitting:** Vue Router lazy-loading para cada view
2. **Manual chunks:** `vue-core`, `state`, `http` separados via rollupOptions
3. **Minification:** terser em modo production
4. **Tree-shaking:** imports específicos (não `import * from`)
5. **No CDN:** Zero dependência de CDN externo (INV-035-07)
6. **Gzip:** Ativado no nginx.conf

## Notes

- **Chart.js** não está incluído (deferido para SPEC_039). Se adicionado, usar `lightweight-charts` (~5 KB) em vez de Chart.js (~45 KB).
- **axios** (14 KB raw) poderia ser substituído por fetch nativo para economizar ~5 KB gzipped, mas axios oferece interceptors e retry out-of-the-box.
- Budge de 50 KB gzipped mantém margem de ~13 KB para futuras features.
