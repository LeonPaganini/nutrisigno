# NutriSigno – Aplicativo de Plano Alimentar Astrológico

O **NutriSigno** é um aplicativo desenvolvido em Python e Streamlit com foco em
dispositivos móveis. Ele combina ciência nutricional com elementos de
astrologia para gerar planos alimentares personalizados de forma ética e
responsável. O projeto utiliza Firebase para armazenamento de dados,
OpenAI para geração de conteúdo inteligente e ReportLab/Matplotlib para
elaboração de relatórios em PDF.

## Recursos principais

* **Interface responsiva:** Construída com Streamlit, o layout foi pensado
  para uso em navegadores de dispositivos móveis. Um menu lateral permite
  navegar pelas seções do formulário sem sair da página.
* **Formulário em etapas:** O usuário fornece dados pessoais, de saúde,
  comportamentais e astrológicos. Todos os campos são obrigatórios e
  verificados antes de prosseguir para o pagamento.
* **Geração de plano personalizado:** Utiliza a API da OpenAI para combinar
  informações do usuário com perfis astrológicos e oferecer um plano
  alimentar sob medida. A resposta da IA é formatada em JSON para fácil
  manipulação no código.
* **Relatórios em PDF:** Após o pagamento, um relatório completo é
  gerado com ReportLab e Matplotlib, incluindo tabelas com o plano
  alimentar, gráficos nutricionais e insights personalizados.
* **Armazenamento em Firebase:** Os dados são gravados no Firebase
  Realtime Database somente ao final do processo, utilizando um ID único
  gerado no início da jornada. O módulo `firebase_utils.py` trata da
  inicialização segura da conexão.
* **Envio por e‑mail:** O relatório e o plano alimentar são enviados
  automaticamente para o endereço de e‑mail informado pelo usuário. O
  módulo `email_utils.py` utiliza SMTP configurável via variáveis de
  ambiente.

## Estrutura de diretórios

A estrutura do projeto está organizada da seguinte forma:

```
nutrisigno/
├── app.py               # Aplicação Streamlit principal
├── requirements.txt     # Dependências do projeto
├── .streamlit/
│   └── config.toml      # Configurações de tema e layout da interface
├── modules/
│   ├── firebase_utils.py  # Inicialização e salvamento no Firebase
│   ├── openai_utils.py    # Funções para interação com a OpenAI
│   ├── pdf_generator.py   # Geração de relatório PDF com gráficos
│   └── email_utils.py     # Envio de e-mails com anexos
└── assets/
    └── example_logo.png   # Imagem de exemplo para o relatório (substitua à vontade)
```

## Configuração

Antes de executar o aplicativo, configure as seguintes variáveis de
ambiente ou crie um arquivo `.env` no diretório raiz com as chaves
necessárias. Você também pode definir as variáveis no serviço de deploy
(Render, Vercel etc.).

| Variável             | Descrição                                                                 |
|----------------------|---------------------------------------------------------------------------|
| `OPENAI_API_KEY`     | Chave de API para acesso à OpenAI.                                        |
| `FIREBASE_JSON`      | Conteúdo JSON da conta de serviço do Firebase (codificado em base64).      |
| `SMTP_SERVER`        | Endereço do servidor SMTP para envio de e‑mails.                          |
| `SMTP_PORT`          | Porta do servidor SMTP.                                                   |
| `EMAIL_USERNAME`     | Nome de usuário para autenticação no servidor SMTP.                        |
| `EMAIL_PASSWORD`     | Senha ou token de autenticação SMTP.                                      |
| `SENDER_EMAIL`       | Endereço de e‑mail do remetente (o app enviará mensagens a partir dele).   |

Para o Firebase, copie o conteúdo JSON da conta de serviço (Firebase
Admin SDK) e converta para base64 usando uma ferramenta como
`base64` no terminal. Em seguida, defina a variável `FIREBASE_JSON` com
esse valor. O código decodificará automaticamente esse conteúdo.

## Executando localmente

1. Clone ou extraia o repositório.
2. Certifique‑se de ter Python 3.8 ou superior instalado.
3. Instale as dependências com `pip install -r requirements.txt`.
4. Defina as variáveis de ambiente necessárias (OpenAI, Firebase e
   servidor SMTP).
5. Execute a aplicação com `streamlit run app.py`.

## Observações

* A integração de pagamento no exemplo é apenas simbólica. Em produção,
  recomenda‑se utilizar um provedor de pagamentos (por exemplo,
  Stripe, PayPal) e verificar o pagamento antes de gerar e enviar o
  relatório.
* Os textos gerados pela OpenAI devem ser validados por um
  nutricionista antes de serem utilizados de forma prescritiva.
* O design é minimalista por padrão, mas pode ser customizado em
  `.streamlit/config.toml` e com recursos adicionais em `/assets`.
