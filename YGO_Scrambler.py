import sqlite3
import random
from pathlib import Path
import urllib.request
import shutil
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from multiprocessing.dummy import Pool as ThreadPool
import tqdm
from functools import partial
from ratelimit import limits, sleep_and_retry

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

# Ratelimit to make sure we do not exceed the YGOPRODeck API's rate limit of 20 requests/second.
@sleep_and_retry
@limits(calls=20, period=1)
def ratelimited_download(imgURL, new_img1, new_img2, old_id):
    try:
        urllib.request.urlretrieve(imgURL, new_img1)
        shutil.copyfile(new_img1, new_img2)
    except Exception as e:
        # This probably means either the YGOPRODeck site is down, or they are missing an image.
        # New/pre-release cards may be missing, if the database gets updated before the site.
        print("\r\nCould not download file {}.\r\n".format(old_id))
        print(e)

def download_images_parallel(old_id, img_old_path, img_new_path):
    # Make sure image does not already exist, so we don't redownload files we don't need to.
    new_img1 = Path(img_new_path, str(PLAYER_1_OFFSET + old_id) + '.jpg')
    new_img2 = Path(img_new_path, str(PLAYER_2_OFFSET + old_id) + '.jpg')
    old_img = Path(img_old_path, str(old_id) + '.jpg')
    if not new_img1.is_file() and not new_img2.is_file():
        if old_img.is_file():
            shutil.copyfile(old_img, new_img1)
        else:
            imgURL = "https://images.ygoprodeck.com/images/cards_small/" + str(old_id) + ".jpg"
            ratelimited_download(imgURL, new_img1, new_img2, old_id)
    elif not new_img2.is_file():
        shutil.copyfile(new_img1, new_img2)
    else:
        shutil.copyfile(new_img2, new_img1)

def download_images(old_ids, img_old_path, img_new_path):
    if not os.path.exists(img_new_path):
        os.makedirs(img_new_path)

    pool = ThreadPool()
    progress_bar = tqdm.tqdm(total=len(old_ids))
    progress_bar.set_description("Copying/downloading images")
    for _ in pool.imap(partial(download_images_parallel, img_old_path=img_old_path, img_new_path=img_new_path), old_ids):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

    seed_img = Path(img_old_path, '76766706.jpg')
    if seed_img.is_file():
        shutil.copyfile(seed_img, Path(img_new_path, str(PLAYER_ID_OFFSET) + '.jpg'))

def copy_scripts_parallel(id_index, old_ids, new_ids, script_old_path1, script_old_path2, script_new_path, new_types):
    old_id = old_ids[id_index]
    new_id = new_ids[id_index]
    new_type = new_types[id_index]

    # Make sure the card is not a normal monster or a normal monster tuner, as those don't have scripts.
    # We can't do a bitwise AND here, because normal pendulum monsters do have scripts.
    if new_type in [0x11, 0x1011]:
        new_script = Path(script_new_path, 'c' + str(new_id) + '.lua')
        if new_script.is_file():
            os.remove(new_script)
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
        # Deal REDMD's script being under the ID given to its pre-errata, for some reason.
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
    if not os.path.exists(script_new_path):
        os.makedirs(script_new_path)
    
    id_indexes = range(len(old_ids))

    pool = ThreadPool()
    progress_bar = tqdm.tqdm(total=len(old_ids))
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
    progress_bar = tqdm.tqdm(total=len(ids))
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
                print("Summoning conditions not found for", new_names[i], new_ids[i])
                old_material = '\r\n'
        in_func = False
        filters_used = [filter for filter in filter_text if filter in old_material]
        if "Link.AddProcedure" in old_material and len(filters_used) > 0:
            for line in file:
                if any(filter in line for filter in ["function " + f for f in filters_used]):
                    in_func = True
                if in_func:
                    filter_func += line
                if line == "end\n" or line == "end\r\n":
                    in_func = False
        for filter in range(len(filters_used)):
            filter_func = filter_func.replace(filters_used[filter], "oldcardfilter"+str(filter))
            old_material = old_material.replace(filters_used[filter], "oldcardfilter"+str(filter))
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
    progress_bar = tqdm.tqdm(total=len(ids))
    progress_bar.set_description("Fixing Xyz and Link materials")
    for _ in pool.imap(partial(fix_xyz_link_materials_parallel, script_old_path1=script_old_path1, script_old_path2=script_old_path2, script_new_path=script_new_path), ids):
        progress_bar.update()
        progress_bar.refresh()
    pool.close()
    pool.join()

