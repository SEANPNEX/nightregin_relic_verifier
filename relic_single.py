import sys
import os
import json
import argparse
import csv
import struct
from http.server import HTTPServer, BaseHTTPRequestHandler
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QLineEdit,
                             QLabel, QFrame, QGridLayout, QMessageBox, QRadioButton, QButtonGroup, QCompleter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QGuiApplication

# Import Legality Checker and constants from relic_parser
from relic_parser import RelicLegalityChecker, VALID_DEEP_DEBUFFS, AES_KEY, FACE_ANCHOR, BLOCK_END_MARKER, VALID_BYTE2, VALID_BYTE3

# --- UI CONSTANTS & TRANSLATIONS ---
UI_TEXT = {
    "en": {
        "title": "Nightreign Relic Inspector (Single)",
        "relic_type": "Relic Type:",
        "relic_id": "Relic ID:",
        "buffs": "Buff Effects:",
        "curses": "Curse Effects:",
        "check": "Verify Legality",
        "reset": "Reset",
        "status": "Status",
        "reason": "Reason",
        "lang": "Language:",
        "invalid_id": "Invalid ID input. Please enter valid integer IDs.",
        "search_placeholder": "Select from list...",
        "slot": "Slot",
        "buff": "Buff",
        "curse": "Curse",
        "result_title": "Verification Result",
        "custom_id_label": "(Or enter custom ID below)"
    },
    "zh": {
        "title": "Nightreign 遗物单体检验工具",
        "relic_type": "遗物类型:",
        "relic_id": "遗物 ID:",
        "buffs": "正面效果 (Buff):",
        "curses": "负面效果 (Curse):",
        "check": "开始验证",
        "reset": "重置",
        "status": "状态",
        "reason": "原因",
        "lang": "语言:",
        "invalid_id": "无效的 ID 输入。请输入合法的整数 ID。",
        "search_placeholder": "从列表中选择...",
        "slot": "槽位",
        "buff": "正面词条",
        "curse": "负面诅咒",
        "result_title": "验证结果",
        "custom_id_label": "(或在下方输入自定义 ID)"
    }
}

def is_dark_mode():
    palette = QGuiApplication.palette()
    return palette.color(QPalette.ColorRole.Window).lightness() < 128

# --- API SERVER HANDLER ---
class RelicVerificationHandler(BaseHTTPRequestHandler):
    checker = None

    def log_message(self, format, *args):
        # Console logging of requests
        sys.stderr.write("%s - - [%s] %s\n" %
                         (self.address_string(),
                          self.log_date_time_string(),
                          format%args))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == '/verify' or self.path == '/api/verify':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                relic_id = int(data.get('relic_id', 0))
                
                buffs_list = data.get('buffs', [])
                curses_list = data.get('curses', [])
                
                buffs = [int(b) for b in buffs_list]
                curses = [int(c) for c in curses_list]
                
                raw_slots = []
                for i in range(4):
                    b_val = buffs[i] if i < len(buffs) else 0
                    c_val = curses[i] if i < len(curses) else 0
                    raw_slots.append({'pos': b_val, 'neg': c_val})
                
                res = self.checker.check(relic_id, raw_slots)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(res).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

# --- CLI FUNCTION ---
def run_cli(args, checker, dictionary):
    buffs = []
    if args.buffs:
        try:
            buffs = [int(b.strip()) for b in args.buffs.split(",") if b.strip()]
        except ValueError:
            print("Error: Buff IDs must be comma-separated integers.")
            return

    curses = []
    if args.curses:
        try:
            curses = [int(c.strip()) for c in args.curses.split(",") if c.strip()]
        except ValueError:
            print("Error: Curse IDs must be comma-separated integers.")
            return

    raw_slots = []
    for i in range(4):
        b_val = buffs[i] if i < len(buffs) else 0
        c_val = curses[i] if i < len(curses) else 0
        raw_slots.append({'pos': b_val, 'neg': c_val})

    res = checker.check(0, raw_slots)
    
    def get_n(idx):
        if idx is None or idx <= 0: return "-"
        e = dictionary.get(str(idx), {})
        return e.get(args.lang, e.get('en', str(idx))) if isinstance(e, dict) else str(idx)

    print(f"\n==================== Relic Effects Legality Check ====================")
    print(f"Status: {res['status']}")
    print(f"Reason: {res['reason']}")
    print(f"Configuration Slots:")
    for idx in range(3):
        s = raw_slots[idx]
        print(f"  Slot [{idx+1}]: Buff: {get_n(s['pos'])} | Curse: {get_n(s['neg'])}")
    print(f"======================================================================\n")

