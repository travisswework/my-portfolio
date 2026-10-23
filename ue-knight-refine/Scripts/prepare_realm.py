"""Prepare the Realm's Unreal sources (run with plain Python 3, outside Unreal).

- SourceAssets/Realm/Realm_Tiles.glb: every KayKit Medieval Hexagon mesh the map uses (realm_layout.py), one node and
  mesh per tile at the origin, sharing a single material and texture, so Unreal imports the atlas once.
- SourceAssets/Realm/Skeleton_<Role>_Loadout.glb: KayKit skeletons with their weapons parented to the hand slots
  (Unreal skins them to those bones on import), the weapons on their own material slot, and only the animations
  the realm uses.
- Dragon.fbx and Horse.fbx (Quaternius) are copied as they are; Unreal imports FBX directly.

    python Scripts/prepare_realm.py <hexagon pack dir> <skeletons gltf dir> <monsters FBX dir> <farm animals FBX dir>
"""
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import realm_layout  # noqa: E402

OUT = os.path.join(HERE, '..', 'SourceAssets', 'Realm')

SKELETONS = {
    # role: (character file, {hand slot: weapon file})
    'Warrior': ('Skeleton_Warrior.glb', {'handslot.r': 'Skeleton_Axe.gltf', 'handslot.l': 'Skeleton_Shield_Large_A.gltf'}),
    'Minion': ('Skeleton_Minion.glb', {'handslot.r': 'Skeleton_Blade.gltf', 'handslot.l': 'Skeleton_Shield_Small_A.gltf'}),
    'Mage': ('Skeleton_Mage.glb', {'handslot.r': 'Skeleton_Staff.gltf'}),
}
SKELETON_ANIMS = ['Idle_Combat', 'Running_A', '1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', 'Block', 'Taunt',
                  'Cheer', 'Spellcasting', 'Spellcast_Summon', 'Spawn_Ground_Skeletons', 'Death_C_Skeletons',
                  'Death_C_Skeletons_Resurrect']


def read_any(path):
    """(json, binary chunk) for a .glb or a .gltf with one external buffer."""
    if path.endswith('.glb'):
        b = open(path, 'rb').read()
        ln = struct.unpack('<I', b[12:16])[0]
        return json.loads(b[20:20 + ln]), b[20 + ln + 8:]
    j = json.load(open(path))
    assert len(j['buffers']) == 1
    return j, open(os.path.join(os.path.dirname(path), j['buffers'][0]['uri']), 'rb').read()


def write_glb(j, binary, path):
    binary = binary + b'\0' * ((4 - len(binary) % 4) % 4)
    j['buffers'] = [{'byteLength': len(binary)}]
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    with open(path, 'wb') as f:
        f.write(b'glTF' + struct.pack('<II', 2, 28 + len(js) + len(binary)))
        f.write(struct.pack('<I', len(js)) + b'JSON' + js)
        f.write(struct.pack('<I', len(binary)) + b'BIN\0' + binary)


class Builder:
    """Appends meshes (and their accessors) from other glTF files into one document."""

    def __init__(self, j, binary):
        self.j, self.bin = j, bytearray(binary)
        for b in self.j['bufferViews']:
            b['buffer'] = 0

    def add_mesh(self, src, src_bin, mesh_index, material):
        views, accs = {}, {}

        def view(i):
            if i not in views:
                v = dict(src['bufferViews'][i])
                data = src_bin[v.get('byteOffset', 0): v.get('byteOffset', 0) + v['byteLength']]
                self.bin += b'\0' * ((4 - len(self.bin) % 4) % 4)
                v['byteOffset'], v['buffer'] = len(self.bin), 0
                self.bin += data
                self.j['bufferViews'].append(v)
                views[i] = len(self.j['bufferViews']) - 1
            return views[i]

        def acc(i):
            if i not in accs:
                a = dict(src['accessors'][i])
                a['bufferView'] = view(a['bufferView'])
                self.j['accessors'].append(a)
                accs[i] = len(self.j['accessors']) - 1
            return accs[i]

        mesh = json.loads(json.dumps(src['meshes'][mesh_index]))
        for p in mesh['primitives']:
            p['attributes'] = {k: acc(v) for k, v in p['attributes'].items()}
            if 'indices' in p:
                p['indices'] = acc(p['indices'])
            p['material'] = material
        self.j['meshes'].append(mesh)
        return len(self.j['meshes']) - 1


