# NutriSigno — Fluxo Oficial (Nov/2025)

Este documento consolida o **fluxo funcional oficial** do NutriSigno e serve como referência rápida para implementação, QA e onboarding.

---

## 1) Visão Geral
Aplicativo de nutrição com insights baseados em dados pessoais e perfil astrológico. Frontend em **Streamlit**, backend em **Python** com **PostgreSQL**, geração de PDF e **Plano IA** liberado após pagamento.

---

## 2) Fluxo do Usuário (alto nível)
1. **Usuário acessa o site** (`/`).
2. **Formulário 4 etapas** (`/form`) — dados pessoais, avaliação nutricional, psicológica, LGPD.
3. **Salvar no DB** (status `concluido`) e manter `pac_id`/`session_id` em estado de sessão.
4. **Renderizar Dashboard & Insights (na página)** (`/resultado?pac_id=...`).
5. **Ações do usuário** (na mesma tela):
   - **Compartilhar resultado** (link curto, somente leitura).
   - **Salvar PDF (resultado)** — resumo sem Plano IA.
   - **Pagamento** (checkout externo).
6. **Checkout externo** → **Webhook** atualiza `status_pagamento = pago`.
7. **Gerar Plano IA** (cardápio + substituições ±2%).
8. **Atualizar Dashboard** com Plano IA e disponibilizar **PDF completo**.
9. **Reabrir sessão** em `/acessar` com **celular + data de nascimento** → validar → carregar Dashboard.

---

## 3) Diagrama (Mermaid)
> Cole diretamente no README do GitHub: ele renderiza o Mermaid nativamente.

```mermaid
flowchart TD
A[Usuário acessa site (/)] --> B[Formulário 4 etapas (/form)]
B --> C[Salvar no DB]
C --> D[Renderizar Dashboard & Insights (na página) (/resultado?pac_id=...)]

D --> E{Ações do usuário}
E --> E1[Compartilhar resultado (link curto)]
E --> E2[Salvar PDF (resultado)]
E --> E3[Pagamento]

E3 --> F[Checkout externo]
F --> |aprovado| G[Webhook → status = pago]
G --> H[Gerar Plano IA (cardápio + substituições)]
H --> I[Atualizar Dashboard com Plano IA]
I --> J[PDF completo disponível]

K[Reabrir sessão (/acessar)] --> L[Validar celular + data nasc.]
L --> |ok| D
```

---

## 4) Rotas e Componentes
- `/` — landing minimal (CTA).
- `/form` — `FormStepper` + validações; `on_submit → save_user() → redirect /resultado`.
- `/resultado` — monta Dashboard, mostra ações (compartilhar, PDF, pagamento, download plano IA).
- `/acessar` — form **celular + data_nasc** → busca e redirect para `/resultado`.

**Serviços** (`services/`):
- `db.py` (CRUD + upsert por `pac_id`).
- `pdf.py` (resumo e completo).
- `payments.py` (checkout + webhook handler).
- `ia_plan.py` (gerar plano e substituições).
- `links.py` (slug curto de compartilhamento).

---

## 5) Banco de Dados (PostgreSQL)
### Tabelas
```sql
CREATE TABLE usuarios (
  pac_id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  nome TEXT, email TEXT,
  telefone TEXT,             -- armazenar normalizado (E.164)
  data_nasc DATE,
  signo TEXT,
  altura_m NUMERIC,
  peso_kg NUMERIC,
  avaliacao_nutricional JSONB,
  avaliacao_psicologica JSONB,
  status_pagamento TEXT CHECK (status_pagamento IN ('pendente','pago')) DEFAULT 'pendente',
  consent_lgpd_at TIMESTAMPTZ
);

CREATE TABLE resultados (
  pac_id UUID REFERENCES usuarios(pac_id) ON DELETE CASCADE,
  insights_basicos JSONB,
  pdf_resumo_url TEXT,
  plano_ia JSONB,
  substituicoes JSONB,
  pdf_completo_url TEXT,
  status_plano TEXT CHECK (status_plano IN ('nao_gerado','gerando','disponivel','erro')) DEFAULT 'nao_gerado',
  PRIMARY KEY (pac_id)
);

CREATE TABLE pagamentos (
  id BIGSERIAL PRIMARY KEY,
  pac_id UUID REFERENCES usuarios(pac_id) ON DELETE CASCADE,
  provider TEXT,
  checkout_id TEXT,
  status TEXT,
  valor NUMERIC(10,2),
  webhook_payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_usuarios_tel_nasc ON usuarios(telefone, data_nasc);
```

---

## 6) Eventos e Webhooks (contratos)
- `on_form_submit(pac_id)` → persiste e redireciona para `/resultado`.
- `POST /webhooks/payments` → body do provedor; ao `status=paid`:
  1. `UPDATE usuarios SET status_pagamento='pago' WHERE pac_id=?`
  2. `ia_plan.generate(pac_id)` → grava em `resultados` e marca `status_plano='disponivel'`.
- `GET /resultado?pac_id=...` → compõe cards + botões conforme estado.

---

## 7) Segurança & LGPD (MVP pragmático)
- Reabertura por **celular + data_nasc**:
  - salvar **hash(SHA-256)** de `telefone_normalizado + data_nasc_iso` com **salt** do servidor e usar para matching.
  - Rate limit + reCAPTCHA no `/acessar`.
- Links de **compartilhamento** exibem apenas **resultado básico** (sem PII sensível).
- Log e **timestamp** do aceite LGPD por `pac_id`.

---

## 8) Checklists de Implementação
### Frontend (Streamlit)
- [ ] Form 4 etapas com validações e progresso
- [ ] Estado `pac_id` em `st.session_state`
- [ ] Tela `/resultado` reagindo a estados: `pendente` vs `pago`
- [ ] Botões: compartilhar, PDF (resumo), pagamento, download Plano IA
- [ ] Tela `/acessar` com validação e redirect

### Backend/Serviços
- [ ] CRUD `usuarios`/`resultados`/`pagamentos`
- [ ] Webhook pagamentos com verificação de assinatura
- [ ] Geração PDF (resumo e completo)
- [ ] Geração Plano IA (cardápio, substituições ±2%)

---

## 9) Estados esperados (QA rápido)
- **Novo usuário**: `status_pagamento='pendente'`, `status_plano='nao_gerado'`
- **Pago**: `status_pagamento='pago'`, `status_plano='disponivel'` e `pdf_completo_url` preenchido
- **Erro IA**: `status_plano='erro'` (mostrar retry no painel)

---

## 10) Roadmap curto
- Link de compartilhamento com expiração opcional
- Fila/worker para geração IA (evitar bloqueio de UI)
- Cache de PDFs para re-download
- Métricas no `/dashboard` (admin)

---

**Responsável:** Paganini (owner).  
**Última revisão:** 2025-11-11 (America/Sao_Paulo).
