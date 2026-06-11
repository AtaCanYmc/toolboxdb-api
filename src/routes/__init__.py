from .category_routes import category_router
from .component_routes import component_router
from .core_routes import core_router, custom_404_handler
from .invoinces_routes import invoinces_router
from .suggestion_routes import suggestion_router
from .auth_routes import auth_router


def add_routes(app):
    app.include_router(category_router)
    app.include_router(component_router)
    app.include_router(invoinces_router)
    app.include_router(core_router)
    app.include_router(suggestion_router)
    app.include_router(auth_router)
    app.add_exception_handler(404, custom_404_handler)


__all__ = ["add_routes"]