def tiles(hex_dir):
    names = realm_layout.meshes_used(realm_layout.build()[0])
    files = {}
    for root, _, fs in os.walk(hex_dir):
        for f in fs:
            if f.endswith('.gltf'):
                files.setdefault(f[:-5], os.path.join(root, f))
    first, first_bin = read_any(files[names[0]])
    doc = {'asset': {'version': '2.0', 'generator': 'prepare_realm.py'}, 'scene': 0, 'scenes': [{'nodes': []}],
           'nodes': [], 'meshes': [], 'accessors': [], 'bufferViews': [],
           'materials': [dict(first['materials'][0], name='hexagons_medieval')],
           'textures': [{'source': 0, **({'sampler': 0} if first.get('samplers') else {})}],
           'samplers': first.get('samplers', [])[:1],
           'images': [{'name': 'hexagons_medieval', 'mimeType': 'image/png', 'bufferView': 0}]}
    png = open(os.path.join(os.path.dirname(files[names[0]]), first['images'][0]['uri']), 'rb').read()
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': 0, 'byteLength': len(png)})
    mat = doc['materials'][0]
    mat.setdefault('pbrMetallicRoughness', {})['baseColorTexture'] = {'index': 0}
    b = Builder(doc, png)
    for name in names:
        src, src_bin = read_any(files[name])

        def copy(ni, parent):
            n = src['nodes'][ni]
            node = {k: n[k] for k in ('name', 'translation', 'rotation', 'scale') if k in n}
            if 'mesh' in n:
                node['mesh'] = b.add_mesh(src, src_bin, n['mesh'], 0)
                doc['meshes'][node['mesh']]['name'] = n.get('name', name)
            doc['nodes'].append(node)
            idx = len(doc['nodes']) - 1
            if parent is None:
                doc['scenes'][0]['nodes'].append(idx)
            else:
                doc['nodes'][parent].setdefault('children', []).append(idx)
            for c in n.get('children', []):
                copy(c, idx)
        for root in src['scenes'][src.get('scene', 0)]['nodes']:
            copy(root, None)
    out = os.path.join(OUT, 'Realm_Tiles.glb')
    write_glb(doc, bytes(b.bin), out)
    return out, len(names)


def skeleton(role, skel_dir):
    char_file, weapons = SKELETONS[role]
    j, binary = read_any(os.path.join(skel_dir, char_file))
    b = Builder(j, binary)
    weapon_mat = dict(j['materials'][0], name=f'skeleton_{role.lower()}_weapon')
    j['materials'].append(weapon_mat)
    for slot, wfile in weapons.items():
        src, src_bin = read_any(os.path.join(skel_dir, wfile))
        parent = next(i for i, n in enumerate(j['nodes']) if n.get('name') == slot)
        src_node = next(n for n in src['nodes'] if 'mesh' in n)
        mesh = b.add_mesh(src, src_bin, src_node['mesh'], len(j['materials']) - 1)
        j['meshes'][mesh]['name'] = wfile[:-5]
        j['nodes'].append({'name': wfile[:-5], 'mesh': mesh})
        j['nodes'][parent].setdefault('children', []).append(len(j['nodes']) - 1)
    missing = set(SKELETON_ANIMS) - {a['name'] for a in j['animations']}
    assert not missing, missing
    j['animations'] = [a for a in j['animations'] if a['name'] in SKELETON_ANIMS]
    out = os.path.join(OUT, f'Skeleton_{role}_Loadout.glb')
    write_glb(j, bytes(b.bin), out + '.raw.glb')
    return out


if __name__ == '__main__':
    hex_dir, skel_dir, monsters, farm = sys.argv[1:5]
    tool = sys.argv[5] if len(sys.argv) > 5 else 'gltf-transform'
    os.makedirs(OUT, exist_ok=True)
    print(tiles(hex_dir))
    import subprocess
    for role in SKELETONS:
        out = skeleton(role, skel_dir)
        # drop the buffer data the trimmed animations no longer use
        subprocess.run([tool, 'prune', out + '.raw.glb', out], check=True, capture_output=True)
        os.remove(out + '.raw.glb')
        print(out, os.path.getsize(out))
    shutil.copy(os.path.join(monsters, 'Dragon.fbx'), os.path.join(OUT, 'Dragon.fbx'))
    shutil.copy(os.path.join(farm, 'Horse.fbx'), os.path.join(OUT, 'Horse.fbx'))
    print('copied Dragon.fbx, Horse.fbx')
