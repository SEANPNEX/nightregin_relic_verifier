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
Randomized relics (e.g., dynamic rolls with base IDs $\ge 2000000$ or custom rolls) follow rules mapped from `EquipParamAntique.csv`, `AttachEffectTableParam.csv`, and `AttachEffectParam.csv`.

### A. Slot Restrictions
* All relics have **4 slots** of combined positive (Buff) and negative (Curse) effects.
* **Slot 4 Check**: Slot 4 must always be empty (`pos = 0, neg = 0`). Any effect placed in Slot 4 is **Illegal**.

### B. Exclusivity Rules (Stacking Limits)
* **Compatibility ID Stacking**: Stacking effects sharing the same non-negative `compatibilityId` ($\neq -1$) inside `relic_list.csv` is forbidden.
* Stacking duplicate compatibility types renders the relic **Illegal**.

### C. Positive Effect Ordering Check
Active positive effects on Deep Relics must follow an ascending sequence of:
1. `overrideBaseEffectId` (ascending)
2. `ID` (ascending, as secondary key)

* **Standard Relic Bypass**: Standard relics (`isDeepRelic == 0`) do not enforce ordering.
* **Save File Bypass**: Because the game places rolled rewards into slot indices randomly when pulling multiple rewards from overlapping pools, the category ordering check is skipped during full save file checks (`parse_save`) to avoid false-positives, but is strictly enforced on deep relics during individual simulated relic configurations.

### D. Negative Effect (Curse) Rules
* **Only for Deep Relics**: Curses are strictly restricted to Deep Relics (`isDeepRelic == 1`). Standard relics (`isDeepRelic == 0`) **cannot** have negative effects.
* **Curse Pool Restrictions**: If a relic is a Deep Relic, all curses must have `isDebuff == 1` in `relic_list.csv`.
* **Pairing Rules**: 
  - Curses can **only** be paired in the same slot with positive effects that require curses (`requiresDebuff == 1` in `relic_list.csv`), with a whitelist exception for `7000090` and `7120900` to support compatible deep rolls in save files.
  - Pairing curses with other standard positive effects is **Illegal**.
  - Placing a curse in an empty positive slot is **Illegal**.
* **No Order Requirement**: Curses do not follow any slot ordering sequence.
* **No Duplication**: Multiple slot curses on a deep relic must be unique (duplicate debuff IDs are **Illegal**).
