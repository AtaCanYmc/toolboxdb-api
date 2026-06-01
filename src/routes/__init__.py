from .category_routes import category_router
from .component_routes import component_router
from .invoinces_routes import invoinces_router


def add_routes(app):
    app.include_router(category_router)
    app.include_router(component_router)
    app.include_router(invoinces_router)


__all__ = [
    "add_routes",
    "category_router",
    "component_router",
    "invoinces_router"
]