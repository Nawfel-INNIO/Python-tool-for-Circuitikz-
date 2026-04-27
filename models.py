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
    voltage_dir: str = "v"
    current_dir: str = "i"
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
    # --- Grounds & Power ---
    "rground":  {"name": "Ref Ground",         "circuitikz": "rground",        "category": "Grounds & Power",
                 "node_style": "rground"},
    "sground":  {"name": "Signal Ground",      "circuitikz": "sground",        "category": "Grounds & Power",
                 "node_style": "sground"},
    "tground":  {"name": "Tailless Ground",    "circuitikz": "tground",        "category": "Grounds & Power",
                 "node_style": "tground"},
    "nground":  {"name": "Noiseless Ground",   "circuitikz": "nground",        "category": "Grounds & Power",
                 "node_style": "nground"},
    "cground":  {"name": "Chassis Ground",     "circuitikz": "cground",        "category": "Grounds & Power",
                 "node_style": "cground"},
    "eground":  {"name": "European Ground",    "circuitikz": "eground",        "category": "Grounds & Power",
                 "node_style": "eground"},
    "tlground": {"name": "TL Ground",          "circuitikz": "tlground",       "category": "Grounds & Power",
                 "node_style": "tlground"},
    "pground":  {"name": "Protective Ground",  "circuitikz": "pground",        "category": "Grounds & Power",
                 "node_style": "pground"},
    "vee":      {"name": "VEE",                "circuitikz": "vee",            "category": "Grounds & Power",
                 "node_style": "vee"},
    # --- Resistors ---
    "open":     {"name": "Open Circuit",       "circuitikz": "open",           "category": "Resistors"},
    "vR":       {"name": "Variable Resistor",  "circuitikz": "vR",             "category": "Resistors"},
    "pR":       {"name": "Potentiometer",      "circuitikz": "pR",             "category": "Resistors"},
    "sR":       {"name": "Sensor Resistor",    "circuitikz": "sR",             "category": "Resistors"},
    "ldR":      {"name": "LDR",                "circuitikz": "ldR",            "category": "Resistors"},
    "varistor": {"name": "Varistor",           "circuitikz": "varistor",       "category": "Resistors"},
    "thR":      {"name": "Thermistor",         "circuitikz": "thR",            "category": "Resistors"},
    "thRp":     {"name": "PTC Thermistor",     "circuitikz": "thRp",           "category": "Resistors"},
    "thRn":     {"name": "NTC Thermistor",     "circuitikz": "thRn",           "category": "Resistors"},
    "phR":      {"name": "Photoresistor",      "circuitikz": "phR",            "category": "Resistors"},
    # --- Capacitors ---
    "eC":       {"name": "Electrolytic Cap",   "circuitikz": "eC",             "category": "Capacitors"},
    "cC":       {"name": "Curved Capacitor",   "circuitikz": "cC",             "category": "Capacitors"},
    "vC":       {"name": "Variable Capacitor", "circuitikz": "vC",             "category": "Capacitors"},
    "PZ":       {"name": "Piezoelectric",      "circuitikz": "PZ",             "category": "Capacitors"},
    # --- Inductors ---
    "vL":       {"name": "Variable Inductor",  "circuitikz": "vL",             "category": "Inductors"},
    "sL":       {"name": "Sensor Inductor",    "circuitikz": "sL",             "category": "Inductors"},
    # --- Diodes ---
    "zD":       {"name": "Zener Diode",        "circuitikz": "zD",             "category": "Diodes"},
    "sD":       {"name": "Schottky Diode",     "circuitikz": "sD",             "category": "Diodes"},
    "leD":      {"name": "LED",                "circuitikz": "leD",            "category": "Diodes"},
    "pD":       {"name": "Photodiode",         "circuitikz": "pD",             "category": "Diodes"},
    "tD":       {"name": "Tunnel Diode",       "circuitikz": "tD",             "category": "Diodes"},
    "VC":       {"name": "Varicap",            "circuitikz": "VC",             "category": "Diodes"},
    "Ty":       {"name": "Thyristor",          "circuitikz": "Ty",             "category": "Diodes"},
    "Tr":       {"name": "Triac",              "circuitikz": "Tr",             "category": "Diodes"},
    # --- Sources ---
    "battery2": {"name": "Battery (alt)",      "circuitikz": "battery2",       "category": "Sources"},
    "solar":    {"name": "Solar Cell",         "circuitikz": "solar",          "category": "Sources"},
    "sI":       {"name": "Sinusoidal Current", "circuitikz": "sI",             "category": "Sources"},
    "cvsource": {"name": "Controlled V Source","circuitikz": "cvsource",       "category": "Sources"},
    "cisource": {"name": "Controlled I Source","circuitikz": "cisource",       "category": "Sources"},
    "dcvsource":{"name": "DC Voltage Source",  "circuitikz": "dcvsource",      "category": "Sources"},
    "dcisource":{"name": "DC Current Source",  "circuitikz": "dcisource",      "category": "Sources"},
    "sqV":      {"name": "Square Wave Source", "circuitikz": "sqV",            "category": "Sources"},
    "nV":       {"name": "Noise V Source",     "circuitikz": "nV",             "category": "Sources"},
    "nI":       {"name": "Noise I Source",     "circuitikz": "nI",             "category": "Sources"},
    "esource":  {"name": "Empty Source",       "circuitikz": "esource",        "category": "Sources"},
    "pvsource": {"name": "PV Source",          "circuitikz": "pvsource",       "category": "Sources"},
    # --- Instruments ---
    "ammeter":  {"name": "Ammeter",            "circuitikz": "ammeter",        "category": "Instruments"},
    "voltmeter":{"name": "Voltmeter",          "circuitikz": "voltmeter",      "category": "Instruments"},
    "ohmmeter": {"name": "Ohmmeter",           "circuitikz": "ohmmeter",       "category": "Instruments"},
    "rmeter":   {"name": "Generic Meter",      "circuitikz": "rmeter",         "category": "Instruments"},
    # --- Switches ---
    "toggle":   {"name": "Toggle Switch",      "circuitikz": "toggle switch",  "category": "Switches"},
    "ncs":      {"name": "NC Switch",          "circuitikz": "ncs",            "category": "Switches"},
    "reed":     {"name": "Reed Switch",        "circuitikz": "reed",           "category": "Switches"},
    # --- Miscellaneous ---
    "afuse":    {"name": "American Fuse",      "circuitikz": "afuse",          "category": "Miscellaneous"},
    "wfuse":    {"name": "Weak Fuse",          "circuitikz": "wfuse",          "category": "Miscellaneous"},
    "thermocouple":{"name": "Thermocouple",    "circuitikz": "thermocouple",   "category": "Miscellaneous"},
    "bulb":     {"name": "Bulb",               "circuitikz": "bulb",           "category": "Miscellaneous"},
    "mic":      {"name": "Microphone",         "circuitikz": "mic",            "category": "Miscellaneous"},
    "loudspeaker":{"name": "Loudspeaker",      "circuitikz": "loudspeaker",    "category": "Miscellaneous"},
    "buzzer":   {"name": "Buzzer",             "circuitikz": "buzzer",         "category": "Miscellaneous"},
    "sparkgap": {"name": "Spark Gap",          "circuitikz": "spark gap",      "category": "Miscellaneous"},
    # --- Crossings ---
    "crossing":  {"name": "Crossing",          "circuitikz": "crossing",       "category": "Crossings"},
    "jumpcross": {"name": "Jump Crossing",     "circuitikz": "jump crossing",  "category": "Crossings"},
    # --- Mechanical ---
    "damper":   {"name": "Damper",             "circuitikz": "damper",          "category": "Mechanical"},
    "spring":   {"name": "Spring",             "circuitikz": "spring",          "category": "Mechanical"},
    "mass":     {"name": "Mass",               "circuitikz": "mass",            "category": "Mechanical"},
    # --- Block Diagram (path-type) ---
    "amp":      {"name": "Amplifier",          "circuitikz": "amp",             "category": "Block Diagram"},
    "adc":      {"name": "ADC",                "circuitikz": "adc",             "category": "Block Diagram"},
    "dac":      {"name": "DAC",                "circuitikz": "dac",             "category": "Block Diagram"},
    "bandpass": {"name": "Bandpass Filter",    "circuitikz": "bandpass",        "category": "Block Diagram"},
    "lowpass":  {"name": "Lowpass Filter",     "circuitikz": "lowpass",         "category": "Block Diagram"},
    "highpass": {"name": "Highpass Filter",    "circuitikz": "highpass",        "category": "Block Diagram"},
    # --- Block Diagram (node-type) ---
    "mixer":    {"name": "Mixer",              "circuitikz": "mixer",           "category": "Block Diagram",
                 "node_style": "mixer"},
    "adder":    {"name": "Adder",              "circuitikz": "adder",           "category": "Block Diagram",
                 "node_style": "adder"},
    "oscillator":{"name": "Oscillator",        "circuitikz": "oscillator",     "category": "Block Diagram",
                  "node_style": "oscillator"},
    # --- Transistors ---
    "npn":      {"name": "NPN",                "circuitikz": "npn",             "category": "Transistors",
                 "node_style": "npn",           "anchors": ["B", "C", "E"],
                 "pin_offsets": {"B": (-1, 0), "C": (0, -1), "E": (0, 1)}},
    "pnp":      {"name": "PNP",                "circuitikz": "pnp",             "category": "Transistors",
                 "node_style": "pnp",           "anchors": ["B", "C", "E"],
                 "pin_offsets": {"B": (-1, 0), "C": (0, 1), "E": (0, -1)}},
    "nmos":     {"name": "NMOS",               "circuitikz": "nmos",            "category": "Transistors",
                 "node_style": "nmos",          "anchors": ["G", "D", "S"],
                 "pin_offsets": {"G": (-1, 0), "D": (0, -1), "S": (0, 1)}},
    "pmos":     {"name": "PMOS",               "circuitikz": "pmos",            "category": "Transistors",
                 "node_style": "pmos",          "anchors": ["G", "D", "S"],
                 "pin_offsets": {"G": (-1, 0), "D": (0, 1), "S": (0, -1)}},
    "nfet":     {"name": "N-Channel FET",      "circuitikz": "nfet",            "category": "Transistors",
                 "node_style": "nfet",          "anchors": ["G", "D", "S"],
                 "pin_offsets": {"G": (-1, 0), "D": (0, -1), "S": (0, 1)}},
    "pfet":     {"name": "P-Channel FET",      "circuitikz": "pfet",            "category": "Transistors",
                 "node_style": "pfet",          "anchors": ["G", "D", "S"],
                 "pin_offsets": {"G": (-1, 0), "D": (0, 1), "S": (0, -1)}},
    "nigbt":    {"name": "N-IGBT",             "circuitikz": "nigbt",           "category": "Transistors",
                 "node_style": "nigbt",         "anchors": ["G", "C", "E"],
                 "pin_offsets": {"G": (-1, 0), "C": (0, -1), "E": (0, 1)}},
    "pigbt":    {"name": "P-IGBT",             "circuitikz": "pigbt",           "category": "Transistors",
                 "node_style": "pigbt",         "anchors": ["G", "C", "E"],
                 "pin_offsets": {"G": (-1, 0), "C": (0, 1), "E": (0, -1)}},
    # --- Amplifiers ---
    "opamp":    {"name": "Op-Amp",             "circuitikz": "op amp",          "category": "Amplifiers",
                 "node_style": "op amp",        "anchors": ["+", "-", "out"],
                 "pin_offsets": {"+": (-1, 1), "-": (-1, -1), "out": (1, 0)}},
    "enamp":    {"name": "EN Amplifier",       "circuitikz": "en amp",          "category": "Amplifiers",
                 "node_style": "en amp",        "anchors": ["+", "-", "out"],
                 "pin_offsets": {"+": (-1, 1), "-": (-1, -1), "out": (1, 0)}},
    "instamp":  {"name": "Inst. Amplifier",    "circuitikz": "inst amp",        "category": "Amplifiers",
                 "node_style": "inst amp",      "anchors": ["+", "-", "out"],
                 "pin_offsets": {"+": (-1, 1), "-": (-1, -1), "out": (1, 0)}},
    "buffer":   {"name": "Buffer",             "circuitikz": "buffer",          "category": "Amplifiers",
                 "node_style": "buffer",        "anchors": ["in", "out"],
                 "pin_offsets": {"in": (-1, 0), "out": (1, 0)}},
    # --- Logic Gates ---
    "andport":  {"name": "AND Gate",           "circuitikz": "and port",        "category": "Logic Gates",
                 "node_style": "and port",      "anchors": ["in 1", "in 2", "out"],
                 "pin_offsets": {"in 1": (-1, -1), "in 2": (-1, 1), "out": (1, 0)}},
    "orport":   {"name": "OR Gate",            "circuitikz": "or port",         "category": "Logic Gates",
                 "node_style": "or port",       "anchors": ["in 1", "in 2", "out"],
                 "pin_offsets": {"in 1": (-1, -1), "in 2": (-1, 1), "out": (1, 0)}},
    "nandport": {"name": "NAND Gate",          "circuitikz": "nand port",       "category": "Logic Gates",
                 "node_style": "nand port",     "anchors": ["in 1", "in 2", "out"],
                 "pin_offsets": {"in 1": (-1, -1), "in 2": (-1, 1), "out": (1, 0)}},
    "norport":  {"name": "NOR Gate",           "circuitikz": "nor port",        "category": "Logic Gates",
                 "node_style": "nor port",      "anchors": ["in 1", "in 2", "out"],
                 "pin_offsets": {"in 1": (-1, -1), "in 2": (-1, 1), "out": (1, 0)}},
    "xorport":  {"name": "XOR Gate",           "circuitikz": "xor port",        "category": "Logic Gates",
                 "node_style": "xor port",      "anchors": ["in 1", "in 2", "out"],
                 "pin_offsets": {"in 1": (-1, -1), "in 2": (-1, 1), "out": (1, 0)}},
    "notport":  {"name": "NOT Gate",           "circuitikz": "not port",        "category": "Logic Gates",
                 "node_style": "not port",      "anchors": ["in", "out"],
                 "pin_offsets": {"in": (-1, 0), "out": (1, 0)}},
    "bufferport":{"name": "Buffer Gate",       "circuitikz": "buffer port",     "category": "Logic Gates",
                  "node_style": "buffer port",  "anchors": ["in", "out"],
                  "pin_offsets": {"in": (-1, 0), "out": (1, 0)}},
    # --- Flip-Flops ---
    "ffD":      {"name": "D Flip-Flop",        "circuitikz": "flipflop D",      "category": "Flip-Flops",
                 "node_style": "flipflop D",    "anchors": ["pin 1", "pin 2", "pin 3", "pin 6"],
                 "pin_offsets": {"pin 1": (-1, -1), "pin 2": (0, 1), "pin 3": (-1, 1), "pin 6": (1, 0)}},
    "ffJK":     {"name": "JK Flip-Flop",       "circuitikz": "flipflop JK",     "category": "Flip-Flops",
                 "node_style": "flipflop JK",   "anchors": ["pin 1", "pin 2", "pin 3", "pin 4", "pin 6"],
                 "pin_offsets": {"pin 1": (-1, -1), "pin 2": (0, 1), "pin 3": (-1, 1), "pin 4": (-1, 0), "pin 6": (1, 0)}},
    "ffT":      {"name": "T Flip-Flop",        "circuitikz": "flipflop T",      "category": "Flip-Flops",
                 "node_style": "flipflop T",    "anchors": ["pin 1", "pin 2", "pin 3", "pin 6"],
                 "pin_offsets": {"pin 1": (-1, -1), "pin 2": (0, 1), "pin 3": (-1, 1), "pin 6": (1, 0)}},
    # --- Mux/Chip ---
    "dipchip":  {"name": "DIP Chip",           "circuitikz": "dipchip",         "category": "ICs",
                 "node_style": "dipchip",       "anchors": ["pin 1"]},
    # --- Transformers ---
    "trafocore":{"name": "Transformer (core)", "circuitikz": "transformer core","category": "Transformers",
                 "node_style": "transformer core", "anchors": ["A1", "A2", "B1", "B2"],
                 "pin_offsets": {"A1": (-1, -1), "A2": (-1, 1), "B1": (1, -1), "B2": (1, 1)}},
    "gyrator":  {"name": "Gyrator",            "circuitikz": "gyrator",         "category": "Transformers",
                 "node_style": "gyrator",       "anchors": ["A1", "A2", "B1", "B2"],
                 "pin_offsets": {"A1": (-1, -1), "A2": (-1, 1), "B1": (1, -1), "B2": (1, 1)}},
    # --- Electronic Tubes ---
    "triode":   {"name": "Triode",             "circuitikz": "triode",          "category": "Tubes",
                 "node_style": "triode",        "anchors": ["anode", "cathode", "grid"],
                 "pin_offsets": {"anode": (0, -1), "cathode": (0, 1), "grid": (-1, 0)}},
    "pentode":  {"name": "Pentode",            "circuitikz": "pentode",         "category": "Tubes",
                 "node_style": "pentode",       "anchors": ["anode", "cathode", "grid"],
                 "pin_offsets": {"anode": (0, -1), "cathode": (0, 1), "grid": (-1, 0)}},
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
