"""analisis_validacion.py — Calcula resultados del cuestionario de validación."""
import csv
import sys
from pathlib import Path


def main(csv_path: str) -> None:
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    if not rows:
        print("Sin datos.")
        return

    task_cols = [f"t{i}" for i in range(1, 11)]
    q_cols = [f"q{i}" for i in range(1, 7)]

    total = len(rows)
    task_success = {t: sum(1 for r in rows if r.get(t, "").strip().lower() == "si") for t in task_cols}
    overall_task_rate = sum(task_success.values()) / (total * len(task_cols)) * 100
    q_means = {q: sum(int(r[q]) for r in rows if r.get(q, "").strip().isdigit()) / total for q in q_cols}
    overall_q = sum(q_means.values()) / len(q_means)

    print(f"=== Resultados de validación ({total} participante(s)) ===")
    print(f"\nTareas completadas:")
    for t, n in task_success.items():
        print(f"  {t}: {n}/{total} ({n/total*100:.0f}%)")
    print(f"  → Tasa global: {overall_task_rate:.1f}% (umbral: 80%)")
    print(f"  → {'✅ CUMPLE' if overall_task_rate >= 80 else '❌ NO CUMPLE'}")

    print(f"\nCuestionario (escala 1–5):")
    for q, m in q_means.items():
        print(f"  {q}: {m:.2f}")
    print(f"  → Promedio global: {overall_q:.2f} (umbral: 3.5)")
    print(f"  → {'✅ CUMPLE' if overall_q >= 3.5 else '❌ NO CUMPLE'}")

    comentarios = [r.get("comentario", "") for r in rows if r.get("comentario", "").strip()]
    if comentarios:
        print(f"\nComentarios:")
        for c in comentarios:
            print(f"  - {c}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analisis_validacion.py <ruta_csv>")
        sys.exit(1)
    main(sys.argv[1])
