from flask import Blueprint

from ..services.jwt_service import admin_required
from ..controllers.products_controller import (
    list_products,
    get_product,
    create_product,
    update_product,
    delete_product,
    create_product_with_image,
    update_product_image,
    get_products_by_category,
)

products_bp = Blueprint('products', __name__)

products_bp.route('/', methods=['GET'])(list_products)
products_bp.route('/<int:id>', methods=['GET'])(get_product)

products_bp.route('/', methods=['POST'])(admin_required(create_product))
products_bp.route('/<int:id>', methods=['PUT'])(admin_required(update_product))
products_bp.route('/<int:id>', methods=['DELETE'])(admin_required(delete_product))
products_bp.route('/with-image', methods=['POST'])(admin_required(create_product_with_image))
products_bp.route('/<int:id>/image', methods=['PUT'])(admin_required(update_product_image))

products_bp.route('/category/<string:categoria>', methods=['GET'])(get_products_by_category)
