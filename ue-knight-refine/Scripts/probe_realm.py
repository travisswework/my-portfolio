"""Diagnostics for the Realm level (run through run.ps1 like the steps): tile mesh UVs, Nanite, and a test capture."""
import json
import os

import unreal

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
report = {}
sm = eal.load_asset('/Game/Realm/Tiles/hex_grass')
for name, fn in [('uv_channels_lib', lambda: unreal.EditorStaticMeshLibrary.get_num_uv_channels(sm, 0)),
                 ('lods', lambda: sm.get_num_lods()),
                 ('nanite', lambda: sm.get_editor_property('nanite_settings').get_editor_property('enabled')),
                 ('tris', lambda: sm.get_num_triangles(0)),
                 ('lightmap_coord', lambda: sm.get_editor_property('light_map_coordinate_index'))]:
    try:
        report[name] = str(fn())
    except Exception as exc:
        report[name] = f'error: {exc}'
world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Realm/Map_Realm')
eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(0, -40, 30))


def shot(name):
    cap_actor = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(1100, 2450, 1550), unreal.Rotator(0, -30, -110))
    cap = cap_actor.get_editor_property('capture_component2d')
    cap.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cap.set_editor_property('fov_angle', 60.0)
    rt = unreal.RenderingLibrary.create_render_target2d(world, 640, 360, unreal.TextureRenderTargetFormat.RTF_RGBA8, unreal.LinearColor(0, 0, 0, 1))
    cap.set_editor_property('texture_target', rt)
    cap.capture_scene()
    cap.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, os.path.join(PROJECT, 'Saved'), f'{name}.png')


shot('probe_tiles')
# same view with a flat grey material on every tile: is the geometry there and lit?
grey = eal.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.StaticMeshActor):
        a.static_mesh_component.set_material(0, grey)
shot('probe_grey')
with open(os.path.join(unreal.Paths.project_saved_dir(), 'probe_realm.json'), 'w') as f:
    json.dump(report, f, indent=1, default=str)
unreal.log('PROBE_DONE')
