import argparse
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

# --- LEGALITY ENGINE ---
class RelicLegalityChecker:
    def __init__(self, data_dir: str = "."):
        self.enabled = False
        self.official_map = {}
        
        # Load Official Relics
        off_file = os.path.join(data_dir, "official_relics.csv")
        if os.path.exists(off_file):
            try:
                df = pd.read_csv(off_file)
                for _, row in df.iterrows():
                    effs = [int(row['Effect_1']), int(row['Effect_2']), int(row['Effect_3'])]
                    self.official_map[int(row['Base_ID'])] = sorted([e for e in effs if e > 0])
            except Exception as e:
                print(f"[WARN] Failed to load official_relics.csv: {e}")

        # Load Game Params
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
        # 1. Official Relic Check
        if item_id in self.official_map:
            active_pos = sorted([s['pos'] for s in raw_slots if s['pos'] > 0])
            active_neg = [s['neg'] for s in raw_slots if s['neg'] > 0]
            
            if active_pos == self.official_map[item_id] and len(active_neg) == 0:
                return "Official", "Matches System Preset"
            else:
                return "Illegal", "Modified Official Relic (Invalid effects or debuff injected)"

        if not self.enabled: return "Unknown", "Missing Params"
        
        # 2. Random Relic Metadata Lookup
        rules = self.equip_param.loc[item_id] if item_id in self.equip_param.index else None
        if rules is None:
            for r in self.pool1_map:
                if raw_slots[0]['pos'] > 0 and raw_slots[0]['pos'] in self.lottery_pools.get(r['attachEffectTableId_1'], set()):
                    rules = r; break
        
        if rules is None: return "Illegal", f"No rule metadata for type {item_id}"

        buff_pools = [int(rules[f"attachEffectTableId_{i}"]) for i in [1, 2, 3] if int(rules[f"attachEffectTableId_{i}"]) > 0]
        curse_pools = [int(rules[f"attachEffectTableId_curse{i}"]) for i in [1, 2, 3] if int(rules[f"attachEffectTableId_curse{i}"]) > 0]
        is_deep = int(rules.get("isDeepRelic", 0)) == 1
        
        pos_ids = [s['pos'] for s in raw_slots[:3] if s['pos'] > 0]
        neg_ids = [s['neg'] for s in raw_slots[:3] if s['neg'] > 0]
        
        # Immediate Fail Checks
        if raw_slots[3]['pos'] > 0 or raw_slots[3]['neg'] > 0:
            return "Illegal", "Slot 4 must be empty"

        if len(neg_ids) != len(set(neg_ids)):
            return "Illegal", "Duplicate debuff IDs"

        if len(pos_ids) > len(buff_pools):
            return "Illegal", "Too many positive effects for this item tier"

        # --- UNIFIED POOL MATCHING (Accounts for RNG Fallbacks) ---
        allowed_pos_effects = set()
        for pool in buff_pools:
            allowed_pos_effects.update(self.lottery_pools.get(pool, set()))
            
        for pos in pos_ids:
            if pos not in allowed_pos_effects:
                return "Illegal", f"Buff {pos} cannot roll on this Relic tier/color."

        # --- DEBUFF CHECKS ---
        if is_deep:
            for neg in neg_ids:
                if neg not in VALID_DEEP_DEBUFFS:
                    return "Illegal", f"Invalid Deep Relic Curse: {neg}"
        else:
            if len(neg_ids) > len(curse_pools):
                return "Illegal", "Too many debuff effects for this item tier"
                
            allowed_neg_effects = set()
            for pool in curse_pools:
                allowed_neg_effects.update(self.lottery_pools.get(pool, set()))
                
            for neg in neg_ids:
                if neg not in allowed_neg_effects:
                    return "Illegal", f"Debuff {neg} cannot roll on this Relic tier/color."

        # 3. Exclusivity Check (Prevents Stacking God Rolls)
        seen = set()
        for eid in pos_ids + neg_ids:
            g = self.exclusivity_map.get(eid, -1)
            if g != -1:
                if g in seen: return "Illegal", "Exclusivity Conflict (Stacking duplicate effect types)"
                seen.add(g)
                
        return "Legal", "Verified"

# --- UTILS ---
def decrypt_data(data, key, iv):
    c = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    d = c.decryptor()
    return d.update(data) + d.finalize()

