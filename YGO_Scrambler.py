import sqlite3
import random
from pathlib import Path
# import urllib.request
import shutil
import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
from multiprocessing.dummy import Pool as ThreadPool
import multiprocessing
# import itertools
from tqdm import tqdm
from functools import partial
# from ratelimit import limits, sleep_and_retry
import time
import hashlib

VERSION_NUMBER = "v1.6.0"

PLAYER_1_OFFSET = 3100000000
PLAYER_2_OFFSET = 3200000000
PLAYER_3_OFFSET = 3300000000
PLAYER_4_OFFSET = 3400000000
PLAYER_5_OFFSET = 3500000000
PLAYER_6_OFFSET = 3600000000
PLAYER_7_OFFSET = 3700000000
PLAYER_8_OFFSET = 3800000000
PLAYER_9_OFFSET = 3900000000
PLAYER_10_OFFSET = 3000000000
PLAYER_ID_OFFSET = 0

def copy_scripts_parallel(id_index, old_ids, new_ids, script_old_path1, script_old_path2, script_new_path, new_types):
    old_id = old_ids[id_index]
    new_id = new_ids[id_index]
    new_type = new_types[id_index]

    # Make sure the card is not a normal monster or a normal monster tuner, as those don't have scripts.
    # We can't do a bitwise AND here, because normal pendulum monsters do have scripts.
    if new_type in [0x11, 0x1011]:
        new_script = Path(script_new_path, 'c' + str(new_id) + '.lua')
        if new_script.is_file():
            new_script.unlink()
    else:
        # This will overwrite existing scripts, which is fine because any existing ones are probably from previous scrambles.
        new_script = Path(script_new_path, 'c' + str(new_id) + '.lua')
        old_script1 = Path(script_old_path1, 'c' + str(old_id) + '.lua')
        old_script2 = Path(script_old_path2, 'c' + str(old_id) + '.lua')
        # Try to use the newer scripts in the /repository folder, if it exists. Otherwise, use the older script.
        if old_script2.is_file():
            copy_and_fix_script(old_script2, new_script, old_id)
        elif old_script1.is_file():
            copy_and_fix_script(old_script1, new_script, old_id)
        # Deal with REDMD's script being under the ID given to its pre-errata, for some reason.
        elif old_id == 88264978:
            old_script1 = Path(script_old_path1, 'c88264988.lua')
            old_script2 = Path(script_old_path2, 'c88264988.lua')
            if old_script2.is_file():
                copy_and_fix_script(old_script2, new_script, old_id)
            elif old_script1.is_file():
                copy_and_fix_script(old_script1, new_script, old_id)
            else:
                print("\r\nCould not locate script c88264978.lua.\r\n")
        else:
            print("\r\nCould not locate script c{}.lua.\r\n".format(old_id))
            print(old_script2)

def copy_scripts(old_ids, new_ids, script_old_path1, script_old_path2, script_new_path, new_types):
    # Make sure destination folder exists.
    script_new_path.mkdir(parents=True, exist_ok=True)

    id_indexes = range(len(old_ids))

    pool = ThreadPool()
    progress_bar = tqdm(total=len(old_ids))
    progress_bar.set_description("Copying scripts")
    for _ in pool.imap(partial(copy_scripts_parallel, old_ids=old_ids, new_ids=new_ids, script_old_path1=script_old_path1, script_old_path2=script_old_path2, script_new_path=script_new_path, new_types=new_types), id_indexes):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def fix_ritual_spells_parallel(new_id, script_new_path, new_effect_id_to_old_id_dict, old_id_to_new_effect_id_dict, ritual_monster_id_lvs_dict):
    # Exclude "Rebirth of Nephthys", "Libromancer Bonded", "Revendread Origin", "Rise of the Salamangreat", "Dogmatikamacabre", "Recette de Poisson (Fish Recipe)", "Recette de Viande (Meat Recipe)", and "Prayers of the Voiceless Voice" because the monsters they mention aren't in the summoning effect.
    if new_effect_id_to_old_id_dict[new_id] not in [23459650, 41085464, 94666032, 38784726, 60921537, 87778106, 14166715, 52472775]:
        ritual_script_path = Path(script_new_path, 'c' + str(new_id) + '.lua')
        new_file_text = ""
        file_changed = False
        with open(ritual_script_path, encoding="utf8") as file:
            lines = [line for line in file]
            mentioned_ids = []
            for line_index in range(len(lines)):
                line_strings = tokenize_string(lines[line_index])
                line_changed = False
                for s in range(len(line_strings)):
                    if line_strings[s].isdigit():
                        n = int(line_strings[s])
                        # Should exclude levels, Cynet Ritual mentioning a token, Meteonis Drytron listing 1000 ATK, etc.
                        if n > 1000 and n in old_id_to_new_effect_id_dict:
                            # Because all cards are aliased to the original card with their name, we need to use the alias ID instead of the actual ID.
                            line_strings[s] = str(old_id_to_new_effect_id_dict[n] - PLAYER_ID_OFFSET)
                            line_changed = True
                            file_changed = True
                            mentioned_ids.append(old_id_to_new_effect_id_dict[n])
                if line_changed:
                    combined_string = ""
                    for substring in line_strings:
                        combined_string += substring
                    lines[line_index] = combined_string
            if file_changed:
                # Try to change the listed level requirements for a ritual summon. This might break some cards, but it's the best I have found.
                # I am especially concerned about any Ritual Spells that name more than one monster, since there's no way to know which level requirement goes with which. But End of the World is the only one that I know does that, and its script doesn't include the level, so it's probably fine.
                level_mapping = {}
                # Get the level of the original Ritual Monster(s).
                for found_id in mentioned_ids:
                    # Make sure the card being mentioned is a Ritual Monster, and not some other card being mentioned.
                    if found_id in ritual_monster_id_lvs_dict:
                        level_mapping[ritual_monster_id_lvs_dict[found_id][0]] = ritual_monster_id_lvs_dict[found_id][1]
                for line_index in range(len(lines)):
                    line_strings = tokenize_string(lines[line_index])
                    line_changed = False
                    for s in range(len(line_strings)):
                        if line_strings[s].isdigit():
                            n = int(line_strings[s])
                            # This should mean we found a level. Hopefully.
                            if n <= 12 and n in level_mapping:
                                line_strings[s] = str(level_mapping[n])
                                line_changed = True
                    if line_changed:
                        combined_string = ""
                        for substring in line_strings:
                            combined_string += substring
                        lines[line_index] = combined_string
                # Write the changed file.
                for line in lines:
                    new_file_text += line
        if file_changed:
            with open(ritual_script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)

def fix_ritual_spells(new_ids, script_new_path, ritual_spell_indexes, new_effect_id_to_old_id_dict, old_id_to_new_effect_id_dict, ritual_monster_id_lvs_dict):
    ids = [new_ids[i] for i in ritual_spell_indexes]

    pool = ThreadPool()
    progress_bar = tqdm(total=len(ids))
    progress_bar.set_description("Fixing Ritual Spells")
    for _ in pool.imap(partial(fix_ritual_spells_parallel, script_new_path=script_new_path, new_effect_id_to_old_id_dict=new_effect_id_to_old_id_dict, old_id_to_new_effect_id_dict=old_id_to_new_effect_id_dict, ritual_monster_id_lvs_dict=ritual_monster_id_lvs_dict), ids):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def fix_xyz_link_materials_parallel(new_id, script_old_path1, script_old_path2, script_new_path):
    old_script_path1 = Path(script_old_path1, 'c' + str(new_id - PLAYER_ID_OFFSET) + '.lua')
    old_script_path2 = Path(script_old_path2, 'c' + str(new_id - PLAYER_ID_OFFSET) + '.lua')
    new_script_path = Path(script_new_path, 'c' + str(new_id) + '.lua')
    old_script_path = ""
    if old_script_path2.is_file():
        old_script_path = old_script_path2
    elif old_script_path1.is_file():
        old_script_path = old_script_path1
    else:
        print("\r\nCould not locate script c" + str(new_id - PLAYER_ID_OFFSET) + ".lua.\r\n")
    old_material = ""
    material_check_func = ""
    filter_func = ""
    filter_text = ["s.matcheck", "s.lcheck", "s.spcheck", "s.matfilter", "s.mfilter", "s.filter"]
    with open(old_script_path, encoding="utf8") as file:
        for line in file:
            if "Xyz.AddProcedure" in line or "Link.AddProcedure" in line:
                old_material = line
                break
        else:
            # Summoning conditions not found
            if new_id == 6165656 + PLAYER_ID_OFFSET:
                # Number C88: Gimmick Puppet Disaster Leo is currently the only Xyz that can't be summoned normally, so its script does not include its materials, even though they are printed on the card.
                old_material = "Xyz.AddProcedure(c,nil,9,4)"
            else:
                print("Summoning conditions not found for", new_id)
                old_material = '\r\n'
        file.seek(0)
        in_func = False
        target_filters = [filt for filt in filter_text if filt in old_material]
        filters_found = []
        if "Link.AddProcedure" in old_material:
            while len(target_filters) > 0:
                found_inner_filters = False
                inner_filters = []
                for line in file:
                    if any(filt in line for filt in ["function " + f for f in target_filters]):
                        in_func = True
                    if in_func:
                        filter_func += line
                        if "IsExists(s." in line:
                            found_inner_filters = True
                            f = "s." + (line.split("IsExists(s.")[1]).split(',')[0]
                            inner_filters.append(f)
                    if line == "end\n" or line == "end\r\n":
                        in_func = False
                filters_found.extend(target_filters)
                if found_inner_filters:
                    target_filters = inner_filters[:]
                    file.seek(0)
                else:
                    target_filters = []
        for filt in range(len(filters_found)):
            filter_func = filter_func.replace(filters_found[filt], "oldcardfilter"+str(filt))
            old_material = old_material.replace(filters_found[filt], "oldcardfilter"+str(filt))
    new_file_text = ""
    with open(new_script_path, encoding="utf8") as file:
        in_func = False
        leaving_func = False
        for line in file:
            if "Xyz.AddProcedure" in line or "Link.AddProcedure" in line:
                new_file_text += old_material
            else:
                new_file_text += line
        new_file_text += '\r\n' + filter_func
    with open(new_script_path, 'w', encoding="utf8") as file:
        file.write(new_file_text)

def fix_xyz_link_materials(new_ids, script_old_path1, script_old_path2, script_new_path, xyz_monst_indexes, link_monst_indexes):
    ids = [new_ids[i] for i in (xyz_monst_indexes + link_monst_indexes)]

    pool = ThreadPool()
    progress_bar = tqdm(total=len(ids))
    progress_bar.set_description("Fixing Link materials")
    for _ in pool.imap(partial(fix_xyz_link_materials_parallel, script_old_path1=script_old_path1, script_old_path2=script_old_path2, script_new_path=script_new_path), ids):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def fix_xyz_material_levels_parallel(id_and_level, script_new_path):
    new_id, level = id_and_level
    new_script_path = Path(script_new_path, 'c' + str(new_id) + '.lua')

    new_file_text = ""
    with open(new_script_path, encoding="utf8") as file:
        for line in file:
            if "Xyz.AddProcedure" in line:
                new_file_text += re.sub(r"(Xyz.AddProcedure\(c,.+,)\d\d?(,\d[,\)])", r"\g<1>{}\2".format(level), line)
            else:
                new_file_text += line

    with open(new_script_path, 'w', encoding="utf8") as file:
        file.write(new_file_text)

def fix_xyz_material_levels(new_ids, new_levels, script_new_path, xyz_monst_indexes):
    # The % 0x100 is for Pendulum monsters, which store their scale in their level.
    ids_and_levels = [(new_ids[i], new_levels[i] % 0x100) for i in xyz_monst_indexes]

    pool = ThreadPool()
    progress_bar = tqdm(total=len(ids_and_levels))
    progress_bar.set_description('Fixing Xyz materials')
    for _ in pool.imap(partial(fix_xyz_material_levels_parallel, script_new_path=script_new_path), ids_and_levels):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def fix_xyz_numbers_parallel(id_and_name, script_new_path):
    new_id, new_name = id_and_name
    new_script_path = Path(script_new_path, 'c' + str(new_id) + '.lua')

    changed = False
    new_file_text = ""
    with open(new_script_path, encoding="utf8") as file:
        for line in file:
            if "s.xyz_number=" in line:
                changed = True
            else:
                new_file_text += line
    if "Number" in new_name:
        numbers = re.findall(r'\d+', new_name)
        for n in numbers:
            new_file_text += "s.xyz_number=" + str(n) + "\n"
            changed = True
    if changed:
        with open(new_script_path, 'w', encoding="utf8") as file:
            file.write(new_file_text)

def fix_xyz_numbers(new_ids, new_names, script_new_path, xyz_monst_indexes):
    ids_and_names = [(new_ids[i], new_names[i]) for i in xyz_monst_indexes]

    pool = ThreadPool()
    progress_bar = tqdm(total=len(ids_and_names))
    progress_bar.set_description('Fixing "Number" monsters')
    for _ in pool.imap(partial(fix_xyz_numbers_parallel, script_new_path=script_new_path), ids_and_names):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def fix_field_cont_spell_mix_parallel(cont_field_spell_index, new_ids, script_new_path, types, new_types):
    replace_target = ""
    replacement_text = ""
    if new_types[cont_field_spell_index] == 0x20002 and types[cont_field_spell_index] == 0x80002:
        replace_target = "LOCATION_FZONE"
        replacement_text = "LOCATION_SZONE"
    elif new_types[cont_field_spell_index] == 0x80002 and types[cont_field_spell_index] == 0x20002:
        replace_target = "LOCATION_SZONE"
        replacement_text = "LOCATION_FZONE"
    else:
        return
    new_script_path = Path(script_new_path, 'c' + str(new_ids[cont_field_spell_index]) + '.lua')
    new_file_text = ""
    with open(new_script_path, encoding="utf8") as file:
        for line in file:
            if replace_target in line:
                new_file_text += line.replace(replace_target, replacement_text)
            else:
                new_file_text += line
    with open(new_script_path, 'w', encoding="utf8") as file:
        file.write(new_file_text)

