# PROMPTS POR MÓDULO ESPECÍFICO

Use um prompt por vez, sempre combinando com o Prompt Geral (ou colando o geral antes, e depois o específico do módulo).

## 2.1. config.py
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `config.py`.

Objetivo do módulo:
- Centralizar configurações do sistema:
  - Caminhos padrão (pastas de fontes, renders, logs, banco SQLite etc.).
  - Configurações de Instagram (ex.: URL de login, seletores genéricos usados pelo Selenium).
  - Configurações de IA externa (endpoint base, nome do modelo, etc.), SEM incluir chaves.
  - Parâmetros default dos posts (tamanho das imagens, margens, paleta de cores).
  - Configurações de logging (nível, formato, arquivo de saída).

Requisitos:
- Usar dataclasses ou estruturas claras para agrupar configurações (`AppConfig`, `DbConfig`, `InstagramConfig`, `ImageConfig`, etc.).
- Ler variáveis de ambiente quando necessário (ex.: caminhos customizados, API keys, path do banco).
- Fornecer uma função helper `load_config()` que retorne uma instância consolidada de configuração para ser usada em outros módulos.
- Manter o código limpo, tipado e preparado para ser importado por qualquer outro módulo.

## 2.2. db.py (SQLite + helpers)
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `db.py`.

Objetivo do módulo:
- Gerenciar a conexão com o banco SQLite.
- Criar tabelas necessárias (se não existirem) para:
  - `posts`:
    - id (PK)
    - tipo_post (str)
    - signo (str opcional)
    - tema (str opcional)
    - texto_imagem (str)
    - legenda (str)
    - hashtags (str)
    - status (str) — ex.: "rascunho", "validado", "renderizado", "agendado", "publicado", "erro"
    - imagem_path (str opcional)
    - data_publicacao_planejada (datetime ou str ISO)
    - data_publicacao_real (datetime ou str ISO opcional)
    - likes (int)
    - comentarios (int)
    - saves (int)
    - shares (int)
  - Se achar necessário, criar tabela auxiliar `logs_execucao` ou similar.

Requisitos:
- Usar `sqlite3` da biblioteca padrão.
- Criar funções helpers como:
  - `init_db()`
  - `insert_post(...)`
  - `update_post_status(post_id, novo_status, ...)`
  - `get_posts_by_status(status: str, limit: int = 10)`
  - `save_metrics(post_id, likes, comentarios, saves, shares)`
- Retornar dados em estruturas Python claras (ex.: dicts ou dataclasses, você escolhe, mas seja consistente).
- Garantir tratamento básico de erros (try/except) e logging nos pontos críticos.
- Código limpo, organizado, com docstrings.

## 2.3. generate_calendar.py
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `generate_calendar.py`.

Objetivo do módulo:
- Gerar um calendário editorial para N dias à frente, definindo:
  - data planejada de publicação;
  - tipo de post;
  - signo (quando aplicável);
  - tema principal (ex.: ansiedade, foco, hidratação, compulsão).

Requisitos:
- Criar função principal, por exemplo: `generate_calendar(dias: int) -> list[dict]`.
- A função deve:
  - distribuir tipos de posts (frase única, carrossel de signo, carrossel de tema, educativo, previsão semanal, motivacional) de forma equilibrada.
  - opcional: balancear signos ao longo do tempo.
- Criar função para salvar essas entradas no banco (usando `db.py`), deixando os registros com `status="rascunho"`.
- Permitir rodar o módulo como script (if __name__ == "__main__") para gerar X dias de conteúdo de uma vez.
- Código em estilo "vibing code": simples, legível, com lógica clara para rotação de tipos de post.

## 2.4. generate_posts.py
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `generate_posts.py`.

Objetivo do módulo:
- Para cada entrada de calendário em `status="rascunho"`, gerar:
  - `texto_imagem` (a frase que vai na arte).
  - `legenda` (texto da legenda do Instagram).
  - `hashtags` (lista ou string pronta para uso).

Requisitos:
- Integrar com um provider de IA de texto (ex.: OpenAI), mas:
  - Encapsular a chamada em uma função clara (ex.: `generate_text_for_post(entry)`) que pode ser mockada.
  - NÃO colocar chave de API no código; usar variável de ambiente ou argumentos.
- Respeitar o tom NutriSigno (místico-racional, sem promessas milagrosas).
- Gerar conteúdo adaptado ao tipo de post:
  - frase única: 1 a 3 linhas fortes.
  - carrossel de insights: estruturar o conteúdo em páginas (retornar estrutura adequada).
  - posts educativos: legenda com educação nutricional simples.
- Atualizar o registro no banco com os textos gerados e mudar `status` para algo como `"gerado"` ou `"para_validar"`.
- Incluir uma função para processar em lote, ex.: `generate_all_pending_posts(limit: int | None = None)`.

Observação:
- Estruturar o código para que o módulo possa ser rodado sozinho, mas também chamado por um orquestrador (ex.: main.py).

## 2.5. validate_posts.py (Agente Guardião)
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `validate_posts.py`.

Objetivo do módulo:
- Validar o conteúdo gerado antes de seguir para renderização de imagem:
  - Tom de voz (místico-racional, sem promessas milagrosas).
  - Clareza e coerência.
  - Ética nutricional básica.
  - Alinhamento com o signo e o tipo de post.
