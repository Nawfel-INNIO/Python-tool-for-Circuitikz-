import json
from pathlib import Path

from models import Circuit, Component, Busbar, COMPONENTS


def generate_latex(circuit: Circuit) -> str:
    # Collect unique hex colors and create LaTeX color definitions
    colors_used: dict[str, str] = {}  # hex -> name
    for comp in circuit.components:
        if comp.color and comp.color not in colors_used:
            name = f"usercolor{len(colors_used) + 1}"
            colors_used[comp.color] = name

    lines = []
    for hex_color, name in colors_used.items():
        raw = hex_color.lstrip("#")
        lines.append(f"  \\definecolor{{{name}}}{{HTML}}{{{raw.upper()}}}")
    lines.append(r"\begin{circuitikz}")

    for bb in circuit.busbars:
        lines.append(
            f"  \\draw[line width=3pt] ({bb.x_start},{-bb.y}) -- ({bb.x_end},{-bb.y});"
        )
        if bb.label:
            lines.append(f"  \\node[above] at ({bb.x_start},{-bb.y}) {{{bb.label}}};")
        taps = set()
        for comp in circuit.components:
            if comp.y1 == bb.y and bb.x_start <= comp.x1 <= bb.x_end:
                taps.add(comp.x1)
            if comp.y2 == bb.y and bb.x_start <= comp.x2 <= bb.x_end:
                taps.add(comp.x2)
        for tx in sorted(taps):
            lines.append(f"  \\draw ({tx},{-bb.y}) -- ({tx},{-bb.y - 0.3});")

    for comp in circuit.components:
        info = COMPONENTS[comp.kind]
        a = f"({comp.x1},{-comp.y1})"
        b = f"({comp.x2},{-comp.y2})"
        label = f", l=${comp.label}$" if comp.label else ""
        value = f", v=${comp.value}$" if comp.value else ""
        current = f", i=${comp.current}$" if comp.current else ""
        annotation = f", a=${comp.annotation}$" if comp.annotation else ""
        color_opt = f", color={{{colors_used[comp.color]}}}" if comp.color else ""

        if info.get("node_style"):
            style = info["node_style"]
            lbl = f"${comp.label}$" if comp.label else ""
            draw_opts = f"[{colors_used[comp.color]}]" if comp.color else ""
            lines.append(f"  \\draw{draw_opts} {a} node[{style}] {{{lbl}}};")
        else:
            kind = info["circuitikz"]
            lines.append(f"  \\draw {a} to[{kind}{label}{value}{current}{annotation}{color_opt}] {b};")

    lines.append(r"\end{circuitikz}")
    return "\n".join(lines)


# ─── Serialization ────────────────────────────────────────────────────

def circuit_to_dict(circuit: Circuit) -> dict:
    return {
        "components": [
            {"kind": c.kind, "label": c.label, "value": c.value,
             "x1": c.x1, "y1": c.y1, "x2": c.x2, "y2": c.y2,
             "current": c.current, "annotation": c.annotation,
             "color": c.color}
            for c in circuit.components
        ],
        "busbars": [
            {"label": b.label, "y": b.y, "x_start": b.x_start, "x_end": b.x_end}
            for b in circuit.busbars
        ],
    }


def circuit_from_dict(data: dict) -> Circuit:
    c = Circuit()
    for d in data.get("components", []):
        c.components.append(Component(**d))
    for d in data.get("busbars", []):
        c.busbars.append(Busbar(**d))
    return c


def save_circuit(circuit: Circuit, path: Path):
    path.write_text(json.dumps(circuit_to_dict(circuit), indent=2), encoding="utf-8")


def load_circuit(path: Path) -> Circuit:
    data = json.loads(path.read_text(encoding="utf-8"))
    return circuit_from_dict(data)
