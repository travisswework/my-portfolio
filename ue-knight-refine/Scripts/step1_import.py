"""Step 1: import the CC0 KayKit characters (loadouts prepared by prepare_sources.py) into /Game/<Character>,
each as one combined skeletal mesh (body parts + headgear, cape and weapons skinned to their bones)."""
import json
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characters  # noqa: E402

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
sub = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def try_set(log, obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
        log['set'].append(prop)
    except Exception as exc:  # property names differ between engine versions
        log['failed'].append(f'{prop}: {exc}')


def import_character(cfg):
    dest = cfg['folder']
    log = {'set': [], 'failed': []}
    # Start from a clean folder (only this project's own assets).
    if unreal.EditorAssetLibrary.does_directory_exist(dest):
        unreal.EditorAssetLibrary.delete_directory(dest)

    pipeline = unreal.InterchangeGenericAssetsPipeline()
    common = pipeline.get_editor_property('common_meshes_properties')
    mesh = pipeline.get_editor_property('mesh_pipeline')
    try_set(log, common, 'force_all_mesh_as_type', unreal.InterchangeForceMeshType.IFMT_SKELETAL_MESH)
    try_set(log, mesh, 'combine_skeletal_meshes', True)
    try_set(log, mesh, 'import_static_meshes', False)

    override = unreal.InterchangePipelineStackOverride()
    override.add_pipeline(pipeline)

    task = unreal.AssetImportTask()
    task.filename = os.path.join(PROJECT, 'SourceAssets', cfg['source'])
    task.destination_path = dest
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.async_ = False
    task.options = override
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    report = {'pipeline': log, 'imported': list(task.imported_object_paths), 'assets': []}
    for path in unreal.EditorAssetLibrary.list_assets(dest, recursive=True):
        asset = unreal.EditorAssetLibrary.load_asset(path)
        entry = {'path': path, 'class': asset.get_class().get_name()}
        if isinstance(asset, unreal.SkeletalMesh):
            entry['lods'] = sub.get_lod_count(asset)
            entry['verts_lod0'] = sub.get_num_verts(asset, 0)
            entry['sections_lod0'] = sub.get_num_sections(asset, 0)
            entry['materials'] = [str(m.material_slot_name) for m in asset.get_editor_property('materials')]
            b = asset.get_bounds()
            entry['bounds_extent'] = [b.box_extent.x, b.box_extent.y, b.box_extent.z]
        report['assets'].append(entry)
    unreal.EditorAssetLibrary.save_directory(dest, only_if_is_dirty=False, recursive=True)
    return report


reports = {name: import_character(cfg) for name, cfg in characters.selected()}
out = os.path.join(unreal.Paths.project_saved_dir(), 'step1_import.json')
with open(out, 'w') as f:
    json.dump(reports, f, indent=1)
unreal.log('STEP1_DONE ' + out)
