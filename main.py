import sys
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import fitz
from PyQt5.QtCore import Qt, QPointF, QTimer
from PyQt5.QtGui import QImage, QPixmap, QKeySequence, QPen, QBrush, QColor, QFont, QPainter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPlainTextEdit,
    QLabel, QScrollArea, QPushButton, QVBoxLayout, QWidget,
    QShortcut, QGraphicsScene, QGraphicsView,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox, QFormLayout,
    QGroupBox, QTabWidget,
)

# ─── Constants ────────────────────────────────────────────────────────

GRID_SIZE = 50
GRID_EXTENT = 15

LATEX_TEMPLATE = r"""\documentclass[border=10pt]{{standalone}}
\usepackage[european, siunitx]{{circuitikz}}
\begin{{document}}
{snippet}
\end{{document}}
"""

COMPONENTS = {
    # --- Basic ---
    "R":       {"name": "Resistor",            "circuitikz": "R",              "category": "Basic"},
    "C":       {"name": "Capacitor",           "circuitikz": "C",              "category": "Basic"},
    "L":       {"name": "Inductor",            "circuitikz": "L",              "category": "Basic"},
    "V":       {"name": "Voltage Source",      "circuitikz": "V",              "category": "Basic"},
    "I":       {"name": "Current Source",      "circuitikz": "I",              "category": "Basic"},
    "D":       {"name": "Diode",               "circuitikz": "D",              "category": "Basic"},
    "short":   {"name": "Wire",                "circuitikz": "short",          "category": "Basic"},
    "ground":  {"name": "Ground",              "circuitikz": "ground",         "category": "Basic",
                "node_style": "ground"},
    # --- Power Systems ---
    "busbar":  {"name": "Busbar",              "circuitikz": "busbar",         "category": "Power Systems",
                "special": True},
    "breaker": {"name": "Circuit Breaker",     "circuitikz": "cspst",          "category": "Power Systems"},
    "fuse":    {"name": "Fuse",                "circuitikz": "fuse",           "category": "Power Systems"},
    "discon":  {"name": "Disconnector",        "circuitikz": "nos",            "category": "Power Systems"},
    "switch":  {"name": "Switch",              "circuitikz": "nos",            "category": "Power Systems"},
    "CT":      {"name": "Current Transformer", "circuitikz": "cute inductor",  "category": "Power Systems"},
    "trafo":   {"name": "Transformer",         "circuitikz": "transformer",    "category": "Power Systems"},
    "gen":     {"name": "Generator",           "circuitikz": "vsourcesin",     "category": "Power Systems",
                "node_style": "circ, label=center:G"},
    "motor":   {"name": "Motor",               "circuitikz": "vsourcesin",     "category": "Power Systems",
                "node_style": "circ, label=center:M"},
    "arrester":{"name": "Surge Arrester",      "circuitikz": "surge arrester", "category": "Power Systems"},
}

# ─── Data Model ───────────────────────────────────────────────────────

_uid_counter = 0


def _next_uid():
    global _uid_counter
    _uid_counter += 1
    return _uid_counter


@dataclass
class Component:
    kind: str
    label: str
    value: str
    x1: int
    y1: int
    x2: int = 0
    y2: int = 0
    uid: int = field(default_factory=_next_uid)


@dataclass
class Busbar:
    label: str
    y: int
    x_start: int
    x_end: int
    uid: int = field(default_factory=_next_uid)


@dataclass
class Circuit:
    components: list = field(default_factory=list)
    busbars: list = field(default_factory=list)


# ─── Code Generation ──────────────────────────────────────────────────

def generate_latex(circuit: Circuit) -> str:
    lines = [r"\begin{circuitikz}"]

    for bb in circuit.busbars:
        lines.append(
            f"  \\draw[line width=3pt] ({bb.x_start},{-bb.y}) -- ({bb.x_end},{-bb.y});"
        )
        if bb.label:
            lines.append(f"  \\node[above] at ({bb.x_start},{-bb.y}) {{{bb.label}}};")
        # Auto-detect taps from component endpoints on this busbar
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

        if info.get("node_style"):
            style = info["node_style"]
            lbl = f"${comp.label}$" if comp.label else ""
            lines.append(f"  \\draw {a} node[{style}] {{{lbl}}};")
        else:
            kind = info["circuitikz"]
            lines.append(f"  \\draw {a} to[{kind}{label}{value}] {b};")

    lines.append(r"\end{circuitikz}")
    return "\n".join(lines)


