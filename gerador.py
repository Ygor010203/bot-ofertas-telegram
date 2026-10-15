"""
Coletor de ofertas do Mercado Livre.

Recebe o link de afiliado de um produto, extrai nome, preço e imagem da página
e grava o resultado em produtos.csv, que é lido pelo bot (main.py).

Uso:
    python gerador.py
"""

import csv
import json
import os

import requests
from bs4 import BeautifulSoup

ARQUIVO_CSV = "produtos.csv"
CABECALHO = ["nome", "preco", "preco_original", "descricao", "link", "imagem"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extrair_dados_mercado_livre(url):
    """Acessa a página do produto e devolve um dicionário com os dados, ou None se falhar."""
    print("\nBuscando dados do produto...")
    try:
        # Segue redirecionamentos (links curtos de afiliado) até a página real
        response = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=15)

        if response.status_code != 200:
            print(f"Erro ao acessar a página. Status: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        titulo = "Produto sem título"
        preco_atual = ""
        preco_original = ""
        imagem = ""

        # 1. Tenta primeiro os dados estruturados (JSON-LD) da página
        for json_ld in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    data = data[0]

                if "name" in data and titulo == "Produto sem título":
                    titulo = data["name"]
                if "image" in data and not imagem:
                    imagem = data["image"]
                    if isinstance(imagem, list):
                        imagem = imagem[0]
                if "offers" in data:
                    offers = data["offers"]
                    if isinstance(offers, list):
                        offers = offers[0]
                    if "price" in offers:
                        valor = str(offers["price"]).replace(".", ",")
                        if "," not in valor:
                            valor += ",00"
                        preco_atual = valor
            except Exception:
                pass

        # 2. Alternativa para o preço atual, caso o JSON falhe
        if not preco_atual or preco_atual == "00,00":
            for span in soup.find_all("span", class_=lambda x: x and "fraction" in x):
                if span.find_parent(["s", "del"]):
                    continue  # ignora o preço riscado
                fracao = span.get_text().strip()
                centavos_span = span.find_next_sibling(
                    "span", class_=lambda x: x and "cents" in x
                )
                centavos = centavos_span.get_text().strip() if centavos_span else "00"
                if fracao:
                    preco_atual = f"{fracao},{centavos}"
                    break

        if not preco_atual:
            preco_atual = "00,00"

        # 3. Alternativa para o título
        if not titulo or titulo == "Produto sem título":
            titulo_tag = soup.find("h1")
            if titulo_tag:
                titulo = titulo_tag.get_text().strip()
            else:
                meta_title = soup.find("meta", property="og:title")
                if meta_title:
                    titulo = meta_title.get("content", "")
        titulo = titulo.replace(",", "")

        # 4. Preço original (riscado)
        tag_original = soup.find("s") or soup.find(
            "span", class_=lambda x: x and "previous" in x
        )
        if tag_original:
            fracao_orig = tag_original.find("span", class_=lambda x: x and "fraction" in x)
            centavos_orig = tag_original.find("span", class_=lambda x: x and "cents" in x)
            if fracao_orig:
                f_o = fracao_orig.get_text().strip()
                c_o = centavos_orig.get_text().strip() if centavos_orig else "00"
                preco_original = f"{f_o},{c_o}"

        # 5. Alternativa para a imagem
        if not imagem:
            img_tag = soup.find("img", class_="ui-pdp-image")
            if img_tag and img_tag.has_attr("src"):
                imagem = img_tag["src"]
            else:
                meta_img = soup.find("meta", property="og:image")
                if meta_img:
                    imagem = meta_img.get("content", "")

        if preco_original == preco_atual:
            preco_original = ""

        if preco_original:
            descricao = f"De: R$ {preco_original} | Por apenas: R$ {preco_atual}"
        else:
            descricao = f"Oferta imperdível: R$ {preco_atual}"

        return {
            "nome": titulo,
            "preco": preco_atual,
            "preco_original": preco_original,
            "descricao": descricao,
            "link": url,  # mantém o link de afiliado original
            "imagem": imagem,
        }

    except Exception as e:
        print(f"Erro ao processar o link: {e}")
        return None


def salvar_no_csv(produto):
    """Acrescenta o produto ao CSV, criando o arquivo com cabeçalho se ele não existir."""
    arquivo_existe = os.path.exists(ARQUIVO_CSV)

    try:
        with open(ARQUIVO_CSV, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not arquivo_existe:
                writer.writerow(CABECALHO)
            writer.writerow([produto[coluna] for coluna in CABECALHO])
        print(f"Produto salvo com sucesso em '{ARQUIVO_CSV}'.")
    except PermissionError:
        print(f"Erro de permissão: feche o arquivo '{ARQUIVO_CSV}' e rode de novo.")


if __name__ == "__main__":
    print("=== GERADOR DE OFERTAS - MERCADO LIVRE ===")
    url_produto = input("Cole o link de afiliado aqui: ").strip()

    if url_produto:
        dados = extrair_dados_mercado_livre(url_produto)
        if dados:
            print("\n--- Dados encontrados ---")
            print(f"Nome: {dados['nome']}")
            print(f"Preço original: R$ {dados['preco_original'] or 'Não informado'}")
            print(f"Preço atual: R$ {dados['preco']}")
            print(f"Link salvo: {dados['link']}")
            print("-------------------------")
            salvar_no_csv(dados)
        else:
            print("Não foi possível extrair os dados.")
    else:
        print("Nenhum link fornecido. Encerrando.")