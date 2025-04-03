from .default_handlers import router as default_router
from .creating_handlers import router as creating_router

routers = [
    creating_router,
    default_router,
]