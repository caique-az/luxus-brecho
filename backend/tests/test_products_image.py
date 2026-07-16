"""
Criação de produto com imagem (POST /api/products/with-image).

Regressão de BE-09: o upload usava um timestamp como id temporário e, como ele
nunca coincidia com o id sequencial do produto, a rota sempre pagava dois
uploads e um delete no Supabase. O id passou a ser reservado antes do upload,
que agora acontece uma vez só, já com o nome final.
"""
import io
from unittest.mock import patch

import pytest


def _imagem(nome="camisa.jpg"):
    return (io.BytesIO(b"\xff\xd8\xff\xe0conteudo-de-imagem-falso"), nome)


def _form(**overrides):
    dados = {
        "titulo": "Camisa de linho",
        "descricao": "Peça única em ótimo estado",
        "preco": "89.90",
        "categoria": "Roupas",
        "image": _imagem(),
    }
    dados.update(overrides)
    return dados


@pytest.fixture(autouse=True)
def _seed(mock_db, sample_category):
    """A validação de produto consulta as categorias reais do banco."""
    mock_db["counters"].insert_one({"name": "products", "seq": 0})
    mock_db["categories"].insert_one(sample_category)


@pytest.fixture
def storage():
    """Mocka o storage para contar uploads sem tocar no Supabase."""
    with patch("app.routes.products_routes.storage_service") as mock:
        mock.upload_image.return_value = (True, "https://storage.test/produtos/1.jpg")
        mock.delete_image.return_value = True
        yield mock


def test_cria_produto_com_um_unico_upload(client, admin_headers, storage):
    r = client.post(
        "/api/products/with-image",
        data=_form(),
        headers=admin_headers,
        content_type="multipart/form-data",
    )

    assert r.status_code == 201, r.data[:300]
    assert storage.upload_image.call_count == 1, (
        f"esperado 1 upload, houve {storage.upload_image.call_count}"
    )
    storage.delete_image.assert_not_called()


def test_upload_usa_o_id_real_do_produto(client, admin_headers, storage):
    """O arquivo sobe já com o id definitivo — não com um timestamp."""
    r = client.post(
        "/api/products/with-image",
        data=_form(),
        headers=admin_headers,
        content_type="multipart/form-data",
    )

    assert r.status_code == 201
    _, id_usado_no_upload = storage.upload_image.call_args[0]
    id_do_produto = r.get_json()["product"]["id"]
    assert id_usado_no_upload == id_do_produto


def test_imagem_e_removida_quando_a_validacao_falha(client, admin_headers, storage):
    """Categoria inexistente passa na checagem do form e só cai no
    prepare_new_product — quando a imagem já subiu. Ela precisa sair."""
    r = client.post(
        "/api/products/with-image",
        data=_form(categoria="Categoria Que Nao Existe"),
        headers=admin_headers,
        content_type="multipart/form-data",
    )

    assert r.status_code == 400
    storage.upload_image.assert_called_once()
    storage.delete_image.assert_called_once_with("https://storage.test/produtos/1.jpg")


def test_campo_obrigatorio_ausente_nem_chega_a_subir_imagem(client, admin_headers, storage):
    """Título vazio é barrado antes do upload — nada sobe, nada a remover."""
    r = client.post(
        "/api/products/with-image",
        data=_form(titulo=""),
        headers=admin_headers,
        content_type="multipart/form-data",
    )

    assert r.status_code == 400
    storage.upload_image.assert_not_called()
    storage.delete_image.assert_not_called()


def test_falha_de_upload_nao_cria_produto(client, admin_headers, storage):
    storage.upload_image.return_value = (False, "bucket indisponível")

    r = client.post(
        "/api/products/with-image",
        data=_form(),
        headers=admin_headers,
        content_type="multipart/form-data",
    )

    assert r.status_code == 400
    assert "upload" in r.get_json()["message"].lower()