# --- GUI CODE ---
class RelicSingleApp(QMainWindow):
    def __init__(self, checker, dictionary):
        super().__init__()
        self.checker = checker
        self.dict = dictionary
        self.lang_var = "zh"
        self.effect_items = []
        
        self.init_data()
        self.init_ui()
        self.populate_dropdowns()

    def init_data(self):
        # Gather all effect types (buffs & curses)
        eff_ids = set()
        if self.checker.enabled:
            for pool_set in self.checker.lottery_pools.values():
                eff_ids.update(pool_set)
            eff_ids.update(self.checker.exclusivity_map.keys())
        eff_ids.update(VALID_DEEP_DEBUFFS)
        
        # Sort effect_items by category, then by ID
        self.effect_items = sorted(list(eff_ids), key=lambda x: (self.checker.get_effect_category(x), x))

    def init_ui(self):
        self.resize(700, 390)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(10)

        # Top bar with language & title
        top_bar = QHBoxLayout()
        self.lbl_title_header = QLabel()
        self.lbl_title_header.setFont(QFont("Segoe UI Semibold", 11))
        top_bar.addWidget(self.lbl_title_header)
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

        # Slots Panel (Grid Layout)
        slots_frame = QFrame()
        slots_frame.setFrameShape(QFrame.Shape.StyledPanel)
        slots_layout = QGridLayout(slots_frame)
        slots_layout.setSpacing(8)
        slots_layout.setContentsMargins(12, 8, 12, 8)

        # Column headers
        self.lbl_col_slot = QLabel("Slot")
        self.lbl_col_slot.setFont(QFont("Segoe UI Semibold", 9))
        self.lbl_col_buff = QLabel("Buff Effect")
        self.lbl_col_buff.setFont(QFont("Segoe UI Semibold", 9))
        self.lbl_col_curse = QLabel("Curse Effect")
        self.lbl_col_curse.setFont(QFont("Segoe UI Semibold", 9))
        
        slots_layout.addWidget(self.lbl_col_slot, 0, 0)
        slots_layout.addWidget(self.lbl_col_buff, 0, 1)
        slots_layout.addWidget(self.lbl_col_curse, 0, 2)

        self.slots_ui = []
        for i in range(3):
            lbl_slot = QLabel(f"Slot {i+1}")
            lbl_slot.setFont(QFont("Segoe UI Semibold", 9))
            
            # Buff selectors
            cb_buff = QComboBox()
            cb_buff.setEditable(True)
            cb_buff.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            cb_buff.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            cb_buff.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

            # Curse selectors
            cb_curse = QComboBox()
            cb_curse.setEditable(True)
            cb_curse.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            cb_curse.completer().setFilterMode(Qt.MatchFlag.MatchContains)
            cb_curse.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

            slots_layout.addWidget(lbl_slot, i+1, 0, Qt.AlignmentFlag.AlignVCenter)
            slots_layout.addWidget(cb_buff, i+1, 1)
            slots_layout.addWidget(cb_curse, i+1, 2)

            self.slots_ui.append({
                "lbl_slot": lbl_slot,
                "cb_buff": cb_buff,
                "cb_curse": cb_curse
            })

        main_layout.addWidget(slots_frame)

        # Buttons layout
        btn_layout = QHBoxLayout()
        self.btn_check = QPushButton()
        self.btn_check.setFont(QFont("Segoe UI Semibold", 9))
        self.btn_check.setFixedHeight(32)
        self.btn_check.clicked.connect(self.verify_combination)
        btn_layout.addWidget(self.btn_check)

        self.btn_reset = QPushButton()
        self.btn_reset.setFont(QFont("Segoe UI Semibold", 9))
        self.btn_reset.setFixedHeight(32)
        self.btn_reset.clicked.connect(self.reset_inputs)
        btn_layout.addWidget(self.btn_reset)

        main_layout.addLayout(btn_layout)

        # Result Panel
        self.result_card = QFrame()
        self.result_card.setFrameShape(QFrame.Shape.StyledPanel)
        self.result_card.setLineWidth(1)
        self.result_card.setFixedHeight(95)
        
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(12, 8, 12, 8)
        result_layout.setSpacing(4)
        
        self.lbl_res_title = QLabel()
        self.lbl_res_title.setFont(QFont("Segoe UI Semibold", 9))
        result_layout.addWidget(self.lbl_res_title)

        self.lbl_res_status = QLabel()
        self.lbl_res_status.setFont(QFont("Segoe UI Bold", 11))
        result_layout.addWidget(self.lbl_res_status)

        self.lbl_res_reason = QLabel()
        self.lbl_res_reason.setFont(QFont("Segoe UI", 9))
        self.lbl_res_reason.setWordWrap(True)
        result_layout.addWidget(self.lbl_res_reason)

        main_layout.addWidget(self.result_card)

        # Default results state
        self.set_result_ui("Unknown", "Enter configuration above and click Verify.")
        self.update_labels()

    def update_labels(self):
        txt = UI_TEXT[self.lang_var]
        self.setWindowTitle(txt["title"])
        self.lbl_title_header.setText(txt["title"])
        self.lbl_lang.setText(txt["lang"])
        self.btn_check.setText(txt["check"])
        self.btn_reset.setText(txt["reset"])
        self.lbl_res_title.setText(txt["result_title"])
        
        self.lbl_col_slot.setText(txt["slot"])
        self.lbl_col_buff.setText(txt["buff"])
        self.lbl_col_curse.setText(txt["curse"])
        
        for i, ui in enumerate(self.slots_ui):
            ui["lbl_slot"].setText(f"{txt['slot']} {i+1}")

    def get_n(self, idx):
        if idx is None or idx <= 0: return "-"
        e = self.dict.get(str(idx), {})
        return e.get(self.lang_var, e.get('en', str(idx))) if isinstance(e, dict) else str(idx)

    def change_language(self, lang):
        if self.lang_var == lang: return
        self.lang_var = lang
        self.update_labels()
        self.populate_dropdowns()

    def populate_dropdowns(self):
        # Block signals to prevent events
        for ui in self.slots_ui:
            ui["cb_buff"].blockSignals(True)
            ui["cb_curse"].blockSignals(True)

        # Save active selected IDs
        active_slots = []
        for ui in self.slots_ui:
            b_idx = ui["cb_buff"].currentIndex()
            c_idx = ui["cb_curse"].currentIndex()
            active_slots.append({
                "buff": ui["cb_buff"].itemData(b_idx) if b_idx >= 0 else 0,
                "curse": ui["cb_curse"].itemData(c_idx) if c_idx >= 0 else 0
            })

        # Effects Combos
        for ui in self.slots_ui:
            ui["cb_buff"].clear()
            ui["cb_buff"].addItem(f"-- Empty / None --", 0)
            ui["cb_curse"].clear()
            ui["cb_curse"].addItem(f"-- Empty / None --", 0)
            
            for eid in self.effect_items:
                cat_lbl = f"[{self.get_cat_name(eid)}]"
                ui["cb_buff"].addItem(f"{cat_lbl} {self.get_n(eid)} ({eid})", eid)
                ui["cb_curse"].addItem(f"{cat_lbl} {self.get_n(eid)} ({eid})", eid)

        # Restore combos to match saved values
        for i, ui in enumerate(self.slots_ui):
            b_val = active_slots[i]["buff"] if active_slots[i]["buff"] is not None else 0
            idx = ui["cb_buff"].findData(b_val)
            ui["cb_buff"].setCurrentIndex(idx if idx >= 0 else 0)

            c_val = active_slots[i]["curse"] if active_slots[i]["curse"] is not None else 0
            idx = ui["cb_curse"].findData(c_val)
            ui["cb_curse"].setCurrentIndex(idx if idx >= 0 else 0)

        # Unblock signals
        for ui in self.slots_ui:
            ui["cb_buff"].blockSignals(False)
            ui["cb_curse"].blockSignals(False)

    def get_cat_name(self, eid):
        cat = self.checker.get_effect_category(eid)
        cats_trans = {
            "en": {
                0: "Ability",
                1: "Combat",
                2: "Utility",
                3: "Attribute",
                4: "Cooldown",
                5: "Attack",
                6: "Defense"
            },
            "zh": {
                0: "专属",
                1: "战斗",
                2: "辅助",
                3: "属性",
                4: "冷却",
                5: "增伤",
                6: "防护"
            }
        }
        return cats_trans[self.lang_var].get(cat, "Unknown")

    def set_result_ui(self, stat, reason):
        dark = is_dark_mode()
        
        if stat == "Illegal":
            colors = ("#3d1313", "#ff4d4d") if dark else ("#fff8f8", "#d32f2f")
            status_color = "#ff4d4d" if dark else "#d32f2f"
        elif stat == "Official":
            colors = ("#20132a", "#bb86fc") if dark else ("#faf5ff", "#7b1fa2")
            status_color = "#bb86fc" if dark else "#7b1fa2"
        elif stat == "Legal":
            colors = ("#133d1c", "#4dff77") if dark else ("#f8fff9", "#2e7d32")
            status_color = "#4dff77" if dark else "#2e7d32"
        else:
            colors = ("#1e1e1e", "#333333") if dark else ("#ffffff", "#e0e0e0")
            status_color = "#aaaaaa" if dark else "#666666"

        self.result_card.setStyleSheet(f"""
            QFrame {{
                background-color: {colors[0]};
                border: 1px solid {colors[1]};
                border-radius: 6px;
            }}
            QLabel {{
                background-color: transparent;
                color: { "#ffffff" if dark else "#000000" };
            }}
        """)
        
        self.lbl_res_status.setText(stat)
        self.lbl_res_status.setStyleSheet(f"color: {status_color}; background-color: transparent;")
        self.lbl_res_reason.setText(reason)

    def verify_combination(self):
        raw_slots = []
        for i in range(3):
            cb_b = self.slots_ui[i]["cb_buff"]
            cb_c = self.slots_ui[i]["cb_curse"]
            
            b_idx = cb_b.currentIndex()
            b_val = cb_b.itemData(b_idx) if b_idx >= 0 else 0
            if b_val is None: b_val = 0
            
            c_idx = cb_c.currentIndex()
            c_val = cb_c.itemData(c_idx) if c_idx >= 0 else 0
            if c_val is None: c_val = 0
            
            raw_slots.append({'pos': b_val, 'neg': c_val})

        # Pad slots to 4 to satisfy checker expectations
        raw_slots.append({'pos': 0, 'neg': 0})

        res = self.checker.check(0, raw_slots)
        self.set_result_ui(res["status"], res["reason"])

    def reset_inputs(self):
        for ui in self.slots_ui:
            ui["cb_buff"].setCurrentIndex(0)
            ui["cb_curse"].setCurrentIndex(0)
        self.set_result_ui("Unknown", "Enter configuration above and click Verify.")