# ─── LaTeX Compilation Pipeline ───────────────────────────────────────

def find_pdflatex() -> str:
    if sys.platform == "win32":
        candidates = [
            Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
            Path("C:/Program Files/MiKTeX/miktex/bin/x64/pdflatex.exe"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
    result = subprocess.run(
        ["where.exe", "pdflatex"] if sys.platform == "win32" else ["which", "pdflatex"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip().splitlines()[0]
    raise FileNotFoundError(
        "pdflatex not found. Install MiKTeX or TeX Live and add it to PATH."
    )


def compile_latex(snippet: str) -> tuple[Path | None, str]:
    tmp = Path(tempfile.mkdtemp(prefix="circuitikz_"))
    tex_file = tmp / "circuit.tex"
    tex_file.write_text(LATEX_TEMPLATE.format(snippet=snippet), encoding="utf-8")
    result = subprocess.run(
        [find_pdflatex(), "-interaction=nonstopmode",
         f"-output-directory={tmp}", str(tex_file)],
        capture_output=True, text=True, timeout=30,
    )
    pdf_path = tmp / "circuit.pdf"
    if pdf_path.exists():
        return pdf_path, ""
    return None, result.stdout + "\n" + result.stderr


def pdf_to_pixmap(pdf_path: Path, dpi: int = 200) -> QPixmap:
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    scale = dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    doc.close()
    fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    return QPixmap.fromImage(qimg)


# ─── Circuit Scene ────────────────────────────────────────────────────

class CircuitScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.circuit = Circuit()
        self._mode = "idle"
        self._active_kind = None
        self._first_pos = None
        self._wire_points = []
        self._selected = None
        self._dynamic_items = []
        self._preview_items = []
        self._counters = {}
        self.on_circuit_changed = None
        self.on_selection_changed = None
        self._init_grid()

    def _init_grid(self):
        brush = QBrush(QColor(190, 190, 190))
        for x in range(-GRID_EXTENT, GRID_EXTENT + 1):
            for y in range(-GRID_EXTENT, GRID_EXTENT + 1):
                dot = self.addEllipse(
                    x * GRID_SIZE - 1.5, y * GRID_SIZE - 1.5, 3, 3,
                    QPen(Qt.NoPen), brush,
                )
                dot.setZValue(-10)

    def _snap(self, pos: QPointF):
        return round(pos.x() / GRID_SIZE), round(pos.y() / GRID_SIZE)

    def _next_label(self, kind):
        n = self._counters.get(kind, 0) + 1
        self._counters[kind] = n
        prefixes = {
            "R": "R", "C": "C", "L": "L", "V": "V", "I": "I", "D": "D",
            "breaker": "CB", "fuse": "F", "discon": "DS", "switch": "SW",
            "CT": "CT", "trafo": "T", "gen": "G", "motor": "M", "arrester": "SA",
        }
        prefix = prefixes.get(kind, "")
        return f"{prefix}_{n}" if prefix else ""

    # ── Placement API ──

    def start_place(self, kind):
        self._clear_preview()
        self._active_kind = kind
        self._first_pos = None
        self._wire_points = []
        info = COMPONENTS[kind]
        if info.get("special"):
            self._mode = "busbar_first"
        elif info.get("node_style"):
            self._mode = "place_single"
        elif kind == "short":
            self._mode = "wire"
        else:
            self._mode = "place_first"

    def cancel_place(self):
        self._mode = "idle"
        self._active_kind = None
        self._first_pos = None
        self._wire_points = []
        self._clear_preview()

    def delete_selected(self):
        if self._selected is None:
            return
        if isinstance(self._selected, Component):
            self.circuit.components.remove(self._selected)
        elif isinstance(self._selected, Busbar):
            self.circuit.busbars.remove(self._selected)
        self._selected = None
        self._redraw()
        if self.on_selection_changed:
            self.on_selection_changed(None)

    # ── Mouse handling ──

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.cancel_place()
            return
        if event.button() != Qt.LeftButton:
            return
        gx, gy = self._snap(event.scenePos())

        if self._mode == "idle":
            self._try_select(gx, gy)
        elif self._mode == "place_single":
            self._add_single(gx, gy)
            self._mode = "idle"
            self._active_kind = None
            self._clear_preview()
        elif self._mode == "place_first":
            self._first_pos = (gx, gy)
            self._mode = "place_second"
        elif self._mode == "place_second":
            self._add_two_terminal(*self._first_pos, gx, gy)
            self._first_pos = None
            self._mode = "idle"
            self._active_kind = None
            self._clear_preview()
        elif self._mode == "busbar_first":
            self._first_pos = (gx, gy)
            self._mode = "busbar_second"
        elif self._mode == "busbar_second":
            self._add_busbar(*self._first_pos, gx, gy)
            self._first_pos = None
            self._mode = "idle"
            self._active_kind = None
            self._clear_preview()
        elif self._mode == "wire":
            self._wire_points.append((gx, gy))
            if len(self._wire_points) >= 2:
                p1, p2 = self._wire_points[-2], self._wire_points[-1]
                if p1 != p2:
                    self.circuit.components.append(
                        Component("short", "", "", p1[0], p1[1], p2[0], p2[1])
                    )
                    self._redraw()

    def update_preview(self, scene_pos: QPointF):
        self._clear_preview()
        if self._mode == "idle":
            return
        gx, gy = self._snap(scene_pos)
        px, py = gx * GRID_SIZE, gy * GRID_SIZE
        cross = QPen(QColor(255, 100, 0), 1, Qt.DashLine)
        self._preview_items.append(self.addLine(px - 8, py, px + 8, py, cross))
        self._preview_items.append(self.addLine(px, py - 8, px, py + 8, cross))
        # Preview line from first click
        origin = self._first_pos
        if self._mode in ("place_second", "busbar_second") and origin:
            fpx, fpy = origin[0] * GRID_SIZE, origin[1] * GRID_SIZE
            pen = QPen(QColor(255, 100, 0, 150), 2, Qt.DashLine)
            self._preview_items.append(self.addLine(fpx, fpy, px, py, pen))
        if self._mode == "wire" and self._wire_points:
            lx, ly = self._wire_points[-1]
            pen = QPen(QColor(255, 100, 0, 150), 2, Qt.DashLine)
            self._preview_items.append(
                self.addLine(lx * GRID_SIZE, ly * GRID_SIZE, px, py, pen)
            )

    def _clear_preview(self):
        for item in self._preview_items:
            self.removeItem(item)
        self._preview_items.clear()

    # ── Selection ──

    @staticmethod
    def _point_to_segment_dist2(px, py, x1, y1, x2, y2):
        """Squared distance from point (px,py) to segment (x1,y1)-(x2,y2)."""
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return (px - x1) ** 2 + (py - y1) ** 2
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        cx, cy = x1 + t * dx, y1 + t * dy
        return (px - cx) ** 2 + (py - cy) ** 2

    def _try_select(self, gx, gy):
        best, best_dist = None, float("inf")
        for comp in self.circuit.components:
            info = COMPONENTS[comp.kind]
            if info.get("node_style"):
                d = (gx - comp.x1) ** 2 + (gy - comp.y1) ** 2
            else:
                d = self._point_to_segment_dist2(gx, gy, comp.x1, comp.y1, comp.x2, comp.y2)
            if d < best_dist:
                best_dist, best = d, comp
        for bb in self.circuit.busbars:
            d = self._point_to_segment_dist2(gx, gy, bb.x_start, bb.y, bb.x_end, bb.y)
            if d < best_dist:
                best_dist, best = d, bb
        self._selected = best if best_dist <= 2.5 else None
        self._redraw()
        if self.on_selection_changed:
            self.on_selection_changed(self._selected)

    # ── Add helpers ──

    def _add_single(self, gx, gy):
        label = self._next_label(self._active_kind)
        self.circuit.components.append(
            Component(self._active_kind, label, "", gx, gy)
        )
        self._redraw()

    def _add_two_terminal(self, x1, y1, x2, y2):
        if x1 == x2 and y1 == y2:
            return
        label = self._next_label(self._active_kind)
        self.circuit.components.append(
            Component(self._active_kind, label, "", x1, y1, x2, y2)
        )
        self._redraw()

    def _add_busbar(self, x1, y1, x2, y2):
        y = y1
        xs, xe = min(x1, x2), max(x1, x2)
        if xs == xe:
            return
        label = f"Bus {len(self.circuit.busbars) + 1}"
        self.circuit.busbars.append(Busbar(label, y, xs, xe))
        self._redraw()

    # ── Drawing ──

    def _redraw(self):
        for item in self._dynamic_items:
            self.removeItem(item)
        self._dynamic_items.clear()
        for bb in self.circuit.busbars:
            self._draw_busbar(bb, bb is self._selected)
        for comp in self.circuit.components:
            self._draw_comp(comp, comp is self._selected)
        self._draw_nodes()
        if self.on_circuit_changed:
            self.on_circuit_changed()

    def _draw_busbar(self, bb, selected):
        px1, px2 = bb.x_start * GRID_SIZE, bb.x_end * GRID_SIZE
        py = bb.y * GRID_SIZE
        color = QColor(255, 140, 0) if selected else QColor(0, 0, 0)
        line = self.addLine(px1, py, px2, py, QPen(color, 5))
        line.setZValue(1)
        self._dynamic_items.append(line)
        if bb.label:
            text = self.addText(bb.label, QFont("Arial", 8))
            text.setDefaultTextColor(color)
            text.setPos(px1, py - 22)
            text.setZValue(2)
            self._dynamic_items.append(text)

    def _draw_comp(self, comp, selected):
        info = COMPONENTS[comp.kind]
        color = QColor(255, 140, 0) if selected else QColor(0, 60, 180)
        wire_color = QColor(255, 140, 0) if selected else QColor(0, 0, 0)
        px1, py1 = comp.x1 * GRID_SIZE, comp.y1 * GRID_SIZE

        if info.get("node_style"):
            # Single-node: ground, generator, motor
            if comp.kind == "ground":
                pen = QPen(color, 2)
                items = [
                    self.addLine(px1, py1, px1, py1 + 10, pen),
                    self.addLine(px1 - 10, py1 + 10, px1 + 10, py1 + 10, pen),
                    self.addLine(px1 - 6, py1 + 15, px1 + 6, py1 + 15, pen),
                    self.addLine(px1 - 2, py1 + 20, px1 + 2, py1 + 20, pen),
                ]
                for it in items:
                    it.setZValue(2)
                self._dynamic_items.extend(items)
            else:
                r = 14
                ellipse = self.addEllipse(
                    px1 - r, py1 - r, 2 * r, 2 * r,
                    QPen(color, 2), QBrush(QColor(255, 255, 255)),
                )
                ellipse.setZValue(2)
                letter = "G" if comp.kind == "gen" else "M"
                text = self.addText(letter, QFont("Arial", 10, QFont.Bold))
                text.setDefaultTextColor(color)
                tr = text.boundingRect()
                text.setPos(px1 - tr.width() / 2, py1 - tr.height() / 2)
                text.setZValue(3)
                self._dynamic_items.extend([ellipse, text])
            # Label to the right
            if comp.label:
                lbl = self.addText(comp.label, QFont("Arial", 7))
                lbl.setDefaultTextColor(color)
                lbl.setPos(px1 + 16, py1 - 6)
                lbl.setZValue(3)
                self._dynamic_items.append(lbl)
        else:
            # Two-terminal
            px2, py2 = comp.x2 * GRID_SIZE, comp.y2 * GRID_SIZE
            mx, my = (px1 + px2) / 2, (py1 + py2) / 2
            if comp.kind == "short":
                line = self.addLine(px1, py1, px2, py2, QPen(wire_color, 2))
                line.setZValue(1)
                self._dynamic_items.append(line)
            else:
                line = self.addLine(px1, py1, px2, py2, QPen(color, 2))
                line.setZValue(1)
                label_text = comp.label or info["name"][:3]
                text = self.addText(label_text, QFont("Arial", 7))
                text.setDefaultTextColor(color)
                tr = text.boundingRect()
                tw, th = tr.width(), tr.height()
                bg = self.addRect(
                    mx - tw / 2 - 3, my - th / 2 - 1, tw + 6, th + 2,
                    QPen(color, 1), QBrush(QColor(255, 255, 240)),
                )
                bg.setZValue(2)
                text.setPos(mx - tw / 2, my - th / 2)
                text.setZValue(3)
                self._dynamic_items.extend([line, bg, text])

    def _draw_nodes(self):
        positions = set()
        for comp in self.circuit.components:
            positions.add((comp.x1, comp.y1))
            if not COMPONENTS[comp.kind].get("node_style"):
                positions.add((comp.x2, comp.y2))
        brush = QBrush(QColor(0, 0, 0))
        for gx, gy in positions:
            px, py = gx * GRID_SIZE, gy * GRID_SIZE
            dot = self.addEllipse(px - 3, py - 3, 6, 6, QPen(Qt.NoPen), brush)
            dot.setZValue(4)
            self._dynamic_items.append(dot)


# ─── Canvas View ──────────────────────────────────────────────────────

class CircuitCanvas(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        extent = GRID_EXTENT * GRID_SIZE + 50
        self.setSceneRect(-extent, -extent, 2 * extent, 2 * extent)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mouseMoveEvent(self, event):
        self.scene().update_preview(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.scene().cancel_place()
        elif event.key() == Qt.Key_Delete:
            self.scene().delete_selected()
        else:
            super().keyPressEvent(event)


# ─── Component Palette ────────────────────────────────────────────────

class ComponentPalette(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setIndentation(15)
        categories = {}
        for kind, info in COMPONENTS.items():
            cat = info["category"]
            if cat not in categories:
                parent = QTreeWidgetItem(self, [cat])
                parent.setFlags(parent.flags() & ~Qt.ItemIsSelectable)
                font = parent.font(0)
                font.setBold(True)
                parent.setFont(0, font)
                categories[cat] = parent
            child = QTreeWidgetItem(categories[cat], [info["name"]])
            child.setData(0, Qt.UserRole, kind)
        self.expandAll()


# ─── Property Panel ───────────────────────────────────────────────────

class PropertyPanel(QGroupBox):
    def __init__(self):
        super().__init__("Properties")
        self._current = None
        self._updating = False
        self.on_changed = None
        self.on_delete = None

        layout = QFormLayout(self)
        self.kind_combo = QComboBox()
        for kind, info in COMPONENTS.items():
            if not info.get("special"):
                self.kind_combo.addItem(info["name"], kind)
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("e.g. R_1")
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("e.g. 1k\\Omega")
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setEnabled(False)

        layout.addRow("Type:", self.kind_combo)
        layout.addRow("Label:", self.label_edit)
        layout.addRow("Value:", self.value_edit)
        layout.addRow(self.delete_btn)

        self.kind_combo.currentIndexChanged.connect(self._apply)
        self.label_edit.textChanged.connect(self._apply)
        self.value_edit.textChanged.connect(self._apply)
        self.delete_btn.clicked.connect(self._on_delete)
        self.setEnabled(False)

    def set_component(self, obj):
        self._updating = True
        self._current = obj
        if obj is None:
            self.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.label_edit.clear()
            self.value_edit.clear()
            self._updating = False
            return
        self.setEnabled(True)
        self.delete_btn.setEnabled(True)
        if isinstance(obj, Busbar):
            self.kind_combo.setEnabled(False)
            self.label_edit.setText(obj.label)
            self.value_edit.setEnabled(False)
            self.value_edit.clear()
        else:
            self.kind_combo.setEnabled(True)
            idx = self.kind_combo.findData(obj.kind)
            self.kind_combo.setCurrentIndex(idx)
            self.label_edit.setText(obj.label)
            self.value_edit.setEnabled(True)
            self.value_edit.setText(obj.value)
        self._updating = False

    def _apply(self):
        if self._updating or self._current is None:
            return
        if isinstance(self._current, Busbar):
            self._current.label = self.label_edit.text()
        else:
            new_kind = self.kind_combo.currentData()
            if new_kind:
                self._current.kind = new_kind
            self._current.label = self.label_edit.text()
            self._current.value = self.value_edit.text()
        if self.on_changed:
            self.on_changed()

    def _on_delete(self):
        if self.on_delete:
            self.on_delete()


# ─── Main Window ──────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CircuitTikZ Visualizer")
        self.resize(1200, 700)
        self._tmp_dirs: list[Path] = []
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(500)
        self._render_timer.timeout.connect(self._do_render)

        # Scene & canvas
        self.scene = CircuitScene()
        self.scene.on_circuit_changed = self._on_circuit_changed
        self.scene.on_selection_changed = self._on_selection_changed
        self.canvas = CircuitCanvas(self.scene)

        # Palette
        self.palette_tree = ComponentPalette()
        self.palette_tree.itemClicked.connect(self._on_palette_click)

        # Property panel
        self.props = PropertyPanel()
        self.props.on_changed = self._on_props_changed
        self.props.on_delete = self._on_delete_selected

        # Left panel
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.palette_tree, 1)
        left_layout.addWidget(self.props)
        left.setMaximumWidth(220)

        # Center: visual editor tab
        self.latex_view = QPlainTextEdit()
        self.latex_view.setReadOnly(True)
        self.latex_view.setMaximumHeight(120)

        visual_widget = QWidget()
        vl = QVBoxLayout(visual_widget)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self.canvas, 1)
        vl.addWidget(QLabel("Generated LaTeX:"))
        vl.addWidget(self.latex_view)

        # Center: manual editor tab
        self.manual_editor = QPlainTextEdit()
        self.manual_editor.setPlainText(
            r"""\begin{circuitikz}
  \draw (0,0)
    to[V, v=$U_q$] (0,3)
    to[R, l=$R_1$] (3,3)
    to[C, l=$C_1$] (3,0)
    -- (0,0);
\end{circuitikz}"""
        )

        self.center_tabs = QTabWidget()
        self.center_tabs.addTab(visual_widget, "Visual Editor")
        self.center_tabs.addTab(self.manual_editor, "LaTeX Editor")

        # Right: rendered preview
        self.image_label = QLabel("Click Render or Ctrl+Enter")
        self.image_label.setAlignment(Qt.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)

        self.render_btn = QPushButton("Render (Ctrl+Enter)")
        self.render_btn.clicked.connect(self._do_render)

        self.error_label = QPlainTextEdit()
        self.error_label.setReadOnly(True)
        self.error_label.setMaximumHeight(60)
        self.error_label.hide()

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(scroll, 1)
        rl.addWidget(self.render_btn)
        rl.addWidget(self.error_label)

        # Main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.center_tabs)
        splitter.addWidget(right)
        splitter.setSizes([200, 550, 400])
        self.setCentralWidget(splitter)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._do_render)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self._on_delete_selected)

    def _on_palette_click(self, item, _column):
        kind = item.data(0, Qt.UserRole)
        if kind:
            self.scene.start_place(kind)

    def _on_circuit_changed(self):
        latex = generate_latex(self.scene.circuit)
        self.latex_view.setPlainText(latex)
        self._render_timer.start()

    def _on_selection_changed(self, obj):
        self.props.set_component(obj)

    def _on_props_changed(self):
        self.scene._redraw()

    def _on_delete_selected(self):
        self.scene.delete_selected()

    def _do_render(self):
        self.error_label.hide()
        self.error_label.clear()
        if self.center_tabs.currentIndex() == 0:
            snippet = generate_latex(self.scene.circuit)
        else:
            snippet = self.manual_editor.toPlainText()
        if not snippet.strip():
            return
        self.render_btn.setEnabled(False)
        self.render_btn.setText("Rendering...")
        QApplication.processEvents()
        try:
            pdf_path, error = compile_latex(snippet)
            if pdf_path is None:
                self.error_label.setPlainText(error)
                self.error_label.show()
                return
            self._tmp_dirs.append(pdf_path.parent)
            pixmap = pdf_to_pixmap(pdf_path)
            self.image_label.setPixmap(pixmap)
            self.image_label.adjustSize()
        except FileNotFoundError as e:
            self.error_label.setPlainText(str(e))
            self.error_label.show()
        except subprocess.TimeoutExpired:
            self.error_label.setPlainText("pdflatex timed out after 30 seconds.")
            self.error_label.show()
        finally:
            self.render_btn.setEnabled(True)
            self.render_btn.setText("Render (Ctrl+Enter)")

    def closeEvent(self, event):
        for d in self._tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)
        self._tmp_dirs.clear()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
