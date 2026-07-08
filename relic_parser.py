import argparse
import json
import os
import struct
import csv
import sys
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
        self.equip_param = {}
        self.pool1_map = []
        self.lottery_pools = {}
        self.exclusivity_map = {}
        self.compatibility_map = {}
        self.enforce_order_check = True
        
        # Path resolver helper supporting PyInstaller _MEIPASS fallback
        def get_path(filename):
            p = os.path.join(data_dir, filename)
            if not os.path.exists(p):
                try:
                    p = os.path.join(sys._MEIPASS, filename)
                except Exception:
                    pass
            return p

        # Load translation dictionary for category/order detection
        dict_path = get_path("dictionary.json")
        self.dictionary = {}
        if os.path.exists(dict_path):
            try:
                with open(dict_path, 'r', encoding='utf-8') as f:
                    self.dictionary = json.load(f)
            except Exception:
                pass

        # Load relic_list.csv rules
        self.relic_rules = {}
        relic_list_file = get_path("relic_list.csv")
        if os.path.exists(relic_list_file):
            try:
                with open(relic_list_file, 'r', encoding='gb18030') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        eid = int(row['ID'])
                        self.relic_rules[eid] = {
                            'ID': eid,
                            'Name': row.get('Name', ''),
                            'requiresDebuff': int(row.get('requiresDebuff', 0) or 0),
                            'isDebuff': int(row.get('isDebuff', 0) or 0),
                            'overrideBaseEffectId': int(row.get('overrideBaseEffectId', -1) or -1),
                            'compatibilityId': int(row.get('compatibilityId', -1) or -1),
                            'canAppearNormal': int(row.get('canAppearNormal', 0) or 0),
                            'canAppearDeep': int(row.get('canAppearDeep', 0) or 0)
                        }
                # Update global VALID_DEEP_DEBUFFS dynamically
                global VALID_DEEP_DEBUFFS
                VALID_DEEP_DEBUFFS.clear()
                for r in self.relic_rules.values():
                    if r['isDebuff'] == 1:
                        VALID_DEEP_DEBUFFS.add(r['ID'])
            except Exception as e:
                print(f"[WARN] Failed to load relic_list.csv: {e}")

        # Load Official Relics
        off_file = get_path("official_relics.csv")
        if os.path.exists(off_file):
            try:
                with open(off_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        effs = [int(row['Effect_1']), int(row['Effect_2']), int(row['Effect_3'])]
                        self.official_map[int(row['Base_ID'])] = sorted([e for e in effs if e > 0])
            except Exception as e:
                print(f"[WARN] Failed to load official_relics.csv: {e}")

        # Load Game Params
        equip_file = get_path("EquipParamAntique.csv")
        table_file = get_path("AttachEffectTableParam.csv")
        param_file = get_path("AttachEffectParam.csv")
        
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

                # Load AttachEffectParam (Exclusivity & Compatibility)
                with open(param_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        eid = int(row['ID'])
                        comp_id = int(row.get('compatibilityId', -1) or -1)
                        ex_id = int(row.get('exclusivityId', -1) or -1)
                        
                        group_id = comp_id if comp_id > 0 else (ex_id if ex_id > 0 else -1)
                        if group_id > 0:
                            self.exclusivity_map[eid] = group_id
                            
                        if comp_id > 0:
                            self.compatibility_map[eid] = comp_id
                
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
        if item_id in self.equip_param:
            return self._check_with_rule(self.equip_param[item_id], raw_slots)

        active_pos_count = sum(1 for s in raw_slots[:3] if s['pos'] > 0)
        active_neg_count = sum(1 for s in raw_slots[:3] if s['neg'] > 0)
        
        # Find candidates matching the first buff and having enough slots
        candidates = []
        for r in self.pool1_map:
            buff_pools_count = sum(1 for i in [1, 2, 3] if int(r.get(f"attachEffectTableId_{i}", -1)) > 0)
            curse_pools_count = sum(1 for i in [1, 2, 3] if int(r.get(f"attachEffectTableId_curse{i}", -1)) > 0)
            is_deep_relic = int(r.get("isDeepRelic", 0)) == 1
            curses_fit = is_deep_relic or (curse_pools_count >= active_neg_count)
            
            if buff_pools_count >= active_pos_count and curses_fit:
                if raw_slots[0]['pos'] > 0 and raw_slots[0]['pos'] in self.lottery_pools.get(r['attachEffectTableId_1'], set()):
                    candidates.append(r)
                    
        if not candidates:
            # Fall back to first matching rule if no perfect fit was found
            for r in self.pool1_map:
                if raw_slots[0]['pos'] > 0 and raw_slots[0]['pos'] in self.lottery_pools.get(r['attachEffectTableId_1'], set()):
                    candidates.append(r)
                    
        if not candidates:
            return {"status": "Illegal", "reason": f"No rule metadata for type {item_id}"}
            
        best_res = None
        for r in candidates:
            res = self._check_with_rule(r, raw_slots)
            if res["status"] in ["Legal", "Official"]:
                return res
            best_res = res
            
        return best_res

    def _check_with_rule(self, rules, raw_slots):
        buff_pools = [int(rules[f"attachEffectTableId_{i}"]) for i in [1, 2, 3] if int(rules[f"attachEffectTableId_{i}"]) > 0]
        curse_pools = [int(rules[f"attachEffectTableId_curse{i}"]) for i in [1, 2, 3] if int(rules[f"attachEffectTableId_curse{i}"]) > 0]
        pos_ids = [s['pos'] for s in raw_slots[:3] if s['pos'] > 0]
        neg_ids = [s['neg'] for s in raw_slots[:3] if s['neg'] > 0]

        is_deep = (int(rules.get("isDeepRelic", 0)) == 1) or (len(neg_ids) > 0)
        if not is_deep:
            for pos in pos_ids:
                pos_rule = self.relic_rules.get(pos)
                if pos_rule and pos_rule.get('canAppearDeep', 0) == 1 and pos_rule.get('canAppearNormal', 0) == 0:
                    is_deep = True
                    break
        
        # Check Slot 4 (Must always be empty)
        if raw_slots[3]['pos'] > 0 or raw_slots[3]['neg'] > 0:
            return {"status": "Illegal", "reason": "Slot 4 must be empty"}

        # Duplicate Buff check
        if len(pos_ids) != len(set(pos_ids)):
            return {"status": "Illegal", "reason": "Exclusivity Conflict (Stacking duplicate effect types)"}

        # Duplicate Debuff check
        if len(neg_ids) != len(set(neg_ids)):
            return {"status": "Illegal", "reason": "Duplicate debuff IDs"}

        # --- DEBUFF CHECKS ---
        if not is_deep and len(neg_ids) > 0:
            return {"status": "Illegal", "reason": "Only deep relics can have negative effects"}

        # Slot-by-slot positive/negative pairing check
        for i, slot in enumerate(raw_slots[:3]):
            pos = slot['pos']
            neg = slot['neg']
            if pos > 0:
                pos_rule = self.relic_rules.get(pos)
                if pos_rule and pos_rule['isDebuff'] == 1:
                    return {"status": "Illegal", "reason": "Curse cannot be placed in a positive slot"}
                req_debuff = pos_rule['requiresDebuff'] if pos_rule else 0
                can_pair = (req_debuff == 1) or (pos in (7000090, 7120900))
                if req_debuff == 1:
                    if neg <= 0:
                        return {"status": "Illegal", "reason": f"Buff {pos} in slot {i+1} must be paired with a curse"}
                if neg > 0 and not can_pair:
                    return {"status": "Illegal", "reason": f"Buff {pos} in slot {i+1} cannot be paired with a curse"}
            else:
                if neg > 0:
                    return {"status": "Illegal", "reason": f"Slot {i+1} cannot have a curse without a positive effect"}

        for neg in neg_ids:
            if neg not in VALID_DEEP_DEBUFFS:
                return {"status": "Illegal", "reason": f"Invalid Deep Relic Curse: {neg}"}

        # 3. Exclusivity: Relic effects with the same compatibilityId cannot be in the same relic
        seen = set()
        for eid in pos_ids + neg_ids:
            rule = self.relic_rules.get(eid)
            if rule:
                compat_id = rule['compatibilityId']
                if compat_id != -1:
                    if compat_id in seen:
                        return {"status": "Illegal", "reason": "Exclusivity Conflict (Stacking duplicate effect types)"}
                    seen.add(compat_id)
                
        # 4. Sorting Order Check: Order by overrideBaseEffectId first, then by ID (Excluding presets/saves if enforce_order_check is disabled)
        if is_deep and getattr(self, 'enforce_order_check', True):
            keys = []
            for pid in pos_ids:
                keys.append((self.get_override_base_effect_id(pid), pid))
            for idx in range(len(keys) - 1):
                if keys[idx] > keys[idx + 1]:
                    sorted_pos_ids = sorted(pos_ids, key=lambda pid: (self.get_override_base_effect_id(pid), pid))
                    correct_names = []
                    for pid in sorted_pos_ids:
                        rule = self.relic_rules.get(pid)
                        name = rule['Name'] if rule else str(pid)
                        correct_names.append(f"{name} ({pid})")
                    return {"status": "Illegal", "reason": f"Wrong order of possitive effect. Correct: {', '.join(correct_names)}"}

        return {"status": "Legal", "reason": "Verified"}

    def get_override_base_effect_id(self, eid):
        rule = self.relic_rules.get(eid)
        if rule:
            return rule['overrideBaseEffectId']
        return -1

    def get_effect_category(self, eid):
        return self.get_override_base_effect_id(eid)

    def get_effect_sub_category(self, eid):
        return self.get_override_base_effect_id(eid)



# --- UTILS ---
def decrypt_data(data, key, iv):
    c = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    d = c.decryptor()
    return d.update(data) + d.finalize()

def read_int_le(data):
    v = 0
    for i, b in enumerate(data): v |= b << (8 * i)
    return v - 0x100000000 if len(data) == 4 and (v & 0x80000000) else v

def parse_save(file_path, checker):
    checker.enforce_order_check = False
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
    try:
        results = parse_save(args.sl2_file, checker)
    except Exception as e:
        print(f"Failed to read save file or decrypt entries: {e}")
        return

    for idx, char_data in enumerate(results):
        relics_found = char_data['relics']
        if args.illegal_only:
            relics_found = [r for r in relics_found if r['legality']['status'] == "Illegal"]
            
        if relics_found:
            print(f"\n{'='*20} Character: {char_data['name']} (Slot {idx}) {'='*20}")
            for r in relics_found:
                print(f"Relic Type: {get_n(r['id'])}")
                print(f"Status: {r['legality']['status']} ({r['legality']['reason']})")
                for s_idx, s in enumerate(r['slots']):
                    if s['pos'] > 0 or s['neg'] > 0:
                        print(f"  [{s_idx+1}] {get_n(s['pos'])} | {get_n(s['neg'])}")
                print("-" * 40)

if __name__ == "__main__":
    main()