from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.agent import router as agent_router
from src.api.routes.market import router as market_router
from src.api.routes.rag import router as rag_router
from src.api.routes.supplier import router as supplier_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Supply Chain Agent API",
        description="Interface for accessing Dynamic Knowledge Graph",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(market_router)
    app.include_router(supplier_router)
    app.include_router(rag_router)
    app.include_router(agent_router)

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
