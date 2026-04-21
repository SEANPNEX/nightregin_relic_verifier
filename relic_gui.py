import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import struct
import pandas as pd
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
        "slot": "Slot"
    },
    "zh": {
        "title": "Nightreign 遗物合法性查询工具",
        "load": "加载 .sl2 存档",
        "show_illegal": "只显示不合法",
        "lang": "语言:",
        "status": "状态",
        "no_relics": "未发现遗物。",
        "no_illegal": "未发现不合法遗物。",
        "slot": "角色槽位"
    }
}

# --- BACKEND LOGIC ---
class RelicLegalityChecker:
    def __init__(self, data_dir: str = "."):
        self.enabled = False
        self.official_map = {}
        
        # Load official whitelist
        off_file = os.path.join(data_dir, "official_relics.csv")
        if os.path.exists(off_file):
            try:
                df = pd.read_csv(off_file)
                for _, row in df.iterrows():
                    effs = [int(row['Effect_1']), int(row['Effect_2']), int(row['Effect_3'])]
                    self.official_map[int(row['Base_ID'])] = sorted([e for e in effs if e > 0])
            except Exception as e:
                print(f"[WARN] Failed to load official_relics.csv: {e}")

        # Load game parameters
        files = ["EquipParamAntique.csv", "AttachEffectTableParam.csv", "AttachEffectParam.csv"]
        if all(os.path.exists(os.path.join(data_dir, f)) for f in files):
            try:
                self.equip_param = pd.read_csv("EquipParamAntique.csv", usecols=[
                    "ID", "attachEffectTableId_1", "attachEffectTableId_2", "attachEffectTableId_3",
                    "attachEffectTableId_curse1", "attachEffectTableId_curse2", "attachEffectTableId_curse3", "isDeepRelic"
                ])
                self.equip_param.columns = self.equip_param.columns.str.strip()
                self.equip_param = self.equip_param.set_index("ID").fillna(-1).apply(pd.to_numeric, errors='coerce').fillna(-1).astype(int)
                
                self.pool1_map = self.equip_param.reset_index().to_dict('records')
                self.lottery_pools = pd.read_csv("AttachEffectTableParam.csv", usecols=["ID", "attachEffectId"]).apply(pd.to_numeric, errors='coerce').fillna(-1).astype(int).groupby("ID")["attachEffectId"].apply(set).to_dict()
                self.exclusivity_map = pd.read_csv("AttachEffectParam.csv", usecols=["ID", "exclusivityId"]).set_index("ID").apply(pd.to_numeric, errors='coerce').fillna(-1).astype(int)["exclusivityId"].to_dict()
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
        rules = self.equip_param.loc[item_id] if item_id in self.equip_param.index else None
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
        f.seek(12); count = struct.unpack('<I', f.read(4))[0]
        entries = []
        f.seek(64)
        for _ in range(count):
            h = f.read(32); entries.append({'size': struct.unpack('<I', h[8:12])[0], 'off': struct.unpack('<I', h[16:20])[0]})

    with open(file_path, 'rb') as f:
        f.seek(entries[10]['off'])
        e10_data = f.read(entries[10]['size'])
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
        with open(file_path, 'rb') as f:
            f.seek(entries[slot_idx]['off'])
            slot_raw = f.read(entries[slot_idx]['size'])
            dec = decrypt_data(slot_raw[16:], AES_KEY, slot_raw[:16])[4:]
        
        relics = []
        n_pos = dec.find(n_b)
        if n_pos != -1:
            ffff = dec.find(BLOCK_END_MARKER, n_pos+1000)
            off = 32
            while off < n_pos - 100:
                if dec[off+2] in VALID_BYTE2 and dec[off+3] in VALID_BYTE3:
                    sz = 72 if dec[off+3] == 192 else (16 if dec[off+3] == 144 else 80)
                    if off + sz <= len(dec) and dec[off+3] == 192:
                        chunk = dec[off:off+sz]
                        raw_slots = []
                        for j in range(4): raw_slots.append({'pos': read_int_le(chunk[16+j*4:20+j*4]), 'neg': read_int_le(chunk[56+j*4:60+j*4])})
                        if dec.find(chunk[0:4] + b'\x01\x00\x00\x00', ffff) != -1:
                            item_id = read_int_le(chunk[4:7])
                            relics.append({'id': item_id, 'slots': raw_slots, 'legality': checker.check(item_id, raw_slots)})
                    off += sz or 1
                else: off += 8 if (dec[off:off+4] == b'\x00'*4 and dec[off+4:off+8] == b'\xff'*4) else 1
        results.append({'name': char_name, 'relics': relics})
    return results

