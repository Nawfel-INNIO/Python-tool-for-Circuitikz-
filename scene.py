import copy

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView

from models import Component, Busbar, Circuit, COMPONENTS

GRID_SIZE = 50
GRID_EXTENT = 15


class CircuitScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.circuit = Circuit()
        self._mode = "idle"
        self._active_kind = None
        self._first_pos = None
        self._wire_points: list[tuple[int, int]] = []
        self._selected = None
        self._dynamic_items = []
        self._preview_items = []
        self._counters: dict[str, int] = {}
        # Undo/redo stacks
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        # Drag state
        self._dragging = False
        self._drag_target = None  # (obj, attr) e.g. (comp, "start") or (comp, "end")
        # Callbacks
        self.on_circuit_changed = None
        self.on_selection_changed = None
        self.on_mode_changed = None
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

    def _set_mode(self, mode):
        self._mode = mode
        if self.on_mode_changed:
            self.on_mode_changed(mode, self._active_kind)

    def mode_text(self):
        if self._mode == "idle":
            return "Idle — click to select, right-click to deselect"
        kind_name = COMPONENTS[self._active_kind]["name"] if self._active_kind else ""
        if self._mode == "place_single":
            return f"Click to place {kind_name}"
        if self._mode == "place_first":
            return f"Click first point for {kind_name}"
        if self._mode == "place_second":
            return f"Click second point for {kind_name}"
        if self._mode == "busbar_first":
            return "Click start point for Busbar"
        if self._mode == "busbar_second":
            return "Click end point for Busbar"
        if self._mode == "wire":
            n = len(self._wire_points)
            return f"Wire mode — click to add points ({n} so far), double-click/Esc to finish"
        return ""

    # ── Undo / Redo ──

    def _snapshot(self):
        """Save current circuit state to undo stack."""
        from latex import circuit_to_dict
        self._undo_stack.append(circuit_to_dict(self.circuit))
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        from latex import circuit_to_dict, circuit_from_dict
        self._redo_stack.append(circuit_to_dict(self.circuit))
        self.circuit = circuit_from_dict(self._undo_stack.pop())
        self._selected = None
        self._redraw()
        if self.on_selection_changed:
            self.on_selection_changed(None)

    def redo(self):
        if not self._redo_stack:
            return
        from latex import circuit_to_dict, circuit_from_dict
        self._undo_stack.append(circuit_to_dict(self.circuit))
        self.circuit = circuit_from_dict(self._redo_stack.pop())
        self._selected = None
        self._redraw()
        if self.on_selection_changed:
            self.on_selection_changed(None)

    # ── Placement API ──

    def start_place(self, kind):
        self._clear_preview()
        self._active_kind = kind
        self._first_pos = None
        self._wire_points = []
        info = COMPONENTS[kind]
        if info.get("special"):
            self._set_mode("busbar_first")
        elif info.get("node_style"):
            self._set_mode("place_single")
        elif kind == "short":
            self._set_mode("wire")
        else:
            self._set_mode("place_first")

    def cancel_place(self):
        self._active_kind = None
        self._first_pos = None
        self._wire_points = []
        self._clear_preview()
        self._deselect()
        self._set_mode("idle")

    def _deselect(self):
        if self._selected is not None:
            self._selected = None
            self._redraw()
            if self.on_selection_changed:
                self.on_selection_changed(None)

    def delete_selected(self):
        if self._selected is None:
            return
        self._snapshot()
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
            if self._mode != "idle":
                self.cancel_place()
            else:
                self._deselect()
            return
        if event.button() != Qt.LeftButton:
            return
        gx, gy = self._snap(event.scenePos())

        if self._mode == "idle":
            # Check if clicking near an endpoint of the selected component (start drag)
            if self._selected and isinstance(self._selected, Component):
                target = self._drag_hit(gx, gy, self._selected)
                if target:
                    self._snapshot()
                    self._dragging = True
                    self._drag_target = target
                    return
            if self._selected and isinstance(self._selected, Busbar):
                target = self._busbar_drag_hit(gx, gy, self._selected)
                if target:
                    self._snapshot()
                    self._dragging = True
                    self._drag_target = target
                    return
            self._try_select(gx, gy)
        elif self._mode == "place_single":
            self._snapshot()
            self._add_single(gx, gy)
            self._set_mode("idle")
            self._active_kind = None
            self._clear_preview()
        elif self._mode == "place_first":
            self._first_pos = (gx, gy)
            self._set_mode("place_second")
        elif self._mode == "place_second":
            self._snapshot()
            self._add_two_terminal(*self._first_pos, gx, gy)
            self._first_pos = None
            self._active_kind = None
            self._clear_preview()
            self._set_mode("idle")
        elif self._mode == "busbar_first":
            self._first_pos = (gx, gy)
            self._set_mode("busbar_second")
        elif self._mode == "busbar_second":
            self._snapshot()
            self._add_busbar(*self._first_pos, gx, gy)
            self._first_pos = None
            self._active_kind = None
            self._clear_preview()
            self._set_mode("idle")
        elif self._mode == "wire":
            if not self._wire_points:
                self._snapshot()
            self._wire_points.append((gx, gy))
            if len(self._wire_points) >= 2:
                p1, p2 = self._wire_points[-2], self._wire_points[-1]
                if p1 != p2:
                    self.circuit.components.append(
                        Component("short", "", "", p1[0], p1[1], p2[0], p2[1])
                    )
                    self._redraw()

    def mouseDoubleClickEvent(self, event):
        if self._mode == "wire" and event.button() == Qt.LeftButton:
            self._wire_points = []
            self._active_kind = None
            self._clear_preview()
            self._set_mode("idle")
            return
        super().mouseDoubleClickEvent(event)

    def drag_move(self, scene_pos: QPointF):
        """Move the drag target to the snapped grid position."""
        if not (self._dragging and self._drag_target):
            return
        gx, gy = self._snap(scene_pos)
        obj, attr = self._drag_target
        if isinstance(obj, Component):
            if attr == "start":
                obj.x1, obj.y1 = gx, gy
            elif attr == "end":
                obj.x2, obj.y2 = gx, gy
            elif attr == "body":
                info = COMPONENTS[obj.kind]
                if info.get("node_style"):
                    obj.x1, obj.y1 = gx, gy
                else:
                    dx = gx - self._drag_origin[0]
                    dy = gy - self._drag_origin[1]
                    obj.x1 += dx
                    obj.y1 += dy
                    obj.x2 += dx
                    obj.y2 += dy
                    self._drag_origin = (gx, gy)
        elif isinstance(obj, Busbar):
            if attr == "start":
                obj.x_start = gx
            elif attr == "end":
                obj.x_end = gx
            elif attr == "body":
                dx = gx - self._drag_origin[0]
                obj.x_start += dx
                obj.x_end += dx
                obj.y = gy
                self._drag_origin = (gx, gy)
        self._redraw()

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_target:
            self.drag_move(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._drag_target = None
        super().mouseReleaseEvent(event)

    def _drag_hit(self, gx, gy, comp):
        """Check if (gx,gy) is near an endpoint of comp for dragging."""
        info = COMPONENTS[comp.kind]
        if info.get("node_style"):
            if abs(gx - comp.x1) <= 1 and abs(gy - comp.y1) <= 1:
                return (comp, "body")
            return None
        if abs(gx - comp.x1) <= 1 and abs(gy - comp.y1) <= 1:
            return (comp, "start")
        if abs(gx - comp.x2) <= 1 and abs(gy - comp.y2) <= 1:
            return (comp, "end")
        # Hit near the body = drag whole thing
        d = self._point_to_segment_dist2(gx, gy, comp.x1, comp.y1, comp.x2, comp.y2)
        if d <= 1.5:
            self._drag_origin = (gx, gy)
            return (comp, "body")
        return None

    def _busbar_drag_hit(self, gx, gy, bb):
        if abs(gy - bb.y) > 1:
            return None
        if abs(gx - bb.x_start) <= 1:
            return (bb, "start")
        if abs(gx - bb.x_end) <= 1:
            return (bb, "end")
        if bb.x_start <= gx <= bb.x_end:
            self._drag_origin = (gx, gy)
            return (bb, "body")
        return None

    def update_preview(self, scene_pos: QPointF):
        self._clear_preview()
        if self._mode == "idle":
            return
        gx, gy = self._snap(scene_pos)
        px, py = gx * GRID_SIZE, gy * GRID_SIZE
        cross = QPen(QColor(255, 100, 0), 1, Qt.DashLine)
        self._preview_items.append(self.addLine(px - 8, py, px + 8, py, cross))
        self._preview_items.append(self.addLine(px, py - 8, px, py + 8, cross))
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
            if comp.label:
                lbl = self.addText(comp.label, QFont("Arial", 7))
                lbl.setDefaultTextColor(color)
                lbl.setPos(px1 + 16, py1 - 6)
                lbl.setZValue(3)
                self._dynamic_items.append(lbl)
        else:
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
                # Offset label perpendicular to component for vertical/diagonal lines
                dx, dy = px2 - px1, py2 - py1
                if abs(dx) < 1:  # vertical
                    ox, oy = 8, 0
                elif abs(dy) < 1:  # horizontal
                    ox, oy = 0, -th / 2 - 4
                else:
                    ox, oy = 6, -th / 2 - 4
                bg = self.addRect(
                    mx - tw / 2 - 3 + ox, my - th / 2 - 1 + oy, tw + 6, th + 2,
                    QPen(color, 1), QBrush(QColor(255, 255, 240)),
                )
                bg.setZValue(2)
                text.setPos(mx - tw / 2 + ox, my - th / 2 + oy)
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
    def __init__(self, scene: CircuitScene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        extent = GRID_EXTENT * GRID_SIZE + 50
        self.setSceneRect(-extent, -extent, 2 * extent, 2 * extent)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mouseMoveEvent(self, event):
        scene = self.scene()
        scene_pos = self.mapToScene(event.pos())
        if scene._dragging:
            scene.drag_move(scene_pos)
        else:
            scene.update_preview(scene_pos)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.scene().cancel_place()
        elif event.key() == Qt.Key_Delete:
            self.scene().delete_selected()
        else:
            super().keyPressEvent(event)

    def zoom_to_fit(self):
        scene = self.scene()
        positions = []
        for comp in scene.circuit.components:
            positions.append((comp.x1, comp.y1))
            if not COMPONENTS[comp.kind].get("node_style"):
                positions.append((comp.x2, comp.y2))
        for bb in scene.circuit.busbars:
            positions.append((bb.x_start, bb.y))
            positions.append((bb.x_end, bb.y))
        if not positions:
            return
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        from PyQt5.QtCore import QRectF
        margin = 2
        rect = QRectF(
            (min(xs) - margin) * GRID_SIZE,
            (min(ys) - margin) * GRID_SIZE,
            (max(xs) - min(xs) + 2 * margin) * GRID_SIZE,
            (max(ys) - min(ys) + 2 * margin) * GRID_SIZE,
        )
        self.fitInView(rect, Qt.KeepAspectRatio)
