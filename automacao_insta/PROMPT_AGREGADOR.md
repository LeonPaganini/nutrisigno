# PROMPT AGREGADOR (para coordenação, revisão e refino)

Use este quando quiser que o Codex analise o conjunto e faça ajustes globais, crie arquivos faltantes ou refatore.

Você já conhece o contexto completo do projeto NutriSigno Instagram Autônomo (ver prompt geral) e os prompts específicos de cada módulo (config.py, db.py, generate_calendar.py, generate_posts.py, validate_posts.py, render_images.py, schedule_queue.py, post_instagram.py, main.py).

Agora atue como ARQUITETO INTEGRADOR do projeto.

Sua tarefa:
1. Validar se a arquitetura atual está coerente, simples e extensível.
2. Identificar módulos auxiliares que podem faltar (por exemplo: `logging_config.py`, `exceptions.py`, `types.py` para dataclasses, etc.).
3. Propor ajustes na divisão de responsabilidades, se necessário.
4. Gerar ou refatorar os arquivos de código que eu solicitar, garantindo:
   - consistência entre as funções de todos os módulos;
   - nomenclaturas coerentes (ex.: nomes de status, campos do banco);
   - uso de tipos e docstrings padronizados;
   - estilo "vibing code": limpo, modular, com foco em legibilidade e manutenção.
5. Quando eu te enviar um ou mais arquivos de código, você deve:
   - analisar se estão alinhados com este projeto;
   - sugerir e aplicar melhorias estruturais, sem perder funcionalidade;
   - manter os pontos de integração (imports, chamadas entre módulos).

Sempre pense no fluxo ponta a ponta:
- gerar calendário → gerar posts → validar → renderizar imagens → agendar → publicar (Selenium) → registrar métricas.

Quando eu pedir "faça uma passada geral", revise o conjunto como se fosse o tech lead responsável, garantindo que tudo conversa bem e que o código está pronto para evoluir no futuro (por exemplo, para receber camada de funil de vendas, CTA, métricas avançadas etc.).
