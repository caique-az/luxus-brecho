"""Pacote de controllers.

A factory real da aplicação vive em ``app.create_app`` (backend/app/__init__.py).
Este arquivo é apenas o marcador de pacote. Havia aqui uma segunda ``create_app``
obsoleta (DEBUG=True, banco fixo ``luxus_brecho``, ``app.mongo`` apontando para o
database e só 2 blueprints) — uma sombra perigosa da factory real, removida na
Fase 6. Não reintroduza uma factory aqui.
"""
