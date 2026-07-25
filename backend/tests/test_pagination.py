"""
Paginação: contrato das rotas que aceitam ``page``/``page_size``.

Regressão de BE-08: as leituras inline de paginação faziam ``int(...)`` cru sobre
a query string, então um valor não numérico levantava ValueError e a rota
respondia 500. As rotas abaixo passaram a usar ``utils.pagination.parse_pagination``,
que cai no default quando o valor não é inteiro.
"""
import pytest


# (rota, precisa de auth, default esperado de page_size)
ROTAS_PAGINADAS = [
    ("/api/categories", None, 10),
    ("/api/products/category/camisas", None, 20),
]


@pytest.mark.parametrize("valor", ["abc", "", "1.5", "None", "-"])
def test_page_nao_numerico_nao_derruba_categorias(client, valor):
    """Valor inválido cai no default em vez de estourar 500."""
    r = client.get(f"/api/categories?page={valor}")
    assert r.status_code != 500, f"page={valor!r} causou 500: {r.data[:200]}"


@pytest.mark.parametrize("valor", ["abc", "", "1.5", "None", "-"])
def test_page_size_nao_numerico_nao_derruba_categorias(client, valor):
    r = client.get(f"/api/categories?page_size={valor}")
    assert r.status_code != 500, f"page_size={valor!r} causou 500: {r.data[:200]}"


def test_page_nao_numerico_nao_derruba_pedidos(client, user_headers):
    r = client.get("/api/orders/user/1?page=abc", headers=user_headers)
    assert r.status_code != 500, f"500: {r.data[:200]}"


def test_page_nao_numerico_nao_derruba_produtos_por_categoria(client):
    """Esta rota não passa pelo schema Marshmallow da listagem principal."""
    r = client.get("/api/products/category/camisas?page=abc")
    assert r.status_code != 500, f"500: {r.data[:200]}"


def test_page_invalida_usa_default_em_categorias(client):
    """Além de não quebrar, o default declarado (10) é aplicado."""
    r = client.get("/api/categories?page=abc&page_size=abc")
    assert r.status_code == 200
    pag = r.get_json()["pagination"]
    assert pag["page"] == 1
    assert pag["page_size"] == 10


def test_page_size_acima_do_maximo_e_limitado(client):
    """page_size é limitado a 100 — um valor gigante varreria a coleção."""
    r = client.get("/api/categories?page_size=99999")
    assert r.status_code == 200
    assert r.get_json()["pagination"]["page_size"] == 100


def test_page_zero_ou_negativa_vira_um(client):
    for valor in ("0", "-5"):
        r = client.get(f"/api/categories?page={valor}")
        assert r.status_code == 200
        assert r.get_json()["pagination"]["page"] == 1