- Ajustar automaticamente pequenas falhas (quando possível) ou marcar como "erro" para revisão manual.

Requisitos:
- Definir uma função `validate_post(post: dict) -> dict` que:
  - receba os campos do post (tipo, signo, texto_imagem, legenda, hashtags).
  - aplique regras básicas de validação (regex, palavras proibidas, tamanho máximo, etc.).
  - opcionalmente use IA em modo "validador" para revisão do texto (pode chamar o mesmo provider de IA com prompt de validação).
  - retorne a versão revisada do post e um status final: `"validado"` ou `"erro"`.
- Criar função `validate_all_pending_posts()` que:
  - busque posts com status `"para_validar"` (ou similar).
  - processe todos.
  - atualize o banco com o novo conteúdo e status.
- Utilizar logging para relatar rejeições, motivos e posts problemáticos.

## 2.6. render_images.py (Pillow)
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `render_images.py`.

Objetivo do módulo:
- Gerar as imagens dos posts usando Pillow, com:
  - fundo em degradês orgânicos (baseado na paleta do NutriSigno);
  - texto centralizado/de forma apropriada;
  - logo do NutriSigno no canto inferior direito;
  - tamanho padrão 1080 x 1350 px.

Requisitos:
- Função principal: `render_post_image(post: dict, config: AppConfig) -> str` que:
  - receba os dados do post (tipo_post, texto_imagem, etc.).
  - crie o fundo (degradê) com variações leves entre posts:
    - pode usar shapes elípticos com alpha sobre fundo base.
  - desenhe o texto de forma legível, com quebras de linha automáticas.
  - insira o logo a partir de um arquivo em disco (path vindo de config).
  - salve a imagem no diretório configurado (ex.: `renders/`) e retorne o caminho.
- Função `render_all_validated_posts()`:
  - busca posts em status `"validado"` sem imagem associada.
  - gera imagens para todos.
  - atualiza o banco com `imagem_path` e `status="renderizado"`.
- Usar tipagem e tratar erros (por exemplo, ausência de fonte ou logo).
- Manter separação clara de responsabilidades:
  - uma função para criar o fundo.
  - uma função para escrever texto.
  - uma função para aplicar o logo.

## 2.7. schedule_queue.py
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `schedule_queue.py`.

Objetivo do módulo:
- Definir a fila de publicação:
  - escolher posts renderizados e prontos.
  - atribuir data e hora de publicação planejada.
  - manter uma ordem lógica (por exemplo, 1 post por dia às 09:00).

Requisitos:
- Função `schedule_posts_for_range(start_date, end_date)`:
  - pega posts com `status="renderizado"` que ainda não têm `data_publicacao_planejada`.
  - define horário padrão (por exemplo 09:00 local) ou recebe por parâmetro.
  - atualiza o banco com a data/hora planejada e status `"agendado"`.
- Função `get_posts_due(now)`:
  - retorna posts com `status="agendado"` e `data_publicacao_planejada <= now`.
  - será usada pelo módulo de publicação para saber o que postar.
- Permitir execução como script para agendar um lote.

## 2.8. post_instagram.py (Selenium)
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `post_instagram.py`.

Objetivo do módulo:
- Publicar os posts no Instagram de forma automatizada via Selenium, usando:
  - login na conta do Instagram (ou Facebook Business, se preferir).
  - upload da imagem gerada.
  - inclusão de legenda + hashtags.
  - confirmação da publicação.

Requisitos:
- Usar Selenium WebDriver de forma robusta:
  - funções para iniciar driver (Chrome ou outro).
  - função para login, usando usuário/senha vindos de variáveis de ambiente ou config.
  - função `publish_post(post: dict, driver)`.
- Ler posts prontos para publicação a partir do banco:
  - status `"agendado"` e `data_publicacao_planejada <= agora`.
- Após postar com sucesso:
  - atualizar status para `"publicado"`.
  - registrar `data_publicacao_real`.
- Em caso de erro:
  - logar a falha.
  - manter ou mudar status para `"erro"` conforme necessário.
- Não deixar credenciais hardcoded no código.
- Prever pontos de espera explícitos (WebDriverWait) para evitar falhas por carregamento lento.

## 2.9. main.py (orquestrador local, opcional mas recomendado)
Usando o contexto do projeto NutriSigno Instagram Autônomo descrito no prompt geral, gere o módulo `main.py`.

Objetivo do módulo:
- Servir como orquestrador/CLI local para o sistema.
- Permitir rodar ações como:
  - gerar calendário;
  - gerar posts;
  - validar posts;
  - renderizar imagens;
  - agendar;
  - publicar.

Requisitos:
- Usar `argparse` ou similar para criar comandos de terminal, ex.:
  - `python main.py generate-calendar --days 30`
  - `python main.py generate-posts`
  - `python main.py validate-posts`
  - `python main.py render-images`
  - `python main.py schedule-posts --start YYYY-MM-DD --end YYYY-MM-DD`
  - `python main.py publish-due`
- Integrar com os módulos anteriores, chamando as funções públicas de cada um.
- Carregar configuração global via `config.load_config()`.
- Usar logging para registrar operações.
