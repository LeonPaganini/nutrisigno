# modules/app_bootstrap.py
from __future__ import annotations

import threading
from typing import Optional
from .repo import init_models

# Evita chamar create_all muitas vezes em ambientes com múltiplas importações
__BOOTSTRAP_LOCK = threading.Lock()
__BOOTSTRAPPED = False

def ensure_bootstrap() -> None:
    global __BOOTSTRAPPED
    if __BOOTSTRAPPED:
        return
    with __BOOTSTRAP_LOCK:
        if __BOOTSTRAPPED:
            return
        init_models()
        __BOOTSTRAPPED = True