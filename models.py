from dataclasses import dataclass, field

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
    current: str = ""
    annotation: str = ""
    color: str = ""
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
    components: list[Component] = field(default_factory=list)
    busbars: list[Busbar] = field(default_factory=list)


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
    "vcc":     {"name": "VCC",                 "circuitikz": "vcc",            "category": "Basic",
                "node_style": "vcc"},
    "battery": {"name": "Battery",              "circuitikz": "battery1",       "category": "Basic"},
    "lamp":    {"name": "Lamp",                "circuitikz": "lamp",           "category": "Basic"},
    "pushbtn": {"name": "Push Button",          "circuitikz": "push button",    "category": "Basic"},
    "spst":    {"name": "SPST Switch",          "circuitikz": "spst",           "category": "Basic"},
    # --- Power Systems ---
    "busbar":  {"name": "Busbar",              "circuitikz": "busbar",         "category": "Power Systems",
                "special": True},
    "breaker": {"name": "Circuit Breaker",     "circuitikz": "cspst",          "category": "Power Systems"},
    "fuse":    {"name": "Fuse",                "circuitikz": "fuse",           "category": "Power Systems"},
    "discon":  {"name": "Disconnector",        "circuitikz": "nos",            "category": "Power Systems"},
    "switch":  {"name": "Switch",              "circuitikz": "nos",            "category": "Power Systems"},
    "CT":      {"name": "Current Transformer", "circuitikz": "cute inductor",  "category": "Power Systems"},
    "trafo":   {"name": "Transformer",         "circuitikz": "transformer",    "category": "Power Systems"},
    "gen":     {"name": "Generator",           "circuitikz": "sV",             "category": "Power Systems"},
    "motor":   {"name": "Motor",               "circuitikz": "sV",             "category": "Power Systems"},
    "arrester":{"name": "Surge Arrester",      "circuitikz": "surge arrester", "category": "Power Systems"},
}
