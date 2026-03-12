# Conciliação Financeira por CSV — Documentação Técnica (v0.1)

## 1. Objetivo
Construir um sistema web que:
1) recebe arquivos (CSV/OFX futuramente) de **banco** e de **provedores de pagamento** (Stripe e/ou CSV genérico),
2) normaliza os dados para um formato interno padrão,
3) executa um processo de **conciliação** (matching) entre lançamentos,
4) apresenta resultados em um dashboard:
   - itens conciliados
   - itens não conciliados (“exceções”)
   - divergências de valor e explicações (quando possível)

O MVP visa conciliar principalmente **payouts/repasse ↔ depósitos no banco**.

## 2. Conceitos e definições
- **Banco (Bank Source):** origem de lançamentos do extrato bancário.
- **Provedor de pagamento (Payment Provider Source):** origem de eventos financeiros do gateway (Stripe, PayPal, etc.).
- **Normalização:** transformar linhas de arquivos diferentes em uma estrutura comum.
- **Conciliação (Reconciliation):** associar itens do banco com itens do provedor que representem o mesmo “evento real” (ex.: depósito no banco = payout do provedor).
- **Exceção:** item sem correspondência confiável ou com divergência significativa.

## 3. Escopo (MVP v0)
### 3.1. Entradas suportadas
- Banco: CSV com mapeamento de colunas (usuário define as colunas).
- Provedor: 
  - Stripe CSV (parser específico) **ou**
  - CSV genérico com mapeamento (para suportar “qualquer gateway”).

### 3.2. Saídas
- Tabelas:
  - **Matches (conciliado)**
  - **Exceções**
- Status de execução:
  - `PENDING`, `RUNNING`, `DONE`, `FAILED`

### 3.3. Fora de escopo (MVP)
- Contabilidade completa / plano de contas
- DRE e apuração fiscal
- Integrações automáticas por OAuth (será fase posterior)
- Detecção por ML (heurísticas primeiro)

## 4. Arquitetura (alto nível)
### 4.1. Componentes
- **Frontend (Vercel):** portal e dashboard (Next.js)
- **Backend API (Render Web Service):** FastAPI (upload, configurações, resultados)
- **Worker (Render Background Worker):** executa imports e conciliações (jobs)
- **DB (Neon ou Supabase):** PostgreSQL (estado do sistema, resultados)
- **Storage (S3):** armazenamento de arquivos brutos (originais)

### 4.2. Fluxo principal
1) Usuário cria um `reconciliation_run`
2) Usuário faz upload de:
   - arquivo do banco
   - arquivo do provedor
3) API grava os arquivos no S3 e registra `uploads`
4) API marca o `reconciliation_run` como `PENDING`
5) Worker pega runs pendentes, processa:
   - parse + normaliza
   - gera candidatos e scores
   - cria matches e exceções
6) Worker grava resultados e marca `DONE`
7) Frontend faz polling do status e exibe resultados

## 5. Modelo de dados (proposto)
> Observação: nomes podem variar, mas a ideia é persistir tudo que permita reprocessamento e auditoria.

### 5.1. Multi-tenant (desde o início)
- Toda tabela relevante deve conter `org_id`.
- Mesmo que no MVP exista apenas 1 org, isso evita retrabalho.

### 5.2. Tabelas principais

#### `orgs`
- `id` (uuid)
- `name`
- `created_at`

#### `users` (opcional no MVP)
- `id`
- `org_id`
- `email`
- `created_at`

#### `data_sources`
Representa uma origem/configuração de import.
- `id`
- `org_id`
- `kind` enum: `bank_csv`, `stripe_csv`, `payment_csv_generic`
- `name` (ex.: "Banco Inter - Conta PJ")
- `config_json` (mapeamento de colunas, moeda default, separador decimal, formato data)
- `created_at`

#### `uploads`
Arquivo bruto no S3.
- `id`
- `org_id`
- `data_source_id`
- `storage_key` (path no S3)
- `original_filename`
- `content_type`
- `size_bytes`
- `sha256` (opcional)
- `uploaded_at`

#### `reconciliation_runs`
Execução de conciliação.
- `id`
- `org_id`
- `status` enum: `PENDING`, `RUNNING`, `DONE`, `FAILED`
- `bank_upload_id`
- `provider_upload_id`
- `params_json` (tolerâncias, janela de datas, moeda)
- `error_message` (nullable)
- `started_at`, `finished_at`, `created_at`

#### `money_events`
Eventos normalizados (linhas).
- `id`
- `org_id`
- `run_id`
- `source_side` enum: `bank`, `provider`
- `provider` text (ex.: `stripe`, `paypal`, `generic`)
- `event_type` enum (MVP focar em: `deposit`, `payout`; futuro: `fee`, `refund`, `chargeback`, `adjustment`)
- `occurred_at` timestamp/date
- `amount` numeric (entrada positiva, saída negativa)
- `currency` text (BRL/USD)
- `description` text
- `external_id` text (nullable)
- `raw_json` jsonb
- índices:
  - `(org_id, run_id, source_side)`
  - `(org_id, occurred_at)`
  - `(org_id, amount)`

#### `match_groups`
Representa um match de 1..N itens do banco com 1..N itens do provedor.
- `id`
- `org_id`
- `run_id`
- `status` enum: `AUTO_MATCHED`, `NEEDS_REVIEW`, `CONFIRMED`, `REJECTED`
- `score` integer (0..100)
- `bank_total` numeric
- `provider_total` numeric
- `diff_amount` numeric
- `reason_code` text (ex.: `EXACT_MATCH`, `AGGREGATED_MATCH`, `TOLERANCE_MATCH`)
- `explanation` text (nullable)
- `created_at`

