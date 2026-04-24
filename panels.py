from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QGroupBox, QFormLayout,
    QComboBox, QLineEdit, QPushButton, QColorDialog,
)

from models import Component, Busbar, COMPONENTS


class ComponentPalette(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setIndentation(15)
        categories: dict[str, QTreeWidgetItem] = {}
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
        self.current_edit = QLineEdit()
        self.current_edit.setPlaceholderText("e.g. I_1")
        self.annotation_edit = QLineEdit()
        self.annotation_edit.setPlaceholderText("e.g. 10\\Omega")
        self.color_btn = QPushButton("Default")
        self.color_btn.clicked.connect(self._pick_color)
        self._color_value = ""
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setEnabled(False)

        layout.addRow("Type:", self.kind_combo)
        layout.addRow("Label:", self.label_edit)
        layout.addRow("Value:", self.value_edit)
        layout.addRow("Current:", self.current_edit)
        layout.addRow("Annotation:", self.annotation_edit)
        layout.addRow("Color:", self.color_btn)
        layout.addRow(self.delete_btn)

        self.kind_combo.currentIndexChanged.connect(self._apply)
        self.label_edit.textChanged.connect(self._apply)
        self.value_edit.textChanged.connect(self._apply)
        self.current_edit.textChanged.connect(self._apply)
        self.annotation_edit.textChanged.connect(self._apply)
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
            self.current_edit.clear()
            self.annotation_edit.clear()
            self._set_color_btn("")
            self._updating = False
            return
        self.setEnabled(True)
        self.delete_btn.setEnabled(True)
        if isinstance(obj, Busbar):
            self.kind_combo.setEnabled(False)
            self.label_edit.setText(obj.label)
            self.value_edit.setEnabled(False)
            self.value_edit.clear()
            self.current_edit.setEnabled(False)
            self.current_edit.clear()
            self.annotation_edit.setEnabled(False)
            self.annotation_edit.clear()
            self.color_btn.setEnabled(False)
            self._set_color_btn("")
        else:
            self.kind_combo.setEnabled(True)
            idx = self.kind_combo.findData(obj.kind)
            self.kind_combo.setCurrentIndex(idx)
            self.label_edit.setText(obj.label)
            self.value_edit.setEnabled(True)
            self.value_edit.setText(obj.value)
            self.current_edit.setEnabled(True)
            self.current_edit.setText(obj.current)
            self.annotation_edit.setEnabled(True)
            self.annotation_edit.setText(obj.annotation)
            self.color_btn.setEnabled(True)
            self._set_color_btn(obj.color)
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
            self._current.current = self.current_edit.text()
            self._current.annotation = self.annotation_edit.text()
            self._current.color = self._color_value
        if self.on_changed:
            self.on_changed()

    def _on_delete(self):
        if self.on_delete:
            self.on_delete()

    def _pick_color(self):
        initial = QColor(self._color_value) if self._color_value else QColor(0, 60, 180)
        c = QColorDialog.getColor(initial, self, "Component Color")
        if c.isValid():
            self._set_color_btn(c.name())
            self._apply()

    def _set_color_btn(self, hex_color: str):
        self._color_value = hex_color
        if hex_color:
            self.color_btn.setText(hex_color)
            self.color_btn.setStyleSheet(
                f"background-color: {hex_color}; color: {'#fff' if QColor(hex_color).lightness() < 128 else '#000'};")
        else:
            self.color_btn.setText("Default")
            self.color_btn.setStyleSheet("")