def fix_field_cont_spell_mix(new_ids, script_new_path, cont_field_spell_indexes, types, new_types):
    pool = ThreadPool()
    progress_bar = tqdm(total=len(cont_field_spell_indexes))
    progress_bar.set_description('Fixing Field and Continuous Spells')
    for _ in pool.imap(partial(fix_field_cont_spell_mix_parallel, new_ids=new_ids, script_new_path=script_new_path, types=types, new_types=new_types), cont_field_spell_indexes):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def copy_and_fix_script(old_script_path, new_script_path, old_id):
    new_file_text = ""
    offsets = [str(PLAYER_1_OFFSET), str(PLAYER_2_OFFSET), str(PLAYER_3_OFFSET), str(PLAYER_4_OFFSET), str(PLAYER_5_OFFSET), str(PLAYER_6_OFFSET), str(PLAYER_7_OFFSET), str(PLAYER_8_OFFSET), str(PLAYER_9_OFFSET), str(PLAYER_10_OFFSET)]
    with open(old_script_path, encoding="utf8") as file:
        for line in file:
            newline = line
            # Tokens have IDs 1 higher than the card that summons them, so we have to use the ID of card that originally had that effect.
            if ("Duel.CreateToken" in newline or "Duel.IsPlayerCanSpecialSummonMonster" in newline or ("local TOKEN_" in newline or ("local " in newline and "_TOKEN" in newline))) and ("id+1" in newline or "id+2" in newline or "id+i" in newline):
                newline = newline.replace("()", "XXXXX")
                newline = newline.replace("id+1", str(old_id + 1)).replace("id+2", str(old_id + 2)).replace("id+i", str(old_id) + "+i")
                newline = newline.replace("XXXXX", "()")
            if "c:IsOriginalCode(" in newline:
                newline = newline.replace("()", "XXXXX")
                replace_string = r"(\1:IsOriginalCode(\2) or " + " or ".join(fr"\1:IsOriginalCode(\2-{o}) or \1:IsOriginalCode(\2+{o})" for o in offsets) + ")"
                newline = re.sub(r"([A-Za-z]*c):IsOriginalCode\((.+?)\)", replace_string, newline)
                newline = newline.replace("XXXXX", "()")
            if "IsCode(id" in newline:
                newline = newline.replace("()", "XXXXX")
                replace_string = r" \1(\2IsCode(math.fmod(\3,100000000)) or " + " or ".join(fr"\2IsCode(math.fmod(\3,100000000)+{o})" for o in offsets) + ")"
                newline = re.sub(r" (\(*)([A-Za-z0-9\(\):]*)IsCode\((id.*?)\)", replace_string, newline)
                newline = newline.replace("XXXXX", "()")
            if "GetCode()~=id" in newline:
                newline = newline.replace("()", "XXXXX")
                replace_string = r" \1(\2GetCode()~=math.fmod(\3,100000000) or " + " or ".join(fr"\2GetCode()~=math.fmod(\3,100000000)+{o}" for o in offsets) + ")"
                newline = re.sub(r" (\(*)([A-Za-z0-9\(\):]*)GetCode\(\)~=(id.*?)", replace_string, newline)
                newline = newline.replace("XXXXX", "()")
            if "(Card.IsCode," in newline and ",id" in newline:
                newline = newline.replace("()", "XXXXX")
                replace_string = r"(Card.IsCode,\1math.fmod(\2,100000000),"+",".join(fr"math.fmod(\2,100000000)+{o}" for o in offsets) + r"\3"
                newline = re.sub(r"\(Card.IsCode,(.*?,)?(id.*?)([,\)])", replace_string, newline)
                newline = newline.replace("XXXXX", "()")
            new_file_text += newline
    with open(new_script_path, 'w', encoding="utf8") as file:
        file.write(new_file_text)

