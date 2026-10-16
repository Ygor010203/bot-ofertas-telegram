# Bot de Ofertas para Telegram

Automação em Python que coleta ofertas do Mercado Livre e as publica em um canal ou grupo do Telegram, com foto, preço e link, em intervalos fixos e sem repetir produtos.

## Como funciona

1. **`gerador.py`** recebe o link de um produto, acessa a página e extrai nome, preço atual, preço original e imagem. O resultado é gravado em `produtos.csv`.
2. **`main.py`** lê o `produtos.csv` e publica uma oferta por vez no Telegram a cada 30 minutos.
3. A posição da fila fica em `estado.json`, então o bot continua de onde parou se for reiniciado.

## Recursos

- Extração de dados com `requests` e BeautifulSoup, com alternativas caso a primeira fonte (JSON-LD da página) falhe.
- Fila persistente: nenhum produto é repetido até a lista terminar.
- Novas tentativas de envio e descarte de produtos com imagem inválida, sem travar a fila.
- Registro de eventos e erros em `bot_ofertas.log`.
- Credenciais fora do código, lidas de variáveis de ambiente.
- Mensagens em HTML com os textos escapados, para nomes com caracteres especiais não quebrarem o envio.

## Tecnologias

Python, requests, BeautifulSoup, python-telegram-bot, schedule e python-dotenv.

## Como usar

1. Clone o repositório e instale as dependências:

```bash
pip install -r requirements.txt
```

2. Crie um bot no Telegram com o [@BotFather](https://t.me/BotFather) e copie o token.
3. Copie `.env.example` para `.env` e preencha:

```
TELEGRAM_TOKEN=token_do_seu_bot
TELEGRAM_CHAT_ID=id_do_canal_ou_grupo
```

4. Adicione o bot como administrador do canal ou grupo.
5. Para testar o formato, copie `produtos_exemplo.csv` para `produtos.csv`. Para usar produtos reais, rode o coletor e cole os links:

```bash
python gerador.py
```

6. Inicie o bot:

```bash
python main.py
```

## Arquivos

| Arquivo | Função |
|---|---|
| `gerador.py` | Coleta os dados de um produto e grava em
