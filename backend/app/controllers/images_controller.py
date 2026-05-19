"""
Controller para gerenciamento de imagens de produtos
Integra com Supabase Storage
"""
from flask import request, jsonify, current_app
from werkzeug.datastructures import FileStorage
from app.services.supabase_storage import storage_service
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
            return jsonify({"error": "Nenhum arquivo foi enviado"}), 400
        
        file = request.files['image']
        
        # Verifica se arquivo foi selecionado
        if file.filename == '':
            return jsonify({"error": "Nenhum arquivo foi selecionado"}), 400
        
        # Obtém product_id se fornecido
        product_id = request.form.get('product_id')
        if product_id:
            try:
                product_id = int(product_id)
            except ValueError:
                return jsonify({"error": "product_id deve ser um número"}), 400
        
        # Faz upload
        success, result = storage_service.upload_image(file, product_id)
        
        if success:
            return jsonify({
                "message": "Imagem enviada com sucesso",
                "image_url": result,
                "product_id": product_id
            }), 201
        else:
            return jsonify({"error": result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro no upload de imagem: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

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
            return jsonify({"error": "image_url é obrigatório"}), 400
        
        image_url = data['image_url']
        
        # Deleta imagem
        success, message = storage_service.delete_image(image_url)
        
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        current_app.logger.error(f"Erro ao deletar imagem: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

def list_product_images(product_id: int):
    """
    Lista todas as imagens de um produto
    GET /api/images/product/<product_id>
    """
    try:
        success, images = storage_service.list_product_images(product_id)
        
        if success:
            return jsonify({
                "product_id": product_id,
                "images": images,
                "total": len(images)
            }), 200
        else:
            return jsonify({
                "product_id": product_id,
                "images": [],
                "total": 0,
                "message": "Nenhuma imagem encontrada ou erro ao buscar"
            }), 200
            
    except Exception as e:
        current_app.logger.error(f"Erro ao listar imagens: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

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
            return jsonify({"error": "image_url é obrigatório"}), 400
        
        image_url = data['image_url']
        info = storage_service.get_image_info(image_url)
        
        if "error" in info:
            return jsonify({"error": info["error"]}), 400
        
        return jsonify(info), 200
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter info da imagem: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

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
            return jsonify({"error": "product_id é obrigatório"}), 400
        
        try:
            product_id = int(product_id)
        except ValueError:
            return jsonify({"error": "product_id deve ser um número"}), 400
        
        # Obtém arquivos enviados
        uploaded_files = request.files.getlist('images')
        
        if not uploaded_files:
            return jsonify({"error": "Nenhum arquivo foi enviado"}), 400
        
        results = []
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
            "images": successful_uploads
        }
        
        if errors:
            response_data["errors"] = errors
        
        status_code = 201 if successful_uploads else 400
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        current_app.logger.error(f"Erro no upload múltiplo: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500