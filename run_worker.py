"""
Executa o worker/agendador do PromoBox como processo independente do painel.

Uso:
    python run_worker.py

O worker roda em loop, executando um ciclo completo (buscar, validar, filtrar,
gerar texto, enfileirar, publicar) a cada CYCLE_INTERVAL_MINUTES minutos,
continuando a funcionar mesmo com o painel administrativo fechado.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import os
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database.db import init_db
from app.scheduler.worker import run_cycle
from app.utils.config import settings
from app.utils.logger import log_event

CYCLE_INTERVAL_MINUTES = int(os.environ.get("CYCLE_INTERVAL_MINUTES", "5"))


def job():
    try:
        result = run_cycle()
        print(f"[worker] ciclo concluído: {result}")
    except Exception as exc:
        print(f"[worker] ERRO no ciclo: {exc}")
        log_event("erro", f"Erro não tratado no ciclo do worker: {exc}", level="ERROR")


if __name__ == "__main__":
    init_db()
    log_event("sistema", f"Worker iniciado. Intervalo: {CYCLE_INTERVAL_MINUTES} min. "
                          f"Modo DEMO: {settings.demo_mode}. Fuso: {settings.timezone}.")
    scheduler = BlockingScheduler(timezone=settings.timezone)
    scheduler.add_job(job, IntervalTrigger(minutes=CYCLE_INTERVAL_MINUTES), next_run_time=None)
    print(f"PromoBox worker rodando a cada {CYCLE_INTERVAL_MINUTES} min (Ctrl+C para parar)...")
    job()  # roda um ciclo imediatamente ao iniciar
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Worker encerrado.")
