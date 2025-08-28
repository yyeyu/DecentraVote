from .default_handlers import router as default_router
from .creating_handlers import router as creating_router
from .info_handlers import router as info_router
from .vote_handlers import router as vote_router

routers = [
    vote_router,
    info_router,
    creating_router,
    default_router,
]