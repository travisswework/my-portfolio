"""Step 5: refine the Realm in Unreal and export it for the site (Export/Realm).

- World: a look-dev material for the hex atlas (realm.TILES), assigned to every tile; the map from realm_layout.py
  is assembled as a level of placed tiles (saved as /Game/Realm/Map_Realm for step6) and exported as one glTF,
  with each tile mesh written once and instanced, and the material baked to a 1024 px texture.
- Dragon: new materials per slot (obsidian scales, backlit wings, molten belly, burning eyes) and its animations.
- Horses: three coats (chestnut, grey, black) on the one mesh, and its gaits.
- Skeleton army: graded atlas material, iron weapons, spectral eye glow, LODs at 100/50 %, and the shared animations.

KNIGHT_REFINE_REALM_ONLY (comma separated: world, dragon, horse, skeletons) limits the run.
"""
import json
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realm  # noqa: E402
import realm_layout  # noqa: E402
from lookdev import build_material, constant_material, mesh_export_options, anim_export_options, make_lods, set_slots  # noqa: E402

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
EXPORT = os.path.join(PROJECT, 'Export', 'Realm')
ROOT = '/Game/Realm'
OUT = f'{ROOT}/Refined'
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {'notes': [], 'exports': {}}
ONLY = [s.strip() for s in os.environ.get('KNIGHT_REFINE_REALM_ONLY', '').split(',') if s.strip()]
os.makedirs(EXPORT, exist_ok=True)

# meshes that make up one decoration (the windmill's sails are their own mesh so the site can turn them)
PARTS = {'building_windmill_blue': ['building_windmill_blue', 'building_windmill_top_blue', 'building_windmill_top_fan_blue']}


def export(obj, name, opts, actors=()):
    path = os.path.join(EXPORT, name)
    ok = unreal.GLTFExporter.export_to_gltf(obj, path, opts, set(actors))
    report['exports'][name] = [str(ok), os.path.exists(path) and os.path.getsize(path)]


def export_anims(folder, prefix, anims, out_prefix, lod=0):
    opts = anim_export_options(lod)
    for key, name in anims.items():
        anim = eal.load_asset(f'{folder}/{prefix}{name}')
        export(anim, f'{out_prefix}_anim_{key}.glb', opts)


def world():
    tex = eal.load_asset(f'{ROOT}/Tiles/hexagons_medieval')
    mat = build_material(OUT, 'M_Realm_Tiles', tex, realm.TILES, skeletal=False)
    meshes = {}
    for path in eal.list_assets(f'{ROOT}/Tiles', recursive=False):
        asset = eal.load_asset(path)
        if isinstance(asset, unreal.StaticMesh):
            asset.set_material(0, mat)
            # tiles are tiny; plain meshes also render completely in a headless capture (Nanite pages never stream in)
            nanite = asset.get_editor_property('nanite_settings')
            if nanite.get_editor_property('enabled'):
                nanite.set_editor_property('enabled', False)
                asset.set_editor_property('nanite_settings', nanite)
            eal.save_loaded_asset(asset)
            meshes[asset.get_name()] = asset
    level = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    tiles, meta = realm_layout.build()
    actors = []

    def place(name, t, turn):
        # glTF (x, y, z) -> Unreal (100x, 100z, 100y); a turn k (-60k deg about glTF +y) is a +60k deg yaw here
        for part in PARTS.get(name, [name]):
            a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(t['x'] * 100, t['z'] * 100, 0), unreal.Rotator(0, 0, 60 * turn))
            a.static_mesh_component.set_static_mesh(meshes[part])
            a.set_actor_label(f"{part}@{t['q']},{t['r']}")
            actors.append(a)
    for t in tiles:
        place(t['tile'], t, t['turn'])
        for d in t['deco']:
            place(d['name'], t, d['turn'])
    report['world_actors'] = len(actors)
    opts = mesh_export_options(report, bake_size=1024)
    for prop, value in (('export_lights', False), ('export_cameras', False)):
        try:
            opts.set_editor_property(prop, value)
        except Exception as exc:
            report['notes'].append(f'{prop}: {exc}')
    export(level, 'realm_world.glb', opts, actors)
    unreal.EditorLoadingAndSavingUtils.save_map(level, f'{ROOT}/Map_Realm')
    with open(os.path.join(EXPORT, 'realm_layout.json'), 'w') as f:
        json.dump({'tiles': [{k: t[k] for k in ('q', 'r', 'x', 'z', 'kind')} for t in tiles], 'meta': meta}, f)


