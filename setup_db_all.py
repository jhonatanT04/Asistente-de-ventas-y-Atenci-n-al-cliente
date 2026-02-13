#!/usr/bin/env python3
"""
Script unificado para ejecutar las migraciones e inicializaciones de la DB.

Ejecuta en orden:
  1. `init.db.py`        -> crea tablas base e inserta usuarios
  2. `migrate_db_add_barcode_discounts.py` -> agrega barcodes y descuentos
  3. `migrate_db_add_chat_history.py`      -> crea tabla `chat_history`
  4. `init_db_2.py`      -> opcional: carga catálogo completo (si existe)
  5. `init_test_db.py`   -> opcional: prepara DB de tests

Uso:
  python setup_db_all.py --all
  python setup_db_all.py --steps init_db,migrate_barcodes,chat_history

Este script ejecuta los otros scripts como procesos separados usando el mismo
intérprete de Python (`sys.executable`).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPTS = [
    ("init_db", "init.db.py", True),
    ("migrate_barcodes", "migrate_db_add_barcode_discounts.py", True),
    ("chat_history", "migrate_db_add_chat_history.py", True),
    ("init_catalog", "init_db_2.py", False),
    ("init_test_db", "init_test_db.py", False),
]


def run_script(path: str) -> None:
    p = Path(path)
    if not p.exists():
        print(f"⚠️  Script no encontrado: {path} — se omite")
        return

    print(f"▶ Ejecutando: {path}")
    try:
        subprocess.run([sys.executable, str(p)], check=True)
        print(f"✔ {path} completado\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ejecutando {path}: exit={e.returncode}")
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner unificado de migraciones e init DB")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ejecutar todos los pasos marcados como recomendados (default si no se pasa --steps)",
    )
    parser.add_argument(
        "--steps",
        type=str,
        help=(
            "Lista separada por comas de pasos a ejecutar. Opciones: "
            + ",".join([s[0] for s in SCRIPTS])
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.steps:
        requested = {s.strip() for s in args.steps.split(",") if s.strip()}
        to_run = [s for s in SCRIPTS if s[0] in requested]
        if not to_run:
            print("No se reconocieron pasos solicitados. Nada que hacer.")
            return
    else:
        # Si se pasa --all o no se especifica steps, ejecutar los recomendados
        if args.all or not args.steps:
            to_run = [s for s in SCRIPTS if s[2]]
        else:
            to_run = []

    print("=== INICIANDO SETUP DE BASE DE DATOS ===")
    for name, script, _ in to_run:
        run_script(script)

    print("=== SETUP COMPLETADO ===")


if __name__ == "__main__":
    main()