# --- UI APPLICATION ---
class RelicApp:
    def __init__(self, root):
        self.root = root
        self.checker = RelicLegalityChecker()
        self.dict = json.load(open('dictionary.json', 'r', encoding='utf-8')) if os.path.exists('dictionary.json') else {}
        self.data = []
        self.lang_var = tk.StringVar(value="zh")
        
        top = ttk.Frame(root, padding=10); top.pack(fill=tk.X)
        self.btn_load = ttk.Button(top, text="", command=self.load_file); self.btn_load.pack(side=tk.LEFT)
        self.char_selector = ttk.Combobox(top, state="readonly", width=22); self.char_selector.pack(side=tk.LEFT, padx=10)
        self.char_selector.bind("<<ComboboxSelected>>", self.display_relics)
        self.show_illegal_only = tk.BooleanVar(value=False)
        self.check_illegal = ttk.Checkbutton(top, text="", variable=self.show_illegal_only, command=self.display_relics); self.check_illegal.pack(side=tk.LEFT, padx=5)
        self.lbl_lang = ttk.Label(top, text="")
        self.lbl_lang.pack(side=tk.LEFT, padx=(10, 2))
        ttk.Radiobutton(top, text="ZH", value="zh", variable=self.lang_var, command=self.change_language).pack(side=tk.LEFT)
        ttk.Radiobutton(top, text="EN", value="en", variable=self.lang_var, command=self.change_language).pack(side=tk.LEFT)
        
        self.canvas = tk.Canvas(root, background="#f8f8f8")
        self.scroll = ttk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.grid_frame = tk.Frame(self.canvas, background="#f8f8f8")
        self.grid_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.update_ui_labels()

    def change_language(self):
        self.update_ui_labels()
        if self.data:
            current = self.char_selector.current()
            self.char_selector['values'] = [f"{UI_TEXT[self.lang_var.get()]['slot']} {i}: {c['name']}" for i, c in enumerate(self.data)]
            if current >= 0: self.char_selector.current(current)
            self.display_relics()

    def update_ui_labels(self):
        txt = UI_TEXT[self.lang_var.get()]
        self.root.title(txt["title"])
        self.btn_load.config(text=txt["load"])
        self.check_illegal.config(text=txt["show_illegal"])
        self.lbl_lang.config(text=txt["lang"])

    def get_n(self, idx):
        if idx is None or idx <= 0: return "-"
        lang = self.lang_var.get()
        e = self.dict.get(str(idx), {})
        return e.get(lang, e.get('en', str(idx))) if isinstance(e, dict) else str(idx)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Save Files", "*.sl2")])
        if path:
            try:
                self.data = parse_save(path, self.checker)
                self.change_language() 
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse: {e}")

    def display_relics(self, event=None):
        for w in self.grid_frame.winfo_children(): w.destroy()
        sel = self.char_selector.current()
        if sel < 0: return
        relics = self.data[sel]['relics']
        txt = UI_TEXT[self.lang_var.get()]
        if self.show_illegal_only.get(): relics = [r for r in relics if r['legality']['status'] == "Illegal"]
        
        if not relics:
            tk.Label(self.grid_frame, text=txt["no_illegal"] if self.show_illegal_only.get() else txt["no_relics"], background="#f8f8f8", font=("Arial", 12)).pack(pady=40)
            return

        for i, r in enumerate(relics):
            stat = r['legality']['status']
            # Color Coding: Red = Illegal, Purple = Official, White/Gray = Legal Random Relic
            colors = {"Illegal": ("#ffebee", "#f44336"), "Official": ("#f3e5f5", "#9c27b0")}.get(stat, ("white", "#e0e0e0"))
            frame = tk.Frame(self.grid_frame, bg=colors[0], highlightbackground=colors[1], highlightthickness=2, padx=10, pady=10)
            frame.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            
            tk.Label(frame, text=self.get_n(r['id']), font=("Arial", 10, "bold"), bg=colors[0], wraplength=250, justify=tk.LEFT).pack(anchor="w")
            tk.Label(frame, text=f"{txt['status']}: {stat}" + (f" ({r['legality']['reason']})" if stat == "Illegal" else ""), fg=colors[1], bg=colors[0], font=("Arial", 8, "italic"), wraplength=250, justify=tk.LEFT).pack(anchor="w")
            tk.Frame(frame, height=1, bg="#bdbdbd").pack(fill=tk.X, pady=5)
            
            for idx, s in enumerate(r['slots']):
                if s['pos'] > 0 or s['neg'] > 0:
                    tk.Label(frame, text=f"[{idx+1}] {self.get_n(s['pos'])}\n    ↳ {self.get_n(s['neg'])}", bg=colors[0], font=("Arial", 8), justify=tk.LEFT, wraplength=250).pack(anchor="w", pady=2)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x700")  # Set a nice default window size
    app = RelicApp(root)
    root.mainloop()