def read_int_le(data):
    v = 0
    for i, b in enumerate(data): v |= b << (8 * i)
    return v - 0x100000000 if len(data) == 4 and (v & 0x80000000) else v

def parse_bnd4_entry(path, idx):
    with open(path, 'rb') as f:
        f.seek(12); count = struct.unpack('<I', f.read(4))[0]
        f.seek(64)
        for i in range(count):
            h = f.read(32)
            if i == idx:
                sz, off = struct.unpack('<I', h[8:12])[0], struct.unpack('<I', h[16:20])[0]
                f.seek(off); return f.read(sz)
    return None

# --- MAIN EXECUTION ---
def main():
    parser = argparse.ArgumentParser(description="Elden Ring: Nightreign Offline Relic Checker")
    parser.add_argument("sl2_file", help="Path to your .sl2 save file")
    parser.add_argument("--dict", default="dictionary.json", help="Path to dictionary.json")
    parser.add_argument("--lang", choices=['zh', 'en'], default="zh", help="Language for output (zh or en)")
    parser.add_argument("--illegal-only", action="store_true", help="Only display illegal relics")
    args = parser.parse_args()

    checker = RelicLegalityChecker()
    dictionary = json.load(open(args.dict, 'r', encoding='utf-8')) if os.path.exists(args.dict) else {}

    def get_n(idx):
        if idx is None or idx <= 0: return "-"
        e = dictionary.get(str(idx), {})
        return e.get(args.lang, e.get('en', str(idx))) if isinstance(e, dict) else str(idx)

    print("Decrypting Save File...")
    e10 = parse_bnd4_entry(args.sl2_file, 10)
    if not e10: 
        print("Failed to read save file or Entry #10 not found.")
        return
        
    name_data = decrypt_data(e10[16:], AES_KEY, e10[:16])[4:]
    
    i = 0
    slots = []
    while True:
        pos = name_data.find(FACE_ANCHOR, i)
        if pos == -1: break
        i = pos + 7
        n_b = name_data[max(0, pos-51):name_data.find(b'\x00\x00', max(0, pos-51))+2]
        if len(n_b) % 2 != 0: n_b = n_b[:-1]
        slots.append((n_b.decode('utf-16le').strip('\x00'), n_b))

    for idx, (name, n_b) in enumerate(slots):
        raw = parse_bnd4_entry(args.sl2_file, idx)
        if not raw: continue
        dec = decrypt_data(raw[16:], AES_KEY, raw[:16])[4:]
        n_pos = dec.find(n_b)
        if n_pos == -1: continue
        
        ffff = dec.find(BLOCK_END_MARKER, n_pos+1000)
        off = 32
        relics_found = []
        while off < n_pos - 100:
            if dec[off+2] in VALID_BYTE2 and dec[off+3] in VALID_BYTE3:
                sz = 72 if dec[off+3] == 192 else (16 if dec[off+3] == 144 else 80)
                if off + sz <= len(dec) and dec[off+3] == 192:
                    chunk = dec[off:off+sz]
                    raw_s = [{'pos': read_int_le(chunk[16+j*4:20+j*4]), 'neg': read_int_le(chunk[56+j*4:60+j*4])} for j in range(4)]
                    if dec.find(chunk[0:4] + b'\x01\x00\x00\x00', ffff) != -1:
                        status, reason = checker.check(read_int_le(chunk[4:7]), raw_s)
                        if not args.illegal_only or status == "Illegal":
                            relics_found.append({
                                'type': read_int_le(chunk[4:7]), 
                                'slots': raw_s, 
                                'status': status, 
                                'reason': reason
                            })
                off += sz or 1
            else: off += 8 if (dec[off:off+4] == b'\x00'*4 and dec[off+4:off+8] == b'\xff'*4) else 1
            
        if relics_found:
            print(f"\n{'='*20} Character: {name} (Slot {idx}) {'='*20}")
            for r in relics_found:
                print(f"Relic Type: {get_n(r['type'])}")
                print(f"Status: {r['status']} ({r['reason']})")
                for s_idx, s in enumerate(r['slots']):
                    if s['pos'] > 0 or s['neg'] > 0:
                        print(f"  [{s_idx+1}] {get_n(s['pos'])} | {get_n(s['neg'])}")
                print("-" * 40)

if __name__ == "__main__":
    main()