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
MEL = unreal.MaterialEditingLibrary
assets = unreal.AssetToolsHelpers.get_asset_tools()
sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)

# ---------------------------------------------------------------- materials
OUTPUTS = [
    ('Base', 'return base;', unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.MaterialProperty.MP_BASE_COLOR),
    ('Metal', 'return metal;', unreal.CustomMaterialOutputType.CMOT_FLOAT1, unreal.MaterialProperty.MP_METALLIC),
    ('Rough', 'return rough;', unreal.CustomMaterialOutputType.CMOT_FLOAT1, unreal.MaterialProperty.MP_ROUGHNESS),
    ('Glow', 'return emi;', unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.MaterialProperty.MP_EMISSIVE_COLOR),
]


def build_material(out_dir, name, texture, code):
    path = f'{out_dir}/{name}'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    mat = assets.create_asset(name, out_dir, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('used_with_skeletal_mesh', True)  # compile the skinned permutations up front
    uv = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -1100, 0)
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -850, 0)
    tex.set_editor_property('texture', texture)
    MEL.connect_material_expressions(uv, '', tex, 'UVs')
    for i, (label, ret, otype, prop) in enumerate(OUTPUTS):
        node = MEL.create_material_expression(mat, unreal.MaterialExpressionCustom, -450, -300 + i * 200)
        node.set_editor_property('description', f'Swatch grade: {label}')
        node.set_editor_property('output_type', otype)
        pins = []
        for pin in ('UV', 'C'):
            ci = unreal.CustomInput()
            ci.set_editor_property('input_name', pin)
            pins.append(ci)
        node.set_editor_property('inputs', pins)
        node.set_editor_property('code', code + ret)
        MEL.connect_material_expressions(uv, '', node, 'UV')
        MEL.connect_material_expressions(tex, 'RGB', node, 'C')
        MEL.connect_material_property(node, '', prop)
    MEL.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def mesh_export_options(report):
    opts = unreal.GLTFExportOptions()
    opts.set_editor_property('bake_material_inputs', unreal.GLTFMaterialBakeMode.SIMPLE)
    try:
        size = opts.get_editor_property('default_material_bake_size')
        for field, value in (('x', 512), ('y', 512), ('auto_detect', False), ('b_auto_detect', False)):
            try:
                size.set_editor_property(field, value)
            except Exception:
                pass
        opts.set_editor_property('default_material_bake_size', size)
    except Exception as exc:
        report['notes'].append(f'bake size not set: {exc}')
    for prop, value in (('export_vertex_skin_weights', True), ('export_emissive_strength', True), ('export_morph_targets', False),
                        ('texture_image_format', unreal.GLTFTextureImageFormat.PNG)):
        try:
            opts.set_editor_property(prop, value)
        except Exception as exc:
            report['notes'].append(f'{prop}: {exc}')
    return opts


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

    anim_opts = unreal.GLTFExportOptions()
    anim_opts.set_editor_property('bake_material_inputs', unreal.GLTFMaterialBakeMode.DISABLED)
    anim_opts.set_editor_property('default_level_of_detail', 2)
    anim_opts.set_editor_property('export_vertex_skin_weights', True)
    anim_opts.set_editor_property('export_animation_sequences', True)
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
