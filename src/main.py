from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Knowledge Intelligence Platform")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
