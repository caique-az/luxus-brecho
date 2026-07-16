# Health — `/api/health`

> Fonte: `backend/app/routes/health_routes.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

Verificação de saúde da API. Não toca o banco (para saber se o Mongo está conectado, use o campo `database` do `GET /` na raiz).

## Resumo

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/api/health` | pública (`@cross_origin`) | Status, memória, ambiente e versão |
| OPTIONS | `/api/health` | pública | Preflight CORS — responde `{"message": "OK"}` |

## `GET /api/health`

Único endpoint com a forma **aninhada** `{success, data}` (os demais usam o envelope plano — ver [Formatos de resposta](../api-reference.md#formatos-de-resposta)):

```json
{
  "success": true,
  "data": {
    "status": "OK",
    "timestamp": "2026-07-07T12:00:00",
    "uptime_seconds": 1751885000.0,
    "memory_usage": { "total": 0, "available": 0, "percent": 0.0 },
    "environment": "production",
    "debug": false,
    "version": "1.0.0"
  }
}
```

- Métricas via `psutil` (`uptime_seconds` é na verdade o `boot_time` do sistema); `environment` vem de `FLASK_ENV`, `debug` de `FLASK_DEBUG`.
- Falha interna → 500 `{"success": false, "status": "ERROR", "message": "Erro no health check", "error": "...", "timestamp": "..."}`.

## Notas de implementação

- A lógica vive **inline na rota** (`health_check` em `health_routes.py`); o `health_controller.check_health` existente é **código morto** ([BE-02](../alinhamento-e-debitos.md#be-02)).
- É a única rota do backend que não usa `@require_db` — funciona com o banco fora do ar.
