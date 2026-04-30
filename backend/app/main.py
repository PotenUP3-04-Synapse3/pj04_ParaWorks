from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title='ParaWorks Harness')

    @app.get('/health')
    def health() -> dict[str, str]:
        return {'status': 'ok', 'service': 'paraworks'}

    return app


app = create_app()
