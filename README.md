# CircuitTikZ Visualizer

A Python desktop application for building circuit diagrams visually and generating LaTeX [CircuitTikZ](https://ctan.org/pkg/circuitikz) code. Place components on a grid canvas, connect them with wires, and render the result as a PDF preview — all without writing LaTeX by hand.

![Python](https://img.shields.io/badge/Python-3.13%2B-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)

## Features

- **Visual drag-and-drop editor** — place components on a snap-to-grid canvas with two-click wiring
- **Live LaTeX preview** — renders the circuit through pdflatex and displays the PDF inline
- **Manual LaTeX tab** — write CircuitTikZ code directly and render it
- **Convention selector** — switch between European (IEC) and American (IEEE/ANSI) symbol styles
- **Save / Load** — circuits stored as JSON files (Ctrl+S / Ctrl+O)
- **Export .tex** — export a complete standalone LaTeX document
- **Undo / Redo** — Ctrl+Z / Ctrl+Shift+Z with full state snapshots
- **Property panel** — edit label, value, current arrow (`i=`), and annotation (`a=`) per component
- **Zoom** — mouse wheel to zoom, "Zoom Fit" button to frame all components

### Available Components

| Basic | Power Systems |
|---|---|
| Resistor, Capacitor, Inductor | Busbar, Circuit Breaker, Fuse |
| Voltage Source, Current Source, Diode | Disconnector, Switch, Transformer |
| Battery, Lamp, Push Button, SPST Switch | Current Transformer, Generator, Motor |
| Wire, Ground, VCC | Surge Arrester |

## Setup

### Prerequisites

- **Python 3.13+**
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **MiKTeX** or **TeX Live** (provides `pdflatex`)

### 1. Clone the repository

```bash
git clone <repo-url>
```

### 2. Create a virtual environment and install dependencies

```bash
uv venv
uv pip install PyQt5 PyMuPDF
```

### 3. Activate the virtual environment

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.\.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

### 4. Install LaTeX dependencies

The app needs `pdflatex` with the following LaTeX packages: **circuitikz**, **standalone**, and **siunitx**.

**Windows (MiKTeX):**
```powershell
winget install MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements
miktex packages install circuitikz standalone siunitx
```

### 5. Run

```bash
python main.py
```

## Usage

1. **Place components** — click a component in the left palette, then click on the grid to place it (two clicks for two-terminal components)
2. **Wire mode** — select "Wire" from the palette, click to add waypoints, double-click or press Escape to finish
3. **Select** — click near a component to select it; right-click or Escape to deselect
4. **Edit properties** — use the property panel (bottom-left) to change type, label, value, current arrow, or annotation
5. **Drag** — click and drag endpoints or the body of a selected component to reposition it
6. **Delete** — press Delete or use the "Delete Selected" button
7. **Render** — press Ctrl+Enter or click "Render" to compile and preview the LaTeX output
8. **Convention** — use the dropdown in the toolbar to switch between European/American symbol styles

## Project Structure

```
main.py       Entry point, MainWindow, LaTeX compilation pipeline
models.py     Component, Busbar, Circuit dataclasses + COMPONENTS registry
latex.py      LaTeX code generation + JSON save/load serialization
scene.py      CircuitScene (QGraphicsScene) + CircuitCanvas (QGraphicsView)
panels.py     ComponentPalette + PropertyPanel widgets
```
