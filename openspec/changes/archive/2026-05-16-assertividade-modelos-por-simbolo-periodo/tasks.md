## 1. Onda A — Base de Layout (index.html, style.css, app.js)

- [x] 1.1 Portar a estrutura visual principal para `src/frontend/static/index.html` (shell, header, navegação por abas e containers por seção).
- [x] 1.2 Aplicar tokens visuais e grid em `src/frontend/static/style.css` com responsividade desktop/mobile.
- [x] 1.3 Implementar controle de abas em `src/frontend/static/app.js` preservando o fluxo atual de polling/fetch.
- [x] 1.4 Critério de aceite: `:8080` abre com novo layout, troca de abas funciona e não há erro JS no console.

## 2. Onda B — Blocos Operacionais (index.html, app.js, style.css)

- [x] 2.1 Reorganizar posições, sinais, performance e histórico no novo layout em `src/frontend/static/index.html` sem remover IDs canônicos.
- [x] 2.2 Ajustar seletores/renderizadores em `src/frontend/static/app.js` para manter compatibilidade com `/positions`, `/signals/history`, `/trades/history`, `/performance*`.
- [x] 2.3 Padronizar estados visuais (vazio, loading, erro) em `src/frontend/static/style.css`.
- [x] 2.4 Critério de aceite: dados continuam renderizando corretamente em todas as áreas após reorganização visual.

## 3. Onda C — Assertividade e Filtros Custom (index.html, app.js, style.css)

- [x] 3.1 Posicionar a seção de assertividade no fluxo por abas em `src/frontend/static/index.html`.
- [x] 3.2 Garantir em `src/frontend/static/app.js` o fluxo completo de `period=custom` com `start/end` e persistência de filtros.
- [x] 3.3 Ajustar responsividade da área de assertividade em `src/frontend/static/style.css` (cards + ranking + timeline).
- [x] 3.4 Critério de aceite: `/performance/assertiveness` funciona com `7d/30d/90d/custom` e atualiza UI por aba.

## 4. Testes e Validação (tests)

- [ ] 4.1 Atualizar `tests/dashboard/test_frontend.py` para refletir nova estrutura visual mantendo contrato funcional.
- [ ] 4.2 Manter alinhados `tests/api/test_assertiveness_endpoint.py` e `tests/api/test_assertiveness_service.py`.
- [ ] 4.3 Executar `pytest` focado em dashboard/assertividade e corrigir regressões.
- [ ] 4.4 Critério de aceite: suíte focada 100% verde e sem perda de cobertura de contrato da UI/API.

## 5. Onda D — Compose e Consolidação de Frontend Único (docker-compose, docs)

- [ ] 5.1 Remover `phicube-frontend` do runtime oficial em `docker-compose.yml` (ou mover para profile não padrão).
- [ ] 5.2 Atualizar `README.md` e documentação operacional para frontend único em `http://127.0.0.1:8080/`.
- [ ] 5.3 Rebuild/restart do stack e smoke final no frontend canônico.
- [ ] 5.4 Critério de aceite: stack padrão sem dual-frontend, health verde e navegação/dados funcionais em `:8080`.
