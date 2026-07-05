"""
Rotas para gerenciamento de imagens de produtos
Integração com Supabase Storage
As mutações (upload/delete) exigem admin; a leitura é pública.
"""
from flask import Blueprint
from app.controllers.images_controller import (
    upload_product_image,
    delete_product_image,
    list_product_images,
    get_image_info,
    upload_multiple_images
)
from app.services.jwt_service import admin_required

images_bp = Blueprint("images", __name__)

# Upload de imagem única — apenas admin
images_bp.route("/upload", methods=["POST"])(admin_required(upload_product_image))

# Upload de múltiplas imagens — apenas admin
images_bp.route("/upload-multiple", methods=["POST"])(admin_required(upload_multiple_images))

# Deletar imagem — apenas admin
images_bp.route("/delete", methods=["DELETE"])(admin_required(delete_product_image))

# Listar imagens de um produto (leitura pública)
images_bp.route("/product/<int:product_id>", methods=["GET"])(list_product_images)

# Informações sobre uma imagem (leitura pública)
images_bp.route("/info", methods=["POST"])(get_image_info)