# --- MAIN INVOCATION ---
def main():
    parser = argparse.ArgumentParser(description="Elden Ring: Nightreign Single Relic Checker")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--api", action="store_true", help="Run in API server mode")
    
    # CLI parameters
    parser.add_argument("--id", type=int, default=0, help="Relic base ID")
    parser.add_argument("--buffs", type=str, default="", help="Comma-separated positive effect IDs")
    parser.add_argument("--curses", type=str, default="", help="Comma-separated negative effect IDs")
    parser.add_argument("--lang", choices=['zh', 'en'], default="zh", help="Output language for CLI ('zh' or 'en')")
    
    # Server parameters
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    
    # Global parameters
    parser.add_argument("--dict", default="dictionary.json", help="Path to dictionary.json")
    parser.add_argument("--data-dir", default=".", help="Path to directory containing game parameter CSVs")
    
    args = parser.parse_args()

    # Load legality checker
    checker = RelicLegalityChecker(data_dir=args.data_dir)
    dictionary = json.load(open(args.dict, 'r', encoding='utf-8')) if os.path.exists(args.dict) else {}

    if args.api:
        # Start API server
        RelicVerificationHandler.checker = checker
        server_address = ('', args.port)
        httpd = HTTPServer(server_address, RelicVerificationHandler)
        print(f"Relic Legality API Service running on port {args.port}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down API server.")
            httpd.server_close()
            
    elif args.cli:
        # Run in CLI verification mode
        run_cli(args, checker, dictionary)
        
    else:
        # Run in GUI mode (Default)
        app = QApplication(sys.argv)
        app.setFont(QFont("Segoe UI", 9))
        window = RelicSingleApp(checker, dictionary)
        window.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
