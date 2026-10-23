"""Step 4: import the Realm's sources (prepared by prepare_realm.py) into /Game/Realm.

- Realm_Tiles.glb -> /Game/Realm/Tiles: one static mesh per KayKit hex tile, sharing one material and texture.
- Skeleton_<Role>_Loadout.glb -> /Game/Realm/Skeleton_<Role>: one skinned mesh each (weapons skinned to the hands).
- Dragon.fbx, Horse.fbx (Quaternius) -> /Game/Realm/Dragon, /Game/Realm/Horse: skeletal meshes with their animations.
The report (Saved/step4_realm_import.json) lists bounds, material slots, UV channels and animations.
"""
import json
import os

import unreal

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJECT, 'SourceAssets', 'Realm')
ROOT = '/Game/Realm'
eal = unreal.EditorAssetLibrary
log = {'set': [], 'failed': []}


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        log['set'].append(prop)
    except Exception as exc:  # property names differ between engine versions
        log['failed'].append(f'{prop}: {exc}')


def import_file(path, dest, skeletal):
    if eal.does_directory_exist(dest):
        eal.delete_directory(dest)
    pipeline = unreal.InterchangeGenericAssetsPipeline()
    common = pipeline.get_editor_property('common_meshes_properties')
    mesh = pipeline.get_editor_property('mesh_pipeline')
    if skeletal:
        try_set(common, 'force_all_mesh_as_type', unreal.InterchangeForceMeshType.IFMT_SKELETAL_MESH)
        try_set(mesh, 'import_static_meshes', False)
    else:
        try_set(common, 'force_all_mesh_as_type', unreal.InterchangeForceMeshType.IFMT_STATIC_MESH)
        try_set(mesh, 'combine_static_meshes', False)
        try_set(mesh, 'import_skeletal_meshes', False)
    override = unreal.InterchangePipelineStackOverride()
    override.add_pipeline(pipeline)
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = dest
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.async_ = False
    task.options = override
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    eal.save_directory(dest, only_if_is_dirty=False, recursive=True)


def describe(dest):
    sm_sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sk_sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    out = []
    for path in eal.list_assets(dest, recursive=True):
        asset = eal.load_asset(path)
        e = {'path': path.split('.')[0], 'class': asset.get_class().get_name()}
        if isinstance(asset, unreal.StaticMesh):
            box = asset.get_bounding_box()
            e['min'] = [box.min.x, box.min.y, box.min.z]
            e['max'] = [box.max.x, box.max.y, box.max.z]
            e['tris'] = asset.get_num_triangles(0)
            lib = sm_sub or unreal.EditorStaticMeshLibrary
            e['uv_channels'] = lib.get_num_uv_channels(asset, 0)
            e['materials'] = [str(m.material_slot_name) for m in asset.get_editor_property('static_materials')]
        elif isinstance(asset, unreal.SkeletalMesh):
            b = asset.get_bounds()
            e['origin'] = [b.origin.x, b.origin.y, b.origin.z]
            e['extent'] = [b.box_extent.x, b.box_extent.y, b.box_extent.z]
            e['verts'] = sk_sub.get_num_verts(asset, 0)
            e['materials'] = [str(m.material_slot_name) for m in asset.get_editor_property('materials')]
            e['bones'] = asset.get_editor_property('skeleton').get_name() if asset.get_editor_property('skeleton') else None
        elif isinstance(asset, unreal.AnimSequence):
            e['length'] = unreal.AnimationLibrary.get_sequence_length(asset)
        out.append(e)
    return out


report = {}
jobs = [('Realm_Tiles.glb', f'{ROOT}/Tiles', False),
        ('Skeleton_Warrior_Loadout.glb', f'{ROOT}/Skeleton_Warrior', True),
        ('Skeleton_Minion_Loadout.glb', f'{ROOT}/Skeleton_Minion', True),
        ('Skeleton_Mage_Loadout.glb', f'{ROOT}/Skeleton_Mage', True),
        ('Dragon.fbx', f'{ROOT}/Dragon', True),
        ('Horse.fbx', f'{ROOT}/Horse', True)]
only = [s.strip() for s in os.environ.get('KNIGHT_REFINE_REALM_ONLY', '').split(',') if s.strip()]
for file, dest, skeletal in jobs:
    if only and not any(o in file for o in only):
        continue
    import_file(os.path.join(SRC, file), dest, skeletal)
    report[file] = describe(dest)
    unreal.log(f'REALM import {file}: {len(report[file])} assets')
report['pipeline'] = log
out = os.path.join(unreal.Paths.project_saved_dir(), 'step4_realm_import.json')
with open(out, 'w') as f:
    json.dump(report, f, indent=1)
unreal.log('STEP4_DONE ' + out)
