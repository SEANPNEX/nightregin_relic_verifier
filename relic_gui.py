import sys
import json
import os
import struct
import csv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QCheckBox, 
                             QLabel, QScrollArea, QFrame, QGridLayout, 
                             QFileDialog, QMessageBox, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- CONSTANTS ---
BND4_MAGIC = b'BND4'
AES_KEY = bytes([24, 246, 50, 102, 5, 189, 23, 138, 85, 36, 82, 58, 192, 160, 198, 9])
FACE_ANCHOR = bytes.fromhex('27000046414345')
BLOCK_END_MARKER = bytes.fromhex('ffffffff')
VALID_BYTE2 = {128, 129, 130, 131, 132, 133}
VALID_BYTE3 = {128, 144, 192}

# Deep Relic Valid Curse Pool
VALID_DEEP_DEBUFFS = {
    6820000, 6820100, 6820200, 6820300, 6820400, 6820500, 6820600, 6830000, 
    6830100, 6830200, 6830300, 6830400, 6840000, 6840100, 6840200, 6850200, 
    6850500, 6850700, 6850800, 6850900, 6851200, 6851300, 6851400, 6851700, 
    8520000, 8520001, 8520002, 8760000, 8760050, 8760100, 8760150, 8760200, 
    8760250, 8761000, 8761050, 8761100, 8761150, 8762000, 8762050, 8763000, 
    8763050, 8766000, 8766050, 8770000, 8770050, 8771000, 8771050, 8800100, 
    8800150, 8800200, 8800250, 8801000, 8801050, 8810000, 8810050, 8810200, 
    8810250, 8810300, 8810350, 8810400, 8810450, 8813100, 8813150, 8821000, 
    8821050, 8830000, 8830050, 8831000, 8831050, 8831200, 8831250
}

