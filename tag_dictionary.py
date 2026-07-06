import json
import os

def tag_dictionary():
    dict_path = "dictionary.json"
    if not os.path.exists(dict_path):
        print(f"Error: {dict_path} not found.")
        return

    with open(dict_path, 'r', encoding='utf-8') as f:
        d = json.load(f)

    def classify(k, en, zh):
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

    def classify_sub(k_str, en, zh):
        if not k_str.isdigit():
            return 999
        k = int(k_str)

        char_en = ['[Revenant]', '[Recluse]', '[Wylder]', '[Ironeye]', '[Duchess]', '[Executor]', '[Guardian]', '[Raider]']
        char_zh = ['【复仇者】', '【隐士】', '【追踪者】', '【铁之眼】', '【女爵】', '【守护者】', '【执行者】', '【学者】', '【无赖】', '【送葬者】']
        if any(x in en for x in char_en) or any(x in zh for x in char_zh) or k == 7220000 or k == 6220000:
            return 1

        k_str = str(k)
        if k_str.startswith('661') and len(k_str) == 7:
            return 47
        if k_str.startswith('663') and len(k_str) == 7:
            return 28

        if k_str.startswith('6') and len(k_str) == 7:
            k = int('7' + k_str[1:])

        if k < 7000000 or k > 7400000:
            return 999

        # 3武器
        if 7080000 <= k <= 7082300:
            return 2
        if 7082500 <= k <= 7082600:
            return 3
        if 7082700 <= k <= 7082900:
            return 4

        # Weapon specific Attack Power
        if '提升' in zh and '攻击力' in zh and any(w in zh for w in ['短剑', '直剑', '大剑', '特大剑', '曲剑', '大曲剑', '刀', '双头剑', '刺剑', '重刺剑', '斧', '大斧', '槌', '大槌', '连枷', '矛', '大矛', '戟', '镰刀', '拳套', '钩爪', '软鞭', '特大型武器', '弓']):
            return 6
        if 7330000 <= k <= 7339900:
            return 6

        # Weapon specific HP recovery
        if ('攻击' in zh or '命中' in zh) and ('恢复HP' in zh or '恢复血量' in zh or '部分恢复' in zh) and any(w in zh for w in ['短剑', '直剑', '大剑', '特大剑', '曲剑', '大曲剑', '刀', '双头剑', '刺剑', '重刺剑', '斧', '大斧', '槌', '大槌', '连枷', '矛', '大矛', '戟', '镰刀', '拳套', '钩爪', '软鞭', '特大型武器', '弓']):
            return 7
        if 7340000 <= k <= 7349900:
            return 7

        # Weapon specific FP recovery
        if ('攻击' in zh or '命中' in zh) and ('恢复专注' in zh or '恢复蓝' in zh) and any(w in zh for w in ['短剑', '直剑', '大剑', '特大剑', '曲剑', '大曲剑', '刀', '双头剑', '刺剑', '重刺剑', '斧', '大斧', '槌', '大槌', '连枷', '矛', '大矛', '戟', '镰刀', '拳套', '钩爪', '软鞭', '特大型武器', '弓']):
            return 8
        if 7350000 <= k <= 7359900:
            return 8

        # Recover HP on hit general
        if k in (7005600, 7001100, 7030200, 7036100, 7090300):
            return 5

        # Hands/Stance
        if k in (7006000, 7006001):
            return 10
        if k in (7006100, 7006101):
            return 11

        # Item heal allies
        if k == 7010200:
            return 12

        # Low health heal / defense
        if k in (7012200, 7012300):
            return 13

        # Aggressive/Defensive
        if k == 7030600:
            return 14
        if k == 7030000 or k == 7030700:
            return 15
        if k == 7030800:
            return 16

        # Grease
        if k == 7030900:
            return 17

        # Receive attack
        if k == 7032200:
            return 18

        # Critical recovery stamina
        if k == 7035100:
            return 19

        # Enhance light/critical/throwables
        if 7040000 <= k <= 7043100:
            return 20

        # Spells
        if 7043200 <= k <= 7043800:
            return 21
        if 7044000 <= k <= 7044600:
            return 22

        # Ally buffs
        if k == 7050000:
            return 23
        if k == 7050100:
            return 24

        # Rise/Invader
        if k == 7060000:
            return 25
        if k == 7060100:
            return 26
        if k == 7060200:
            return 27

        # Treasure / discovery
        if k == 7070000 or '潜在能力' in zh or 'DormantPower' in en:
            return 28

        # Kill rewards
        if k == 7090000:
            return 29
        if k == 7090100:
            return 30

        # Attack recovery stamina
        if 7100100 <= k <= 7100110:
            return 31

        # Runes
        if k == 7110000:
            return 32

        # Spawn with items & skills
        if 7120000 <= k <= 7126002:
            return 34

        # Spawn with skills (incant/magic overrides)
        if 7360000 <= k <= 7379900:
            return 35
        if '改为' in zh:
            return 35

        # Counter counter
        if k == 7150000:
            return 36

        # Pierce counter
        if k == 7160000:
            return 37

        # Shop discount
        if 7230000 <= k <= 7230001:
            return 38

        # Poise/Reduction on hit
        if k == 7240000:
            return 39

        # Status attack power
        if k == 7037700 or (7260000 <= k <= 7269900):
            return 40

        # Runes on critical
        if k == 7031900:
            return 41

        # Attributes (Vigor/Mind/Endurance)
        if 7000000 <= k <= 7000290:
            return 42

        # Attributes (Strength/Dex/Int/Faith/Arcane)
        if 7000300 <= k <= 7000702:
            return 43

        # Cooldowns
        if 7000800 <= k <= 7000802:
            return 44

        # Ultimate
        if 7000900 <= k <= 7000902:
            return 45

        # Poise
        if 7001000 <= k <= 7001002:
            return 46

        # Elements AP
        if 7001400 <= k <= 7001802:
            return 47

        # Elements Def
        if 7002600 <= k <= 7002900:
            return 48

        # Resistances
        if 7003000 <= k <= 7003600:
            return 49

        return 999

    tagged_count = 0
    for k, v in d.items():
        if not k.isdigit(): continue
        en = v.get('en', '')
        zh = v.get('zh', '')
        v['category'] = classify(k, en, zh)
        v['sub_category'] = classify_sub(k, en, zh)
        tagged_count += 1

    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    print(f"Successfully tagged {tagged_count} entries in dictionary.json")

if __name__ == "__main__":
    tag_dictionary()
