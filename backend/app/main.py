from fastapi import FastAPI

from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title='ParaWorks Harness')

    @app.get('/health')
    def health() -> dict[str, bool | str]:
        return {'status': 'ok', 'service': 'paraworks', 'demo_mode': settings.paraworks_demo_mode}

    return app


app = create_app()
