import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QPlainTextEdit,
    QLabel, QScrollArea, QPushButton, QVBoxLayout, QHBoxLayout, QWidget,
    QShortcut, QTabWidget, QFileDialog, QStatusBar,
)

from models import Circuit, COMPONENTS
from latex import generate_latex, save_circuit, load_circuit
from scene import CircuitScene, CircuitCanvas, GRID_SIZE
from panels import ComponentPalette, PropertyPanel

CONVENTIONS = {
    "European": "european",
    "American": "american",
    "European Resistors": "european resistors",
    "American Resistors": "american resistors",
    "European Voltages": "european voltages",
    "American Voltages": "american voltages",
}


def latex_template(convention: str = "european") -> str:
    return (
        "\\documentclass[border=10pt]{{standalone}}\n"
        f"\\usepackage[{convention}, siunitx]{{{{circuitikz}}}}\n"
        "\\begin{{document}}\n"
        "{snippet}\n"
        "\\end{{document}}\n"
    )


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


def compile_latex(snippet: str, convention: str = "european") -> tuple[Path | None, str]:
    tmp = Path(tempfile.mkdtemp(prefix="circuitikz_"))
    tex_file = tmp / "circuit.tex"
    tex_file.write_text(latex_template(convention).format(snippet=snippet), encoding="utf-8")
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


# ─── Main Window ──────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CircuitTikZ Visualizer")
        self.resize(1200, 700)
        self._tmp_dirs: list[Path] = []
        self._current_file: Path | None = None
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(500)
        self._render_timer.timeout.connect(self._do_render)

        # Scene & canvas
        self.scene = CircuitScene()
        self.scene.on_circuit_changed = self._on_circuit_changed
        self.scene.on_selection_changed = self._on_selection_changed
        self.scene.on_mode_changed = self._on_mode_changed
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

        # Status bar for mode
        self.status_label = QLabel("Idle — click to select, right-click to deselect")
        self.status_label.setStyleSheet("padding: 2px 6px; color: #555;")

        # Center: visual editor tab
        self.latex_view = QPlainTextEdit()
        self.latex_view.setReadOnly(True)
        self.latex_view.setMaximumHeight(120)

        visual_widget = QWidget()
        vl = QVBoxLayout(visual_widget)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self.canvas, 1)
        vl.addWidget(self.status_label)
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

        # Toolbar buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self._load)
        self.export_btn = QPushButton("Export .tex")
        self.export_btn.clicked.connect(self._export_tex)
        self.fit_btn = QPushButton("Zoom Fit")
        self.fit_btn.clicked.connect(self.canvas.zoom_to_fit)

        from PyQt5.QtWidgets import QComboBox
        self.convention_combo = QComboBox()
        for label in CONVENTIONS:
            self.convention_combo.addItem(label)
        self.convention_combo.currentTextChanged.connect(lambda _: self._render_timer.start())

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.fit_btn)
        btn_layout.addWidget(self.convention_combo)

        self.error_label = QPlainTextEdit()
        self.error_label.setReadOnly(True)
        self.error_label.setMaximumHeight(60)
        self.error_label.hide()

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(scroll, 1)
        rl.addWidget(self.render_btn)
        rl.addWidget(btn_row)
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
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.scene.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self.scene.redo)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save)
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self._load)

    # ── Callbacks ──

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

    def _on_mode_changed(self, mode, kind):
        self.status_label.setText(self.scene.mode_text())

    def _on_props_changed(self):
        self.scene._snapshot()
        self.scene._redraw()

    def _on_delete_selected(self):
        self.scene.delete_selected()

    # ── Save / Load / Export ──

    def _save(self):
        path = self._current_file
        if not path:
            path_str, _ = QFileDialog.getSaveFileName(
                self, "Save Circuit", "", "Circuit JSON (*.json)")
            if not path_str:
                return
            path = Path(path_str)
        save_circuit(self.scene.circuit, path)
        self._current_file = path
        self.setWindowTitle(f"CircuitTikZ Visualizer — {path.name}")

    def _load(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Load Circuit", "", "Circuit JSON (*.json)")
        if not path_str:
            return
        path = Path(path_str)
        self.scene.circuit = load_circuit(path)
        self.scene._selected = None
        self.scene._redraw()
        self.scene.on_selection_changed(None)
        self._current_file = path
        self.setWindowTitle(f"CircuitTikZ Visualizer — {path.name}")

    def _export_tex(self):
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export LaTeX", "", "LaTeX files (*.tex)")
        if not path_str:
            return
        snippet = generate_latex(self.scene.circuit)
        conv = CONVENTIONS[self.convention_combo.currentText()]
        full = latex_template(conv).format(snippet=snippet)
        Path(path_str).write_text(full, encoding="utf-8")

    # ── Render ──

    def _do_render(self):
        self.error_label.hide()
        self.error_label.clear()
        if self.center_tabs.currentIndex() == 0:
            snippet = generate_latex(self.scene.circuit)
        else:
            snippet = self.manual_editor.toPlainText()
        if not snippet.strip():
            return
        conv = CONVENTIONS[self.convention_combo.currentText()]
        self.render_btn.setEnabled(False)
        self.render_btn.setText("Rendering...")
        QApplication.processEvents()
        try:
            pdf_path, error = compile_latex(snippet, conv)
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
