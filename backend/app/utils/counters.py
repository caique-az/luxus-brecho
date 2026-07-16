"""
Geração de IDs sequenciais via coleção ``counters``.

IDs de entidade são inteiros sequenciais (não ``ObjectId``), gerados por um
contador atômico por nome. O padrão ``find_one_and_update`` com ``$inc`` estava
duplicado em quatro models (categories, products, orders, users); esta função
concentra a lógica.
"""
from pymongo.collection import ReturnDocument

COUNTERS_COLLECTION = "counters"


def next_sequence(db, name: str) -> int:
    """Retorna o próximo número sequencial para o contador ``name`` (faz upsert)."""
    doc = db[COUNTERS_COLLECTION].find_one_and_update(
        {"name": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"]) if doc and "seq" in doc else 1
