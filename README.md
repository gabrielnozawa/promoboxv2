# 📦 PromoBox

**Suas melhores ofertas, no automático.**

Sistema de automação de ofertas e promoções de programas de afiliados: importa
ofertas de plataformas autorizadas (ou CSV), organiza e pontua os produtos,
gera textos promocionais com IA, agenda e publica automaticamente nos canais
configurados (WhatsApp Business Cloud API, Telegram, Webhook, E-mail).

---

## Índice
1. [Tecnologias](#tecnologias)
2. [Estrutura de arquivos](#estrutura-de-arquivos)
3. [Instalação local](#instalação-local)
4. [Modo DEMO](#modo-demo)
5. [Banco de dados](#banco-de-dados)
6. [Configuração de secrets](#configuração-de-secrets)
7. [IA](#ia)
8. [Integrações — status atual](#integrações--status-atual)
9. [Executando o worker (automação)](#executando-o-worker-automação)
10. [Deploy no Streamlit Cloud](#deploy-no-streamlit-cloud)
11. [Segurança](#segurança)
12. [Testes realizados](#testes-realizados)

---

## Tecnologias

- **Python 3.11+**
- **Streamlit** — painel administrativo (dashboard, cadastro, agendamento etc.)
- **SQLAlchemy + SQLite** — banco relacional (trocável para Postgres/MySQL via `DATABASE_URL`)
- **APScheduler** — worker/agendador em background
- **Requests** — chamadas HTTP para APIs oficiais (WhatsApp Cloud API, Telegram Bot API, webhooks)
- **Anthropic SDK** (opcional) — geração de texto por IA além do modo template

## Estrutura de arquivos

```
promobox/
├── Home.py                     # Dashboard (entrada principal do Streamlit)
├── run_worker.py                # Worker standalone (automação contínua)
├── webhook_server.py             # Servidor HTTP standalone p/ webhook oficial do WhatsApp
├── pages/                        # Páginas do painel (requisito do Streamlit multipage)
│   ├── 0_WhatsApp_Business.py    # Canal principal: config, destinos, automação, fila, teste, histórico
│   ├── 1_Ofertas.py
│   ├── 2_Importacao.py
│   ├── 3_Agendamento.py
│   ├── 4_Canais.py                # Telegram, Webhook, E-mail (WhatsApp fica na página dedicada)
│   ├── 5_Historico.py
│   ├── 6_Analytics.py
│   ├── 7_Logs.py
│   └── 8_Configuracoes.py
├── app/
│   ├── database/                 # models.py, db.py, settings_repo.py, seed_demo.py
│   ├── services/
│   │   ├── validation.py, scoring.py, rotation.py
│   │   └── whatsapp/              # WhatsAppService — módulo dedicado do canal principal
│   │       ├── client.py          # cliente da Cloud API oficial (auth, teste de conexão, envio)
│   │       ├── templates.py       # modelos de mensagem + toggles imagem/texto/link
│   │       ├── destinations.py    # tipos de destino REALMENTE suportados pela API oficial
│   │       └── webhook.py         # verificação e parsing do webhook oficial
│   ├── integrations/              # shopee/, mercadolivre/, amazon/, other/, csv_importer.py
│   ├── channels/                  # whatsapp.py (adaptador, usa services/whatsapp), telegram.py, webhook.py, email_channel.py
│   ├── ai/                        # generator.py
│   ├── scheduler/                 # queue.py, worker.py
│   ├── components/                # auth.py, layout.py
│   └── utils/                     # config.py, logger.py
├── data/                          # banco SQLite + logs (não versionado)
├── .streamlit/
│   ├── config.toml                # tema escuro azul/roxo
│   └── secrets.toml.example
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

> O restante do PromoBox nunca fala diretamente com a Graph API da Meta — ele
> passa sempre por `app/channels/whatsapp.py`, que por sua vez usa
> `app/services/whatsapp/`. Isso deixa a arquitetura pronta para adicionar
> outros canais (Discord, etc.) sem tocar no worker ou na fila.

> Nota de arquitetura: o Streamlit exige que a pasta `pages/` fique ao lado do
> script principal (`Home.py`) para o multipage funcionar — por isso as
> páginas ficam em `/pages` na raiz, enquanto toda a lógica de negócio
> (banco, IA, integrações, canais, agendador) fica modularizada dentro de
> `/app`, conforme pedido.

## Instalação local

```bash
git clone <seu-repositorio>
cd promobox
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# opcional, só se for usar AI_PROVIDER=anthropic:
# pip install -r requirements-ai.txt

cp .env.example .env           # edite conforme necessário
streamlit run Home.py
```

Login padrão em modo DEMO: **admin** / **promobox123** (troque via
`ADMIN_PASSWORD_HASH` antes de ir para produção).

### O app fica "carregando" e não inicia — o que verificar

Esse sintoma quase sempre vem de um destes pontos:

1. **`pip install` ainda rodando.** Olhe o terminal onde você rodou o comando
   — em máquinas mais lentas ou no primeiro build do Streamlit Cloud, resolver
   as dependências pode levar alguns minutos. O `requirements.txt` usa faixas
   de versão (`>=`) em vez de versões travadas exatas, exatamente para evitar
   builds que travam tentando resolver conflitos.
2. **Comando errado.** Rode `streamlit run Home.py` de dentro da pasta
   `promobox/` (onde `Home.py` e a pasta `pages/` estão lado a lado). Rodar de
   outro diretório, ou apontar para outro arquivo, faz o Streamlit não achar
   as páginas.
3. **Porta ocupada.** Se a 8501 já estiver em uso, rode
   `streamlit run Home.py --server.port 8502` e acesse a nova porta.
4. **Nomes de arquivo com emoji.** As páginas em `pages/` usam apenas letras,
   números e `_` no nome do arquivo (os ícones ficam só dentro do conteúdo de
   cada página) — isso evita problemas de encoding que alguns sistemas
   Windows e alguns fluxos de deploy (zip/git) têm com nomes de arquivo com
   emoji, que podem travar a descoberta de páginas do Streamlit.
5. **Cache do navegador.** Se você já tinha aberto uma versão antiga do app na
   mesma aba, dê um refresh forçado (Ctrl+Shift+R) ou abra em uma aba anônima.
6. **Streamlit Cloud preso em "carregando".** Confira os *logs* do deploy
   (canto inferior direito da página do app) — normalmente o motivo real
   (erro de import, dependência faltando) aparece lá, mesmo quando a tela
   principal só mostra o spinner.

### `ModuleNotFoundError: No module named 'app'` (ou `app.algumacoisa`) no Streamlit Cloud

Esse erro específico — diferente do "fica carregando" acima — quase sempre
significa que a pasta `app/` (com `database/`, `services/`, `integrations/`,
`channels/`, `ai/`, `scheduler/`, `components/`, `utils/` dentro dela) **não
foi enviada para o repositório do GitHub**, algo comum quando se faz upload
pela interface web do GitHub ("Add file → Upload files") em vez de usar
`git push`. Checklist:

1. Abra o repositório no GitHub pelo navegador e confirme que existe uma
   pasta `app/` na raiz, com todas as subpastas acima e arquivos `.py`
   dentro delas (inclusive os `__init__.py`, que são vazios mas precisam
   existir).
2. Confirme que `Home.py`, `pages/` e `requirements.txt` estão direto na
   raiz do repositório — não dentro de outra subpasta (ex:
   `promoboxv2/promobox/Home.py` em vez de `promoboxv2/Home.py`).
3. Em **Manage app → Settings** no Streamlit Cloud, confirme que o **Main
   file path** é exatamente `Home.py`.
4. Se algo estava faltando, o jeito mais confiável de reenviar tudo
   corretamente é por linha de comando (evita os limites/bugs do upload
   pela web):
   ```bash
   cd promobox
   git init
   git add .
   git commit -m "PromoBox"
   git branch -M main
   git remote add origin <url-do-seu-repositorio>
   git push -u origin main
   ```
5. Depois de corrigir o repositório, clique em **Reboot app** no menu
   "Manage app" do Streamlit Cloud.

Como proteção extra, `Home.py`, todas as páginas, `run_worker.py` e
`webhook_server.py` agora adicionam explicitamente a raiz do projeto ao
`sys.path` antes de importar qualquer módulo `app.*` — isso evita esse erro
em ambientes de deploy que, por algum motivo, não adicionam o diretório do
script automaticamente ao `sys.path` (mesmo com o `app/` presente).

## Modo DEMO

Com `DEMO_MODE=true` (padrão), o sistema:
- Popula automaticamente produtos e ofertas fictícios, todos prefixados com `[DEMO]`.
- Nunca mistura dados DEMO com dados reais (todo filtro do painel respeita `is_demo`).
- Todos os canais (WhatsApp, Telegram, Webhook, E-mail) **simulam o envio**
  em vez de chamar as APIs reais, mesmo que credenciais estejam presentes.
- Permite testar cadastro, importação CSV, IA, agendamento, fila, histórico e
  analytics (inclusive simulando cliques/conversões na página Analytics).

Para operar com dados reais, defina `DEMO_MODE=false` e preencha as
credenciais necessárias.

## Banco de dados

SQLite local por padrão (`data/promobox.db`), criado automaticamente na
primeira execução. Tabelas: `users, categories, affiliate_sources, products,
offers, affiliate_links, channels, scheduled_posts, published_posts, clicks,
conversions, settings, logs`.

Para produção, troque `DATABASE_URL` no `.env`/secrets para um banco externo,
por exemplo:
```
DATABASE_URL=postgresql://usuario:senha@host:5432/promobox
```

## Configuração de secrets

**Local:** copie `.env.example` para `.env` e preencha os valores.
**Streamlit Cloud:** copie `.streamlit/secrets.toml.example` para
`.streamlit/secrets.toml` (local, não versionado) ou cole o conteúdo no painel
"Secrets" do Streamlit Community Cloud.

Nenhuma chave, token ou senha fica hardcoded no código-fonte.

## IA

O módulo `app/ai/generator.py` gera título, descrição curta, CTA, resumo do
desconto e textos para WhatsApp/Telegram/Instagram usando **somente os dados
reais da oferta** (produto, preços, desconto, loja, link). Dois modos:

- `template` (padrão): geração 100% local, sem chamadas externas.
- `anthropic`: usa a API da Anthropic para redigir com mais variedade,
  mantendo um prompt que proíbe explicitamente inventar preço, desconto,
  características, avaliações, disponibilidade ou benefícios não informados.
  Requer `ANTHROPIC_API_KEY`; se ausente, cai automaticamente para `template`.

## Integrações — status atual

| Plataforma | Status | Observação |
|---|---|---|
| **CSV manual** | ✅ Funcionando | Importação completa, validação de colunas e linhas |
| **Modo DEMO** | ✅ Funcionando | Produtos/ofertas fictícios para testar todo o fluxo |
| **WhatsApp Business Cloud API** | ⏳ Aguardando credenciais | Adaptador pronto (`app/channels/whatsapp.py`), só falta `WHATSAPP_ACCESS_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` |
| **Telegram Bot API** | ⏳ Aguardando credenciais | Adaptador pronto (`app/channels/telegram.py`), só falta `TELEGRAM_BOT_TOKEN` |
| **Webhook** | ✅ Funcionando | Envia POST JSON para qualquer URL cadastrada |
| **E-mail (SMTP)** | ⏳ Aguardando credenciais | Adaptador pronto, falta host/usuário/senha SMTP |
| **Shopee Affiliate Open API** | ⏳ Aguardando aprovação/API | Esqueleto de autenticação (HMAC) pronto; `fetch_offers` implementado como TODO — endpoint real não foi inventado |
| **Mercado Livre** | ⏳ Aguardando aprovação/API | Esqueleto OAuth2 pronto; feed de afiliados depende de aprovação no programa oficial |
| **Amazon PA-API 5.0** | ⏳ Aguardando credenciais | Esqueleto pronto; chamada real requer SDK oficial + Access/Secret Key + Partner Tag |

Nenhum endpoint foi inventado: onde a documentação oficial de uma plataforma
não estava disponível/acessível para implementação completa, o conector foi
deixado como módulo preparado (`NotImplementedError` explícito), pronto para
receber a implementação assim que as credenciais/documentação estiverem
disponíveis.

## WhatsApp Business — canal principal

O WhatsApp é o canal principal do PromoBox e usa **exclusivamente** a WhatsApp
Business Platform / Cloud API oficial da Meta — nunca WhatsApp Web, QR Code,
Selenium, Puppeteer ou qualquer automação de cliques. A página **WhatsApp
Business** (menu lateral, primeira opção) concentra:

- **Configuração**: status (✅/⬜) de Access Token, Phone Number ID, WABA ID,
  App ID, App Secret e Webhook Verify Token, sempre lidos de variáveis de
  ambiente/secrets — nunca exibidos nem editados no frontend. Botão
  **Testar conexão**, que chama `GET /{phone_number_id}` na Graph API e mostra
  🟢 Conectado / 🔴 Não conectado.
- **Destinos**: cada destino tem nome, identificador, tipo, categoria
  permitida, horários, dias da semana, limite diário e toggles de
  imagem/texto/link. Dois tipos são suportados de forma legítima pela API
  oficial:
  - **Número individual** — um único número de WhatsApp.
  - **Lista de transmissão** — vários números (separados por vírgula no
    cadastro). Não é um recurso de "grupo": o sistema envia a mesma mensagem
    **individualmente** para cada número da lista, uma chamada oficial
    `POST /messages` por destinatário (ver `WhatsAppClient.send_broadcast`
    em `app/services/whatsapp/client.py`). Fora da janela de 24h de sessão
    com cada contato, a Meta exige o uso de *message templates* aprovados
    para iniciar a conversa — configure isso na sua conta Meta conforme a
    política vigente; o PromoBox não contorna essa exigência.

  **Importante:** "grupos do WhatsApp" continuam fora do escopo — não existe
  suporte oficial da Meta para publicar automaticamente em um grupo. Se você
  tentar cadastrar um destino do tipo grupo, o sistema
  avisa claramente que esse tipo não está disponível na integração oficial e
  o mantém fora da fila automática, em vez de fingir que funciona.
- **Automação**: botão ATIVAR/DESATIVAR a publicação automática do WhatsApp
  no worker (os demais canais não são afetados por esse botão).
- **Fila**: lista de publicações agendadas para o WhatsApp, com editar
  horário, cancelar, reprogramar e publicar manualmente.
- **Teste**: envia uma mensagem de exemplo somente para um destino marcado
  como "destinatário de teste" — nunca para destinos reais, mesmo com
  DEMO_MODE=false.
- **Histórico**: publicações do WhatsApp com data, hora, produto, destino,
  status (🟢 Enviada / 🟡 Agendada / 🔴 Erro / ⚪ Cancelada), mensagem e erro.

O webhook oficial (verificação GET + eventos POST da Meta) roda como um
processo HTTP separado, já que o Streamlit não atende requisições webhook
cruas:

```bash
python webhook_server.py
# expõe http://0.0.0.0:8090/webhook/whatsapp
```

Configure essa URL (atrás de HTTPS/proxy) no painel da Meta, junto com o
mesmo valor de `WHATSAPP_WEBHOOK_VERIFY_TOKEN` do seu `.env`/secrets.

## Executando o worker (automação)

O worker roda **independente do painel estar aberto**:

```bash
python run_worker.py
```

A cada `CYCLE_INTERVAL_MINUTES` (padrão 5 min), ele executa o fluxo completo:
buscar → validar → filtrar → verificar duplicidade/rotação → pontuar →
selecionar → gerar texto com IA → enfileirar → aguardar horário → publicar →
registrar resultado/erro → atualizar estatísticas.

Também é possível disparar um ciclo manual pelo painel, na página
**Agendamento** (botão "Rodar ciclo do worker agora"), útil para testes.

## Deploy no Streamlit Cloud

1. Suba o repositório no GitHub (o `.gitignore` já protege `.env` e o banco local).
2. Em [share.streamlit.io](https://share.streamlit.io), crie um novo app apontando para `Home.py`.
3. Em "Secrets", cole o conteúdo de `.streamlit/secrets.toml.example` preenchido.
4. (Opcional) Rode `run_worker.py` separadamente em outro serviço (ex: uma
   máquina/worker dedicado, um cron job, ou um segundo processo), já que o
   Streamlit Cloud não mantém processos em background de forma garantida.
5. Para banco externo em produção, ajuste `DATABASE_URL` nos secrets.

## Segurança

- Autenticação obrigatória para acessar o painel (`app/components/auth.py`).
- Senhas armazenadas com hash (SHA-256 + salt), nunca em texto puro.
- Todas as credenciais vêm de variáveis de ambiente/secrets — nunca do código.
- Logs mascaram automaticamente qualquer token/senha/secret antes de gravar
  (`app/utils/logger.py::mask_sensitive`).
- Links de afiliado nunca são substituídos automaticamente por outro
  desconhecido — o sistema apenas armazena e exibe o link fornecido.

## Testes realizados

Durante o desenvolvimento foram verificados manualmente:
- ✅ Inicialização do banco e criação de todas as tabelas (`init_db()`).
- ✅ Seed de dados DEMO (produtos, ofertas, canais) sem duplicar em reexecuções.
- ✅ Cálculo automático de desconto (`compute_discount()`).
- ✅ Importação de CSV com colunas válidas/; inválidas e linhas com preços inconsistentes.
- ✅ Geração de texto promocional via template (sem inventar dados).
- ✅ Montagem da fila do dia respeitando desconto mínimo, limite diário,
  limite por categoria e intervalo de repetição.
- ✅ Ciclo completo do worker em modo DEMO: validação → geração de texto →
  envio simulado → status `PUBLICADA` → registro em `published_posts`.
- ✅ Simulação de cliques/conversões e reflexo correto nas métricas do
  Dashboard e Analytics.
- ✅ Login/logout e bloqueio de acesso sem autenticação.
- ✅ Mascaramento de tokens nos logs.

**Não foi possível testar** (por depender de credenciais reais de terceiros,
propositalmente não simuladas): chamadas reais às APIs da Shopee, Mercado
Livre, Amazon, WhatsApp Cloud API, Telegram Bot API e SMTP real. Os
adaptadores estão prontos e claramente sinalizados como "aguardando
credenciais" tanto no código quanto na página de Importação/Configurações do
painel.
