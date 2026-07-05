from flask import Blueprint
from app.controllers.categories_controller import (
    list_categories,
    get_category,
    create_category,
    update_category,
    delete_category,
    activate_category,
    get_categories_summary,
)
from app.services.jwt_service import admin_required

categories_bp = Blueprint("categories", __name__)

# Leitura pública
categories_bp.route("/", methods=["GET"])(list_categories)
categories_bp.route("/<int:id>", methods=["GET"])(get_category)
categories_bp.route("/summary", methods=["GET"])(get_categories_summary)

# Mutações — apenas admin
categories_bp.route("/", methods=["POST"])(admin_required(create_category))
categories_bp.route("/<int:id>", methods=["PUT"])(admin_required(update_category))
categories_bp.route("/<int:id>", methods=["DELETE"])(admin_required(delete_category))
categories_bp.route("/<int:id>/activate", methods=["PUT"])(admin_required(activate_category))
