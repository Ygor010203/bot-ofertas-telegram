"""
Bot de ofertas para Telegram.

Lê o produtos.csv (gerado pelo gerador.py) e publica uma oferta por vez, com foto,
preço e link, em um intervalo fixo e sem repetir. A posição da fila é guardada em
estado.json, então o bot continua de onde parou se for reiniciado.

Configuração: copie .env.example para .env e preencha TELEGRAM_TOKEN e TELEGRAM_CHAT_ID.

Uso:
    python main.py
"""

import asyncio
import csv
import html
import io
import json
import logging
import os
import time

import requests
import schedule
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

# ======= CONFIGURAÇÕES =======
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ARQUIVO_PRODUTOS = "produtos.csv"
ARQUIVO_ESTADO = "estado.json"
INTERVALO_MINUTOS = 30
TENTATIVAS_ENVIO = 3

if not TOKEN or not CHAT_ID:
    raise RuntimeError(
        "Defina TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no arquivo .env (veja .env.example)."
    )

logging.basicConfig(
    filename="bot_ofertas.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

bot = Bot(token=TOKEN)


def preco_para_float(valor):
    """Converte um preço no formato brasileiro ('1.164,74') para float. Retorna 0.0 se inválido."""
    try:
        limpo = valor.replace("R$", "").strip()
        limpo = limpo.replace(".", "").replace(",", ".")
        return float(limpo)
    except (ValueError, AttributeError):
        return 0.0


def carregar_produtos():
    """Lê o CSV (com cabeçalho) e devolve a lista de produtos válidos."""
    produtos = []
    if not os.path.exists(ARQUIVO_PRODUTOS):
        logging.warning("Arquivo %s não encontrado.", ARQUIVO_PRODUTOS)
        return produtos

    with open(ARQUIVO_PRODUTOS, newline="", encoding="utf-8-sig") as f:
        for linha in csv.DictReader(f):
            nome = (linha.get("nome") or "").strip()
            link = (linha.get("link") or "").strip()
            imagem = (linha.get("imagem") or "").strip()
            if not nome or not link:
                continue  # ignora linhas incompletas

            produtos.append(
                {
                    "nome": nome,
                    "preco_atual": (linha.get("preco") or "00,00").strip(),
                    "preco_antigo": (linha.get("preco_original") or "").strip(),
                    "link": link,
                    "imagem": imagem,
                }
            )
    return produtos


def carregar_posicao():
    """Devolve o índice do próximo produto a postar."""
    if os.path.exists(ARQUIVO_ESTADO):
        with open(ARQUIVO_ESTADO, "r", encoding="utf-8") as f:
            try:
                return json.load(f).get("proximo_indice", 0)
            except (json.JSONDecodeError, AttributeError):
                return 0
    return 0


def salvar_posicao(indice):
    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump({"proximo_indice": indice}, f)


def montar_mensagem(produto):
    """Monta a legenda em HTML, mostrando 'De / Por' só se o preço antigo for maior que o atual."""
    nome = html.escape(produto.get("nome", "Oferta imperdível"))
    preco_atual = produto.get("preco_atual", "00,00")
    preco_antigo = produto.get("preco_antigo", "")
    link = html.escape(produto.get("link", ""))

    texto = f"🔥 <b>{nome}</b>\n\n"

    if preco_para_float(preco_antigo) > preco_para_float(preco_atual):
        texto += f"De: R$ {html.escape(preco_antigo)} por:\n"
        texto += f"<b>R$ {html.escape(preco_atual)}</b>\n\n"
    else:
        texto += f"<b>Por apenas: R$ {html.escape(preco_atual)}</b>\n\n"

    texto += f"Garanta o seu aqui:\n{link}"
    return texto


def baixar_imagem(url):
    """Baixa a imagem do produto. Devolve um BytesIO ou None se falhar."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.mercadolivre.com.br/",
    }
    try:
        resposta = requests.get(url, headers=headers, timeout=15)
        resposta.raise_for_status()
        return io.BytesIO(resposta.content)
    except Exception as e:
        logging.warning("Não foi possível baixar a imagem (%s): %s", url, e)
        return None


async def postar_uma_oferta():
    produtos = carregar_produtos()
    if not produtos:
        logging.warning("Nenhum produto encontrado no CSV.")
        print("Nenhum produto encontrado no CSV.")
        return

    indice = carregar_posicao()
    if indice >= len(produtos):
        indice = 0  # volta ao início da fila

    produto = produtos[indice]
    mensagem = montar_mensagem(produto)
    imagem_url = produto.get("imagem", "")

    sucesso = False
    tentativas = TENTATIVAS_ENVIO

    while tentativas > 0 and not sucesso and imagem_url:
        imagem_bytes = baixar_imagem(imagem_url)
        if imagem_bytes:
            try:
                await bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=imagem_bytes,
                    caption=mensagem,
                    parse_mode="HTML",
                )
                sucesso = True
            except Exception as e:
                logging.error(
                    "Falha ao enviar foto (tentativas restantes %d): %s", tentativas - 1, e
                )
                await asyncio.sleep(2)
        tentativas -= 1

    if not sucesso:
        logging.error("Produto '%s' ignorado nesta rodada.", produto.get("nome"))
        print(f"Falha ao enviar '{produto.get('nome')}'. Pulando para o próximo.")
        salvar_posicao(indice + 1)
        return

    logging.info("Postado (%d/%d): %s", indice + 1, len(produtos), produto["nome"])
    print(f"Postado com sucesso ({indice + 1}/{len(produtos)}): {produto['nome']}")
    salvar_posicao(indice + 1)


def job():
    try:
        asyncio.run(postar_uma_oferta())
    except Exception as e:
        logging.error("Erro inesperado na rodada de postagem: %s", e)
        print(f"Erro no envio: {e}")


if __name__ == "__main__":
    print(f"Bot iniciado. Postando a cada {INTERVALO_MINUTOS} minutos, em ordem, sem repetir.")
    logging.info("Bot iniciado.")

    job()
    schedule.every(INTERVALO_MINUTOS).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)