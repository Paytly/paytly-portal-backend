# Roadmap de Desenvolvimento (MVP)

## Fase 0 — Fundação (1–2 dias)
**Objetivo:** ter base para evoluir sem refazer.

### Tarefas
1) **Definir o modelo mínimo no Postgres**
- `reconciliation_runs` (status, timestamps)
- `uploads` (storage_key, side, status)
- `money_events` (normalizado)
- (opcional agora) `exceptions`, `match_groups`

2) **Criar o projeto backend**
- FastAPI + SQLAlchemy + Alembic
- Config por env vars (`DATABASE_URL`, `S3_BUCKET` etc.)

3) **Criar o projeto frontend**
- Next.js (página simples)
- Chamadas HTTP para API (sem login)

### Entrega
- API rodando + DB migrado + frontend básico conectando.

---

## Fase 1 — Upload via Presigned URL (MVP real começa) (2–4 dias)
**Objetivo:** conseguir mandar arquivo para S3 sem passar pelo backend.

### Tarefas
1) Endpoint `POST /uploads/presign`
- retorna `presigned_url` (PUT) + `upload_id` + `storage_key`

2) Frontend faz upload direto para S3
- implementa `PUT` no browser
- UI com progresso (opcional)
- depois chama `POST /uploads/{id}/complete`

3) Endpoint `POST /runs/{id}/start`
- valida que tem bank + provider upload “UPLOADED”
- marca run como `PENDING`

### Entrega
- você já consegue criar um run e anexar dois arquivos ao run (no S3), e disparar processamento (mesmo que ainda não exista worker).

---

## Fase 2 — Worker + parsing mínimo (5–7 dias)
**Objetivo:** processar e salvar algo no DB.

### Tarefas
1) Subir um worker (processo separado)
- loop buscando `reconciliation_runs` com `PENDING`
- lock com `FOR UPDATE SKIP LOCKED`
- marca `RUNNING`

2) Parsing mínimo dos CSVs
- Banco: exigir um CSV com colunas fixas temporárias para destravar (ex.: `date,amount,description`)
- Provedor: idem (ou começar com Stripe parser se você preferir)

3) Normalizar e gravar `money_events`
- salvar todas as linhas normalizadas (bank/provider)
- status do run: `DONE`

### Entrega
- fluxo completo funcionando. Você faz upload, o worker processa e você consegue ver no DB “o que entrou”.

> Importante: nessa fase, o matching pode ser “vazio” e ainda assim você tem algo testável.

---

## Fase 3 — Primeiro matching útil (3–6 dias)
**Objetivo:** entregar valor “de verdade”: conciliar depósitos/payouts e listar pendências.

### Tarefas
1) Implementar matching 1:1 simples
- match por:
  - valor igual
  - data dentro de `±3 dias`
- criar:
  - `match_groups` (`AUTO_MATCHED`)
  - `exceptions` para itens sem match (`UNMATCHED`)

2) Endpoint `GET /runs/{id}/results`
- paginado: matches + exceptions
- contadores (quantos conciliados, quantos pendentes)

3) Frontend: tela de resultados
- tabs: “Matched” e “Exceptions”
- filtros simples (por data, por valor)

### Entrega
- primeira versão “que alguém usaria”.

---

## Fase 4 — Mapeamento de colunas (banco) (4–8 dias)
**Objetivo:** aceitar CSV de qualquer banco sem ficar preso em um formato.

### Tarefas
1) Criar `data_sources` com `config_json` (mapeamento)
- salvar: qual coluna é `date/amount/description` etc.
- salvar: separador decimal, formato de data

2) UI de mapeamento
- preview das 10 primeiras linhas
- dropdowns para mapear
- “save template”

3) Atualizar parser do banco para usar o mapping

### Entrega
- muito mais universal e vendável.

---

## Fase 5 — Melhorias que aumentam muito o valor (iterativo)
**Objetivo:** evoluir precisão, UX e possibilidades de uso.

### Itens sugeridos
1) Matching com tolerância + agregação
- tolerância de centavos / FX
- “1 depósito = soma de N payouts”

2) Reprocessamento
- botão “re-run” usando os mesmos uploads e novos parâmetros

3) Export de resultados (CSV/Excel)
- “lista de pendências para o contador”

4) “Explain” (explicações)
- começa simples: “diff = X”
- depois: breakdown (fees/refunds) quando tiver conector específico (Stripe)