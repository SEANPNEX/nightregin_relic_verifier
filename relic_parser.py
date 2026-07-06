import argparse
import json
import os
import struct
import csv
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
        
        # Load translation dictionary for category/order detection
        dict_path = os.path.join(data_dir, "dictionary.json") if os.path.exists(os.path.join(data_dir, "dictionary.json")) else "dictionary.json"
        self.dictionary = {}
        if os.path.exists(dict_path):
            try:
                with open(dict_path, 'r', encoding='utf-8') as f:
                    self.dictionary = json.load(f)
            except Exception:
                pass

        # Load Official Relics
        off_file = os.path.join(data_dir, "official_relics.csv")
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
        equip_file = os.path.join(data_dir, "EquipParamAntique.csv")
        table_file = os.path.join(data_dir, "AttachEffectTableParam.csv")
        param_file = os.path.join(data_dir, "AttachEffectParam.csv")
        
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
        is_deep = int(rules.get("isDeepRelic", 0)) == 1
        
        pos_ids = [s['pos'] for s in raw_slots[:3] if s['pos'] > 0]
        neg_ids = [s['neg'] for s in raw_slots[:3] if s['neg'] > 0]
        
        # Check Slot 4 (Must always be empty)
        if raw_slots[3]['pos'] > 0 or raw_slots[3]['neg'] > 0:
            return {"status": "Illegal", "reason": "Slot 4 must be empty"}

        # Duplicate Buff check
        if len(pos_ids) != len(set(pos_ids)):
            return {"status": "Illegal", "reason": "Exclusivity Conflict (Stacking duplicate effect types)"}

        # Duplicate Debuff check
        if len(neg_ids) != len(set(neg_ids)):
            return {"status": "Illegal", "reason": "Duplicate debuff IDs"}

        if len(pos_ids) > len(buff_pools):
            return {"status": "Illegal", "reason": "Too many positive effects for this item tier"}

        # --- UNIFIED POOL MATCHING (Accounts for RNG Fallbacks) ---
        allowed_pos_compat = set()
        for pool in buff_pools:
            for eid in self.lottery_pools.get(pool, set()):
                allowed_pos_compat.add(self.compatibility_map.get(eid, eid))
            
        for pos in pos_ids:
            pos_compat = self.compatibility_map.get(pos, pos)
            if pos_compat not in allowed_pos_compat:
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
                
        # 4. Category Order Check (Excluding presets/saves if enforce_order_check is disabled)
        if getattr(self, 'enforce_order_check', True):
            cats = [self.get_effect_category(pid) for pid in pos_ids]
            norm_cats = [1 if c == 0 else c for c in cats]
            for idx in range(len(norm_cats) - 1):
                if norm_cats[idx] > norm_cats[idx + 1]:
                    return {"status": "Illegal", "reason": "Illegal (Negative effects are not in the correct game order)"}

        return {"status": "Legal", "reason": "Verified"}

    def get_effect_category(self, eid):
        e = self.dictionary.get(str(eid)) if hasattr(self, 'dictionary') and self.dictionary else None
        if e and "category" in e:
            return e["category"]
        return self._classify_inline(eid)

    def get_effect_sub_category(self, eid):
        e = self.dictionary.get(str(eid)) if hasattr(self, 'dictionary') and self.dictionary else None
        if e and "sub_category" in e:
            return e["sub_category"]
        return self._classify_sub_inline(eid)

    def _classify_sub_inline(self, eid):
        e = self.dictionary.get(str(eid), {}) if hasattr(self, 'dictionary') and self.dictionary else {}
        en = e.get('en', '')
        zh = e.get('zh', '')
        
        char_en = ['[Revenant]', '[Recluse]', '[Wylder]', '[Ironeye]', '[Duchess]', '[Executor]', '[Guardian]', '[Raider]']
        char_zh = ['【复仇者】', '【隐士】', '【追踪者】', '【铁之眼】', '【女爵】', '【守护者】', '【执行者】', '【学者】', '【无赖】', '【送葬者】']
        if any(x in en for x in char_en) or any(x in zh for x in char_zh) or eid == 7220000:
            return 1

        if eid < 7000000 or eid > 7400000:
            return 999

        # 3武器
        if 7080000 <= eid <= 7082300:
            return 2
        if 7082500 <= eid <= 7082600:
            return 3
        if 7082700 <= eid <= 7082900:
            return 4

        # Weapon specific Attack Power
        if '提升' in zh and '攻击力' in zh and any(w in zh for w in ['短剑', '直剑', '大剑', '特大剑', '曲剑', '大曲剑', '刀', '双头剑', '刺剑', '重刺剑', '斧', '大斧', '槌', '大槌', '连枷', '矛', '大矛', '戟', '镰刀', '拳套', '钩爪', '软鞭', '特大型武器', '弓']):
            return 6
        if 7330000 <= eid <= 7339900:
            return 6

        # Weapon specific HP recovery
        if ('攻击' in zh or '命中' in zh) and ('恢复HP' in zh or '恢复血量' in zh or '部分恢复' in zh) and any(w in zh for w in ['短剑', '直剑', '大剑', '特大剑', '曲剑', '大曲剑', '刀', '双头剑', '刺剑', '重刺剑', '斧', '大斧', '槌', '大槌', '连枷', '矛', '大矛', '戟', '镰刀', '拳套', '钩爪', '软鞭', '特大型武器', '弓']):
            return 7
        if 7340000 <= eid <= 7349900:
            return 7

        # Weapon specific FP recovery
        if ('攻击' in zh or '命中' in zh) and ('恢复专注' in zh or '恢复蓝' in zh) and any(w in zh for w in ['短剑', '直剑', '大剑', '特大剑', '曲剑', '大曲剑', '刀', '双头剑', '刺剑', '重刺剑', '斧', '大斧', '槌', '大槌', '连枷', '矛', '大矛', '戟', '镰刀', '拳套', '钩爪', '软鞭', '特大型武器', '弓']):
            return 8
        if 7350000 <= eid <= 7359900:
            return 8

        # Recover HP on hit general
        if eid in (7005600, 7001100, 7030200, 7036100, 7090300):
            return 5

        # Hands/Stance
        if eid in (7006000, 7006001):
            return 10
        if eid in (7006100, 7006101):
            return 11

        # Item heal allies
        if eid == 7010200:
            return 12

        # Low health heal / defense
        if eid in (7012200, 7012300):
            return 13

        # Aggressive/Defensive
        if eid == 7030600:
            return 14
        if eid == 7030000 or eid == 7030700:
            return 15
        if eid == 7030800:
            return 16

        # Grease
        if eid == 7030900:
            return 17

        # Receive attack
        if eid == 7032200:
            return 18

        # Critical recovery stamina
        if eid == 7035100:
            return 19

        # Enhance light/critical/throwables
        if 7040000 <= eid <= 7043100:
            return 20

        # Spells
        if 7043200 <= eid <= 7043800:
            return 21
        if 7044000 <= eid <= 7044600:
            return 22

        # Ally buffs
        if eid == 7050000:
            return 23
        if eid == 7050100:
            return 24

        # Rise/Invader
        if eid == 7060000:
            return 25
        if eid == 7060100:
            return 26
        if eid == 7060200:
            return 27

        # Treasure / discovery
        if eid == 7070000 or '潜在能力' in zh or 'DormantPower' in en:
            return 28

        # Kill rewards
        if eid == 7090000:
            return 29
        if eid == 7090100:
            return 30

        # Attack recovery stamina
        if 7100100 <= eid <= 7100110:
            return 31

        # Runes
        if eid == 7110000:
            return 32

        # Spawn with items & skills
        if 7120000 <= eid <= 7126002:
            return 34

        # Spawn with skills (incant/magic overrides)
        if 7360000 <= eid <= 7379900:
            return 35
        if '改为' in zh:
            return 35

        # Counter counter
        if eid == 7150000:
            return 36

        # Pierce counter
        if eid == 7160000:
            return 37

        # Shop discount
        if 7230000 <= eid <= 7230001:
            return 38

        # Poise/Reduction on hit
        if eid == 7240000:
            return 39

        # Status attack power
        if eid == 7037700 or (7260000 <= eid <= 7269900):
            return 40

        # Runes on critical
        if eid == 7031900:
            return 41

        # Attributes (Vigor/Mind/Endurance)
        if 7000000 <= eid <= 7000290:
            return 42

        # Attributes (Strength/Dex/Int/Faith/Arcane)
        if 7000300 <= eid <= 7000702:
            return 43

        # Cooldowns
        if 7000800 <= eid <= 7000802:
            return 44

        # Ultimate
        if 7000900 <= eid <= 7000902:
            return 45

        # Poise
        if 7001000 <= eid <= 7001002:
            return 46

        # Elements AP
        if 7001400 <= eid <= 7001802:
            return 47

        # Elements Def
        if 7002600 <= eid <= 7002900:
            return 48

        # Resistances
        if 7003000 <= eid <= 7003600:
            return 49

        return 999

    def _classify_inline(self, eid):
        e = self.dictionary.get(str(eid), {}) if hasattr(self, 'dictionary') and self.dictionary else {}
        en = e.get('en', '')
        zh = e.get('zh', '')
        
        char_en = ['[Revenant]', '[Recluse]', '[Wylder]', '[Ironeye]', '[Duchess]', '[Executor]', '[Guardian]', '[Raider]']
        char_zh = ['【复仇者】', '【隐士】', '【追踪者】', '【铁之眼】', '【女爵】', '【守护者】', '【执行者】', '【学者】', '【无赖】', '【送葬者】']
        if any(en.startswith(x) for x in char_en) or any(zh.startswith(x) for x in char_zh):
            return 0
        if 'Attack Power' in en or 'attack power' in en or 'Attack power' in en or 'Damage Increased' in en or 'Power up' in en or 'Damage negation and attack power' in en or 'damage increased' in en or 'Attack Up' in en or 'attack up' in en or \
           '提升攻击力' in zh or '增加伤害' in zh or '属性攻击力' in zh or '物理攻击力' in zh or '物攻' in zh or '攻击力提升' in zh or '提升攻击力' in zh:
            return 5
        if 'Damage Negation' in en or 'Dmg Negation' in en or 'Resistance' in en or 'resistance' in en or 'Guard' in en or 'Poise' in en or 'Defensive' in en or 'Immunity' in en or 'immunity' in en or \
           '减伤率' in zh or '抵抗力' in zh or '免疫力' in zh or '防御力' in zh or '减伤' in zh or '异常状态' in zh or '防性' in zh or '坚韧度' in zh:
            return 6
        if 'Cooldown' in en or 'gauge charge' in en or 'Charge Speed' in en or 'cooldown' in en or 'gauge' in en or \
           '冷却时间' in zh or '槽' in zh or '冷却' in zh:
            return 4
        if any(x in en for x in ['HP', 'FP', 'Stamina', 'Vigor', 'Mind', 'Endurance', 'Strength', 'Dexterity', 'Intelligence', 'Faith', 'Arcane', 'maximum', 'max']) or \
           any(x in zh for x in ['ＨＰ', '专注', '精力', '生命力', '集中力', '耐力', '力气', '灵巧', '智力', '信仰', '感应', '上限']):
            return 3
        if any(x in en for x in ['attack', 'Attack', 'weapon', 'Weapon', 'sorcery', 'Incantation', 'incantation', 'skill', 'Skill', 'spell', 'Spell', 'critical', 'Critical', 'dodging', 'Dodging', 'dodge', 'projectile', 'Projectile', 'parry', 'Parry', 'guard counter', 'Guard Counter', 'chain attack', 'finishers', 'charged', 'Charged', 'counterattack', 'Counterattack', 'strike', 'Slash', 'thrust', 'backstab']) or \
           any(x in zh for x in ['武器', '打倒', '蓄力', '绝招', '致命一击', '技能', '招式', '魔法', '祷告', '闪避', '防反', '防御反击', '弹反', '双手持', '双持']):
            return 1
        return 2

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