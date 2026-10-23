"""Step 2: refinement pass on each imported character, then glTF export for the portfolio site.

- New look-dev materials (built node by node): each palette swatch is re-graded into a PBR response (polished steel,
  gunmetal, dark leathers, house cloth, gold or bronze trims), plus a weapon material on the weapon's own slot
  with an emissive accent (the knight's enchanted blade, the barbarian's ember edge, the mage's crystal, ...).
  The per-character swatch tables are in characters.py.
- LOD chain generated with Unreal's skeletal mesh reduction.
- glTF export per LOD with the new materials baked to textures, plus each animation.
"""
import json
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characters  # noqa: E402

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
EXPORT = os.path.join(PROJECT, 'Export')
sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
from lookdev import build_material, mesh_export_options, anim_export_options  # noqa: E402


def refine(cfg):
    report = {'notes': []}
    folder, prefix = cfg['folder'], cfg['export']
    out_dir = f'{folder}/Refined'
    texture = unreal.EditorAssetLibrary.load_asset(f"{folder}/{cfg['texture']}")
    main_mat = build_material(out_dir, cfg['main_material'], texture, characters.HEADER + cfg['main'])
    weapon_mat = build_material(out_dir, cfg['weapon_material'], texture, characters.HEADER + cfg['main'] + cfg['weapon'])

    skm = unreal.EditorAssetLibrary.load_asset(f"{folder}/{cfg['asset']}")
    # Struct elements come back as copies, so write each one back by index.
    slots = skm.get_editor_property('materials')
    for i in range(len(slots)):
        slot = slots[i]
        slot_name = str(slot.get_editor_property('material_slot_name'))
        slot.set_editor_property('material_interface', weapon_mat if slot_name.endswith(('_blade', '_weapon')) else main_mat)
        slots[i] = slot
    skm.set_editor_property('materials', slots)
    report['slots'] = [(str(s.get_editor_property('material_slot_name')), s.get_editor_property('material_interface').get_name())
                       for s in skm.get_editor_property('materials')]

    # ------------------------------------------------------------ LODs
    try:
        lod_settings = unreal.new_object(unreal.SkeletalMeshLODSettings, outer=skm)
        groups = []
        for pct in (1.0, 0.5, 0.25):
            group = unreal.SkeletalMeshLODGroupSettings()
            rs = group.get_editor_property('reduction_settings')
            rs.set_editor_property('num_of_triangles_percentage', pct)
            rs.set_editor_property('num_of_vert_percentage', pct)
            group.set_editor_property('reduction_settings', rs)
            groups.append(group)
        lod_settings.set_editor_property('lod_groups', groups)
        skm.set_editor_property('lod_settings', lod_settings)
        report['notes'].append('LOD settings applied: 100% / 50% / 25% triangles')
    except Exception as exc:
        report['notes'].append(f'LOD settings not applied, using engine defaults: {exc}')
    ok = unreal.EditorSkeletalMeshLibrary.regenerate_lod(skm, 3, True, False)
    report['notes'].append(f'regenerate_lod(3): {ok}')
    report['lod_verts'] = [sub.get_num_verts(skm, i) for i in range(sub.get_lod_count(skm))]
    unreal.EditorAssetLibrary.save_loaded_asset(skm)

    # ------------------------------------------------------------ export
    os.makedirs(EXPORT, exist_ok=True)
    opts = mesh_export_options(report)
    report['exports'] = {}
    for lod in range(sub.get_lod_count(skm)):
        opts.set_editor_property('default_level_of_detail', lod)
        path = os.path.join(EXPORT, f'{prefix}_refined_lod{lod}.glb')
        result = unreal.GLTFExporter.export_to_gltf(skm, path, opts, set())
        report['exports'][f'lod{lod}'] = [str(result), os.path.exists(path) and os.path.getsize(path)]

    anim_opts = anim_export_options(lod=2)
    for key, anim_name in cfg['anims'].items():
        anim = unreal.EditorAssetLibrary.load_asset(f"{folder}/{cfg['asset']}{anim_name}")
        path = os.path.join(EXPORT, f'{prefix}_anim_{key}.glb')
        result = unreal.GLTFExporter.export_to_gltf(anim, path, anim_opts, set())
        report['exports'][f'anim_{key}'] = [str(result), os.path.exists(path) and os.path.getsize(path)]

    unreal.EditorAssetLibrary.save_directory(folder, only_if_is_dirty=False, recursive=True)
    return report


reports = {}
for name, cfg in characters.selected():
    reports[name] = refine(cfg)
    unreal.log(f'STEP2 {name} done')
out = os.path.join(unreal.Paths.project_saved_dir(), 'step2_refine.json')
with open(out, 'w') as f:
    json.dump(reports, f, indent=1, default=str)
unreal.log('STEP2_DONE ' + out)
