"""ParaWorks 진입점.

백엔드:   uvicorn backend.main:app --reload --port 8000
프론트엔드: cd frontend && npm run dev
"""
import subprocess
import sys


def run_backend():
    subprocess.run(
        [sys.executable, '-m', 'uvicorn', 'backend.main:app', '--reload', '--port', '8000'],
        check=True,
    )


def run_frontend():
    subprocess.run(
        ['npm', 'run', 'dev'],
        cwd='frontend',
        check=True,
    )


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'backend'
    if mode == 'frontend':
        run_frontend()
    else:
        run_backend()
