"""Cliente Python: consulta las tareas con requests.

Uso:  python clientes/cliente.py [URL_BASE]
Ejemplo: python clientes/cliente.py https://mi-app.onrender.com
"""
import sys

import requests

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

respuesta = requests.get(f"{base}/api/tasks/", timeout=15)
print("Código HTTP:", respuesta.status_code)
print("Content-Type:", respuesta.headers.get("Content-Type"))
for tarea in respuesta.json():
    estado = "x" if tarea["completed"] else " "
    print(f"[{estado}] {tarea['id']}: {tarea['title']}")
