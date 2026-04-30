# Sprint Drag&Drop — Editor Visual VDX Render
**Data:** 2026-04-30 overnight  
**Executor:** Claude Sonnet 4.6

---

## Desvios das Regras (documentado para Allan)

| Regra Sprint | Realidade encontrada | Decisão |
|---|---|---|
| Branch=master (Regra 1) | Repo usa `main`; não existe branch `master`; CI workflows configurados em `branches: [main]` | Trabalhar em `main` — criar `master` quebraria CI |
| pytest baseline = 591 passed | Resultado local: `584 passed, 7 skipped` (total = 591 testes coletados) | Floor defendido: **584 passed** (o "591" da sprint conta passed+skipped) |
| SSH: `-i ~/.ssh/nexus_deploy` | Arquivo não existe; SSH conecta via chave padrão | Usar `ssh -p 5567 sw3innovation@177.73.87.130` sem `-i` |

---

## Sub-entrega 1 — Setup base + página /editor

**Status:** ✅ concluída

- Página /editor acessível: sim (HTTP 200)
- Botão header: sim (todas as páginas têm link "Editor")
- pytest: 584 passed, 7 skipped (baseline mantido)
- CI: verde (Tests + Deploy)
- curl https://render.sw3.tec.br/editor → 200, title "VDX Glass Engine", HTML 5352 bytes
- Desvio: branch `main` em vez de `master` (sem `master` no repo; CI configurado em `main`)

---

## Sub-entrega 2 — Drag de painéis + snap

**Status:** —

---

## Sub-entrega 3 — Drag de ferragens + boundary

**Status:** —

---

## Sub-entrega 4 — Resize de painel via handles

**Status:** —

---

## Sub-entrega 5 — Undo/redo com zundo

**Status:** —

---

## Sub-entrega 6 — Touch sensors + mobile

**Status:** —

---

## Sub-entrega 7 — Salvar versão + persistência

**Status:** —

---

## TOTAL
- Sub-entregas concluídas: 0/7
- Testes finais: —
- CI final: —
- Paradas para investigar de manhã: —