def fix_individual_cards(old_id_to_new_effect_id_dict, script_new_path):
    # Add progress bar
    with tqdm(total=22, desc="Doing final script fixes") as progress_bar:

        # Fix "That's 10!"
        if 97223101 in old_id_to_new_effect_id_dict:
            thats_ten_new_id = old_id_to_new_effect_id_dict[97223101]
            script_path = Path(script_new_path, 'c' + str(thats_ten_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                is_field = False
                for line in file:
                    if "return code1~=id and code2~=id" in line:
                        new_file_text += f"return code1~=id and code2~=id and code1~=id-{PLAYER_ID_OFFSET} and code2~=id-{PLAYER_ID_OFFSET}\r\n"
                    else:
                        new_file_text += line
                    if "LOCATION_FZONE" in line:
                        is_field = True
                # The effect to enable the adding of counters uses LOCATION_STZONE instead of LOCATION_SZONE, so we need to manually replace it if That's 10 is a Field Spell.
                if is_field:
                    new_file_text.replace("LOCATION_STZONE", "LOCATION_FZONE")
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Dark Sage"
        if 92377303 in old_id_to_new_effect_id_dict:
            dark_sage_new_id = old_id_to_new_effect_id_dict[92377303]
            script_path = Path(script_new_path, 'c' + str(dark_sage_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "71625222" in line:
                        new_file_text += line.replace("71625222", str(old_id_to_new_effect_id_dict[71625222]))
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Metalzoa" and "Red-Eyes Black Metal Dragon"
        for metal_id in [50705071, 64335804]:
            if metal_id in old_id_to_new_effect_id_dict:
                newid = old_id_to_new_effect_id_dict[metal_id]
                script_path = Path(script_new_path, 'c' + str(newid) + '.lua')
                new_file_text = ""
                with open(script_path, encoding="utf8") as file:
                    for line in file:
                        if "68540058" in line:
                            new_file_text += line.replace("68540058", str(old_id_to_new_effect_id_dict[68540058] - PLAYER_ID_OFFSET))
                        else:
                            new_file_text += line
                with open(script_path, 'w', encoding="utf8") as file:
                    file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Tellus the Little Angel"
        if 19280589 in old_id_to_new_effect_id_dict:
            tellus_new_id = old_id_to_new_effect_id_dict[19280589]
            script_path = Path(script_new_path, 'c' + str(tellus_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "c:IsCode(id+1)" in line:
                        new_file_text += "return c:IsCode(19280590) and c:IsType(TYPE_TOKEN)\r\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Number 48: Shadow Lich"
        if 1426714 in old_id_to_new_effect_id_dict:
            lich_new_id = old_id_to_new_effect_id_dict[1426714]
            script_path = Path(script_new_path, 'c' + str(lich_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "Duel.IsExistingMatchingCard" in line:
                        new_file_text += "\treturn Duel.IsExistingMatchingCard(Card.IsCode,e:GetHandlerPlayer(),LOCATION_ONFIELD,0,1,nil,1426715)\r\n"
                    elif "Duel.GetMatchingGroupCount" in line:
                        new_file_text += "\treturn Duel.GetMatchingGroupCount(Card.IsCode,c:GetControler(),LOCATION_ONFIELD,0,nil,1426715)*500\r\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Exodia"
        if 33396948 in old_id_to_new_effect_id_dict:
            exodia_new_id = old_id_to_new_effect_id_dict[33396948]
            script_path = Path(script_new_path, 'c' + str(exodia_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "elseif code==id then a5=true" in line:
                        new_file_text += f"elseif code==math.fmod(id,100000000) then a5=true\r\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Quickdraw Synchron"
        if 20932152 in old_id_to_new_effect_id_dict:
            quickdraw_new_id = old_id_to_new_effect_id_dict[20932152]
            script_path = Path(script_new_path, 'c' + str(quickdraw_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "e3:SetCode(id)" in line:
                        new_file_text += "e3:SetCode(20932152)\r\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Ruin, Angel of Oblivion" and "Ruin, Supreme Queen of Oblivion"
        if 46427957 in old_id_to_new_effect_id_dict:
            new_og_ruin_id = old_id_to_new_effect_id_dict[46427957]
            for old_ruin_id in [50139096, 13518809]:
                if old_ruin_id in old_id_to_new_effect_id_dict:
                    ruin_new_id = old_id_to_new_effect_id_dict[old_ruin_id]
                    script_path = Path(script_new_path, 'c' + str(ruin_new_id) + '.lua')
                    new_file_text = ""
                    with open(script_path, encoding="utf8") as file:
                        for line in file:
                            if "e1:SetValue(46427957)" in line:
                                new_file_text += "e1:SetValue(" + str(new_og_ruin_id) + ")\r\n"
                            else:
                                new_file_text += line
                    with open(script_path, 'w', encoding="utf8") as file:
                        file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Demise, Agent of Armageddon" and "Demise, Supreme King of Armageddon"
        if 72426662 in old_id_to_new_effect_id_dict:
            new_og_demise_id = old_id_to_new_effect_id_dict[72426662]
            for old_demise_id in [86124104, 59913418]:
                if old_demise_id in old_id_to_new_effect_id_dict:
                    demise_new_id = old_id_to_new_effect_id_dict[old_demise_id]
                    script_path = Path(script_new_path, 'c' + str(demise_new_id) + '.lua')
                    new_file_text = ""
                    with open(script_path, encoding="utf8") as file:
                        for line in file:
                            if "e1:SetValue(72426662)" in line:
                                new_file_text += "e1:SetValue(" + str(new_og_demise_id) + ")\r\n"
                            else:
                                new_file_text += line
                    with open(script_path, 'w', encoding="utf8") as file:
                        file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Shinobaron Shade Peacock"
        if 60823690 in old_id_to_new_effect_id_dict and 52900000 in old_id_to_new_effect_id_dict:
            shade_new_id = old_id_to_new_effect_id_dict[60823690]
            new_baron_id = old_id_to_new_effect_id_dict[52900000]
            script_path = Path(script_new_path, 'c' + str(shade_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "e1:SetValue(52900000)" in line:
                        new_file_text += "e1:SetValue(" + str(new_baron_id) + ")\r\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Shinobaroness Shade Peacock"
        if 33325951 in old_id_to_new_effect_id_dict and 25415052 in old_id_to_new_effect_id_dict:
            shade_new_id = old_id_to_new_effect_id_dict[33325951]
            new_baroness_id = old_id_to_new_effect_id_dict[25415052]
            script_path = Path(script_new_path, 'c' + str(shade_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "e1:SetValue(25415052)" in line:
                        new_file_text += "e1:SetValue(" + str(new_baroness_id) + ")\r\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Pyro Clock of Destiny"
        if 1082946 in old_id_to_new_effect_id_dict:
            clock_new_id = old_id_to_new_effect_id_dict[1082946]
            script_path = Path(script_new_path, 'c' + str(clock_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "Card.IsHasEffect" in line or "tc:GetCardEffect" in line:
                        new_file_text += line.replace("id", "1082946")
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Double Snare"
        if 3682106 in old_id_to_new_effect_id_dict:
            snare_new_id = old_id_to_new_effect_id_dict[3682106]
            script_path = Path(script_new_path, 'c' + str(snare_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "c:IsHasEffect(id)" in line:
                        new_file_text += line.replace("c:IsHasEffect(id)", "c:IsHasEffect(3682106)")
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Void Expansion"
        if 34822850 in old_id_to_new_effect_id_dict:
            void_new_id = old_id_to_new_effect_id_dict[34822850]
            script_path = Path(script_new_path, 'c' + str(void_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "e3:SetCode(id)" in line:
                        new_file_text += line.replace("e3:SetCode(id)", "e3:SetCode(34822850)")
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Chaos Witch"
        # This script doesn't summon tokens the same way others do, so it doesn't get covered by fix_scripts().
        if 30327674 in old_id_to_new_effect_id_dict:
            witch_new_id = old_id_to_new_effect_id_dict[30327674]
            script_path = Path(script_new_path, 'c' + str(witch_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "id+" in line:
                        new_file_text += line.replace("id+", "30327674+")
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Golden Castle of Stromberg" and "Shining Sarcophagus"
        # These are the only two cards I found with effects that interact with other cards that mention them and don't
        # use global constants for thier IDs. We want them to still interact with cards that name those original cards,
        # AND cards that name whatever they were shuffled on to.
        mentioned_card_ids = [72283691, 79791878]
        for id in mentioned_card_ids:
            if id in old_id_to_new_effect_id_dict:
                new_mentioned_id = old_id_to_new_effect_id_dict[id]
                script_path = Path(script_new_path, 'c' + str(new_mentioned_id) + '.lua')
                new_file_text = ""
                with open(script_path, encoding="utf8") as file:
                    for line in file:
                        if "c:ListsCode(id)" in line:
                            new_file_text += line.replace("c:ListsCode(id)", "(c:ListsCode(" + str(id) + ") or c:ListsCode(" + str(new_mentioned_id - PLAYER_ID_OFFSET) + ")")
                        else:
                            new_file_text += line
                with open(script_path, 'w', encoding="utf8") as file:
                    file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix Monsters that halve their ATK/DEF and have the new values hardcoded. ("Emissary from Pandemonium", "Archfiend Emperor, the First Lord of Horror", "Vice Dragon", "Fusilier Dragon, the Dual-Mode Beast", "Solar Wind Jammer", and "Segmental Dragon".)
        half_old_ids = [42685062, 28423537, 54343893, 51632798, 33911264, 15066114]
        for id in half_old_ids:
            if id in old_id_to_new_effect_id_dict:
                script_path = Path(script_new_path, 'c' + str(old_id_to_new_effect_id_dict[id]) + '.lua')
                new_file_text = ""
                with open(script_path, encoding="utf8") as file:
                    # All of these scripts set ATK before DEF, so this works. It's not completely generic, but it's better than hardcoding the changes to each of these scripts.
                    times_found = 0
                    for line in file:
                        if times_found < 2 and re.search(r":SetValue\(\d\d\d+\)", line):
                            newline = ""
                            if times_found == 0:
                                newline = re.sub(r":SetValue\(\d\d\d+\)", r":SetValue(c:GetBaseAttack()/2)", line)
                            else:
                                newline = re.sub(r":SetValue\(\d\d\d+\)", r":SetValue(c:GetBaseDefense()/2)", line)
                            new_file_text += newline
                            times_found += 1
                        else:
                            new_file_text += line
                with open(script_path, 'w', encoding="utf8") as file:
                    file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "/Assault Mode" monsters
        for (assault_id, synchro_id) in [(37169670, 95526884), (77336644, "CARD_RED_DRAGON_ARCHFIEND"), (38898779, 23693634), (61257789, "CARD_STARDUST_DRAGON"), (1764972, 6021033), (47027714, 97836203), (14553285, 31924889)]:
            if assault_id in old_id_to_new_effect_id_dict:
                newid = assault_id + PLAYER_ID_OFFSET
                script_path = Path(script_new_path, 'c' + str(newid) + '.lua')
                if not script_path.is_file():
                    # If an "/Assault Mode" monster became a normal monster
                    new_file_text = "local s,id=GetID()\nfunction s.initial_effect(c)\nend\ns.assault_mode=" + str(synchro_id) + "\n"
                    with open(script_path, 'w', encoding="utf8") as file:
                        file.write(new_file_text)
                else:
                    with open(script_path, 'a', encoding="utf8") as file:
                        file.write("\ns.assault_mode=" + str(synchro_id) + "\n")
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Vanadis of the Nordic Ascendant"
        if 61777313 in old_id_to_new_effect_id_dict:
            vanadis_new_id = old_id_to_new_effect_id_dict[61777313]
            script_path = Path(script_new_path, 'c' + str(vanadis_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "e1:SetCode(id)" in line:
                        new_file_text += line.replace("e1:SetCode(id)", "e1:SetCode(EFFECT_SYNSUB_NORDIC)")
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Primite Roar" and "Primite Howl"
        for primite_id in [92501449, 41488249]:
            if primite_id in old_id_to_new_effect_id_dict:
                newid = old_id_to_new_effect_id_dict[primite_id]
                script_path = Path(script_new_path, 'c' + str(newid) + '.lua')
                new_file_text = ""
                with open(script_path, encoding="utf8") as file:
                    for line in file:
                        if "e1:SetTarget(s.target)" in line:
                            new_file_text += line.replace("e1:SetTarget(s.target)", "e1:SetTarget(s.sptg)")
                        else:
                            new_file_text += line
                    new_file_text += '\n'.join(["\nfunction s.spfilter2(c,e,tp,code)",
                        "\treturn c:IsType(TYPE_NORMAL)",
                        "end",
                        "function s.sptg(e,tp,eg,ep,ev,re,r,rp,chk)",
                        "\tif chk==0 then return true end",
                        "\tlocal g=Duel.GetMatchingGroup(s.spfilter2,tp,LOCATION_ALL,0,nil,e,tp)",
                        "\tlocal ids={}",
                        "\tfor tc in g:Iter() do",
                        "\t\tids[tc:GetCode()]=true",
                        "\tend",
                        "\ts.announce_filter={TYPE_NORMAL,OPCODE_ISTYPE}",
                        "\tfor code,iter in pairs(ids) do",
                        "\t\tif #s.announce_filter==0 then",
                        "\t\t\ttable.insert(s.announce_filter,code)",
                        "\t\t\ttable.insert(s.announce_filter,OPCODE_ISCODE)",
                        "\t\telse",
                        "\t\t\ttable.insert(s.announce_filter,code)",
                        "\t\t\ttable.insert(s.announce_filter,OPCODE_ISCODE)",
                        "\t\t\ttable.insert(s.announce_filter,OPCODE_OR)",
                        "\t\tend",
                        "\tend",
                        "\tlocal code=Duel.AnnounceCard(tp,table.unpack(s.announce_filter))",
                        "\tDuel.SetTargetParam(code)",
                        "\tDuel.SetOperationInfo(0,CATEGORY_ANNOUNCE,nil,0,tp,ANNOUNCE_CARD_FILTER)"])
                if id == 92501449:
                    new_file_text += "\n\tDuel.SetOperationInfo(0,CATEGORY_SPECIAL_SUMMON,nil,1,tp,LOCATION_DECK)"
                else:
                    new_file_text += "\n\tDuel.SetOperationInfo(0,CATEGORY_SPECIAL_SUMMON,nil,1,tp,LOCATION_DECK|LOCATION_GRAVE)"
                new_file_text += "\nend"
                with open(script_path, 'w', encoding="utf8") as file:
                    file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Supreme King's Castle"
        if 72043279 in old_id_to_new_effect_id_dict:
            dark_sage_new_id = old_id_to_new_effect_id_dict[72043279]
            script_path = Path(script_new_path, 'c' + str(dark_sage_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "e2:SetCode(id)" in line:
                        new_file_text += line.replace("e2:SetCode(id)", "e2:SetCode(72043279)")
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

        # Fix "Mixeroid"
        if 71340250 in old_id_to_new_effect_id_dict:
            mixeroid_new_id = old_id_to_new_effect_id_dict[71340250]
            script_path = Path(script_new_path, 'c' + str(mixeroid_new_id) + '.lua')
            new_file_text = ""
            with open(script_path, encoding="utf8") as file:
                for line in file:
                    if "return c:IsRace(RACE_MACHINE) and c:IsAbleToRemoveAsCost()" in line:
                        new_file_text += line.replace("return c:IsRace(RACE_MACHINE) and c:IsAbleToRemoveAsCost()",
                            "return (c:IsRace(RACE_MACHINE) or c:GetCardID()==cardid) and c:IsAbleToRemoveAsCost()")
                    elif "local c=e:GetHandler()" in line:
                        new_file_text += line
                        new_file_text += "\tcardid=c:GetCardID()\n"
                    else:
                        new_file_text += line
            with open(script_path, 'w', encoding="utf8") as file:
                file.write(new_file_text)
        progress_bar.update()
        progress_bar.refresh()

def fix_replacement_effects(effect_ids, replacement_constant, tributes_self, tributes_other, script_new_path, replacement_progress_bar):
    for eff_id in effect_ids:
        script_path = Path(script_new_path, 'c' + str(eff_id) + '.lua')
        if not script_path.is_file():
            # Skip cards that don't have scripts. (Which should just be Normal Monsters.)
            replacement_progress_bar.update()
            replacement_progress_bar.refresh()
            continue
        new_file_text = ""
        cost_functions = []
        tribute_cost_functions = []
        with open(script_path, encoding="utf8") as file:
            in_func = ""
            for line in file:
                if "SetCost(Cost.SelfTribute)" in line:
                    if tributes_self:
                        new_file_text += line.replace("SetCost(Cost.SelfTribute)", f"SetCost(aux.CostWithReplace(Cost.SelfTribute,{replacement_constant}))")
                    else:
                        new_file_text += line
                elif "SetCost(" in line:
                    cost_functions.append(line.split("SetCost(")[1].split(")")[0])
                    new_file_text += line
                elif line.split(" ")[0] == "function":
                    if line.split(" ")[1].split("(")[0] in cost_functions:
                        in_func = line.split(" ")[1].split("(")[0]
                    new_file_text += line
                elif in_func and "Duel.Release" in line and "REASON_COST" in line:
                    tribute_cost_functions.append(in_func)
                    new_file_text += line
                elif in_func and line in ("end\n", "end\r\n"):
                    in_func = ""
                    new_file_text += line
                else:
                    new_file_text += line
            if tributes_other and len(tribute_cost_functions) > 0:
                file.seek(0)
                for line in file:
                    if "SetCost(" in line:
                        newline = line
                        for func in tribute_cost_functions:
                            if func in line:
                                newline = line.replace("SetCost("+func+")", "SetCost(aux.CostWithReplace("+func+f",{replacement_constant}))")
                                newline = line.replace("SetCost("+func+",", "SetCost(aux.CostWithReplace("+func+f",{replacement_constant},") + ")"
                        new_file_text += newline
                    else:
                        new_file_text += line
        with open(script_path, 'w', encoding="utf8") as file:
            file.write(new_file_text)
        replacement_progress_bar.update()
        replacement_progress_bar.refresh()

def update_config_file(config_file_path):
    if not config_file_path.is_file():
        with config_file_path.open('w') as file:
            config_json = dict(repos=[])
            json.dump(config_json, file)

    config_json = {}
    with config_file_path.open('r') as file:
        config_json = json.load(file)

    found_repo = False
    found_art_url = False
    for repo in config_json['repos']:
        if repo['repo_name'] == "YGO Scrambler":
            found_repo = True
    for url in config_json['urls']:
        if "YGO-Scrambler-Card-Art" in url['url']:
            found_art_url = True
    if not found_repo:
        config_json['repos'].append(dict(repo_name='YGO Scrambler',
            repo_path='./repositories/ygo-scrambler',
            lflist_path='.',
            script_path='./script',
            should_update=True,
            should_read=True,
            not_git_repo=True))
    if not found_art_url:
        config_json['urls'].append(dict(url='https://raw.githubusercontent.com/TheLetterJ0/YGO-Scrambler-Card-Art/refs/heads/main/pics/{}.jpg',
            type='pic'))
    if not (found_repo and found_art_url):
        with config_file_path.open('w') as file:
            json.dump(config_json, file, indent=4)

def tokenize_string(input_string):
    substrings = []
    current_string = ""
    alph_dig_other = 0

    for char in input_string:
        if char.isalpha():
            if alph_dig_other == 1:
                current_string += char
            else:
                alph_dig_other = 1
                if current_string:
                    substrings.append(current_string)
                current_string = char
        elif char.isdigit():
            if alph_dig_other == 2:
                current_string += char
            else:
                alph_dig_other = 2
                if current_string:
                    substrings.append(current_string)
                current_string = char
        else:
            if alph_dig_other == 3:
                current_string += char
            else:
                alph_dig_other = 3
                if current_string:
                    substrings.append(current_string)
                current_string = char

    # Append the last number if there was one at the end of the string
    if current_string:
        substrings.append(current_string)

    return substrings

def read_flavor_text_file():
    generic_flavor = []
    monster_flavor = []
    ritual_mon_flavor = []
    fusion_flavor = []
    synchro_flavor = []
    xyz_flavor = []
    pendulum_flavor = []
    link_flavor = []
    spell_flavor = []
    cont_spell_flavor = []
    field_flavor = []
    equip_flavor = []
    ritual_spell_flavor = []
    quickplay_flavor = []
    trap_flavor = []
    cont_trap_flavor = []
    counter_flavor = []
    label_mapping = {"===GENERIC===":generic_flavor, "===MONSTER===": monster_flavor, "===RITUAL MONSTER===":ritual_mon_flavor, "===FUSION MONSTER===":fusion_flavor, "===SYNCHRO MONSTER===":synchro_flavor, "===XYZ MONSTER===":xyz_flavor, "===PENDULUM MONSTER===":pendulum_flavor, "===LINK MONSTER===":link_flavor, "===SPELL===":spell_flavor, "===EQUIP SPELL===":equip_flavor, "===FIELD SPELL===":field_flavor, "===CONTINUOUS SPELL===":cont_spell_flavor, "===RITUAL SPELL===":ritual_spell_flavor, "===QUICK-PLAY SPELL===":quickplay_flavor, "===TRAP===":trap_flavor, "===CONTINUOUS TRAP===":cont_trap_flavor, "===COUNTER TRAP===":counter_flavor}

    flavor_path = Path(Path.cwd(), 'scramble_flavor_text.txt')
    if flavor_path.is_file():
        with open(flavor_path) as file:
            current_card_type = generic_flavor
            for line in file:
                if not line.strip() or line.strip()[0] == ';':
                    continue
                if line.strip() in label_mapping:
                    current_card_type = label_mapping[line.strip()]
                    continue
                current_card_type.append(line)
    else:
        generic_flavor.append("")

    return label_mapping

def add_flavor_text(desc_list, new_types, new_names, norm_effect_monst_indexes):
    flavor_dict = read_flavor_text_file()
    generic_flavor = flavor_dict["===GENERIC==="]
    monster_flavor = flavor_dict["===MONSTER==="]
    ritual_mon_flavor = flavor_dict["===RITUAL MONSTER==="]
    fusion_flavor = flavor_dict["===FUSION MONSTER==="]
    synchro_flavor = flavor_dict["===SYNCHRO MONSTER==="]
    xyz_flavor = flavor_dict["===XYZ MONSTER==="]
    pendulum_flavor = flavor_dict["===PENDULUM MONSTER==="]
    link_flavor = flavor_dict["===LINK MONSTER==="]
    spell_flavor = flavor_dict["===SPELL==="]
    equip_flavor = flavor_dict["===EQUIP SPELL==="]
    field_flavor = flavor_dict["===FIELD SPELL==="]
    cont_spell_flavor = flavor_dict["===CONTINUOUS SPELL==="]
    ritual_spell_flavor = flavor_dict["===RITUAL SPELL==="]
    quickplay_flavor = flavor_dict["===QUICK-PLAY SPELL==="]
    trap_flavor = flavor_dict["===TRAP==="]
    cont_trap_flavor = flavor_dict["===CONTINUOUS TRAP==="]
    counter_flavor = flavor_dict["===COUNTER TRAP==="]

    for i in range(len(desc_list)):
        cardtype = new_types[i]
        possible_flavors = generic_flavor
        if cardtype & 0x1:                  # Monster
            possible_flavors = possible_flavors + monster_flavor
            if cardtype & 0x80:             # Ritual
                possible_flavors = possible_flavors + ritual_mon_flavor
            if cardtype & 0x40:             # Fusion
                possible_flavors = possible_flavors + fusion_flavor
            if cardtype & 0x2000:           # Synchro
                possible_flavors = possible_flavors + synchro_flavor
            if cardtype & 0x800000:         # Xyz
                possible_flavors = possible_flavors + xyz_flavor
            if cardtype & 0x4000000:        # Link
                possible_flavors = possible_flavors + link_flavor
            if cardtype & 0x1000000:        # Pendulum
                possible_flavors = possible_flavors + pendulum_flavor
        elif cardtype & 0x2:                # Spell
            possible_flavors = possible_flavors + spell_flavor
            if cardtype & 0x40000:          # Equip
                possible_flavors = possible_flavors + equip_flavor
            if cardtype & 0x80000:          # Field
                possible_flavors = possible_flavors + field_flavor
            if cardtype & 0x20000:          # Continuous
                possible_flavors = possible_flavors + cont_spell_flavor
            if cardtype & 0x80:             # Ritual
                possible_flavors = possible_flavors + ritual_spell_flavor
            if cardtype & 0x10000:          # Quick-Play
                possible_flavors = possible_flavors + quickplay_flavor
        elif cardtype & 0x4:                # Trap
            possible_flavors = possible_flavors + trap_flavor
            if cardtype & 0x20000:          # Continuous
                possible_flavors = possible_flavors + cont_trap_flavor
            if cardtype & 0x100000:         # Counter
                possible_flavors = possible_flavors + counter_flavor

        flavor = random.choice(possible_flavors)
        flavor = flavor.replace("[X]", new_names[i])
        flavor = flavor.replace("[Y]", new_names[norm_effect_monst_indexes[random.randrange(len(norm_effect_monst_indexes))]])
        flavor = flavor.replace("\\n", '\n')

        desc_list[i] = flavor
    return desc_list

def create_banlist_file(new_ids, lflist_path, pool_size, seed):
    text = "!Scrambled Card Pool\n$whitelist\n#Created with the Yu-Gi-Oh Card Scrambler, " + VERSION_NUMBER + ".\n#Scramble seed: " + str(seed) + '\n'
    allowed_ids = new_ids
    if pool_size > 0 and pool_size < len(new_ids):
        allowed_ids = random.sample(new_ids, pool_size)
    for id in new_ids:
        if id in allowed_ids:
            text += str(id) + " 3\n"
        else:
            text += str(id) + " 0\n"
    with open(Path(lflist_path, "scramble.lflist.conf"), 'w', encoding="utf8") as file:
        file.write(text)

def banlist_file_filter(banlist_file, id_list):
    allowed_id_set = set()
    banned_id_set = set()
    is_whitelist = False
    if banlist_file.is_file():
        with open(banlist_file) as file:
            for line in file:
                tokens = line.split()
                if not is_whitelist and len(tokens) >= 1 and tokens[0] == "$whitelist":
                    is_whitelist = True
                elif len(tokens) >= 2 and tokens[0].isdigit() and tokens[1].isdigit():
                    banlist_id = int(tokens[0])
                    if tokens[1] == '0':
                        banned_id_set.add(banlist_id)
                        allowed_id_set.discard(banlist_id)
                    else:
                        allowed_id_set.add(banlist_id)
                        banned_id_set.discard(banlist_id)
    else:
        return id_list
    if is_whitelist:
        return list(allowed_id_set & set(id_list))
    else:
        return list(set(id_list) - banned_id_set)

class YGOScramblerGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # Initialize the main window
        parent.title("Yugioh Card Scrambler, " + VERSION_NUMBER)
        # parent.geometry("425x550")
        parent.resizable(False, False)

        main = tk.ttk.Notebook(parent)
        main.pack(expand = True, fill ="both")

        scramble_tab = tk.Frame(main)
        load_tab = tk.Frame(main)
        extra_tab = tk.Frame(main)
        help_tab = tk.Frame(main)
        main.add(scramble_tab, text="Scramble")
        main.add(load_tab, text="Load Opponent's Files")
        main.add(extra_tab, text="Delete Scramble Files")
        main.add(help_tab, text="Help and Links")

        # Use a variable to track rows for easier updating.
        row_counter = 0

        # Frame to hold file and directory selections
        file_select_frame = tk.Frame(scramble_tab)
        file_select_frame.grid(row=row_counter, column=0, sticky="w", pady=(5,0))
        row_counter += 1
        frame_row_counter = 0

        # .cdb file selection
        tk.Label(file_select_frame, text="Select your .cdb file:").grid(row=frame_row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        frame_row_counter += 1
        self.cdb_path = tk.StringVar()
        tk.Entry(file_select_frame, textvariable=self.cdb_path, width=50).grid(row=frame_row_counter, column=0, sticky="w", padx=13)
        tk.Button(file_select_frame, text="Browse", command=self.select_cdb_file, width=10).grid(row=frame_row_counter, column=1, sticky="w")
        frame_row_counter += 1

        # ProjectIgnis directory selection
        tk.Label(file_select_frame, text="Select your ProjectIgnis directory:").grid(row=frame_row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        frame_row_counter += 1
        self.ignis_dir_path = tk.StringVar()
        tk.Entry(file_select_frame, textvariable=self.ignis_dir_path, width=50).grid(row=frame_row_counter, column=0, sticky="w", padx=13)
        tk.Button(file_select_frame, text="Browse", command=self.select_directory, width=10).grid(row=frame_row_counter, column=1, sticky="w")
        frame_row_counter += 1

        # Banlist file selection
        tk.Label(file_select_frame, text="Select your banlist file (optional):").grid(row=frame_row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        frame_row_counter += 1
        self.banlist_path = tk.StringVar()
        tk.Entry(file_select_frame, textvariable=self.banlist_path, width=50).grid(row=frame_row_counter, column=0, sticky="w", padx=13)
        tk.Button(file_select_frame, text="Browse", command=self.select_banlist_file, width=10).grid(row=frame_row_counter, column=1, sticky="w")
        frame_row_counter += 1

        # Dropdown box to select player number
        tk.Label(scramble_tab, text="Select your player number:").grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        row_counter += 1
        self.player_number = tk.IntVar(value=1)
        self.player_number_dropdown = tk.ttk.Combobox(scramble_tab, state="readonly", textvariable=self.player_number, values=list(range(1, 11)), width=3)
        self.player_number_dropdown.grid(row=row_counter, column=0, padx=13, sticky="w")
        row_counter += 1
        self.player_number_dropdown.current(0)
        self.player_number_dropdown.bind("<<ComboboxSelected>>", self.player_selected)

        # Checkboxes for merging extra deck cards
        tk.Label(scramble_tab, text="Select categories of Extra Deck cards to merge together (optional):").grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        row_counter += 1
        ed_merge_boxes_frame = tk.Frame(scramble_tab)
        ed_merge_boxes_frame.grid(row=row_counter, column=0, sticky="w", pady=(0,0))
        row_counter += 1
        self.merge_choices = [tk.IntVar() for _ in range(8)]
        tk.Checkbutton(ed_merge_boxes_frame, text="Fusion Monsters", variable=self.merge_choices[0]).grid(row=0, column=0, sticky="w", padx=13)
        tk.Checkbutton(ed_merge_boxes_frame, text="Synchro Monsters", variable=self.merge_choices[1]).grid(row=0, column=1, sticky="w", padx=13)
        tk.Checkbutton(ed_merge_boxes_frame, text="Xyz Monsters", variable=self.merge_choices[2]).grid(row=0, column=2, sticky="w", padx=13)

        # Checkboxes for merging card categories
        tk.Label(scramble_tab, text="Select categories of cards to merge (optional):").grid(row=row_counter, column=0, sticky="w", padx=5, pady=(0,0))
        row_counter += 1
        tk.Checkbutton(scramble_tab, text="Ritual and Normal/Effect Monsters", variable=self.merge_choices[3]).grid(row=row_counter, column=0, sticky="w", padx=13)
        row_counter += 1
        tk.Checkbutton(scramble_tab, text="Pendulum and non-Pendulum Monsters", variable=self.merge_choices[4]).grid(row=row_counter, column=0, sticky="w", padx=13)
        row_counter += 1
        tk.Checkbutton(scramble_tab, text="Normal and Ritual Spells", variable=self.merge_choices[5]).grid(row=row_counter, column=0, sticky="w", padx=13)
        row_counter += 1
        tk.Checkbutton(scramble_tab, text="Field and Continuous Spells", variable=self.merge_choices[6]).grid(row=row_counter, column=0, sticky="w", padx=13)
        row_counter += 1
        tk.Checkbutton(scramble_tab, text="Normal Traps and Quick-Play Spells", variable=self.merge_choices[7]).grid(row=row_counter, column=0, sticky="w", padx=13)
        row_counter += 1

        # Option to randomize monster stats
        random_frame = tk.Frame(scramble_tab)
        random_frame.grid(row=row_counter, column=0, sticky="w", pady=(5,0))
        row_counter += 1
        tk.Label(random_frame, text="Change monster stats?").grid(row=0, column=0, sticky="w", padx=5, pady=(0,0))
        self.extra_random = tk.StringVar(value="Don't change stats")
        self.extra_random_dropdown = tk.ttk.Combobox(random_frame, state="readonly", textvariable=self.extra_random, values=list(["Don't change stats", "Shuffle stats together", "Shuffle stats separately", "Randomize stats"]))
        self.extra_random_dropdown.grid(row=0, column=1, padx=13, sticky="w")
        self.extra_random_dropdown.current(0)

        # Limit text entry to numbers
        def testVal(inStr,acttyp):
            if acttyp == '1': #insert
                if not inStr.isdigit():
                    return False
            return True

        # Limit number of cards
        card_pool_size_frame = tk.Frame(scramble_tab)
        card_pool_size_frame.grid(row=row_counter, column=0, sticky="w", pady=(5,0))
        tk.Label(card_pool_size_frame, anchor="center", text="Size of card pool to allow (0 for no limit):").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        self.pool_size = tk.StringVar()
        self.pool_size.set(0)
        size_entry = tk.Entry(card_pool_size_frame, validate="key", textvariable = self.pool_size, width=13)
        size_entry['validatecommand'] = (size_entry.register(testVal),'%P','%d')
        size_entry.grid(row=0, column=1, sticky="w", pady=(3,0))
        row_counter += 1

        seed_scramble_frame = tk.Frame(scramble_tab)
        seed_scramble_frame.grid(row=row_counter, column=0, sticky="ew", pady=(0,10))
        scramble_tab.grid_columnconfigure(0, weight=1)

        # Seed entry
        seed_frame = tk.Frame(seed_scramble_frame)
        seed_frame.grid(row=0, column=0, sticky="w", pady=(0,0))
        tk.Label(seed_frame, text="Your seed:").grid(row=0, column=0, sticky="w", padx=5)
        self.seed = tk.StringVar()
        self.seed.set(random.randrange(0, 9_999_999_999)) # Ten digits should be way more than enough for a seed.
        seed_entry = tk.Entry(seed_frame, validate="key", textvariable = self.seed, width=13)
        seed_entry['validatecommand'] = (seed_entry.register(testVal),'%P','%d')
        seed_entry.grid(row=0, column=1, sticky="w")

        # Scramble button
        seed_scramble_frame.grid_columnconfigure(0, weight=1)
        tk.Button(seed_scramble_frame, text="Scramble!", command=self.scramble, width=10).grid(row=0, column=1, sticky="e", padx=(0,10))


        # Load opponent's files tab
        row_counter = 0
        tk.Label(load_tab, justify="left", text=("The player hosting the duel should load the P[X]ScrambledForOpponent.cdb\n"
            "file sent to them here to generate the necessary scripts and files.")).grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        row_counter += 1

        # Frame to hold file and directory selections
        file_select_frame = tk.Frame(load_tab)
        file_select_frame.grid(row=row_counter, column=0, sticky="w", pady=(5,0))
        row_counter += 1
        frame_row_counter = 0

        # .cdb file selection
        tk.Label(file_select_frame, text="Select your opponent's .cdb file:").grid(row=frame_row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        frame_row_counter += 1
        self.opp_cdb_path = tk.StringVar()
        tk.Entry(file_select_frame, textvariable=self.opp_cdb_path, width=50).grid(row=frame_row_counter, column=0, sticky="w", padx=13)
        tk.Button(file_select_frame, text="Browse", command=self.select_opp_cdb_file, width=10).grid(row=frame_row_counter, column=1, sticky="w")
        frame_row_counter += 1

        # ProjectIgnis directory selection
        tk.Label(file_select_frame, text="Select your ProjectIgnis directory:").grid(row=frame_row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        frame_row_counter += 1
        # self.ignis_dir_path = tk.StringVar()
        tk.Entry(file_select_frame, textvariable=self.ignis_dir_path, width=50).grid(row=frame_row_counter, column=0, sticky="w", padx=13)
        tk.Button(file_select_frame, text="Browse", command=self.select_directory, width=10).grid(row=frame_row_counter, column=1, sticky="w")
        frame_row_counter += 1

        # Generate button
        tk.Button(load_tab, text="Generate", command=self.generate_opp_files, width=10).grid(row=row_counter, column=0, pady=(10,0))


        # Extra Functions tab
        row_counter = 0
        tk.Label(extra_tab, justify="left", text=("To remove custom files from a previous scramble, delete the folder at:\n"
            "\tProjectIgnis\\repositories\\ygo-scrambler\n"
            "This is NOT necessary to do before creating a new scramble.")).grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        row_counter += 1

        tk.Label(extra_tab, justify="left", text='If you delete all files, you should also use the "Reset Config File" button\n'
            "below to also remove the Scrambler\'s additions to your EDOPro \nuser_configs.json file.").grid(row=row_counter, column=0, sticky="w", padx=5, pady=(15,0))
        row_counter += 1
        tk.Label(extra_tab, justify="left", text='You can also use the "Delete Card Arts" button below to remove all of the\n'
            "card arts for scrambled cards that EDO has downloaded.\n     (Warning: if you have other custom cards with IDs in the\n"
            "     3000000000 - 3999999999 range that the YGO Scrambler uses, their\n     arts may also get deleted. If those arts were configured to download\n"
            "     automatically, they will download again.)").grid(row=row_counter, column=0, sticky="w", padx=5, pady=(15,0))
        row_counter += 1

        # ProjectIgnis directory selection
        file_selection_frame = tk.Frame(extra_tab)
        file_selection_frame.grid(row=row_counter, column=0, sticky="w", pady=(0,0))
        row_counter += 1
        tk.Label(file_selection_frame, text="Select your ProjectIgnis directory:").grid(row=1, column=0, sticky="w", padx=5, pady=(0,0))
        self.ignis_dir_config_path = tk.StringVar()
        tk.Entry(file_selection_frame, textvariable=self.ignis_dir_config_path, width=50).grid(row=2, column=0, sticky="w", padx=13)
        tk.Button(file_selection_frame, text="Browse", command=self.select_config_directory, width=10).grid(row=2, column=1, sticky="w")

        button_frame = tk.Frame(extra_tab)
        button_frame.grid(row=row_counter, column=0, pady=(10,0))
        tk.Button(button_frame, text="Reset Config File", command=self.reset_config_file, width=15).grid(row=0, column=0, padx=13)
        tk.Button(button_frame, text="Delete Card Arts", command=self.delete_card_arts, width=15).grid(row=0, column=1, padx=13)
        row_counter += 1

        # Help tab
        row_counter = 0
        tk.Label(help_tab, text="This is " + VERSION_NUMBER + " of the YGO Scrambler.").grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        row_counter += 1
        release_link = tk.Label(help_tab, text="Click here to check for a newer release.", fg="blue", cursor="hand2")
        release_link.grid(row=row_counter, column=0, sticky="w", padx=5, pady=(0,0))
        release_link.bind("<Button-1>", lambda e: self.open_link(r"https://github.com/TheLetterJ0/YGO-Scrambler/releases"))
        row_counter += 1
        readme_link = tk.Label(help_tab, text="Click here to view the README file for detailed instructions.", fg="blue", cursor="hand2")
        readme_link.grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        readme_link.bind("<Button-1>", lambda e: self.open_link(r"https://github.com/TheLetterJ0/YGO-Scrambler/blob/main/README.md"))
        row_counter += 1
        cdb_link = tk.Label(help_tab, text="Click here to download an up-to-date .cdb file.", fg="blue", cursor="hand2")
        cdb_link.grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        cdb_link.bind("<Button-1>", lambda e: self.open_link(r"https://github.com/ProjectIgnis/BabelCDB/blob/master/cards.cdb"))
        row_counter += 1
        release_link = tk.Label(help_tab, text="Click here to join the YGO Scrambler Discord Server.", fg="blue", cursor="hand2")
        release_link.grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        release_link.bind("<Button-1>", lambda e: self.open_link(r"https://discord.gg/sCQWRkRYPk"))
        row_counter += 1
        cdb_link = tk.Label(help_tab, text="Click here to download EDOPro.", fg="blue", cursor="hand2")
        cdb_link.grid(row=row_counter, column=0, sticky="w", padx=5, pady=(5,0))
        cdb_link.bind("<Button-1>", lambda e: self.open_link(r"https://projectignis.github.io"))

    def open_link(self, url):
        webbrowser.open_new(url)

    # Function to handle the Reset Config File button click
    def reset_config_file(self):
        ignis_dir_entry = self.ignis_dir_config_path.get()
        if not ignis_dir_entry:
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Include a path to your ProjectIgnis directory.")
            return

        ignis_dir = Path(ignis_dir_entry)
        if not ignis_dir.is_dir():
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Could not find ProjectIgnis directory at:\r\n" + ignis_dir)
            return
        config_file_path = Path(ignis_dir, 'config', 'user_configs.json')
        if config_file_path.is_file():
            config_json = {}
            with config_file_path.open('r') as file:
                config_json = json.load(file)
            found_repo = False
            for i in range(len(config_json['urls']) - 1, -1, -1):
                if 'YGO-Scrambler-Card-Art' in config_json['urls'][i]['url']:
                    config_json['urls'].pop(i)
                    found_repo = True
            for i in range(len(config_json['repos']) - 1, -1, -1):
                if config_json['repos'][i]['repo_name'] == "YGO Scrambler":
                    config_json['repos'].pop(i)
                    found_repo = True
            if found_repo:
                with config_file_path.open('w') as file:
                    json.dump(config_json, file, indent=4)

        messagebox.showinfo("Config File Reset", "YGO Scrambler settings have been removed from your EDOPro config file.")

    # Function to handle the Delete Card Arts button click
    def delete_card_arts(self):
        ignis_dir_entry = self.ignis_dir_config_path.get()
        if not ignis_dir_entry:
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Include a path to your ProjectIgnis directory.")
            return

        ignis_dir = Path(ignis_dir_entry)
        if not ignis_dir.is_dir():
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Could not find ProjectIgnis directory at:\r\n" + ignis_dir)
            return

        pics_dir = Path(ignis_dir, "pics")
        if not pics_dir.is_dir():
            messagebox.showerror("Missing Path to Pics Directory", "Could not find ProjectIgnis\\pics directory at:\r\n" + pics_dir)
            return

        for file_path in tqdm(list(Path(pics_dir).rglob("3"+("[0-9]"*9)+".jpg")), desc='Deleting scrambled card arts'):
            file_path.unlink()

    # Function to open a .cdb file selection dialog
    def select_cdb_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CDB Files", "*.cdb")])
        self.cdb_path.set(file_path)

    # Function to open a .cdb file selection dialog for opponent's .cdb file
    def select_opp_cdb_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CDB Files", "*.cdb")])
        self.opp_cdb_path.set(file_path)

    # Function to open a banlist file selection dialog
    def select_banlist_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Banlist Files", "*.conf")])
        self.banlist_path.set(file_path)

    # Function to open a directory selection dialog
    def select_directory(self):
        dir_path = filedialog.askdirectory()
        self.ignis_dir_path.set(dir_path)

    # Function to open a directory selection dialog
    def select_config_directory(self):
        dir_path = filedialog.askdirectory()
        self.ignis_dir_config_path.set(dir_path)

    def player_selected(self, event):
        player_number = self.player_number_dropdown.get()

    # Function to handle the Scramble button click
    def scramble(self):
        old_db_path_entry = self.cdb_path.get()
        if not old_db_path_entry:
            messagebox.showerror("Missing .cdb File", "Include a path to your .cdb file.")
            return
        old_db_path = Path(old_db_path_entry)
        if not old_db_path.is_file():
            messagebox.showerror("Missing .cdb File", "Could not find .cdb file at:\r\n" + str(old_db_path))
            return

        ignis_dir_entry = self.ignis_dir_path.get()
        if not ignis_dir_entry:
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Include a path to your ProjectIgnis directory.")
            return
        ignis_dir = Path(ignis_dir_entry)
        scrambler_repo_path = Path(ignis_dir, 'repositories', 'ygo-scrambler')
        scrambler_repo_path.mkdir(parents=True, exist_ok=True)
        if not scrambler_repo_path.is_dir():
            messagebox.showerror("Could Not Create YGO Scrambler Repository", "Could not find/create a YGO Scrambler repository:\r\n" + str(scrambler_repo_path))
            return
        script_old_path1 = Path(ignis_dir, 'script\\official')
        script_old_path2 = Path(ignis_dir, 'repositories\\delta-bagooska\\script\\official')
        lflist_path = Path(scrambler_repo_path)

        if not (ignis_dir.is_dir()):
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Could not find ProjectIgnis directory at:\r\n" + str(ignis_dir))
            return
        if not (script_old_path1.is_dir()):
            messagebox.showerror("Missing Path to ProjectIgnis scripts Directory", "Could not find ProjectIgnis scripts directory at:\r\n" + str(script_old_path1))
            return
        if not (lflist_path.is_dir()):
            messagebox.showerror("Missing Path to lflist Directory", "Could not find target lflist path at:\r\n" + str(lflist_path))
            return

        banlist_path_entry = self.banlist_path.get().strip()
        banlist_path = Path(banlist_path_entry)
        if banlist_path_entry and not banlist_path.is_file():
            messagebox.showerror("Missing Banlist File", "Could not find banlist file at:\r\n" + str(banlist_path))
            return

        global PLAYER_ID_OFFSET
        player_number = self.player_number.get()

        new_db_path = Path(scrambler_repo_path, 'P' + str(player_number) + 'Scrambled.cdb')
        db_path_for_opponent = Path(Path.cwd(), 'P' + str(player_number) + 'ScrambledForOpponent.cdb')
        script_new_path = Path(scrambler_repo_path, 'script')

        config_file_path = Path(ignis_dir, 'config', 'user_configs.json')

        merge_choices = [self.merge_choices[i].get() for i in range(8)]
        merge_choices_hex = sum([merge_choices[x] * 2**x for x in range(len(merge_choices))])
        pool_size = int(self.pool_size.get().strip()) if self.pool_size.get().strip() else 0
        seed = int(self.seed.get().strip()) if self.seed.get().strip() else 0

        rng = random.seed(seed)

        match player_number:
            case 1:
                PLAYER_ID_OFFSET = PLAYER_1_OFFSET
            case 2:
                PLAYER_ID_OFFSET = PLAYER_2_OFFSET
            case 3:
                PLAYER_ID_OFFSET = PLAYER_3_OFFSET
            case 4:
                PLAYER_ID_OFFSET = PLAYER_4_OFFSET
            case 5:
                PLAYER_ID_OFFSET = PLAYER_5_OFFSET
            case 6:
                PLAYER_ID_OFFSET = PLAYER_6_OFFSET
            case 7:
                PLAYER_ID_OFFSET = PLAYER_7_OFFSET
            case 8:
                PLAYER_ID_OFFSET = PLAYER_8_OFFSET
            case 9:
                PLAYER_ID_OFFSET = PLAYER_9_OFFSET
            case 10:
                PLAYER_ID_OFFSET = PLAYER_10_OFFSET
            case _:
                PLAYER_ID_OFFSET = PLAYER_10_OFFSET

        random_level = self.extra_random.get()
        extra_random = 0
        if "together" in random_level:
            extra_random = 1
        elif "separately" in random_level:
            extra_random = 2
        elif "Randomize" in random_level:
            extra_random = 3

        self.shuffle_and_create_new_db(old_db_path, new_db_path, db_path_for_opponent, merge_choices_hex, script_old_path1, script_old_path2, script_new_path, lflist_path, config_file_path, banlist_path, extra_random, pool_size, seed)

    def shuffle_and_create_new_db(self, old_db_path, new_db_path, db_path_for_opponent, merge_speeds, script_old_path1, script_old_path2, script_new_path, lflist_path, config_file_path, banlist_path, extra_random, pool_size, seed):
        # Connect to the old database.
        conn_old = sqlite3.connect(f'file:{old_db_path}?mode=ro', uri=True)
        cursor_old = conn_old.cursor()

        # Retrieve the values from the "texts" table.
        cursor_old.execute("SELECT id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16 FROM texts")
        textsrows = cursor_old.fetchall()

        # Retrieve the values from the "datas" table.
        cursor_old.execute("SELECT id, ot, alias, setcode, type, atk, def, level, race, attribute, category FROM datas")
        datasrows = cursor_old.fetchall()

        # Extract the values retrieved from the tables.
        old_ids = [row[0] for row in textsrows]     # The card's ID number.
        names = [row[1] for row in textsrows]       # The card's name.
        descs = [row[2] for row in textsrows]       # The card's flavortext or effect text, including materials and Pendulum effects, for cards that have them.
        str1s = [row[3] for row in textsrows]       # These are a card's "strings." They are mostly used for scripting and could probably be ignored.
        str2s = [row[4] for row in textsrows]       # But since they're there, we might as well keep them around.
        str3s = [row[5] for row in textsrows]
        str4s = [row[6] for row in textsrows]
        str5s = [row[7] for row in textsrows]
        str6s = [row[8] for row in textsrows]
        str7s = [row[9] for row in textsrows]
        str8s = [row[10] for row in textsrows]
        str9s = [row[11] for row in textsrows]
        str10s = [row[12] for row in textsrows]
        str11s = [row[13] for row in textsrows]
        str12s = [row[14] for row in textsrows]
        str13s = [row[15] for row in textsrows]
        str14s = [row[16] for row in textsrows]
        str15s = [row[17] for row in textsrows]
        str16s = [row[18] for row in textsrows]
        textfields = [old_ids, names, descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s]

        # See https://github.com/NaimSantos/DataEditorX/blob/master/DataEditorX/data/cardinfo_english.txt for what the values in these fields correspond to.
        dataids = [row[0] for row in datasrows]         # The card's ID number. This should be identical to old_ids.
        ots = [row[1] for row in datasrows]             # The card's format: OCG, TCG, Rush, custom card, and so on.
        aliases = [row[2] for row in datasrows]         # For alt art cards, the ID of the original card.
        setcodes = [row[3] for row in datasrows]        # The archtypes a card belongs to.
        types = [row[4] for row in datasrows]           # Monster, Spell, Trap, Tuner, Xyz, Equip, and so on. See the link above.
        atks = [row[5] for row in datasrows]            # ATK. ? is stored as -2.
        defs = [row[6] for row in datasrows]            # DEF. ? is stored as -2. Link monsters use this field to store which arrows they have. See the link above.
        levels = [row[7] for row in datasrows]          # Level/Rank/Link rating. Pendulum scales are also stored here in the format 0xW0Y000Z, where W and Y are the values of the scales, and Z is the level.
        races = [row[8] for row in datasrows]           # Monster type.
        attributes = [row[9] for row in datasrows]      # Monster Attribute.
        categorys = [row[10] for row in datasrows]      # The type of effects the card has (draw, destroy, negate, etc.). See the link above.
                                                        # This field is not strictly necessary, but the simulators use it to filter cards by effect.
        datafields = [dataids, ots, aliases, setcodes, types, atks, defs, levels, races, attributes, categorys]

        # Clean up the data a bit.
        # Iterating from the end of the list to the front so that entries can be removed without interfering with the iteration.
        for i in range(len(old_ids) - 1, -1, -1):
            cardtype = types[i]
            # Remove cards that are not from the OCG (OT=1), TCG (OT=2), or both (OT=3), and alt art cards, and tokens.
            if ((ots[i] < 1 or ots[i] > 3) or cardtype & 0x4000):
                for field in textfields:
                    del field[i]
                for field in datafields:
                    del field[i]
            elif aliases[i] != 0:
                # If a card is an alias for a card with an ID right below, or occasionally right above, it, it is an alt art. If it is from further away, it is a card whose name is treated as another card, like "Cyber Harpie" or "A Legendary Ocean".
                # Except for the Arcana Dark Magician and alt art Poly, which have completely different IDs, for some reason.
                # We want to remove the alt arts, but keep cards being treated as other cards.
                if ((old_ids[i] > aliases[i] - 20) and (old_ids[i] < aliases[i] + 20)) or (old_ids[i] in [36996508, 27847700]):
                    for field in textfields:
                        del field[i]
                    for field in datafields:
                        del field[i]

        # Apply banlist to cardpool, if one was provided.
        if banlist_path and banlist_path.is_file():
            filtered_ids = banlist_file_filter(banlist_path, old_ids)
            for i in range(len(old_ids) - 1, -1, -1):
                if old_ids[i] not in filtered_ids:
                    for field in textfields:
                        del field[i]
                    for field in datafields:
                        del field[i]

        norm_effect_monst_indexes = []
        ritual_monst_indexes = []
        fusion_monst_indexes = []
        synchro_monst_indexes = []
        xyz_monst_indexes = []
        pend_monst_indexes = []
        pend_ritual_indexes = []
        pend_fusion_indexes = []
        pend_sync_indexes = []
        pend_xyz_indexes = []
        pend_link_indexes = []      # None exist right now, but we're future proofing, just in case.
        link_monst_indexes = []

        norm_spell_indexes = []
        field_spell_indexes = []
        equip_spell_indexes = []
        cont_spell_indexes = []
        quick_spell_indexes = []
        ritual_spell_indexes = []

        norm_trap_indexes = []
        cont_trap_indexes = []
        counter_trap_indexes = []

        # Create new copies of the data fields that will be randomized.
        new_ids = old_ids[:]
        new_names = names[:]
        new_aliases = aliases[:]
        new_setcodes = setcodes[:]
        new_types = types[:]
        new_atks = atks[:]
        new_defs = defs[:]
        new_levels = levels[:]
        new_races = races[:]
        new_attributes = attributes[:]

        # These cards' scripts are affected by cards_specific_functions.lua and/or utility.lua. Since we don't want to alter those files and break real cards, we will just force these cards to never scramble.
        cards_to_unscramble = [89785779, 48829461, 14088859, 69832741, 84012625, 75223115, 42015635, 55049722, 75402014, 58858807, 12081875]

        # Save which indexes into the data lists correspond to which type of card.
        # We do this so that Equip Spells only swap with Equip Spells, Links only swap with Links, and so on.
        for i in range(len(old_ids)):
            cardtype = types[i]
            if old_ids[i] in cards_to_unscramble:
                new_ids[i] = PLAYER_ID_OFFSET + old_ids[i]
            else:
                if cardtype & 0x1:                  # Monster
                    if cardtype & 0x40 and not cardtype & 0x1000000:        # Non-Pendulum Fusion
                        fusion_monst_indexes.append(i)
                    elif cardtype & 0x2000 and not cardtype & 0x1000000:    # Non-Pendulum Synchro
                        synchro_monst_indexes.append(i)
                    elif cardtype & 0x800000 and not cardtype & 0x1000000:  # Non-Pendulum Xyz
                        xyz_monst_indexes.append(i)
                    elif cardtype & 0x4000000 and not cardtype & 0x1000000: # Non-Pendulum Link
                        link_monst_indexes.append(i)
                    elif cardtype & 0x1000000:      # Pendulum Monster
                        if cardtype & 0x40:         # Pendulum Fusion
                            pend_fusion_indexes.append(i)
                        elif cardtype & 0x2000:     # Pendulum Synchro
                            pend_sync_indexes.append(i)
                        elif cardtype & 0x800000:   # Pendulum Xyz
                            pend_xyz_indexes.append(i)
                        elif cardtype & 0x4000000:  # Pendulum Link (curently does not exist)
                            pend_link_indexes.append(i)
                        elif cardtype & 0x80:       # Pendulum Ritual
                            pend_ritual_indexes.append(i)
                        else:                       # Main Deck non-Ritual Pendulum Monster
                            pend_monst_indexes.append(i)
                    elif cardtype & 0x80:           # Non-Pendulum Ritual Monster
                        ritual_monst_indexes.append(i)
                    else:                           # Non-Pendulum Main Deck Monster
                        norm_effect_monst_indexes.append(i)
                elif cardtype & 0x2:                    # Spell
                    if cardtype & 0x20000:              # Continuous Spell
                        cont_spell_indexes.append(i)
                    elif cardtype & 0x10000:            # Quick-Play Spell
                        quick_spell_indexes.append(i)
                    elif cardtype & 0x40000:            # Equip Spell
                        equip_spell_indexes.append(i)
                    elif cardtype & 0x80000:            # Field Spell
                        field_spell_indexes.append(i)
                    elif cardtype & 0x80:               # Ritual Spell
                        ritual_spell_indexes.append(i)
                    else:                               # Normal Spell
                        norm_spell_indexes.append(i)
                elif cardtype & 0x4:                # Trap
                    if cardtype & 0x20000:          # Continuous Trap
                        cont_trap_indexes.append(i)
                    elif cardtype & 0x100000:       # Counter Trap
                        counter_trap_indexes.append(i)
                    else:                           # Normal Trap
                        norm_trap_indexes.append(i)

        norm_rit_spell_indexes = norm_spell_indexes + ritual_spell_indexes
        quick_spell_normal_trap_indexes = quick_spell_indexes + norm_trap_indexes
        cont_field_spell_indexes = cont_spell_indexes + field_spell_indexes

        fusion_synchro_indexes = fusion_monst_indexes + synchro_monst_indexes
        pend_fusion_synchro_indexes = pend_fusion_indexes + pend_sync_indexes
        all_fusion_synchro_indexes = fusion_monst_indexes + synchro_monst_indexes + pend_fusion_indexes + pend_sync_indexes

        fusion_xyz_indexes = fusion_monst_indexes + xyz_monst_indexes
        pend_fusion_xyz_indexes = pend_fusion_indexes + pend_xyz_indexes
        all_fusion_xyz_indexes = fusion_monst_indexes + xyz_monst_indexes + pend_fusion_indexes + pend_xyz_indexes

        synchro_xyz_indexes = xyz_monst_indexes + synchro_monst_indexes
        pend_synchro_xyz_indexes = pend_xyz_indexes + pend_sync_indexes
        all_synchro_xyz_indexes = xyz_monst_indexes + synchro_monst_indexes + pend_xyz_indexes + pend_sync_indexes

        extra_deck_indexes = fusion_monst_indexes + synchro_monst_indexes + xyz_monst_indexes
        pend_extra_deck_indexes = pend_fusion_indexes + pend_sync_indexes + pend_xyz_indexes
        all_extra_deck_indexes = fusion_monst_indexes + synchro_monst_indexes + xyz_monst_indexes + pend_fusion_indexes + pend_sync_indexes + pend_xyz_indexes

        ritual_norm_effect_indexes = norm_effect_monst_indexes + ritual_monst_indexes
        all_ritual_indexes = ritual_monst_indexes + pend_ritual_indexes
        pend_ritual_effect_normal_indexes = pend_ritual_indexes + pend_monst_indexes

        all_effect_normal_indexes = norm_effect_monst_indexes + pend_monst_indexes
        all_maindeck_monster_indexes = norm_effect_monst_indexes + pend_monst_indexes + ritual_monst_indexes + pend_ritual_indexes
        all_fusion_indexes = fusion_monst_indexes + pend_fusion_indexes
        all_synchro_indexes = synchro_monst_indexes + pend_sync_indexes
        all_xyz_indexes = xyz_monst_indexes + pend_xyz_indexes
        all_link_indexes = link_monst_indexes + pend_link_indexes

        all_card_indexes = [equip_spell_indexes, cont_trap_indexes, counter_trap_indexes]

        merge_pends = merge_speeds & 0x10

        if merge_speeds & 0x7 == 0x3:
            if merge_pends:
                all_card_indexes.append(all_fusion_synchro_indexes)
                all_card_indexes.append(all_xyz_indexes)
                all_card_indexes.append(all_link_indexes)
            else:
                all_card_indexes.append(fusion_synchro_indexes)
                all_card_indexes.append(pend_fusion_synchro_indexes)
                all_card_indexes.append(xyz_monst_indexes)
                all_card_indexes.append(pend_xyz_indexes)
                all_card_indexes.append(link_monst_indexes)
                all_card_indexes.append(pend_link_indexes)
        elif merge_speeds & 0x7 == 0x5:
            if merge_pends:
                all_card_indexes.append(all_fusion_xyz_indexes)
                all_card_indexes.append(all_synchro_indexes)
                all_card_indexes.append(all_link_indexes)
            else:
                all_card_indexes.append(fusion_xyz_indexes)
                all_card_indexes.append(pend_fusion_xyz_indexes)
                all_card_indexes.append(synchro_monst_indexes)
                all_card_indexes.append(pend_sync_indexes)
                all_card_indexes.append(link_monst_indexes)
                all_card_indexes.append(pend_link_indexes)
        elif merge_speeds & 0x7 == 0x6:
            if merge_pends:
                all_card_indexes.append(all_synchro_xyz_indexes)
                all_card_indexes.append(all_fusion_indexes)
                all_card_indexes.append(all_link_indexes)
            else:
                all_card_indexes.append(synchro_xyz_indexes)
                all_card_indexes.append(pend_synchro_xyz_indexes)
                all_card_indexes.append(fusion_monst_indexes)
                all_card_indexes.append(pend_fusion_indexes)
                all_card_indexes.append(link_monst_indexes)
                all_card_indexes.append(pend_link_indexes)
        elif merge_speeds & 0x7 == 0x7:
            if merge_pends:
                all_card_indexes.append(all_extra_deck_indexes)
                all_card_indexes.append(all_link_indexes)
            else:
                all_card_indexes.append(extra_deck_indexes)
                all_card_indexes.append(pend_extra_deck_indexes)
                all_card_indexes.append(link_monst_indexes)
                all_card_indexes.append(pend_link_indexes)
        elif merge_pends:
            all_card_indexes.append(all_fusion_indexes)
            all_card_indexes.append(all_synchro_indexes)
            all_card_indexes.append(all_xyz_indexes)
            all_card_indexes.append(all_link_indexes)
        else:
            all_card_indexes.append(fusion_monst_indexes)
            all_card_indexes.append(synchro_monst_indexes)
            all_card_indexes.append(pend_fusion_indexes)
            all_card_indexes.append(pend_sync_indexes)
            all_card_indexes.append(xyz_monst_indexes)
            all_card_indexes.append(pend_xyz_indexes)
            all_card_indexes.append(link_monst_indexes)
            all_card_indexes.append(pend_link_indexes)
        if merge_speeds & 0x20:
            all_card_indexes.append(norm_rit_spell_indexes)
        else:
            all_card_indexes.append(norm_spell_indexes)
            all_card_indexes.append(ritual_spell_indexes)
        if merge_speeds & 0x40:
            all_card_indexes.append(cont_field_spell_indexes)
        else:
            all_card_indexes.append(field_spell_indexes)
            all_card_indexes.append(cont_spell_indexes)
        if merge_speeds & 0x80:
            all_card_indexes.append(quick_spell_normal_trap_indexes)
        else:
            all_card_indexes.append(quick_spell_indexes)
            all_card_indexes.append(norm_trap_indexes)
        if merge_speeds & 0x8:
            if merge_pends:
                all_card_indexes.append(all_maindeck_monster_indexes)
            else:
                all_card_indexes.append(ritual_norm_effect_indexes)
                all_card_indexes.append(pend_ritual_effect_normal_indexes)
        elif merge_pends:
            all_card_indexes.append(all_ritual_indexes)
            all_card_indexes.append(all_effect_normal_indexes)
        else:
            all_card_indexes.append(norm_effect_monst_indexes)
            all_card_indexes.append(ritual_monst_indexes)
            all_card_indexes.append(pend_monst_indexes)
            all_card_indexes.append(pend_ritual_indexes)

        new_effect_id_to_old_id_dict = {}
        old_id_to_new_effect_id_dict = {}

        ritual_monster_id_lvs_dict = {}
        name_condition_dict = {}

        if extra_random == 3:
            # Generate random values outside of loop to avoid recreating them every loop.
            rand_attr_values = [0x1]*100 + [0x2]*100 + [0x4]*100 + [0x8]*100 + [0x10]*100 + [0x20]*100 + [0x40]
            rand_race_values = [0x1]*100 + [0x2]*100 + [0x4]*100 + [0x8]*100 + [0x10]*100 + [0x20]*100 + [0x40]*100 + [0x80]*100 + [0x100]*100 + [0x200]*100 + [0x400]*100 + [0x800]*100 + [0x1000]*100 + [0x2000]*100 + [0x4000]*100 + [0x8000]*100 + [0x10000]*100 + [0x20000]*100 + [0x40000]*100 + [0x80000]*100 + [0x100000]*100 + [0x200000]*10 + [0x400000] + [0x800000]*100 + [0x1000000]*100 + [0x2000000]*100
            atk_values = [a for a in range(0, 3000, 100)] * 96 + [a for a in range(3000, 4000, 100)] * 3 + [a for a in range(4000, 4600, 100)]
            rand_atk_values = atk_values * 19 + [a + 50 for a in atk_values]
        cardcount = 0
        with tqdm(total=len(old_ids)-len(cards_to_unscramble), desc="Scrambling database") as progress_bar:
            for index in all_card_indexes:
                # Since we have multiple lists we want to shuffle the same way, we just take the list of indexes, shuffle it, and use that to put all the data in the other lists where it now belongs.
                shuffled_index = index[:]
                random.shuffle(shuffled_index)

                extra_random_shuffled_index_atk = index[:]
                random.shuffle(extra_random_shuffled_index_atk)
                extra_random_shuffled_index_def = index[:]
                random.shuffle(extra_random_shuffled_index_def)
                extra_random_shuffled_index_level = index[:]
                random.shuffle(extra_random_shuffled_index_level)
                extra_random_shuffled_index_race = index[:]
                random.shuffle(extra_random_shuffled_index_race)
                extra_random_shuffled_index_attr = index[:]
                random.shuffle(extra_random_shuffled_index_attr)

                for i in range(len(index)):
                    new_ids[index[i]] = PLAYER_ID_OFFSET + old_ids[shuffled_index[i]]     # Konami uses 8 digit IDs. 9 digit IDs are used for custom cards, pre-errata
                                                                                    # cards, and so on, but 10 digit ids under 2^32 still seem to work.
                    new_names[index[i]] = names[shuffled_index[i]]                  # Adding a 30-39 to the front shouldn't conflict with anything.
                    new_setcodes[index[i]] = setcodes[shuffled_index[i]]
                    # Spells and Traps need to keep atk, def, level, type, and attribute with the effect for trapmonsters to work.
                    # Salamangreat Circle also has atk and def, for some reason, which probably doesn't matter, but we're including spells just in case.
                    if types[index[i]] & 0x6:
                        new_atks[index[i]] = atks[index[i]]
                        new_defs[index[i]] = defs[index[i]]
                        new_levels[index[i]] = levels[index[i]]
                        new_races[index[i]] = races[index[i]]
                        new_attributes[index[i]] = attributes[index[i]]
                        new_types[index[i]] = types[shuffled_index[i]]  # Keep card type with the card, not the effect.
                    else:
                        if extra_random == 1:
                            # Since we're shuffling the stats together, we'll just use the atk one for all of them.
                            new_atks[index[i]] = atks[extra_random_shuffled_index_atk[i]]
                            new_races[index[i]] = races[extra_random_shuffled_index_atk[i]]
                            new_attributes[index[i]] = attributes[extra_random_shuffled_index_atk[i]]
                            if new_types[index[i]] & 0x4000000:     # Link monster
                                new_defs[index[i]] = defs[shuffled_index[i]]
                                new_levels[index[i]] = levels[shuffled_index[i]]
                            else:
                                new_defs[index[i]] = defs[extra_random_shuffled_index_atk[i]]
                                new_levels[index[i]] = levels[extra_random_shuffled_index_atk[i]]
                                if (new_types[index[i]] & 0x1000000) and not (types[shuffled_index[i]] & 0x1000000) and not (types[extra_random_shuffled_index_atk[i]] & 0x1000000):
                                    new_levels[index[i]] += ((levels[index[i]] >> 8) << 8)
                        elif extra_random == 2:
                            new_atks[index[i]] = atks[extra_random_shuffled_index_atk[i]]
                            new_races[index[i]] = races[extra_random_shuffled_index_race[i]]
                            new_attributes[index[i]] = attributes[extra_random_shuffled_index_attr[i]]
                            if new_types[index[i]] & 0x4000000:     # Link monster
                                new_defs[index[i]] = defs[shuffled_index[i]]
                                new_levels[index[i]] = levels[shuffled_index[i]]
                            else:
                                new_defs[index[i]] = defs[extra_random_shuffled_index_def[i]]
                                new_levels[index[i]] = levels[extra_random_shuffled_index_level[i]]
                                if (new_types[index[i]] & 0x1000000) and not (types[shuffled_index[i]] & 0x1000000) and not (types[extra_random_shuffled_index_level[i]] & 0x1000000):
                                    new_levels[index[i]] += ((levels[index[i]] >> 8) << 8)
                        elif extra_random == 3:
                            new_atks[index[i]] = random.choice(rand_atk_values)
                            new_races[index[i]] = random.choice(rand_race_values)
                            new_attributes[index[i]] = random.choice(rand_attr_values)
                            # If it's a Link Monster, ramdomize the link arrows in the DEF field. And keep the levels shuffled normally so they don't break.
                            if new_types[index[i]] & 0x4000000:
                                arrows = 0
                                link_rating = levels[shuffled_index[i]]
                                for arrow in random.sample([0x40, 0x80, 0x100, 0x8, 0x20, 0x1, 0x2, 0x4], link_rating):
                                    arrows += arrow
                                new_defs[index[i]] = arrows
                                new_levels[index[i]] = link_rating
                            # If it's a Pendulum Monster, randomize the scales along with the level.
                            elif new_types[index[i]] & 0x1000000:
                                pend_level = random.randrange(1, 13)
                                pend_level += random.randrange(0, 14, 1) * 0x1010000
                                new_levels[index[i]] = pend_level
                                new_defs[index[i]] = random.choice(rand_atk_values)
                            else:
                                new_defs[index[i]] = random.choice(rand_atk_values)
                                new_levels[index[i]] = random.randrange(1, 13)
                        else:   # No extra stat randomization
                            new_atks[index[i]] = atks[shuffled_index[i]]
                            new_defs[index[i]] = defs[shuffled_index[i]]
                            if (new_types[index[i]] & 0x1000000) and not (types[shuffled_index[i]] & 0x1000000):
                                new_levels[index[i]] = levels[shuffled_index[i]] + ((levels[index[i]] >> 8) << 8)
                            else:
                                new_levels[index[i]] = levels[shuffled_index[i]]
                            new_races[index[i]] = races[shuffled_index[i]]
                            new_attributes[index[i]] = attributes[shuffled_index[i]]

                    # Add alias to original cards, for cards that don't have aliases.
                    if aliases[shuffled_index[i]] == 0:
                        new_aliases[index[i]] = old_ids[shuffled_index[i]]
                    else:
                        new_aliases[index[i]] = aliases[shuffled_index[i]]

                    new_effect_id_to_old_id_dict[new_ids[index[i]]] = old_ids[index[i]]
                    old_id_to_new_effect_id_dict[old_ids[index[i]]] = new_ids[index[i]]

                    # Collect Ritual Monster ID, the old level that ritual had, and the new level it now has.
                    if types[index[i]] & 0x81 == 0x81:
                        ritual_monster_id_lvs_dict[new_ids[index[i]]] = (levels[index[i]], new_levels[index[i]])

                    # Collect Condition Effect texts (like names and archetypes) to return to the original card.
                    # "Number S0: Utopic ZEXAL", "Neo-Spacian Marine Dolphin", and "Neo-Spacian Twinkle Moss" get handled separately, since their texts do not follow standard formatting.
                    manual_condition_dict = {52653092: "(This card's original Rank is always treated as 1.)", 78734254: 'This card\'s name is also treated as "Neo-Spacian Aqua Dolphin".', 13857930: 'This card\'s name is also treated as "Neo-Spacian Glow Moss".'}
                    # Don't remove Name Condition from Legendary Dragon spells, due to how they are coded.
                    ids_not_to_remove_conditions = [11082056, 1784686, 46232525]
                    if old_ids[index[i]] in manual_condition_dict:
                        condition = manual_condition_dict[old_ids[index[i]]]
                        # Standardize parentheses.
                        name_condition_dict[old_ids[index[i]] + PLAYER_ID_OFFSET] = '(' + condition.replace('(', '').replace(')', '') + ')'
                        descs[index[i]] = descs[index[i]].replace(condition + " ", "")
                    else:
                        split_desc = descs[index[i]].split('\n')
                        desc_without_condition = ""
                        for line in split_desc:
                            line = line.strip()
                            if line and line[0] == '(' and line[-1] == ')' and 'treated' in line and not 'Xyz Summon' in line:
                                name_condition_dict[old_ids[index[i]] + PLAYER_ID_OFFSET] = line
                                if old_ids[index[i]] in ids_not_to_remove_conditions:
                                    desc_without_condition += line + '\r\n'
                            else:
                                desc_without_condition += line + '\r\n'
                        descs[index[i]] = desc_without_condition.strip()

                    # Synchrons, Plaguespreader, and other Tuners specifically named as material for certain Synchro monsters are forced to be tuners so those cards are possible to summon.
                    if old_ids[shuffled_index[i]] in [33420078, 19642774, 652362, 78868119, 56286179, 68505803, 9742784, 63977008, 21159309, 74509280, 78552773, 36107810, 96182448, 71971554, 78275321, 6142213, 67270095, 89392810]:
                        new_types[index[i]] |= 0x1000

                    # Update progress bar at the end of the loop
                    progress_bar.update()
                    progress_bar.refresh()
                    cardcount += 1
        print("count:", cardcount)

        # Link monsters really don't work if the materials stay with the effect instead of the name/stats. (For example, how do you handle a Link-1 that says it takes 3+ monsters?)
        # So this replaces the materials listed in their text and replaces it with the materials from their original text.
        # The scripts are edited to match in fix_xyz_link_materials(), called below. (It is not currently used with Xyz monsters, but has not been renamed becuase it could be.)
        for index in [all_link_indexes]:
            materials = {}
            for i in range(len(index)):
                lines = [l.strip() for l in descs[index[i]].split('\n')]
                effect_start = 0
                if new_types[index[i]] & 0x1000000:
                    # Pendulum Monsters get Conditions in their monster effects.
                    if "[ Monster Effect ]" in lines:
                        effect_start = lines.index("[ Monster Effect ]") + 1
                    elif "[ Flavor Text ]" in lines:
                        # For Normal Pendulum Monsters
                        effect_start = lines.index("[ Flavor Text ]") + 1
                materials[old_ids[index[i]]] = lines[effect_start]
            for i in range(len(index)):
                d = descs[index[i]].split('\n')
                descs[index[i]] = materials[new_ids[index[i]] - PLAYER_ID_OFFSET] + '\n' + '\n'.join(d[1:])

        # Change the text of Xyz monster summoning conditions to replace the old levels with the new monster's rank.
        # The scripts are changed to match in fix_xyz_material_levels(), called below.
        for i in range(len(all_xyz_indexes)):
            lines = [l.strip() for l in descs[all_xyz_indexes[i]].split('\n')]
            effect_start = 0
            level = new_levels[all_xyz_indexes[i]] % 0x100  # The % 0x100 is to remove the scale values stored in the level of Pendulum monsters.
            if new_types[all_xyz_indexes[i]] & 0x1000000:
                # Pendulum Monsters get Conditions in their monster effects.
                if "[ Monster Effect ]" in lines:
                    effect_start = lines.index("[ Monster Effect ]") + 1
                elif "[ Flavor Text ]" in lines:
                    # For Normal Pendulum Monsters
                    effect_start = lines.index("[ Flavor Text ]") + 1
            lines[effect_start] = re.sub(r"(\d\+?( or more( \(max. \d\))?)? Level) \d\d?", r"\g<1> {}".format(level), lines[effect_start])
            descs[all_xyz_indexes[i]] = '\r\n'.join(lines)

        # Some final cleanup on effect text.
        name_replace_fields = [descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s]
        # Special cases for cards whose name is also their archetype, and use that archetype name in their effect.
        phrases_not_to_replace = ['card', 'monster', 'Effect Monster', 'Normal', 'non-', 'Ritual', 'Fusion', 'Synchro', 'Xyz', 'Pendulum', 'Link', 'Spell', 'Trap', 'Quick', 'Continuous', 'Field', 'Equip', 'Counter']
        # Cards with old text that erroneously get caught by this filter ("Numinous Healer", "Gather Your Mind", "Good Goblin Housekeeping", "Attack and Receive", "7", "3-Hump Lacooda")
        ids_to_force_replace = [2130625, 7512044, 9744376, 63689843, 67048711, 86988864]
        for i in tqdm(range(len(new_ids)), desc="Updating effect text"):
            # Replace the old card's name with the new card's name in the effect and in the EDO prompts. So effects like hard once-per-turn effects make more sense.
            # Also give all cards extra text at the bottom to say what card their effect originally came from.
            for text in name_replace_fields:
                if old_ids[i] not in ids_to_force_replace:
                    for phrase in phrases_not_to_replace:
                        text[i] = text[i].replace('"' + names[i] + '" ' + phrase, '"XXXXX" ' + phrase)

                text[i] = text[i].replace('"' + names[i] + '"', '"' + new_names[i] + '"')
                text[i] = text[i].replace('"' + names[i] + '(s)"', '"' + new_names[i] + '(s)"')
                if "of Endymion" in names[i]:
                    # Special case for for Reflection/Magister/Servant of Endymion, which get a "(s)" put in the middle of their names
                    split_name = names[i].split(' ')
                    plural_name = ' '.join(split_name[:-2]) + '(s) of Endymion'
                    text[i] = text[i].replace('"' + plural_name + '"', '"' + new_names[i] + '(s)"')
                if old_ids[i] not in ids_to_force_replace:
                    for phrase in phrases_not_to_replace:
                        text[i] = text[i].replace('"XXXXX" ' + phrase, '"' + names[i] + '" ' + phrase)

            # Add condition text back to cards that originally had them.
            if new_ids[i] in name_condition_dict:
                lines = [l.strip() for l in descs[i].split('\n')]
                effect_start = 0
                if new_types[i] & 0x1000000:
                    # Pendulum Monsters get Conditions in their monster effects.
                    if "[ Monster Effect ]" in lines:
                        effect_start = lines.index("[ Monster Effect ]") + 1
                    elif "[ Flavor Text ]" in lines:
                        # For Normal Pendulum Monsters
                        effect_start = lines.index("[ Flavor Text ]") + 1
                if new_types[i] & 0x4802040:
                    # Fusion, Synchro, Xyz, and Link monsters get Conditions after their materials.
                    if "Must be Special Summoned" in lines[effect_start] or "cannot be Special Summoned except with" in lines[effect_start]:
                        # Handle cards that don't have materials, like Masked HEROs, Neo-Spacians, and Ursarctics
                        pass
                    else:
                        effect_start += 1
                descs[i] = '\r\n'.join(lines[0:effect_start]).strip() + ('\r\n' * (effect_start > 0)) + name_condition_dict[new_ids[i]] + '\r\n' + '\r\n'.join(lines[effect_start:]).strip()

            descs[i] += "\r\n\r\n(Effect origin is: " + names[i] + ".)"
            if old_ids[i] in cards_to_unscramble:
                descs[i] += "\r\n\r\n(Due to technical limitations, this card is set to never scramble. It may still not work completely accurately, so you may want to use the original unscrambled card instead.)"

        with tqdm(total=13, desc="Saving scrambled database") as progress_bar:
            # Connect to the new database.
            conn_new = sqlite3.connect(new_db_path)
            cursor_new = conn_new.cursor()

            # Create the texts table in the new database.
            cursor_new.execute("DROP TABLE IF EXISTS texts")
            cursor_new.execute("""
                CREATE TABLE texts (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    desc TEXT,
                    str1 TEXT,
                    str2 TEXT,
                    str3 TEXT,
                    str4 TEXT,
                    str5 TEXT,
                    str6 TEXT,
                    str7 TEXT,
                    str8 TEXT,
                    str9 TEXT,
                    str10 TEXT,
                    str11 TEXT,
                    str12 TEXT,
                    str13 TEXT,
                    str14 TEXT,
                    str15 TEXT,
                    str16 TEXT
                )
            """)
            progress_bar.update()
            progress_bar.refresh()

            # Insert the shuffled values into the new table.
            for id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16, in zip(new_ids, new_names, descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s):
                cursor_new.execute(f"INSERT INTO texts (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16))
            progress_bar.update()
            progress_bar.refresh()

            # Add in a card marked illegal that records the seed used to generate the scramble.
            seed_card_text = "This scramble was generated with the Yu-Gi-Oh Card Scrambler, " + VERSION_NUMBER + ".\r\n"
            seed_card_text += "Scramble seed: " + str(seed) + "\r\n"
            player_number = str((PLAYER_ID_OFFSET - PLAYER_10_OFFSET) // 100000000 or 10)
            seed_card_text += "Player number: " + player_number + "\r\n"
            if merge_speeds & 0x7 == 0x3:
                seed_card_text += "Fusion and Synchro Monsters were merged.\r\n"
            elif merge_speeds & 0x7 == 0x5:
                seed_card_text += "Fusion and Xyz Monsters were merged.\r\n"
            elif merge_speeds & 0x7 == 0x6:
                seed_card_text += "Synchro and Xyz Monsters were merged.\r\n"
            elif merge_speeds & 0x7 == 0x7:
                seed_card_text += "Fusion, Synchro, and Xyz Monsters were merged.\r\n"
            if merge_speeds & 0x8:
                seed_card_text += "Ritual and Normal/Effect Monsters were merged.\r\n"
            if merge_speeds & 0x10:
                seed_card_text += "Pendulum and non-Pendulum Monsters were merged.\r\n"
            if merge_speeds & 0x20:
                seed_card_text += "Normal and Ritual Spells were merged.\r\n"
            if merge_speeds & 0x40:
                seed_card_text += "Field and Continuous Spells were merged.\r\n"
            if merge_speeds & 0x80:
                seed_card_text += "Normal Traps and Quick-Play Spells were merged.\r\n"
            if extra_random == 0:
                seed_card_text += "Monster Stats were not changed.\r\n"
            if extra_random == 1:
                seed_card_text += "Monster Stats were shuffled together.\r\n"
            if extra_random == 2:
                seed_card_text += "Monster Stats were shuffled separately.\r\n"
            if extra_random == 3:
                seed_card_text += "Monster Stats were randomized.\r\n"
            if pool_size > 0:
                seed_card_text += "Card pool size: " + str(pool_size) + "\r\n"
            else:
                seed_card_text += "No card pool size was set.\r\n"
            if banlist_path and banlist_path.is_file():
                seed_card_text += "Provided Banlist: " + banlist_path.name + "\r\n"
            cdb_hash = ""
            with open(old_db_path, 'rb', buffering=0) as file:
                cdb_hash = str(hashlib.file_digest(file, 'sha256').hexdigest())
            seed_card_text += "Provided .cdb file: " + old_db_path.name + "\r\n"
            if cdb_hash:
                seed_card_text += ".cdb file SHA256 hash: " + cdb_hash + "\r\n"
            cursor_new.execute(f"INSERT INTO texts (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (PLAYER_ID_OFFSET, "Scramble Seed", seed_card_text, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''))
            progress_bar.update()
            progress_bar.refresh()

            # Create the datas table in the new database.
            cursor_new.execute("DROP TABLE IF EXISTS datas")
            # 32 in the "ot" field is 0x20, the code for custom cards.
            cursor_new.execute("""
                CREATE TABLE datas (
                    id INTEGER PRIMARY KEY,
                    ot INTEGER DEFAULT 32,
                    alias INTEGER DEFAULT 0,
                    setcode INTEGER,
                    type INTEGER,
                    atk INTEGER,
                    def INTEGER,
                    level INTEGER,
                    race INTEGER,
                    attribute INTEGER,
                    category INTEGER
                )
            """)
            progress_bar.update()
            progress_bar.refresh()

            # Insert the shuffled values into the new table.
            for id, alias, setcode, card_type, atk, defense, level, race, attribute, category in zip(new_ids, new_aliases, new_setcodes, new_types, new_atks, new_defs, new_levels, new_races, new_attributes, categorys):
                cursor_new.execute(f"INSERT INTO datas (id, alias, setcode, type, atk, def, level, race, attribute, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, alias, setcode, card_type, atk, defense, level, race, attribute, category))

            cursor_new.execute(f"INSERT INTO datas (id, ot, setcode, type, atk, def, level, race, attribute, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (PLAYER_ID_OFFSET, 8, 0, 0, 0, 0, 0, 0, 0, 0))
            progress_bar.update()
            progress_bar.refresh()

            # Commit the changes and close the connections.
            conn_new.commit()
            conn_new.close()
            progress_bar.update()
            progress_bar.refresh()

            # Get descriptions for opponent's database.
            opp_descs = add_flavor_text(descs, new_types, new_names, norm_effect_monst_indexes)
            progress_bar.update()
            progress_bar.refresh()

            # Create database for opponent.
            conn_new = sqlite3.connect(db_path_for_opponent)
            cursor_new = conn_new.cursor()
            progress_bar.update()
            progress_bar.refresh()

            # Create the texts table in the new database.
            cursor_new.execute("DROP TABLE IF EXISTS texts")
            cursor_new.execute("""
                CREATE TABLE texts (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    desc TEXT,
                    str1 TEXT,
                    str2 TEXT,
                    str3 TEXT,
                    str4 TEXT,
                    str5 TEXT,
                    str6 TEXT,
                    str7 TEXT,
                    str8 TEXT,
                    str9 TEXT,
                    str10 TEXT,
                    str11 TEXT,
                    str12 TEXT,
                    str13 TEXT,
                    str14 TEXT,
                    str15 TEXT,
                    str16 TEXT
                )
            """)
            progress_bar.update()
            progress_bar.refresh()

            # Insert the shuffled values into the new table.
            for id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16, in zip(new_ids, new_names, opp_descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s):
                cursor_new.execute(f"INSERT INTO texts (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16))
            progress_bar.update()
            progress_bar.refresh()

            # Create the datas table in the new database.
            cursor_new.execute("DROP TABLE IF EXISTS datas")
            # 8 in the "ot" field is the code for illegal cards.
            cursor_new.execute("""
                CREATE TABLE datas (
                    id INTEGER PRIMARY KEY,
                    ot INTEGER DEFAULT 8,
                    alias INTEGER DEFAULT 0,
                    setcode INTEGER,
                    type INTEGER,
                    atk INTEGER,
                    def INTEGER,
                    level INTEGER,
                    race INTEGER,
                    attribute INTEGER,
                    category INTEGER,
                    old_id INTEGER,
                    old_level INTEGER
                )
            """)
            progress_bar.update()
            progress_bar.refresh()

            # Insert the shuffled values into the new table.
            for id, alias, setcode, card_type, atk, defense, level, race, attribute, category, old_id, old_level in zip(new_ids, new_aliases, new_setcodes, new_types, new_atks, new_defs, new_levels, new_races, new_attributes, categorys, old_ids, levels):
                cursor_new.execute(f"INSERT INTO datas (id, alias, setcode, type, atk, def, level, race, attribute, category, old_id, old_level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, alias, setcode, card_type, atk, defense, level, race, attribute, category, old_id, old_level))
            progress_bar.update()
            progress_bar.refresh()

            # Commit the changes and close the connections.
            conn_new.commit()
            conn_old.close()
            conn_new.close()
            progress_bar.update()
            progress_bar.refresh()

        # Update user config file.
        update_config_file(config_file_path)

        # Copy scripts
        copy_scripts(old_ids, new_ids, script_old_path1, script_old_path2, script_new_path, new_types)

        # Fix Ritual Spells so they can summon the new correct monsters.
        fix_ritual_spells(new_ids, script_new_path, ritual_spell_indexes, new_effect_id_to_old_id_dict, old_id_to_new_effect_id_dict, ritual_monster_id_lvs_dict)

        if len(link_monst_indexes) > 0:
            # Give Link monsters their original summoning conditions.
            fix_xyz_link_materials(new_ids, script_old_path1, script_old_path2, script_new_path, [], link_monst_indexes)

        if len(all_xyz_indexes) > 0:
            # Change Xyz monsters to be summoned according to their new rank.
            fix_xyz_material_levels(new_ids, new_levels, script_new_path, all_xyz_indexes)
            # Make sure "Number" Xyz monsters have their number identified in their script, and that non-"Number" Xyz monsters do not.
            if merge_speeds & 0x4 == 0x4:
                fix_xyz_numbers(new_ids, new_names, script_new_path, all_extra_deck_indexes)
            else:
                fix_xyz_numbers(new_ids, new_names, script_new_path, all_xyz_indexes)

        # If Field and Continuous spells were swapped, make sure they have the correct type of effects.
        if merge_speeds & 0x4:
            fix_field_cont_spell_mix(new_ids, script_new_path, cont_field_spell_indexes, types, new_types)

        naturia_ids = [new_ids[i] for i in range(len(new_ids)) if new_setcodes[i] in (0x2a, 0x52002a, 0x123002a)]
        prankkids_ids = [new_ids[i] for i in range(len(new_ids)) if new_setcodes[i] == 0x120]
        ursarctic_ids = [new_ids[i] for i in range(len(new_ids)) if new_setcodes[i] in (0x165, 0x1510165)]
        with tqdm(total=len(naturia_ids+prankkids_ids+ursarctic_ids), desc="Fixing replacement effects") as replacement_progress_bar:
            fix_replacement_effects(naturia_ids, "CARD_NATURIA_CAMELLIA", True, True, script_new_path, replacement_progress_bar)
            fix_replacement_effects(prankkids_ids, "CARD_PRANKKIDS_MEOWMU", True, False, script_new_path, replacement_progress_bar)
            fix_replacement_effects(ursarctic_ids, "CARD_URSARCTIC_BIG_DIPPER", True, True, script_new_path, replacement_progress_bar)

        fix_individual_cards(old_id_to_new_effect_id_dict, script_new_path)

        create_banlist_file(new_ids, lflist_path, pool_size, seed)

        messagebox.showinfo("Scramble complete!", "Done! You may now close the Scrambler window.")

    # Function to handle the Generate button click
    def generate_opp_files(self):
        old_db_path_entry = self.opp_cdb_path.get()
        if not old_db_path_entry:
            messagebox.showerror("Missing .cdb File", "Include a path to your opponent's .cdb file.")
            return
        opp_db_path = Path(old_db_path_entry)
        if not opp_db_path.is_file():
            messagebox.showerror("Missing .cdb File", "Could not find .cdb file at:\r\n" + str(opp_db_path))
            return

        ignis_dir_entry = self.ignis_dir_path.get()
        if not ignis_dir_entry:
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Include a path to your ProjectIgnis directory.")
            return
        ignis_dir = Path(ignis_dir_entry)
        scrambler_repo_path = Path(ignis_dir, 'repositories', 'ygo-scrambler')
        scrambler_repo_path.mkdir(parents=True, exist_ok=True)
        if not scrambler_repo_path.is_dir():
            messagebox.showerror("Could Not Create YGO Scrambler Repository", "Could not find/create a YGO Scrambler repository:\r\n" + str(scrambler_repo_path))
            return
        script_old_path1 = Path(ignis_dir, 'script\\official')
        script_old_path2 = Path(ignis_dir, 'repositories\\delta-bagooska\\script\\official')

        if not (ignis_dir.is_dir()):
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Could not find ProjectIgnis directory at:\r\n" + str(ignis_dir))
            return
        if not (script_old_path1.is_dir()):
            messagebox.showerror("Missing Path to ProjectIgnis scripts Directory", "Could not find ProjectIgnis scripts directory at:\r\n" + str(script_old_path1))
            return

        # Connect to the opponent's database.
        conn_opp = sqlite3.connect(f'file:{opp_db_path}?mode=ro', uri=True)
        cursor_old = conn_opp.cursor()

        # Retrieve the names.
        cursor_old.execute("SELECT name FROM texts")
        textsrows = cursor_old.fetchall()

        # Retrieve the scrambled and original IDs.
        cursor_old.execute("SELECT id, type, level, old_id, old_level FROM datas")
        datasrows = cursor_old.fetchall()

        # Extract the values retrieved from the tables.
        new_names = [row[0] for row in textsrows]       # The card's name.
        new_ids = [row[0] for row in datasrows]     # The card's ID number.
        new_types = [row[1] for row in datasrows]     # The card's type.
        new_levels = [row[2] for row in datasrows]     # The card's level.
        old_ids = [row[3] for row in datasrows]     # The card's original ID number.
        old_levels = [row[4] for row in datasrows]     # The card's original level.

        if new_ids[0] < PLAYER_10_OFFSET or new_ids[0] >= (PLAYER_9_OFFSET + PLAYER_1_OFFSET - PLAYER_10_OFFSET):
            messagebox.showerror("Not a scrambled .cdb", "The given .cdb is not a scrambled file.")
            return

        config_file_path = Path(ignis_dir, 'config', 'user_configs.json')

        player_number = (new_ids[0] - PLAYER_10_OFFSET) // 100000000 or 10
        global PLAYER_ID_OFFSET
        match player_number:
            case 1:
                PLAYER_ID_OFFSET = PLAYER_1_OFFSET
            case 2:
                PLAYER_ID_OFFSET = PLAYER_2_OFFSET
            case 3:
                PLAYER_ID_OFFSET = PLAYER_3_OFFSET
            case 4:
                PLAYER_ID_OFFSET = PLAYER_4_OFFSET
            case 5:
                PLAYER_ID_OFFSET = PLAYER_5_OFFSET
            case 6:
                PLAYER_ID_OFFSET = PLAYER_6_OFFSET
            case 7:
                PLAYER_ID_OFFSET = PLAYER_7_OFFSET
            case 8:
                PLAYER_ID_OFFSET = PLAYER_8_OFFSET
            case 9:
                PLAYER_ID_OFFSET = PLAYER_9_OFFSET
            case 10:
                PLAYER_ID_OFFSET = PLAYER_10_OFFSET
            case _:
                PLAYER_ID_OFFSET = PLAYER_10_OFFSET

        # Generate needed inputs for script editing functions
        script_new_path = Path(scrambler_repo_path, 'script')
        old_id_to_new_effect_id_dict = {}
        new_effect_id_to_old_id_dict = {}
        ritual_monster_id_lvs_dict = {}
        ritual_spell_indexes = []
        cont_field_spell_indexes = []
        all_extra_deck_indexes = []
        link_monst_indexes = []
        all_xyz_indexes = []
        id_to_type_dict = {}
        old_types = []
        for i in range(len(old_ids)):
            new_effect_id_to_old_id_dict[new_ids[i]] = old_ids[i]
            old_id_to_new_effect_id_dict[old_ids[i]] = new_ids[i]
            id_to_type_dict[new_ids[i]] = new_types[i]

            if new_types[i] & 0x81 == 0x81:
                ritual_monster_id_lvs_dict[new_ids[i]] = (old_levels[i], new_levels[i])
            elif new_types[i] & 0x82 == 0x82:
                ritual_spell_indexes.append(i)
            elif new_types[i] & 0x2 and new_types[i] & 0xA0000:
                cont_field_spell_indexes.append(i)
            elif new_types[i] & 0x1:
                if new_types[i] & 0x4802040:
                    all_extra_deck_indexes.append(i)
                    if new_types[i] & 0x4000000:
                        link_monst_indexes.append(i)
                    if new_types[i] & 0x800000:
                        all_xyz_indexes.append(i)
        old_types = [id_to_type_dict[i+PLAYER_ID_OFFSET] for i in old_ids]

        # Copy scripts
        copy_scripts(old_ids, new_ids, script_old_path1, script_old_path2, script_new_path, new_types)

        # Fix Ritual Spells so they can summon the new correct monsters.
        fix_ritual_spells(new_ids, script_new_path, ritual_spell_indexes, new_effect_id_to_old_id_dict, old_id_to_new_effect_id_dict, ritual_monster_id_lvs_dict)

        if len(link_monst_indexes) > 0:
            # Give Link monsters their original summoning conditions.
            fix_xyz_link_materials(new_ids, script_old_path1, script_old_path2, script_new_path, [], link_monst_indexes)

        if len(all_xyz_indexes) > 0:
            # Change Xyz monsters to be summoned according to their new rank.
            fix_xyz_material_levels(new_ids, new_levels, script_new_path, all_xyz_indexes)
            # Make sure "Number" Xyz monsters have their number identified in their script, and that non-"Number" Xyz monsters do not.
            fix_xyz_numbers(new_ids, new_names, script_new_path, all_extra_deck_indexes)

        # If Field and Continuous spells were swapped, make sure they have the correct type of effects.
        fix_field_cont_spell_mix(new_ids, script_new_path, cont_field_spell_indexes, old_types, new_types)

        naturia_ids = [new_ids[i] for i in range(len(new_ids)) if new_setcodes[i] in (0x2a, 0x52002a, 0x123002a)]
        prankkids_ids = [new_ids[i] for i in range(len(new_ids)) if new_setcodes[i] == 0x120]
        ursarctic_ids = [new_ids[i] for i in range(len(new_ids)) if new_setcodes[i] in (0x165, 0x1510165)]
        with tqdm(total=len(naturia_ids+prankkids_ids+ursarctic_ids), desc="Fixing replacement effects") as replacement_progress_bar:
            fix_replacement_effects(naturia_ids, "CARD_NATURIA_CAMELLIA", True, True, script_new_path, replacement_progress_bar)
            fix_replacement_effects(prankkids_ids, "CARD_PRANKKIDS_MEOWMU", True, False, script_new_path, replacement_progress_bar)
            fix_replacement_effects(ursarctic_ids, "CARD_URSARCTIC_BIG_DIPPER", True, True, script_new_path, replacement_progress_bar)

        fix_individual_cards(old_id_to_new_effect_id_dict, script_new_path)

        # Copy the .cdb file into the repo folder
        shutil.copy(old_db_path_entry, scrambler_repo_path)

        # Update the config file, if necessary
        update_config_file(config_file_path)

        messagebox.showinfo("Generation complete!", "Done! You may now close the Scrambler window.")

if __name__=="__main__":
    root = tk.Tk()
    YGOScramblerGUI(root).pack(side="top", fill="both", expand=True)
    root.mainloop()