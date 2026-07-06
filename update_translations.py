import json
import os

def update_translations():
    dict_path = "dictionary.json"
    idlist_path = "idlist.txt"
    
    if not os.path.exists(dict_path):
        print(f"Error: {dict_path} not found.")
        return
    if not os.path.exists(idlist_path):
        print(f"Error: {idlist_path} not found.")
        return

    with open(dict_path, 'r', encoding='utf-8') as f:
        d = json.load(f)

    updated_count = 0
    with open(idlist_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":", 1)
            eid = parts[0].strip()
            zh_val = parts[1].strip()
            
            if not eid.isdigit():
                continue
                
            # If the ID exists in dictionary, update its 'zh' field
            if eid in d:
                # We skip updating if the value in idlist.txt contains raw English flags and the dict already has a proper Chinese translation
                # E.g. 7370900 has a proper Chinese translation in the dict, but in idlist it has English text
                if "Changes compatible" in zh_val or "ro375|STD" in zh_val:
                    continue
                    
                d[eid]['zh'] = zh_val
                updated_count += 1

    with open(dict_path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    print(f"Successfully updated {updated_count} Chinese translations in dictionary.json")

if __name__ == "__main__":
    update_translations()