def dragon():
    mats = {slot: constant_material(OUT, f'M_Dragon_{slot}', **cfg) for slot, cfg in realm.DRAGON.items()}
    body = eal.load_asset(f'{ROOT}/Dragon/Dragon')
    eyes = eal.load_asset(f'{ROOT}/Dragon/Eyes1')
    report['dragon_slots'] = set_slots(body, mats)
    report['dragon_eye_slots'] = set_slots(eyes, mats)
    for a in (body, eyes):
        eal.save_loaded_asset(a)
    opts = mesh_export_options(report)
    export(body, 'dragon.glb', opts)
    export(eyes, 'dragon_eyes.glb', opts)
    export_anims(f'{ROOT}/Dragon', 'DragonDragonArmature_', realm.DRAGON_ANIMS, 'dragon')


def horse():
    body = eal.load_asset(f'{ROOT}/Horse/Horse')
    # the source has a coat material and a darker mane/hoof material: tell them apart by their colour
    lum = {}
    for slot in body.get_editor_property('materials'):
        mi = slot.get_editor_property('material_interface')
        values = mi.get_editor_property('vector_parameter_values') if isinstance(mi, unreal.MaterialInstance) else []
        col = values[0].get_editor_property('parameter_value') if values else unreal.LinearColor(0.5, 0.5, 0.5, 1)
        lum[str(slot.get_editor_property('material_slot_name'))] = 0.2126 * col.r + 0.7152 * col.g + 0.0722 * col.b
    coat_slot, mane_slot = sorted(lum, key=lum.get, reverse=True)
    report['horse_slots'] = {'coat': coat_slot, 'mane': mane_slot, 'luminance': lum}
    opts = mesh_export_options(report)
    for coat, cfg in realm.HORSE_COATS.items():
        coat_mat = constant_material(OUT, f'M_Horse_{coat}_Coat', cfg['coat'], rough=0.55)
        mane_mat = constant_material(OUT, f'M_Horse_{coat}_Mane', cfg['mane'], rough=0.45)
        set_slots(body, {coat_slot: coat_mat, mane_slot: mane_mat})
        export(body, f'horse_{coat}.glb', opts)
    eal.save_loaded_asset(body)  # keeps the last coat (black); the beauty step sets its own per horse
    export_anims(f'{ROOT}/Horse', 'HorseArmature_', realm.HORSE_ANIMS, 'horse')


def skeletons():
    tex = eal.load_asset(f'{ROOT}/Skeleton_Warrior/skeleton_texture')
    main = build_material(OUT, 'M_Skeleton', tex, realm.SKELETON)
    weapon = build_material(OUT, 'M_Skeleton_Weapon', tex, realm.SKELETON_WEAPON)
    col, strength = realm.SKELETON_GLOW
    glow = constant_material(OUT, 'M_Skeleton_Glow', col, rough=0.3, emissive=tuple(c * strength for c in col))
    sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    for role in realm.ROLES:
        skm = eal.load_asset(f'{ROOT}/Skeleton_{role}/Skeleton_{role}_Loadout')
        report[f'skeleton_{role}_slots'] = set_slots(skm, {'skeleton': main, 'Glow': glow, f'skeleton_{role.lower()}_weapon': weapon})
        report[f'skeleton_{role}_lods'] = str(make_lods(skm, (1.0, 0.5), report))
        report[f'skeleton_{role}_verts'] = [sub.get_num_verts(skm, i) for i in range(sub.get_lod_count(skm))]
        eal.save_loaded_asset(skm)
        opts = mesh_export_options(report)
        for lod in range(sub.get_lod_count(skm)):
            opts.set_editor_property('default_level_of_detail', lod)
            export(skm, f'skeleton_{role.lower()}_lod{lod}.glb', opts)
    export_anims(f'{ROOT}/Skeleton_Warrior', 'Skeleton_Warrior_Loadout', realm.SKELETON_ANIMS, 'skeleton', lod=1)


for name, fn in (('world', world), ('dragon', dragon), ('horse', horse), ('skeletons', skeletons)):
    if not ONLY or name in ONLY:
        fn()
        unreal.log(f'STEP5 {name} done')
out = os.path.join(unreal.Paths.project_saved_dir(), 'step5_realm_refine.json')
with open(out, 'w') as f:
    json.dump(report, f, indent=1, default=str)
unreal.log('STEP5_DONE ' + out)