#### `match_group_items`
- `match_group_id`
- `money_event_id`
- `side` enum: `bank`, `provider`

#### `exceptions`
Itens que ficaram sem match aceitável ou com divergência.
- `id`
- `org_id`
- `run_id`
- `side` enum: `bank`, `provider`, `mixed`
- `exception_type` enum:
  - `UNMATCHED_BANK_DEPOSIT`
  - `UNMATCHED_PROVIDER_PAYOUT`
  - `VALUE_MISMATCH`
  - `AMBIGUOUS_MATCH`
- `severity` enum: `LOW`, `MEDIUM`, `HIGH`
- `summary`
- `details_json`
- `resolved_at` (nullable)
- `resolution_note` (nullable)

## 6. Padrão interno e normalização
### 6.1. Regras de normalização (banco CSV)
O importador do banco deve suportar:
- Coluna de data (vários formatos; deve ter detecção + override)
- Valor:
  - coluna única (com sinal ou tipo)
  - colunas separadas crédito/débito
- Descrição/histórico
- Moeda:
  - fixo por configuração ou coluna no CSV (opcional)
- Output: criar `money_event` com:
  - `source_side=bank`
  - `event_type=deposit` quando `amount > 0`, `withdrawal` quando `< 0` (no MVP pode ignorar withdrawals)
  - `raw_json` preservando a linha original

### 6.2. Regras de normalização (payment provider CSV)
- **Stripe CSV:** parser específico (ex.: balance/payout export)
- **Genérico:** mapeamento semelhante ao banco, porém com:
  - tentativa de mapear `event_type` (payout/refund/fee/etc.)
  - no MVP: mínimo é identificar `payout` (repasse)

## 7. Motor de conciliação (matching)
### 7.1. Objetivo do matching
Associar depósitos do banco (`deposit`) com payouts do provedor (`payout`).

### 7.2. Parâmetros (configuráveis por run)
- `date_window_days`: default 3
- `amount_tolerance_abs`: default 0.00 (ou 1.00 dependendo da moeda)
- `amount_tolerance_pct`: default 0.0% (opcional)
- `allow_aggregation`: default true (permitir somar vários payouts para bater com 1 depósito)

### 7.3. Estratégia (camadas)
1) **Exact match**: valor igual + data dentro da janela
2) **Tolerance match**: valor dentro da tolerância + data dentro da janela
3) **Aggregation match**: 1 depósito = soma de N payouts (N pequeno, ex. 2..10)
4) **Ambiguous**: múltiplas combinações possíveis → `NEEDS_REVIEW`

### 7.4. Scoring (0..100)
Exemplo (ajustável):
- base por match de valor:
  - exact: +60
  - tolerance: +45
- match de data:
  - mesmo dia: +30
  - 1 dia diff: +20
  - 2-3 dias diff: +10
- match por descrição/keywords (opcional): +0..10

Threshold:
- `score >= 85` → `AUTO_MATCHED`
- `score 60..84` → `NEEDS_REVIEW`
- `< 60` → vira exceção ou candidato fraco

## 8. Jobs e execução
### 8.1. Motivo
Evitar que o request de upload fique aguardando o processamento (que pode levar segundos/minutos).

### 8.2. Modelo recomendado (sem Redis)
- O status do run fica no Postgres.
- O worker executa loop:
  - `SELECT ... FOR UPDATE SKIP LOCKED` em `reconciliation_runs` com `status='PENDING'`
  - marca `RUNNING`
  - processa
  - marca `DONE` ou `FAILED`

Benefícios:
- Sem dependência de Redis
- Resiliente a reinício do web service
- Fácil de operar no Render (Web Service + Background Worker)

## 9. API (contratos sugeridos)
> Endpoints exemplificativos; ajuste conforme preferir REST ou RPC.

### 9.1. Runs
- `POST /runs` → cria run
- `GET /runs/{run_id}` → status e metadados
- `GET /runs/{run_id}/results` → matches e exceções (paginado)

### 9.2. Upload
- `POST /runs/{run_id}/uploads/bank` → upload CSV do banco
- `POST /runs/{run_id}/uploads/provider` → upload CSV do provedor

### 9.3. Data source templates (mapeamento)
- `POST /data-sources` → cria template de mapeamento
- `GET /data-sources` → lista
- `PUT /data-sources/{id}` → atualiza

## 10. Segurança e privacidade (mínimo)
- Tráfego HTTPS (Render/Vercel já fazem)
- Dados sensíveis:
  - criptografar secrets (keys S3) no provedor (env vars)
  - restringir acesso por `org_id`
- Armazenamento de CSV:
  - S3 com bucket privado
  - armazenar somente o necessário no DB, manter `raw_json` para auditoria
- Logs:
  - nunca logar linhas completas com dados pessoais (ex.: nomes, IBAN, etc.)

## 11. Observabilidade e suporte
- `run_id` em logs
- registrar contagem:
  - linhas importadas
  - itens conciliados
  - exceções
  - tempo total

## 12. Roadmap (evolução)
- Conectores automáticos (OAuth/API):
  - Stripe API first
  - depois PayPal/Shopify Payments
- Suporte a OFX/QIF e XLSX para bancos
- Regras customizadas por cliente
- Alertas automáticos (email/Slack)
- “Explain” avançado (ex.: breakdown por fees/refunds)
- Multi-moeda robusta e FX
- Portal com múltiplas soluções e UI kit compartilhado

---