def fix_field_cont_spell_mix(new_ids, script_new_path, cont_field_spell_indexes, types, new_types):
    script_count = 1
    total_scripts = len(cont_field_spell_indexes)
    for index in (cont_field_spell_indexes):
        script_percent = 100 * script_count // total_scripts
        print(f"Fixing Field and Continuous Spell {script_count} of {total_scripts}. ({script_percent}%)", end='\r')
        replace_target = ""
        replacement_text = ""
        if new_types[index] == 0x20002 and types[index] == 0x80002:
            replace_target = "LOCATION_FZONE"
            replacement_text = "LOCATION_SZONE"
        elif new_types[index] == 0x80002 and types[index] == 0x20002:
            replace_target = "LOCATION_SZONE"
            replacement_text = "LOCATION_FZONE"
        else:
            script_count += 1
            continue
        new_script_path = Path(script_new_path, 'c' + str(new_ids[index]) + '.lua')
        new_file_text = ""
        with open(new_script_path, encoding="utf8") as file:
            for line in file:
                if replace_target in line:
                    new_file_text += line.replace(replace_target, replacement_text)
                else:
                    new_file_text += line
        with open(new_script_path, 'w', encoding="utf8") as file:
            file.write(new_file_text)
        script_count += 1
    print()

def copy_and_fix_script(old_script_path, new_script_path, old_id):
    new_file_text = ""
    with open(old_script_path, encoding="utf8") as file:
        for line in file:
            newline = line
            # Tokens have IDs 1 higher than the card that summons them, so we have to use the ID of card that originally had that effect.
            if ("Duel.CreateToken" in newline or "Duel.IsPlayerCanSpecialSummonMonster" in newline or ("local TOKEN_" in newline or ("local " in newline and "_TOKEN" in newline))) and ("id+1" in newline or "id+2" in newline or "id+i" in newline):
                newline = newline.replace("id+1", str(old_id + 1)).replace("id+2", str(old_id + 2)).replace("id+i", str(old_id) + "+i")
            if "aux.Stringid(id," in newline:
                newline = newline.replace("aux.Stringid(id,", "aux.Stringid(math.fmod(id,100000000),")
            if "GetCode()~=id" in newline:
                newline = newline.replace("GetCode()~=id", "GetCode()~=math.fmod(id,100000000)")
            new_file_text += newline
    with open(new_script_path, 'w', encoding="utf8") as file:
        file.write(new_file_text)

def fix_individual_cards(old_id_to_new_effect_id_dict, script_new_path):
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
    
    # Fix "Exodia"
    if 33396948 in old_id_to_new_effect_id_dict:
        exodia_new_id = old_id_to_new_effect_id_dict[33396948]
        script_path = Path(script_new_path, 'c' + str(exodia_new_id) + '.lua')
        new_file_text = ""
        with open(script_path, encoding="utf8") as file:
            for line in file:
                if "elseif code==id then a5=true" in line:
                    new_file_text += f"elseif (code==id or code==id-{PLAYER_1_OFFSET} or code==id-{PLAYER_2_OFFSET}) then a5=true\r\n"
                else:
                    new_file_text += line
        with open(script_path, 'w', encoding="utf8") as file:
            file.write(new_file_text)
    
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
    
    # Fix "Ruin, Angel of Oblivion" and "Ruin, Supreme Queen of Oblivion"
    if 46427957 in old_id_to_new_effect_id_dict:
        new_og_ruin_id = old_id_to_new_effect_id_dict[46427957]
        for old_ruin_id in [50139096, 13518809]:
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
    
    # Fix "Demise, Agent of Armageddon" and "Demise, Supreme King of Armageddon"
    if 72426662 in old_id_to_new_effect_id_dict:
        new_og_demise_id = old_id_to_new_effect_id_dict[72426662]
        for old_demise_id in [86124104, 59913418]:
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
    if os.path.exists(flavor_path):
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
    text = "!Scrambled Card Pool\n$whitelist\n#Created with the Yu-Gi-Oh Card Scrambler.\n#Scramble seed: " + str(seed) + '\n'
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