UI_TEXT = {
    "en": {
        "title": "Nightreign Relic Legality Inspector",
        "load": "Load .sl2 Save",
        "show_illegal": "Show Illegal Only",
        "lang": "Lang:",
        "status": "Status",
        "no_relics": "No relics found.",
        "no_illegal": "No illegal relics found.",
        "slot": "Slot",
        "processing": "Processing..."
    },
    "zh": {
        "title": "Nightreign 遗物合法性查询工具",
        "load": "加载 .sl2 存档",
        "show_illegal": "只显示不合法",
        "lang": "语言:",
        "status": "状态",
        "no_relics": "未发现遗物。",
        "no_illegal": "未发现不合法遗物。",
        "slot": "角色槽位",
        "processing": "正在处理..."
    }
}

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- BACKEND LOGIC ---
class RelicLegalityChecker:
    def __init__(self, data_dir: str = "."):
        self.enabled = False
        self.official_map = {}
        self.equip_param = {}
        self.pool1_map = []
        self.lottery_pools = {}
        self.exclusivity_map = {}
        
        # Resolve paths using resource_path
        off_file = resource_path("official_relics.csv")
        equip_file = resource_path("EquipParamAntique.csv")
        table_file = resource_path("AttachEffectTableParam.csv")
        param_file = resource_path("AttachEffectParam.csv")

        # Load official whitelist
        if os.path.exists(off_file):
            try:
                with open(off_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        effs = [int(row['Effect_1']), int(row['Effect_2']), int(row['Effect_3'])]
                        self.official_map[int(row['Base_ID'])] = sorted([e for e in effs if e > 0])
            except Exception as e:
                print(f"[WARN] Failed to load official_relics.csv: {e}")

        # Load game parameters
        if all(os.path.exists(f) for f in [equip_file, table_file, param_file]):
            try:
                # Load EquipParamAntique
                with open(equip_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row = {k.strip(): v for k, v in row.items()}
                        item_id = int(row['ID'])
                        rule = {
                            "attachEffectTableId_1": int(row.get("attachEffectTableId_1", -1) or -1),
                            "attachEffectTableId_2": int(row.get("attachEffectTableId_2", -1) or -1),
                            "attachEffectTableId_3": int(row.get("attachEffectTableId_3", -1) or -1),
                            "attachEffectTableId_curse1": int(row.get("attachEffectTableId_curse1", -1) or -1),
                            "attachEffectTableId_curse2": int(row.get("attachEffectTableId_curse2", -1) or -1),
                            "attachEffectTableId_curse3": int(row.get("attachEffectTableId_curse3", -1) or -1),
                            "isDeepRelic": int(row.get("isDeepRelic", 0) or 0)
                        }
                        self.equip_param[item_id] = rule
                        rule_with_id = rule.copy(); rule_with_id['ID'] = item_id
                        self.pool1_map.append(rule_with_id)
                
                # Load AttachEffectTableParam (Lottery Pools)
                with open(table_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        tid = int(row['ID'])
                        eid = int(row['attachEffectId'])
                        if tid not in self.lottery_pools: self.lottery_pools[tid] = set()
                        self.lottery_pools[tid].add(eid)

                # Load AttachEffectParam (Exclusivity)
                with open(param_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        eid = int(row['ID'])
                        ex_id = int(row.get('exclusivityId', -1) or -1)
                        if ex_id != -1: self.exclusivity_map[eid] = ex_id
                
                self.enabled = True
            except Exception as e:
                print(f"[ERROR] Engine init failed: {e}")

    def check(self, item_id, raw_slots):
        # 1. Official Relic Check (Order Independent)
        if item_id in self.official_map:
            active_pos = sorted([s['pos'] for s in raw_slots if s['pos'] > 0])
            active_neg = [s['neg'] for s in raw_slots if s['neg'] > 0]
            
            if active_pos == self.official_map[item_id] and len(active_neg) == 0:
                return {"status": "Official", "reason": "Matches System Preset"}
            else:
                return {"status": "Illegal", "reason": "Modified Official Relic (Invalid effects or debuff injected)"}

        if not self.enabled: return {"status": "Unknown", "reason": "Missing Params"}
        
        # 2. Random Relic Rule Row Lookup
        rules = self.equip_param.get(item_id)
        if rules is None:
            for r in self.pool1_map:
                if raw_slots[0]['pos'] > 0 and raw_slots[0]['pos'] in self.lottery_pools.get(r['attachEffectTableId_1'], set()):
                    rules = r; break
        
        if rules is None: return {"status": "Illegal", "reason": f"No rule metadata for type {item_id}"}

        buff_pools = [int(rules[f"attachEffectTableId_{i}"]) for i in [1, 2, 3] if int(rules[f"attachEffectTableId_{i}"]) > 0]
        curse_pools = [int(rules[f"attachEffectTableId_curse{i}"]) for i in [1, 2, 3] if int(rules[f"attachEffectTableId_curse{i}"]) > 0]
        is_deep = int(rules.get("isDeepRelic", 0)) == 1
        
        pos_ids = [s['pos'] for s in raw_slots[:3] if s['pos'] > 0]
        neg_ids = [s['neg'] for s in raw_slots[:3] if s['neg'] > 0]
        
        # Check Slot 4 (Must always be empty)
        if raw_slots[3]['pos'] > 0 or raw_slots[3]['neg'] > 0:
            return {"status": "Illegal", "reason": "Slot 4 must be empty"}

        # Duplicate Debuff check
        if len(neg_ids) != len(set(neg_ids)):
            return {"status": "Illegal", "reason": "Duplicate debuff IDs"}

        if len(pos_ids) > len(buff_pools):
            return {"status": "Illegal", "reason": "Too many positive effects for this item tier"}

        # --- UNIFIED POOL MATCHING (Accounts for RNG Fallbacks) ---
        allowed_pos_effects = set()
        for pool in buff_pools:
            allowed_pos_effects.update(self.lottery_pools.get(pool, set()))
            
        for pos in pos_ids:
            if pos not in allowed_pos_effects:
                return {"status": "Illegal", "reason": f"Buff {pos} cannot roll on this Relic tier/color."}

        # --- DEBUFF CHECKS ---
        if is_deep:
            for neg in neg_ids:
                if neg not in VALID_DEEP_DEBUFFS:
                    return {"status": "Illegal", "reason": f"Invalid Deep Relic Curse: {neg}"}
        else:
            if len(neg_ids) > len(curse_pools):
                return {"status": "Illegal", "reason": "Too many debuff effects for this item tier"}
                
            allowed_neg_effects = set()
            for pool in curse_pools:
                allowed_neg_effects.update(self.lottery_pools.get(pool, set()))
                
            for neg in neg_ids:
                if neg not in allowed_neg_effects:
                    return {"status": "Illegal", "reason": f"Debuff {neg} cannot roll on this Relic tier/color."}

        # 3. Exclusivity
        seen = set()
        for eid in pos_ids + neg_ids:
            g = self.exclusivity_map.get(eid, -1)
            if g != -1:
                if g in seen: return {"status": "Illegal", "reason": "Exclusivity Conflict (Stacking duplicate effect types)"}
                seen.add(g)
                
        return {"status": "Legal", "reason": "Verified"}


# --- SAVE FILE PARSER ---
def decrypt_data(data, key, iv):
    c = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    d = c.decryptor()
    return d.update(data) + d.finalize()

def read_int_le(data):
    v = 0
    for i, b in enumerate(data): v |= b << (8 * i)
    return v - 0x100000000 if len(data) == 4 and (v & 0x80000000) else v

def parse_save(file_path, checker):
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    mv = memoryview(file_data)
    count = struct.unpack('<I', mv[12:16])[0]
    entries = []
    for j in range(count):
        h_off = 64 + j * 32
        h = mv[h_off:h_off+32]
        entries.append({
            'size': struct.unpack('<I', h[8:12])[0], 
            'off': struct.unpack('<I', h[16:20])[0]
        })

    e10 = entries[10]
    e10_data = file_data[e10['off']:e10['off']+e10['size']]
    name_data = decrypt_data(e10_data[16:], AES_KEY, e10_data[:16])[4:]
    
    results = []
    i = 0
    while True:
        pos = name_data.find(FACE_ANCHOR, i)
        if pos == -1: break
        i = pos + 7
        n_b = name_data[max(0, pos-51):name_data.find(b'\x00\x00', max(0, pos-51))+2]
        if len(n_b) % 2 != 0: n_b = n_b[:-1]
        char_name = n_b.decode('utf-16le').strip('\x00')
        
        slot_idx = len(results)
        if slot_idx >= 10: break
        
        slot_e = entries[slot_idx]
        slot_raw = file_data[slot_e['off']:slot_e['off']+slot_e['size']]
        dec_raw = decrypt_data(slot_raw[16:], AES_KEY, slot_raw[:16])[4:]
        dec = memoryview(dec_raw)
        
        relics = []
        n_pos = dec_raw.find(n_b)
        if n_pos != -1:
            ffff = dec_raw.find(BLOCK_END_MARKER, n_pos+1000)
            off = 32
            while off < n_pos - 100:
                b3 = dec[off+3]
                if dec[off+2] in VALID_BYTE2 and b3 in VALID_BYTE3:
                    sz = 72 if b3 == 192 else (16 if b3 == 144 else 80)
                    if off + sz <= len(dec) and b3 == 192:
                        chunk = dec[off:off+sz]
                        raw_slots = []
                        for j in range(4): 
                            raw_slots.append({
                                'pos': read_int_le(chunk[16+j*4:20+j*4]), 
                                'neg': read_int_le(chunk[56+j*4:60+j*4])
                            })
                        # Check magic/footer pattern efficiently
                        if dec_raw.find(dec_raw[off:off+4] + b'\x01\x00\x00\x00', ffff) != -1:
                            item_id = read_int_le(chunk[4:7])
                            relics.append({
                                'id': item_id, 
                                'slots': raw_slots, 
                                'legality': checker.check(item_id, raw_slots)
                            })
                    off += sz or 1
                else: 
                    if dec[off:off+4] == b'\x00'*4 and dec[off+4:off+8] == b'\xff'*4:
                        off += 8
                    else:
                        off += 1
        results.append({'name': char_name, 'relics': relics})
    return results

# --- PYQT6 UI ---

class ParseWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_path, checker):
        super().__init__()
        self.file_path = file_path
        self.checker = checker

    def run(self):
        try:
            results = parse_save(self.file_path, self.checker)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class RelicCard(QFrame):
    def __init__(self, relic, app_instance):
        super().__init__()
        self.relic = relic
        self.app = app_instance
        self.init_ui()

    def init_ui(self):
        stat = self.relic['legality']['status']
        colors = {
            "Illegal": ("#fff8f8", "#d32f2f"), 
            "Official": ("#faf5ff", "#7b1fa2")
        }.get(stat, ("#ffffff", "#e0e0e0"))

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)
        self.setFixedSize(280, 180)
        self.setStyleSheet(f"""
            RelicCard {{
                background-color: {colors[0]};
                border: 1px solid {colors[1]};
                border-radius: 4px;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        # Title
        title = QLabel(self.app.get_n(self.relic['id']))
        title.setFont(QFont("Segoe UI Semibold", 10))
        title.setWordWrap(True)
        layout.addWidget(title)

        # Status
        txt = UI_TEXT[self.app.lang_var]
        stat_text = f"{txt['status']}: {stat}"
        if stat == "Illegal":
            stat_text += f" ({self.relic['legality']['reason']})"
        
        status_lbl = QLabel(stat_text)
        status_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal, True))
        status_lbl.setStyleSheet(f"color: {colors[1] if stat != 'Legal' else '#666666'};")
        status_lbl.setWordWrap(True)
        layout.addWidget(status_lbl)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet("color: #eeeeee;")
        layout.addWidget(line)

        # Slot Info
        slot_info = []
        for idx, s in enumerate(self.relic['slots']):
            if s['pos'] > 0 or s['neg'] > 0:
                pos_n = self.app.get_n(s['pos'])
                neg_n = self.app.get_n(s['neg'])
                slot_info.append(f"[{idx+1}] {pos_n}\n    \u21b3 {neg_n}")
        
        slots_lbl = QLabel("\n".join(slot_info))
        slots_lbl.setFont(QFont("Segoe UI", 8))
        slots_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        slots_lbl.setWordWrap(True)
        layout.addWidget(slots_lbl)
        layout.addStretch()

class RelicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.checker = RelicLegalityChecker()
        dict_path = resource_path('dictionary.json')
        self.dict = json.load(open(dict_path, 'r', encoding='utf-8')) if os.path.exists(dict_path) else {}
        self.data = []
        self.lang_var = "zh"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Nightreign Relic Inspector")
        self.resize(920, 750)
        
        # Set Window Icon
        icon_path = resource_path("fav.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top Bar
        top_bar = QHBoxLayout()
        self.btn_load = QPushButton()
        self.btn_load.setFixedWidth(150)
        self.btn_load.clicked.connect(self.load_file)
        top_bar.addWidget(self.btn_load)

        self.char_selector = QComboBox()
        self.char_selector.setFixedWidth(250)
        self.char_selector.currentIndexChanged.connect(self.display_relics)
        top_bar.addWidget(self.char_selector)

        self.check_illegal = QCheckBox()
        self.check_illegal.toggled.connect(self.display_relics)
        top_bar.addWidget(self.check_illegal)

        top_bar.addStretch()

        self.lbl_lang = QLabel()
        top_bar.addWidget(self.lbl_lang)

        self.lang_group = QButtonGroup(self)
        self.rb_zh = QRadioButton("ZH")
        self.rb_en = QRadioButton("EN")
        self.lang_group.addButton(self.rb_zh)
        self.lang_group.addButton(self.rb_en)
        self.rb_zh.setChecked(True)
        self.rb_zh.toggled.connect(lambda: self.change_language("zh"))
        self.rb_en.toggled.connect(lambda: self.change_language("en"))
        top_bar.addWidget(self.rb_zh)
        top_bar.addWidget(self.rb_en)

        main_layout.addLayout(top_bar)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: white; }")
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: white;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid_layout.setSpacing(15)
        
        self.scroll.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll)

        self.update_ui_labels()

    def update_ui_labels(self):
        txt = UI_TEXT[self.lang_var]
        self.setWindowTitle(txt["title"])
        self.btn_load.setText(txt["load"])
        self.check_illegal.setText(txt["show_illegal"])
        self.lbl_lang.setText(txt["lang"])

    def get_n(self, idx):
        if idx is None or idx <= 0: return "-"
        e = self.dict.get(str(idx), {})
        return e.get(self.lang_var, e.get('en', str(idx))) if isinstance(e, dict) else str(idx)

    def change_language(self, lang):
        if self.lang_var == lang: return
        self.lang_var = lang
        self.update_ui_labels()
        if self.data:
            current = self.char_selector.currentIndex()
            txt_slot = UI_TEXT[self.lang_var]['slot']
            self.char_selector.blockSignals(True)
            self.char_selector.clear()
            self.char_selector.addItems([f"{txt_slot} {i}: {c['name']}" for i, c in enumerate(self.data)])
            self.char_selector.setCurrentIndex(current)
            self.char_selector.blockSignals(False)
            self.display_relics()

    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Save File", "", "Save Files (*.sl2)")
        if path:
            self.btn_load.setEnabled(False)
            self.btn_load.setText(UI_TEXT[self.lang_var]["processing"])
            
            self.worker = ParseWorker(path, self.checker)
            self.worker.finished.connect(self._on_parse_complete)
            self.worker.error.connect(self._on_parse_error)
            self.worker.start()

    def _on_parse_error(self, err_msg):
        QMessageBox.critical(self, "Error", f"Failed to parse: {err_msg}")
        self.btn_load.setEnabled(True)
        self.btn_load.setText(UI_TEXT[self.lang_var]["load"])

    def _on_parse_complete(self, results):
        self.data = results
        self.btn_load.setEnabled(True)
        self.btn_load.setText(UI_TEXT[self.lang_var]["load"])
        
        txt_slot = UI_TEXT[self.lang_var]['slot']
        self.char_selector.blockSignals(True)
        self.char_selector.clear()
        self.char_selector.addItems([f"{txt_slot} {i}: {c['name']}" for i, c in enumerate(self.data)])
        self.char_selector.setCurrentIndex(0)
        self.char_selector.blockSignals(False)
        self.display_relics()

    def display_relics(self):
        # Clear current grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sel = self.char_selector.currentIndex()
        if sel < 0 or not self.data: return
        
        all_relics = self.data[sel]['relics']
        txt = UI_TEXT[self.lang_var]
        if self.check_illegal.isChecked():
            all_relics = [r for r in all_relics if r['legality']['status'] == "Illegal"]
        
        if not all_relics:
            lbl = QLabel(txt["no_illegal"] if self.check_illegal.isChecked() else txt["no_relics"])
            lbl.setFont(QFont("Segoe UI", 12))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl, 0, 0, 1, 3)
            return

        for i, r in enumerate(all_relics):
            card = RelicCard(r, self)
            self.grid_layout.addWidget(card, i // 3, i % 3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set app-wide font for better look
    app.setFont(QFont("Segoe UI", 9))
    window = RelicApp()
    window.show()
    sys.exit(app.exec())
