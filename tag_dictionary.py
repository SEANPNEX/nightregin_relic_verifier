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
            # 角色专属
            return 0
        if 'Attack Power' in en or 'attack power' in en or 'Attack power' in en or 'Damage Increased' in en or 'Power up' in en or 'Damage negation and attack power' in en or 'damage increased' in en or 'Attack Up' in en or 'attack up' in en or \
           '提升攻击力' in zh or '增加伤害' in zh or '属性攻击力' in zh or '物理攻击力' in zh or '物攻' in zh or '攻击力提升' in zh or '提升攻击力' in zh:
            # X攻击力提升
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

    tagged_count = 0
    for k, v in d.items():
        if not k.isdigit(): continue
        en = v.get('en', '')
        zh = v.get('zh', '')
        v['category'] = classify(k, en, zh)
        tagged_count += 1

    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    print(f"Successfully tagged {tagged_count} entries in dictionary.json")

if __name__ == "__main__":
    tag_dictionary()