class YGOScramblerGUI(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # Initialize the main window
        parent.title("Yugioh Card Scrambler")
        parent.geometry("420x390")
        parent.resizable(False, False)

        main = tk.ttk.Notebook(parent)
        main.pack(expand = True, fill ="both") 

        scramble_tab = tk.Frame(main)
        delete_tab = tk.Frame(main)
        main.add(scramble_tab, text="Scramble")
        main.add(delete_tab, text="Delete")

        # An up to date cards.cdb file can be downloaded at https://github.com/ProjectIgnis/BabelCDB/blob/master/cards.cdb
        # .cdb file selection
        tk.Label(scramble_tab, text="Select your .cdb file:").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        self.cdb_path = tk.StringVar()
        tk.Entry(scramble_tab, textvariable=self.cdb_path, width=50).grid(row=1, column=0, sticky="w", padx=13)
        tk.Button(scramble_tab, text="Browse", command=self.select_file, width=10).grid(row=1, column=1, sticky="w")

        # ProjectIgnis directory selection
        tk.Label(scramble_tab, text="Select your ProjectIgnis directory:").grid(row=2, column=0, sticky="w", padx=5, pady=(5,0))
        self.ignis_dir_path = tk.StringVar()
        tk.Entry(scramble_tab, textvariable=self.ignis_dir_path, width=50).grid(row=3, column=0, sticky="w", padx=13)
        tk.Button(scramble_tab, text="Browse", command=self.select_directory, width=10).grid(row=3, column=1, sticky="w")

        # Dropdown box to select player number
        tk.Label(scramble_tab, text="Select your player number:").grid(row=4, column=0, sticky="w", padx=5, pady=(5,0))
        self.player_number = tk.IntVar(value=1)
        # Uncomment when support for more than 2 players is implemented.
        #self.player_number_dropdown = tk.ttk.Combobox(scramble_tab, textvariable=self.player_number, values=list(range(1, 11)), width=3)
        self.player_number_dropdown = tk.ttk.Combobox(scramble_tab, state="readonly", textvariable=self.player_number, values=list(range(1, 3)), width=3)
        self.player_number_dropdown.grid(row=5, column=0, padx=13, sticky="w")
        self.player_number_dropdown.current(0)
        self.player_number_dropdown.bind("<<ComboboxSelected>>", self.player_selected)

        # Uncomment when support for more than 2 players is implemented.
        # # Checkboxes for opponent player numbers
        # tk.Label(scramble_tab, text="Select the player numbers your opponents are using:").grid(row=6, column=0, sticky="w", padx=5, pady=(5,0))
        # opponent_checkboxes_frame = tk.Frame(scramble_tab)
        # opponent_checkboxes_frame.grid(row=7, column=0, sticky="w", padx=5)
        # self.opponent_numbers = [tk.IntVar() for _ in range(10)]
        # self.opponent_checkboxes = [tk.Checkbutton(opponent_checkboxes_frame, text=f"{i+1}", variable=self.opponent_numbers[i]) for i in range(10)]
        # for i in range(5):
            # self.opponent_checkboxes[i].grid(row=0, column=i, sticky="w", padx=13)
        # for i in range(5, 10):
            # self.opponent_checkboxes[i].grid(row=1, column=i-5, sticky="w", padx=13)
        # self.opponent_checkboxes[0].config(state=tk.DISABLED)

        # Checkboxes for merging card categories
        tk.Label(scramble_tab, text="Select categories of cards to merge (optional):").grid(row=6, column=0, sticky="w", padx=5, pady=(5,0))
        self.merge_choices = [tk.IntVar() for _ in range(4)]
        tk.Checkbutton(scramble_tab, text="Fusion and Synchro Monsters", variable=self.merge_choices[0]).grid(row=7, column=0, sticky="w", padx=13)
        tk.Checkbutton(scramble_tab, text="Normal and Ritual Spells", variable=self.merge_choices[1]).grid(row=8, column=0, sticky="w", padx=13)
        tk.Checkbutton(scramble_tab, text="Field and Continuous Spells", variable=self.merge_choices[2]).grid(row=9, column=0, sticky="w", padx=13)
        tk.Checkbutton(scramble_tab, text="Normal Traps and Quick-Play Spells", variable=self.merge_choices[3]).grid(row=10, column=0, sticky="w", padx=13)

        # Option to randomize monster stats
        random_frame = tk.Frame(scramble_tab)
        random_frame.grid(row=11, column=0, sticky="w", pady=(5,0))
        tk.Label(random_frame, text="Change monster stats?").grid(row=0, column=0, sticky="w", padx=5, pady=(0,0))
        self.extra_random = tk.StringVar(value="Don't change stats")
        self.extra_random_dropdown = tk.ttk.Combobox(random_frame, state="readonly", textvariable=self.extra_random, values=list(["Don't change stats", "Shuffle stats", "Randomize stats"]))
        self.extra_random_dropdown.grid(row=0, column=1, padx=13, sticky="w")
        self.extra_random_dropdown.current(0)
        
        # Limit text entry to numbers
        def testVal(inStr,acttyp):
            if acttyp == '1': #insert
                if not inStr.isdigit():
                    return False
            return True

        # Limit number of cards
        tk.Label(scramble_tab, text="Size of card pool to allow (0 for no limit):").grid(row=12, column=0, sticky="w", padx=5, pady=(5,0))
        self.pool_size = tk.StringVar()
        self.pool_size.set(0)
        size_entry = tk.Entry(scramble_tab, validate="key", textvariable = self.pool_size, width=13)
        size_entry['validatecommand'] = (size_entry.register(testVal),'%P','%d')
        size_entry.grid(row=12, column=1, sticky="w")

        # Seed entry
        seed_frame = tk.Frame(scramble_tab)
        seed_frame.grid(row=13, column=0, sticky="w", pady=(5,0))
        tk.Label(seed_frame, text="Your seed:").grid(row=0, column=0, sticky="w", padx=5)
        self.seed = tk.StringVar()
        self.seed.set(random.randrange(0, 9_999_999_999)) # Ten digits should be way more than enough for a seed.
        seed_entry = tk.Entry(seed_frame, validate="key", textvariable = self.seed, width=13)
        seed_entry['validatecommand'] = (seed_entry.register(testVal),'%P','%d')
        seed_entry.grid(row=0, column=1, sticky="w")

        # Scramble button
        tk.Button(scramble_tab, text="Scramble!", command=self.scramble, width=10).grid(row=13, column=1, sticky="e", pady=(5,0))

        # Delete tab
        tk.Label(delete_tab, justify="left", text="Use this to clean up custom files from a previous scramble.\nThis is NOT necessary to do before creating a new scramble.").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        
        # .cdb file selection
        tk.Label(delete_tab, text="Select the scrambled .cdb file, or the original .cdb used to generate it:").grid(row=1, column=0, sticky="w", padx=5, pady=(5,0))
        self.cdb_del_path = tk.StringVar()
        file_selection_frame = tk.Frame(delete_tab)
        file_selection_frame.grid(row=2, column=0, sticky="w", pady=(0,0))
        tk.Entry(file_selection_frame, textvariable=self.cdb_del_path, width=50).grid(row=0, column=0, sticky="w", padx=13)
        tk.Button(file_selection_frame, text="Browse", command=self.select_del_file, width=10).grid(row=0, column=1, sticky="w")

        # ProjectIgnis directory selection
        tk.Label(file_selection_frame, text="Select your ProjectIgnis directory:").grid(row=1, column=0, sticky="w", padx=5, pady=(5,0))
        self.ignis_dir_del_path = tk.StringVar()
        tk.Entry(file_selection_frame, textvariable=self.ignis_dir_del_path, width=50).grid(row=2, column=0, sticky="w", padx=13)
        tk.Button(file_selection_frame, text="Browse", command=self.select_del_directory, width=10).grid(row=2, column=1, sticky="w")

        # Checkboxes for what to delete
        tk.Label(delete_tab, text="Select which files to delete:").grid(row=3, column=0, sticky="w", padx=5, pady=(5,0))
        delete_boxes_frame = tk.Frame(delete_tab)
        delete_boxes_frame.grid(row=4, column=0, sticky="w", pady=(5,0))
        self.delete_choices = [tk.IntVar() for _ in range(4)]
        tk.Checkbutton(delete_boxes_frame, text="Scripts", variable=self.delete_choices[0]).grid(row=0, column=0, sticky="w", padx=13)
        tk.Checkbutton(delete_boxes_frame, text="Card images", variable=self.delete_choices[1]).grid(row=0, column=1, sticky="w", padx=13)
        tk.Checkbutton(delete_boxes_frame, text="Banlist file", variable=self.delete_choices[2]).grid(row=1, column=0, sticky="w", padx=13)
        tk.Checkbutton(delete_boxes_frame, text="Scrambled .cdb file", variable=self.delete_choices[3]).grid(row=1, column=1, sticky="w", padx=13)

        tk.Label(delete_tab, justify="left", text="Files for your opponent of the selected type(s) will be deleted too, if present.\n\nNote that images are not unique to a scramble, and will need to be recopied\nor redownloaded by the scrambler if you use it again.").grid(row=5, column=0, sticky="w", padx=5, pady=(5,0))

        # Delete button
        tk.Button(delete_tab, text="Delete", command=self.delete, width=10).grid(row=6, column=0, sticky="e", padx=5, pady=(5,0))
    
    # Function to handle the Scramble button click
    def delete(self):
        cdb_path = self.cdb_del_path.get()
        if not cdb_path:
            messagebox.showerror("Missing .cdb File", "Include a path to your .cdb file.")
            return
        if not os.path.exists(cdb_path):
            messagebox.showerror("Missing .cdb File", "Could not find .cdb file at:\r\n" + cdb_path)
            return
        
        ignis_dir = self.ignis_dir_del_path.get()
        if not ignis_dir:
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Include a path to your ProjectIgnis directory.")
            return
        img_path = Path(ignis_dir, 'expansions\\pics')
        script_path = Path(ignis_dir, 'expansions\\script')
        lflist_path = Path(ignis_dir, 'lflists')
        
        if not (os.path.exists(ignis_dir) and os.path.exists(img_path) and os.path.exists(script_path) and os.path.exists(lflist_path)):
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Could not find ProjectIgnis directory at:\r\n" + ignis_dir)
            return

        delete_choices = [self.delete_choices[i].get() for i in range(4)]
        delete_message = ""

        # Get ids
        if delete_choices[0] or delete_choices[1]:
            # Connect to the database.
            conn = sqlite3.connect(f'file:{cdb_path}?mode=ro', uri=True)
            cursor = conn.cursor()

            # Retrieve the ids from the "texts" table.
            cursor.execute("SELECT id FROM texts")
            ids = [id[0] for id in cursor.fetchall()]
            conn.close()
            
            # 0 for original cdb, 1 for player 1, 2 for player 2
            player_number = 0

            # If the .cdb the original, convert the ids to scramble ids. If it is scrambled, add the ids for the other player.
            if ids[0] < 3100000000:
                ids = [id + 3100000000 for id in ids] + [id + 3200000000 for id in ids]
            elif ids[0] >= 3100000000 and ids[0] < 3200000000:
                player_number = 1
                ids += [id + 100000000 for id in ids]
            elif ids[0] >= 3200000000 and ids[0] < 3300000000:
                player_number = 2
                ids += [id - 100000000 for id in ids]
            else:
                messagebox.showerror("Invalid IDs", "The IDs in your .cdb file are not valid.\nNo files have been deleted.")
                return

            def check_for_file_and_delete(file_path):
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    return 1
                return 0

            # Delete scripts
            if delete_choices[0]:
                paths = [Path(script_path, "c"+ str(i) + ".lua") for i in ids]
                pool = ThreadPool()
                progress_bar = tqdm.tqdm(total=len(ids))
                progress_bar.set_description("Deleting scripts")
                for _ in pool.imap(check_for_file_and_delete, paths):
                    progress_bar.update()
                    progress_bar.refresh()
                pool.close()
                pool.join()
                delete_message += "Deleted scripts.\n"
            # Delete images
            if delete_choices[1]:
                paths = [Path(img_path, str(i) + ".jpg") for i in ids]
                pool = ThreadPool()
                progress_bar = tqdm.tqdm(total=len(ids))
                progress_bar.set_description("Deleting images")
                for _ in pool.imap(check_for_file_and_delete, paths):
                    progress_bar.update()
                    progress_bar.refresh()
                pool.close()
                pool.join()
                delete_message += "Deleted images.\n"
        # Delete banlist
        if delete_choices[2]:
            banlist_path = Path(lflist_path, "scramble.lflist.conf")
            if check_for_file_and_delete(banlist_path):
                delete_message += "Deleted banlist file.\n"
            else:
                delete_message += "Could not find banlist file to delete.\n"
        # Delete .cdb
        if delete_choices[3]:
            if player_number == 0:
                delete_message += "Could not find scrambled .cdb files to delete since the unscrambled .cdb file was given.\n"
            elif player_number == 1:
                os.unlink(cdb_path)
                scram_cdb_path = Path(ignis_dir, "expansions\\P1Scrambled.cdb")
                opp_scram_cdb_path = Path(ignis_dir, "expansions\\P2ScrambledForOpponent.cdb")
                if check_for_file_and_delete(scram_cdb_path):
                    delete_message += "Deleted P1Scrambled.cdb file.\n"
                else:
                    delete_message += "Could not find P1Scrambled.cdb file to delete.\n"
                if check_for_file_and_delete(opp_scram_cdb_path):
                    delete_message += "Deleted P2ScrambledForOpponent.cdb file.\n"
                else:
                    delete_message += "Could not find P2ScrambledForOpponent.cdb file to delete.\n"
            elif player_number == 2:
                scram_cdb_path = Path(ignis_dir, "expansions\\P2Scrambled.cdb")
                opp_scram_cdb_path = Path(ignis_dir, "expansions\\P1ScrambledForOpponent.cdb")
                if check_for_file_and_delete(scram_cdb_path):
                    delete_message += "Deleted P2Scrambled.cdb file.\n"
                else:
                    delete_message += "Could not find P2Scrambled.cdb file to delete.\n"
                if check_for_file_and_delete(opp_scram_cdb_path):
                    delete_message += "Deleted P1ScrambledForOpponent.cdb file.\n"
                else:
                    delete_message += "Could not find P1ScrambledForOpponent.cdb file to delete.\n"

        delete_message += "\nYou may now close the Scrambler window."
        messagebox.showinfo("Deletion complete", delete_message)
        print()

    # Function to open a file selection dialog
    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CDB Files", "*.cdb")])
        self.cdb_path.set(file_path)

    # Function to open a directory selection dialog
    def select_directory(self):
        dir_path = filedialog.askdirectory()
        self.ignis_dir_path.set(dir_path)

    # Function to open a file selection dialog
    def select_del_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CDB Files", "*.cdb")])
        self.cdb_del_path.set(file_path)

    # Function to open a directory selection dialog
    def select_del_directory(self):
        dir_path = filedialog.askdirectory()
        self.ignis_dir_del_path.set(dir_path)

    def player_selected(self, event):
        player_number = self.player_number_dropdown.get()
        # Uncomment when support for more than 2 players is implemented.
        # for i in range(10):
            # if i == int(player_number) - 1:
                # self.opponent_checkboxes[i].config(state=tk.DISABLED)
                # self.opponent_checkboxes[i].deselect()
            # else:
                # self.opponent_checkboxes[i].config(state=tk.NORMAL)

    # Function to handle the Scramble button click
    def scramble(self):
        old_db_path = self.cdb_path.get()
        if not old_db_path:
            messagebox.showerror("Missing .cdb File", "Include a path to your .cdb file.")
            return
        if not os.path.exists(old_db_path):
            messagebox.showerror("Missing .cdb File", "Could not find .cdb file at:\r\n" + old_db_path)
            return
        
        ignis_dir = self.ignis_dir_path.get()
        if not ignis_dir:
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Include a path to your ProjectIgnis directory.")
            return
        img_old_path = Path(ignis_dir, 'pics')
        script_old_path1 = Path(ignis_dir, 'script\\official')
        script_old_path2 = Path(ignis_dir, 'repositories\\delta-bagooska\\script\\official')
        lflist_path = Path(ignis_dir, 'lflists')
        
        if not (os.path.exists(ignis_dir) and os.path.exists(img_old_path) and os.path.exists(script_old_path1) and os.path.exists(lflist_path)):
            messagebox.showerror("Missing Path to ProjectIgnis Directory", "Could not find ProjectIgnis directory at:\r\n" + ignis_dir)
            return
        
        global PLAYER_ID_OFFSET
        player_number = self.player_number.get()

        new_db_path = Path(ignis_dir, 'expansions', 'P' + str(player_number) + 'Scrambled.cdb')
        db_path_for_opponent = Path(Path.cwd(), 'P' + str(player_number) + 'ScrambledForOpponent.cdb')
        img_new_path = Path(ignis_dir, 'expansions\\pics')
        script_new_path = Path(ignis_dir, 'expansions\\script')

        # Uncomment when support for more than 2 players is implemented.
        #opponent_numbers = [self.opponent_numbers[i].get() for i in range(10)]
        merge_choices = [self.merge_choices[i].get() for i in range(4)]
        merge_choices_hex = merge_choices[0] + merge_choices[1]*2 + merge_choices[2]*4 + merge_choices[3]*8
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
        if "Shuffle" in random_level:
            extra_random = 1
        elif "Randomize" in random_level:
            extra_random = 2

        self.shuffle_and_create_new_db(old_db_path, new_db_path, db_path_for_opponent, img_old_path, img_new_path, merge_choices_hex, script_old_path1, script_old_path2, script_new_path, lflist_path, extra_random, pool_size, seed)
    
    def shuffle_and_create_new_db(self, old_db_path, new_db_path, db_path_for_opponent, img_old_path, img_new_path, merge_speeds, script_old_path1, script_old_path2, script_new_path, lflist_path, extra_random, pool_size, seed):
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
        levels = [row[7] for row in datasrows]          # Level/Rank/Link rating. Pendulum scales are also stored here in the format 0xW0Y000Z, where W and Y are
                                                        # the values of the scales, and Z is the level.
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
        
        norm_effect_monst_indexes = []
        fusion_monst_indexes = []
        synchro_monst_indexes = []
        xyz_monst_indexes = []
        pend_monst_indexes = []
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
                        else:                       # Main Deck Pendulum Monster
                            pend_monst_indexes.append(i)
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
        
        all_card_indexes = [equip_spell_indexes, cont_trap_indexes, counter_trap_indexes, norm_effect_monst_indexes, xyz_monst_indexes, pend_monst_indexes, pend_xyz_indexes, pend_link_indexes, link_monst_indexes]
        
        if merge_speeds & 0x1:
            all_card_indexes.append(fusion_synchro_indexes)
            all_card_indexes.append(pend_fusion_synchro_indexes)
        else:
            all_card_indexes.append(fusion_monst_indexes)
            all_card_indexes.append(synchro_monst_indexes)
            all_card_indexes.append(pend_fusion_indexes)
            all_card_indexes.append(pend_sync_indexes)
        if merge_speeds & 0x2:
            all_card_indexes.append(norm_rit_spell_indexes)
        else:
            all_card_indexes.append(norm_spell_indexes)
            all_card_indexes.append(ritual_spell_indexes)
        if merge_speeds & 0x4:
            all_card_indexes.append(cont_field_spell_indexes)
        else:
            all_card_indexes.append(field_spell_indexes)
            all_card_indexes.append(cont_spell_indexes)
        if merge_speeds & 0x8:
            all_card_indexes.append(quick_spell_normal_trap_indexes)
        else:
            all_card_indexes.append(quick_spell_indexes)
            all_card_indexes.append(norm_trap_indexes)
        
        new_effect_id_to_old_id_dict = {}
        old_id_to_new_effect_id_dict = {}
        
        ritual_monster_id_lvs_dict = {}
        
        for index in all_card_indexes:
            # Since we have eight lists we want to shuffle the same way, we just take the list of indexes, shuffle it, and use that to put all the data in the other lists where it now belongs.
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
                # Spells and Traps need to keep atk, def, level, type, and arribute with the effect for trapmonsters to work.
                # Salamangreat Circle also has atk and def, for some reason, which probably doesn't matter, but we're including spells just in case.
                if types[index[i]] & 0x6:
                    new_atks[index[i]] = atks[index[i]]
                    new_defs[index[i]] = defs[index[i]]
                    new_levels[index[i]] = levels[index[i]]
                    new_races[index[i]] = races[index[i]]
                    new_attributes[index[i]] = attributes[index[i]]
                    if merge_speeds & 0xe:
                        new_types[index[i]] = types[shuffled_index[i]]
                else:
                    if extra_random == 1:
                        new_atks[index[i]] = atks[extra_random_shuffled_index_atk[i]]
                        new_races[index[i]] = races[extra_random_shuffled_index_race[i]]
                        new_attributes[index[i]] = attributes[extra_random_shuffled_index_attr[i]]
                        if types[index[i]] & 0x4000000:
                            new_defs[index[i]] = defs[shuffled_index[i]]
                            new_levels[index[i]] = levels[shuffled_index[i]]
                        else:
                            new_defs[index[i]] = defs[extra_random_shuffled_index_def[i]]
                            new_levels[index[i]] = levels[extra_random_shuffled_index_level[i]]
                    elif extra_random == 2:
                        new_atks[index[i]] = random.randrange(0, 3100, 100) + random.choice([0]*95 + [50]*5)
                        new_races[index[i]] = random.choice([0x1]*100 + [0x2]*100 + [0x4]*100 + [0x8]*100 + [0x10]*100 + [0x20]*100 + [0x40]*100 + [0x80]*100 + [0x100]*100 + [0x200]*100 + [0x400]*100 + [0x800]*100 + [0x1000]*100 + [0x2000]*100 + [0x4000]*100 + [0x8000]*100 + [0x10000]*100 + [0x20000]*100 + [0x40000]*100 + [0x80000]*100 + [0x100000]*100 + [0x200000]*10 + [0x400000] + [0x800000]*100 + [0x1000000]*100 + [0x2000000]*100)
                        new_attributes[index[i]] = random.choice([0x1]*100 + [0x2]*100 + [0x4]*100 + [0x8]*100 + [0x10]*100 + [0x20]*100 + [0x40])
                        # If it's a Link Monster, ramdomize the link arrows in the DEF field. And keep the levels shuffled normally so they don't break.
                        if types[index[i]] & 0x4000000:
                            arrows = 0
                            link_rating = levels[shuffled_index[i]]
                            for arrow in random.sample([0x40, 0x80, 0x100, 0x8, 0x20, 0x1, 0x2, 0x4], link_rating):
                                arrows += arrow
                            new_defs[index[i]] = arrows
                            new_levels[index[i]] = link_rating
                        # If it's a Pendulum Monster, randomize the scales along with the level.
                        elif types[index[i]] & 0x1000000:
                            pend_level = random.randrange(1, 13)
                            pend_level += random.randrange(0, 14, 1) * 0x1010000
                            new_levels[index[i]] = pend_level
                            new_defs[index[i]] = random.randrange(0, 3100, 100) + random.choice([0]*95 + [50]*5)
                        else:
                            new_defs[index[i]] = random.randrange(0, 3100, 100) + random.choice([0]*95 + [50]*5)
                            new_levels[index[i]] = random.randrange(1, 13)
                    else:   # No extra stat randomization
                        new_atks[index[i]] = atks[shuffled_index[i]]
                        new_defs[index[i]] = defs[shuffled_index[i]]
                        new_levels[index[i]] = levels[shuffled_index[i]]
                        new_races[index[i]] = races[shuffled_index[i]]
                        new_attributes[index[i]] = attributes[shuffled_index[i]]
                
                # Add alias to original cards, for cards that don't have aliases.
                if aliases[index[i]] == 0:
                    new_aliases[index[i]] = old_ids[shuffled_index[i]]
                else:
                    new_aliases[index[i]] = aliases[index[i]]
                
                new_effect_id_to_old_id_dict[new_ids[index[i]]] = old_ids[index[i]]
                old_id_to_new_effect_id_dict[old_ids[index[i]]] = new_ids[index[i]]
                
                # Collect Ritual Monster ID, the old level that ritual had, and the new level it now has.
                if types[index[i]] & 0x81 == 0x81:
                    ritual_monster_id_lvs_dict[new_ids[index[i]]] = (levels[index[i]], new_levels[index[i]])
                
                # Synchrons, Plaguespreader, and other Tuners specifically named as material for certain Synchro monsters are forced to be tuners so those cards are possible to summon.
                if old_ids[shuffled_index[i]] in [33420078, 19642774, 652362, 78868119, 56286179, 68505803, 9742784, 63977008, 21159309, 74509280, 78552773, 36107810, 96182448, 71971554, 78275321, 6142213, 67270095]:
                    new_types[index[i]] |= 0x1000
        
        # Unlike Fusion and Link monsters, Xyz and Link monsters really don't work if the materials stay with the effect instead of the name/stats. (For example, how do you handle a Rank 4 that says it takes two Level 8s or a Link-1 that says it takes 3+ monsters?)
        # While tying Fusion and Synchro materials to the name instead of the effect might be nice too, there are currently 26 Fusion and Synchro monsters that do not have materials (like Masked Heros and Ursarctics), and they would likely need to all be listed out as exceptions. And that list would need to be manually updated if any new ones are printed. So it's more practical to leave their materials tied to their effects, even if it creates an inconsistency and probably breaks a few cards.
        # Fortunately, there are no Xyz or Link monsters that do not list materials, so this works. If any are ever printed, a new solution will need to be found.
        # Also fortunately, all of the Pendulum Xyz monsters have their materials listed, so it is fine that they get left out here.
        for index in [xyz_monst_indexes, link_monst_indexes]:
            materials = {}
            for i in range(len(index)):
                materials[old_ids[index[i]]] = descs[index[i]].split('\n')[0]
            for i in range(len(index)):
                d = descs[index[i]].split('\n')
                descs[index[i]] = materials[new_ids[index[i]] - PLAYER_ID_OFFSET] + '\n' + '\n'.join(d[1:])
        
        # Some final cleanup on effect text.
        name_replace_fields = [descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s]
        for i in range(len(new_ids)):
            # Replace the old card's name with the new card's name in the effect and in the EDO prompts. So effects like hard once-per-turn effects make more sense.
            # Also give all cards extra text at the bottom to say what card their effect originally came from.
            for s in name_replace_fields:
                s[i] = s[i].replace('"' + names[i] + '"', '"' + new_names[i] + '"')
            descs[i] = descs[i] + "\r\n\r\n(Effect origin is: " + names[i] + ".)"
        
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

        # Insert the shuffled values into the new table.
        for id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16, in zip(new_ids, new_names, descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s):
            cursor_new.execute(f"INSERT INTO texts (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16))
        
        # Add in a card marked illegal that records the seed used to generate the scramble.
        cursor_new.execute(f"INSERT INTO texts (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (PLAYER_ID_OFFSET, "Scramble Seed", "This scramble was generated with the seed " + str(seed) + ".", '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''))
        
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

        # Insert the shuffled values into the new table.
        for id, alias, setcode, card_type, atk, defense, level, race, attribute, category in zip(new_ids, new_aliases, new_setcodes, new_types, new_atks, new_defs, new_levels, new_races, new_attributes, categorys):
            cursor_new.execute(f"INSERT INTO datas (id, alias, setcode, type, atk, def, level, race, attribute, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, alias, setcode, card_type, atk, defense, level, race, attribute, category))
        
        cursor_new.execute(f"INSERT INTO datas (id, ot, setcode, type, atk, def, level, race, attribute, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (PLAYER_ID_OFFSET, 8, 0, 0, 0, 0, 0, 0, 0, 0))

        # Commit the changes and close the connections.
        conn_new.commit()
        conn_new.close()
        
        # Get descriptions for opponent's database.
        opp_descs = add_flavor_text(descs, new_types, new_names, norm_effect_monst_indexes)
        
        # Create database for opponent.
        conn_new = sqlite3.connect(db_path_for_opponent)
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

        # Insert the shuffled values into the new table.
        for id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16, in zip(new_ids, new_names, opp_descs, str1s, str2s, str3s, str4s, str5s, str6s, str7s, str8s, str9s, str10s, str11s, str12s, str13s, str14s, str15s, str16s):
            cursor_new.execute(f"INSERT INTO texts (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, name, desc, str1, str2, str3, str4, str5, str6, str7, str8, str9, str10, str11, str12, str13, str14, str15, str16))
        
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
                category INTEGER
            )
        """)

        # Insert the shuffled values into the new table.
        for id, alias, setcode, card_type, atk, defense, level, race, attribute, category in zip(new_ids, new_aliases, new_setcodes, new_types, new_atks, new_defs, new_levels, new_races, new_attributes, categorys):
            cursor_new.execute(f"INSERT INTO datas (id, alias, setcode, type, atk, def, level, race, attribute, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (id, alias, setcode, card_type, atk, defense, level, race, attribute, category))

        # Commit the changes and close the connections.
        conn_new.commit()
        conn_old.close()
        conn_new.close()
        
        # Copy/Download card images.
        download_images(old_ids, img_old_path, img_new_path)
        
        # Copy scripts
        copy_scripts(old_ids, new_ids, script_old_path1, script_old_path2, script_new_path, new_types)
        
        # Fix Ritual Spells so they can summon the new correct monsters.
        fix_ritual_spells(new_ids, script_new_path, ritual_spell_indexes, new_effect_id_to_old_id_dict, old_id_to_new_effect_id_dict, ritual_monster_id_lvs_dict)
        
        # Give Xyz and Link monsters their original summoning conditions.
        fix_xyz_link_materials(new_ids, script_old_path1, script_old_path2, script_new_path, xyz_monst_indexes, link_monst_indexes)
        
        # If Field and Continuous spells were swapped, make sure they have the correct type of effects.
        if merge_speeds & 0x4:
            fix_field_cont_spell_mix(new_ids, script_new_path, cont_field_spell_indexes, types, new_types)
        
        # Fixing tokens and cards referencing original IDs
        #fix_scripts(old_ids, new_ids, script_new_path, new_types)
        
        fix_individual_cards(old_id_to_new_effect_id_dict, script_new_path)

        create_banlist_file(new_ids, lflist_path, pool_size, seed)
        
        messagebox.showinfo("Scramble complete!", "Done! You may now close the Scrambler window.")

if __name__=="__main__": 
    #main()
    root = tk.Tk()
    YGOScramblerGUI(root).pack(side="top", fill="both", expand=True)
    root.mainloop()