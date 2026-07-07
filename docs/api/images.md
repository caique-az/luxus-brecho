# Imagens — `/api/images`

> Fonte: `backend/app/routes/images_routes.py` · `backend/app/controllers/images_controller.py` · `backend/app/services/supabase_storage.py`
> Contrato geral: [../api-reference.md](../api-reference.md) · Divergências: [../alinhamento-e-debitos.md](../alinhamento-e-debitos.md)

Integração com **Supabase Storage** (bucket `SUPABASE_BUCKET`, default `product-images`). O serviço redimensiona imagens (máx 1200×1200, JPEG qualidade 85 via Pillow), nomeia com UUID sob `product_<id>/` e retorna **signed URL de 1 ano** (fallback para URL pública).

**Atenção ao formato de erro:** este é um dos módulos que respondem `{"error": ...}` em vez de `{"message": ...}` ([BE-01](../alinhamento-e-debitos.md#be-01)).

## Resumo

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/api/images/upload` | `admin_required` | Upload de imagem única |
| POST | `/api/images/upload-multiple` | `admin_required` | Upload de várias imagens |
| DELETE | `/api/images/delete` | `admin_required` | Remove imagem por URL |
| GET | `/api/images/product/<int:product_id>` | pública | Lista imagens de um produto |
| POST | `/api/images/info` | pública | Metadados de uma imagem por URL |

## `POST /api/images/upload` (multipart/form-data)

Campos: arquivo `image` (obrigatório) e `product_id` (opcional, precisa ser numérico). Erros → 400 `{"error": ...}`. Sucesso 201:

```json
{ "message": "Imagem enviada com sucesso", "image_url": "https://...", "product_id": 12 }
```

## `POST /api/images/upload-multiple` (multipart/form-data)

Campos: arquivos `images` (lista) e `product_id` (**obrigatório**). Processa cada arquivo individualmente; falhas parciais entram em `errors`. Status 201 se ao menos um upload funcionou, 400 se nenhum:

```json
{
  "product_id": 12,
  "successful_uploads": 2,
  "total_files": 3,
  "images": [ { "filename": "a.jpg", "image_url": "https://..." } ],
  "errors": [ "Arquivo 'b.bmp': ..." ]
}
```

## `DELETE /api/images/delete`

Body JSON `{"image_url": "https://..."}`. Sucesso 200 `{"message": ...}`; falha do storage → 400 `{"error": ...}`.

## `GET /api/images/product/<product_id>`

Lista os arquivos do prefixo `product_<id>/` no bucket. **Sempre responde 200**, mesmo em erro do storage (com `images: []` e uma `message`):

```json
{ "product_id": 12, "images": [ ... ], "total": 2 }
```

## `POST /api/images/info`

Body `{"image_url": "https://..."}` → metadados retornados pelo storage; erro → 400 `{"error": ...}`.

## Notas de implementação

- `SupabaseStorageService` inicializa de forma tolerante: sem `SUPABASE_URL`/`SUPABASE_KEY` o app sobe, e os uploads falham em runtime com mensagem de indisponibilidade (`is_available()`/`get_connection_status()`).
- Em erro de RLS, o serviço tenta re-login com `SUPABASE_SERVICE_ROLE_EMAIL`/`SUPABASE_SERVICE_ROLE_KEY` (vars ausentes do `.env.example` — [BE-03](../alinhamento-e-debitos.md#be-03)).
- O fluxo "criar produto já com imagem" não passa por aqui — é `POST /api/products/with-image` ([products.md](./products.md)).
