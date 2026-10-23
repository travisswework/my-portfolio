"""Prepare the Unreal source files from the KayKit Adventurers pack (run with plain Python 3, outside Unreal).

For each character: keep one loadout (drop the alternative props), give the weapon its own material slot so it can
glow without the body, keep the four animations shown on the site, then prune unused data with glTF Transform.

    python Scripts/prepare_sources.py <folder with the pack's Characters/gltf GLBs> [<gltf-transform executable>]
"""
import copy
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'SourceAssets')

# character: (source file, props to drop, weapon meshes, animations kept)
CHARACTERS = {
    'Knight': ('Knight.glb', {'1H_Sword_Offhand', 'Rectangle_Shield', 'Round_Shield', 'Spike_Shield', '2H_Sword'},
               {'1H_Sword'}, ['Idle', '1H_Melee_Attack_Slice_Diagonal', 'Blocking', 'Cheer']),
    'Barbarian': ('Barbarian.glb', {'1H_Axe_Offhand', 'Barbarian_Round_Shield', '1H_Axe', 'Mug'},
                  {'2H_Axe'}, ['2H_Melee_Idle', '2H_Melee_Attack_Chop', '2H_Melee_Attack_Spin', 'Cheer']),
    'Mage': ('Mage.glb', {'Spellbook', 'Spellbook_open', '1H_Wand'},
             {'2H_Staff'}, ['Idle', 'Spellcast_Shoot', 'Spellcasting', 'Cheer']),
    'Rogue': ('Rogue.glb', {'1H_Crossbow', '2H_Crossbow', 'Throwable'},
              {'Knife', 'Knife_Offhand'}, ['Idle', 'Dualwield_Melee_Attack_Slice', 'Dualwield_Melee_Attack_Stab', 'Cheer']),
    'RogueHooded': ('Rogue_Hooded.glb', {'2H_Crossbow', 'Knife', 'Throwable'},
                    {'1H_Crossbow', 'Knife_Offhand'}, ['Idle', '1H_Ranged_Shoot', '1H_Ranged_Reload', 'Cheer']),
}


def prepare(name, pack_dir, gltf_transform):
    src, drop, weapons, anims = CHARACTERS[name]
    b = open(os.path.join(pack_dir, src), 'rb').read()
    ln = struct.unpack('<I', b[12:16])[0]
    j = json.loads(b[20:20 + ln])
    binchunk = b[20 + ln:]
    for n in j['nodes']:
        if n.get('name') in drop:
            n.pop('mesh', None)
    weapon_mat = copy.deepcopy(j['materials'][0])
    weapon_mat['name'] = f'{name.lower()}_weapon' if name != 'Knight' else 'knight_blade'
    j['materials'].append(weapon_mat)
    for n in j['nodes']:
        if n.get('name') in weapons and 'mesh' in n:
            for p in j['meshes'][n['mesh']]['primitives']:
                p['material'] = len(j['materials']) - 1
    missing = set(anims) - {a['name'] for a in j['animations']}
    assert not missing, f'{name}: missing animations {missing}'
    j['animations'] = [a for a in j['animations'] if a['name'] in anims]
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    raw = os.path.join(OUT, f'{name}_Loadout_raw.glb')
    with open(raw, 'wb') as f:
        f.write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + len(binchunk)) + struct.pack('<I', len(js)) + b'JSON' + js + binchunk)
    final = os.path.join(OUT, f'{name}_Loadout.glb')
    subprocess.run([gltf_transform, 'prune', raw, final], check=True, capture_output=True)
    os.remove(raw)
    return final, os.path.getsize(final)


if __name__ == '__main__':
    pack = sys.argv[1]
    tool = sys.argv[2] if len(sys.argv) > 2 else 'gltf-transform'
    names = sys.argv[3].split(',') if len(sys.argv) > 3 else list(CHARACTERS)
    for character in names:
        print(character, prepare(character, pack, tool))
