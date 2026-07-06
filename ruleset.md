# Elden Ring: Nightreign Relic Legality Ruleset

This document outlines the rules governing the legality of relics in **Elden Ring: Nightreign** as verified by this inspector tool. Relics fall into two categories: **Official Presets** and **Randomized Relics**.

---

## 1. Official Presets (System Presets)
Official presets are hardcoded by the game (defined in `official_relics.csv`).
* **Preset Matching**: The base relic ID must exist in the official whitelist.
* **Exact Effect Match**: The relic's positive slots must contain exactly the official pre-defined effects in the precise preset order.
* **No Debuffs**: Official presets cannot contain any negative effects (curses/debuffs). Any modification or injection of a curse renders the relic **Illegal**.

---

## 2. Randomized Relics
Randomized relics (e.g., dynamic rolls with base IDs $\ge 2000000$ or custom rolls) follow strict generation rules mapped from `EquipParamAntique.csv`, `AttachEffectTableParam.csv`, and `AttachEffectParam.csv`.

### A. Slot Restrictions
* All relics have **4 slots** of combined positive (Buff) and negative (Curse) effects.
* **Slot 4 Check**: According to game engine logic, **Slot 4 must always be empty** (`pos = 0, neg = 0`). Any effect placed in Slot 4 is **Illegal**.

### B. Positive Effect (Buff) Pool Matching
* **Tier-Specific Pools**: Each relic tier (e.g. Standard, Deep) defines up to three lottery tables (`attachEffectTableId_1`, `attachEffectTableId_2`, and `attachEffectTableId_3`).
* **Slot Pool Validation**: Positive effects in Slot $i$ must belong to the lottery pool corresponding to that slot.
* **RNG Compatibility Fallbacks**: If a slot rolled an equivalent tier-compatible override, it is mapped using compatibility groups in `AttachEffectParam.csv`.

### C. Exclusivity Rules (Stacking Limits)
* **Duplicate Group Exclusion**: Relics cannot contain multiple positive effects from the same exclusivity group (e.g., having two physical attack buffs, or two distinct active-combat art overrides).
* Stacking duplicate effect classes renders the relic **Illegal**.

### D. Category Ordering Check
Positive effects are categorized into first-level categories (0-6) based on their internal gameplay tags (sub-categories 1-49):
* `0` (Character Specific) / `1` (Combat Action / Spell)
* `2` (Utility / Gameplay Modifiers)
* `3` (Basic Attributes)
* `4` (Cooldowns / Ultimate Charge Speed)
* `5` (Attack Power / Element Buffs)
* `6` (Defense / Resistances)

* **Combat Action Equivalence**: Category 0 and Category 1 are treated as equivalent (both represent combat actions) and can sit interchangeably in Slot 1 and Slot 2.
* **Ascending Category Sort**: The categories of the slots must follow an ascending sequence:
  $$\text{Slot } 1 \le \text{Slot } 2 \le \text{Slot } 3$$
* **Save File Randomization Bypass**: Because the game places rolled rewards into slot indices randomly when pulling multiple rewards from overlapping pools, the category ordering check is skipped during full save file checks (`parse_save`) to avoid false-positives, but is strictly enforced during simulated/individual relic configurations.

### E. Negative Effect (Curse) Rules
* **Only for Deep Relics**: Curses are strictly restricted to Deep Relics (`isDeepRelic = 1`). Standard relics (`isDeepRelic = 0`) **cannot** have negative effects.
* **Curse Pool Restrictions**: If a relic is a Deep Relic, all curses must belong to the flat, pre-defined `VALID_DEEP_DEBUFFS` pool.
* **Allowed Pairing Buffs**: Curses can **only** be paired with specific positive effects from the approved pairing pool (containing 272 verified game buffs, such as dynamic attack adjustments, weapon overrides, element increments, and health recovery). Pairing a standard attribute buff (e.g. basic HP/FP/stamina increases) with negative effects is **Illegal**.
* **No Order Requirement**: Curses do not follow any slot ordering sequence.
* **No Duplication**: Multiple slot curses on a deep relic must be unique (duplicate debuff IDs are **Illegal**).
