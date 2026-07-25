"""
Controller para gerenciamento de imagens de produtos
Integra com Supabase Storage
"""
from flask import request, current_app
from werkzeug.datastructures import FileStorage
from app.services.supabase_storage import storage_service
from app.utils.responses import ok, err
from typing import Tuple, Any

def upload_product_image():
    """
    Upload de imagem para um produto
    POST /api/images/upload

    Form Data:
    - image: arquivo de imagem
    - product_id: ID do produto (opcional)
    """
    try:
        # Verifica se há arquivo na requisição
        if 'image' not in request.files:
            return err("Nenhum arquivo foi enviado")

        file = request.files['image']

        # Verifica se arquivo foi selecionado
        if file.filename == '':
            return err("Nenhum arquivo foi selecionado")

        # Obtém product_id se fornecido
        product_id = request.form.get('product_id')
        if product_id:
            try:
                product_id = int(product_id)
            except ValueError:
                return err("product_id deve ser um número")

        # Faz upload
        success, result = storage_service.upload_image(file, product_id)

        if success:
            return ok(
                message="Imagem enviada com sucesso",
                status=201,
                image_url=result,
                product_id=product_id,
            )
        else:
            return err(result)

    except Exception as e:
        current_app.logger.error(f"Erro no upload de imagem: {e}")
        return err("Erro interno no servidor", 500)

def delete_product_image():
    """
    Deleta uma imagem de produto
    DELETE /api/images/delete

    JSON Body:
    - image_url: URL da imagem a ser deletada
    """
    try:
        data = request.get_json()

        if not data or 'image_url' not in data:
            return err("image_url é obrigatório")

        image_url = data['image_url']

        # Deleta imagem
        success, message = storage_service.delete_image(image_url)

        if success:
            return ok(message=message)
        else:
            return err(message)

    except Exception as e:
        current_app.logger.error(f"Erro ao deletar imagem: {e}")
        return err("Erro interno no servidor", 500)

def list_product_images(product_id: int):
    """
    Lista todas as imagens de um produto
    GET /api/images/product/<product_id>
    """
    try:
        success, images = storage_service.list_product_images(product_id)

        if success:
            return ok({
                "product_id": product_id,
                "images": images,
                "total": len(images),
            })
        else:
            return ok(
                {
                    "product_id": product_id,
                    "images": [],
                    "total": 0,
                },
                message="Nenhuma imagem encontrada ou erro ao buscar",
            )

    except Exception as e:
        current_app.logger.error(f"Erro ao listar imagens: {e}")
        return err("Erro interno no servidor", 500)

def get_image_info():
    """
    Obtém informações sobre uma imagem
    POST /api/images/info

    JSON Body:
    - image_url: URL da imagem
    """
    try:
        data = request.get_json()

        if not data or 'image_url' not in data:
            return err("image_url é obrigatório")

        image_url = data['image_url']
        info = storage_service.get_image_info(image_url)

        if "error" in info:
            return err(info["error"])

        return ok(info)

    except Exception as e:
        current_app.logger.error(f"Erro ao obter info da imagem: {e}")
        return err("Erro interno no servidor", 500)

def upload_multiple_images():
    """
    Upload de múltiplas imagens para um produto
    POST /api/images/upload-multiple

    Form Data:
    - images[]: múltiplos arquivos de imagem
    - product_id: ID do produto (obrigatório)
    """
    try:
        # Verifica product_id
        product_id = request.form.get('product_id')
        if not product_id:
            return err("product_id é obrigatório")

        try:
            product_id = int(product_id)
        except ValueError:
            return err("product_id deve ser um número")

        # Obtém arquivos enviados
        uploaded_files = request.files.getlist('images')

        if not uploaded_files:
            return err("Nenhum arquivo foi enviado")

        successful_uploads = []
        errors = []

        # Processa cada arquivo
        for idx, file in enumerate(uploaded_files):
            if file.filename == '':
                errors.append(f"Arquivo {idx + 1}: Nenhum arquivo selecionado")
                continue

            success, result = storage_service.upload_image(file, product_id)

            if success:
                successful_uploads.append({
                    "filename": file.filename,
                    "image_url": result
                })
            else:
                errors.append(f"Arquivo '{file.filename}': {result}")

        # Prepara resposta
        response_data = {
            "product_id": product_id,
            "successful_uploads": len(successful_uploads),
            "total_files": len(uploaded_files),
            "images": successful_uploads,
        }

        if successful_uploads:
            if errors:
                # `errors` (dict) fica reservado a erros de validação; aqui é uma
                # lista de falhas por arquivo, então usa a mesma chave do ramo de
                # falha total (`upload_errors`).
                response_data["upload_errors"] = errors
            return ok(response_data, status=201)

        return err(
            "Nenhuma imagem foi enviada com sucesso",
            400,
            product_id=product_id,
            total_files=len(uploaded_files),
            upload_errors=errors,
        )

    except Exception as e:
        current_app.logger.error(f"Erro no upload múltiplo: {e}")
        return err("Erro interno no servidor", 500)
