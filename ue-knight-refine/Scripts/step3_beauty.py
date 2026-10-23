"""Step 3: render a beauty still of each refined character inside Unreal (studio level + scene capture).

Builds a small studio in a fresh map (plinth with a glowing rim, softbox rect lights), then for each character:
spawns it, poses it from one of its animations, sets the rim lights to its accent colours and captures raw HDR
scene colour to Export/Beauty. Exposure, filmic curve, bloom and the backdrop are graded afterwards by
grade_beauty.py, because a headless capture can't rely on Unreal's auto exposure.

With KNIGHT_REFINE_PREVIEW=1 (run.ps1 -Preview) it instead captures small frames of several poses per character,
and with KNIGHT_REFINE_PREVIEW=angles (-Preview angles) the chosen pose from four sides, for picking the shot that
goes in characters.py.
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import characters  # noqa: E402

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
OUT = os.path.join(PROJECT, 'Export', 'Beauty')
MAT_DIR = '/Game/Knight/Showcase'
PREVIEW = os.environ.get('KNIGHT_REFINE_PREVIEW', '')  # '1': pose grid, 'angles': the chosen pose from 4 sides
KNIGHT_HALF_HEIGHT = 123.33  # the camera distances below were set up for the knight
MEL = unreal.MaterialEditingLibrary
assets = unreal.AssetToolsHelpers.get_asset_tools()
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = {'notes': [], 'captures': []}


def note(msg):
    log['notes'].append(str(msg))
    unreal.log('BEAUTY ' + str(msg))


def flat_material(name, props, unlit=False):
    path = f'{MAT_DIR}/{name}'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    mat = assets.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property('two_sided', True)
    if unlit:
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    for prop, value in props.items():
        node = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector if isinstance(value, tuple) else unreal.MaterialExpressionConstant, -300, 0)
        if isinstance(value, tuple):
            node.set_editor_property('constant', unreal.LinearColor(*value, 1.0))
        else:
            node.set_editor_property('r', value)
        MEL.connect_material_property(node, '', prop)
    MEL.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


# ---------------------------------------------------------------- level
world = None
try:
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    note(f'new blank map: {world}')
except Exception as exc:
    note(f'new_blank_map failed: {exc}')
if world is None:
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    note(f'using editor world: {world}')

# ---------------------------------------------------------------- studio
plinth_mat = flat_material('M_Plinth', {
    unreal.MaterialProperty.MP_BASE_COLOR: (0.025, 0.018, 0.06),
    unreal.MaterialProperty.MP_ROUGHNESS: 0.32,
    unreal.MaterialProperty.MP_METALLIC: 0.25,
})
rim_mat = flat_material('M_PlinthRim', {unreal.MaterialProperty.MP_EMISSIVE_COLOR: (3.0, 1.9, 0.6)}, unlit=True)

cyl = unreal.EditorAssetLibrary.load_asset('/Engine/BasicShapes/Cylinder')
plinth = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -10), unreal.Rotator(0, 0, 0))
plinth.static_mesh_component.set_static_mesh(cyl)
plinth.set_actor_scale3d(unreal.Vector(3.4, 3.4, 0.2))
plinth.static_mesh_component.set_material(0, plinth_mat)
rim = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -1.4), unreal.Rotator(0, 0, 0))
rim.static_mesh_component.set_static_mesh(cyl)
rim.set_actor_scale3d(unreal.Vector(3.47, 3.47, 0.024))
rim.static_mesh_component.set_material(0, rim_mat)


def light(cls, loc, target, intensity, rgb, **kw):
    """Spawn a light aimed at target. Colours go through set_light_color (unreal.Color is BGRA-ordered)."""
    d = target - loc
    rot = unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x)))
    a = eas.spawn_actor_from_class(cls, loc, rot)
    comp = a.get_component_by_class(unreal.LightComponent)
    if 'units' in kw:
        comp.set_editor_property('intensity_units', kw.pop('units'))
    comp.set_editor_property('intensity', intensity)
    comp.set_light_color(unreal.LinearColor(*rgb, 1.0))
    for k, v in kw.items():
        comp.set_editor_property(k, v)
    return comp


aim_at = unreal.Vector(0, 0, KNIGHT_HALF_HEIGHT)
front = math.radians(120)  # the characters face roughly this way in the imported rig


def around(deg, dist, z):
    r = front + math.radians(deg)
    return unreal.Vector(math.cos(r) * dist, math.sin(r) * dist, z)


# studio softboxes: broad shapes the polished metals can reflect, plus two coloured rims set per character
soft = dict(units=unreal.LightUnits.CANDELAS, attenuation_radius=2000.0)
key_light = light(unreal.RectLight, around(-40, 330, 300), aim_at, 1600, (1.0, 0.93, 0.84), source_width=220.0, source_height=160.0, **soft)
rim_a = light(unreal.RectLight, around(150, 340, 260), aim_at, 1500, (1, 1, 1), source_width=60.0, source_height=260.0, **soft)
rim_b = light(unreal.RectLight, around(-150, 340, 200), aim_at, 1300, (1, 1, 1), source_width=60.0, source_height=260.0, **soft)
light(unreal.RectLight, around(40, 300, 60), aim_at, 450, (0.70, 0.55, 1.0), source_width=200.0, source_height=120.0, **soft)
light(unreal.DirectionalLight, unreal.Vector(0, 0, 600), unreal.Vector(-150, 80, 0), 1.2, (0.85, 0.80, 1.0))

# ---------------------------------------------------------------- capture
cap_actor = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
cap = cap_actor.get_editor_property('capture_component2d')
cap.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
cap.set_editor_property('capture_every_frame', False)
cap.set_editor_property('capture_on_movement', False)
cap.set_editor_property('fov_angle', 30.0)
os.makedirs(OUT, exist_ok=True)


def aim(cam_loc, target):
    d = target - cam_loc
    yaw = math.degrees(math.atan2(d.y, d.x))
    pitch = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    return unreal.Rotator(0, pitch, yaw)


def shoot(tag, w, h, yaw_deg, dist, elev, center_z):
    """Raw HDR scene colour; empty pixels stay exactly black, which grade_beauty.py uses as the backdrop mask."""
    rad = math.radians(yaw_deg)
    target = unreal.Vector(0, 0, center_z)
    loc = unreal.Vector(math.cos(rad) * dist, math.sin(rad) * dist, center_z + elev)
    cap_actor.set_actor_location_and_rotation(loc, aim(loc, target), False, False)
    rt = unreal.RenderingLibrary.create_render_target2d(world, w, h, unreal.TextureRenderTargetFormat.RTF_RGBA16F, unreal.LinearColor(0, 0, 0, 1))
    cap.set_editor_property('texture_target', rt)
    cap.capture_scene()
    cap.capture_scene()
    name = f'{tag}.hdr'
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, name)
    path = os.path.join(OUT, name)
    log['captures'].append([name, yaw_deg, os.path.exists(path) and os.path.getsize(path)])


def spawn_posed(skm, cfg, key, frac):
    """A fresh actor per pose: headless runs never tick, so the animation override only shows on an actor that
    has not been rendered yet."""
    actor = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    skc = actor.get_editor_property('skeletal_mesh_component')
    try:
        skc.set_skeletal_mesh_asset(skm)
    except Exception:
        skc.set_editor_property('skeletal_mesh_asset', skm)
    anim = unreal.EditorAssetLibrary.load_asset(f"{cfg['folder']}/{cfg['asset']}{cfg['anims'][key]}")
    t = unreal.AnimationLibrary.get_sequence_length(anim) * frac
    skc.override_animation_data(anim, False, False, t, 0.0)
    return actor


for name, cfg in characters.selected():
    skm = unreal.EditorAssetLibrary.load_asset(f"{cfg['folder']}/{cfg['asset']}")
    bounds = skm.get_bounds()
    rim_a.set_light_color(unreal.LinearColor(*cfg['rims'][0], 1.0))
    rim_b.set_light_color(unreal.LinearColor(*cfg['rims'][1], 1.0))
    key_light.set_editor_property('specular_scale', cfg['key_specular'])
    # frame every character like the knight: same fill of the frame, centred on its own bounds
    scale = bounds.box_extent.z / KNIGHT_HALF_HEIGHT
    center_z = bounds.origin.z
    note(f'{name}: bounds origin z {center_z:.1f}, half height {bounds.box_extent.z:.1f}')
    if PREVIEW == 'angles':
        key, frac, _, elev = cfg['shot']
        for yaw in (95, 115, 135, 155):
            actor = spawn_posed(skm, cfg, key, frac)
            shoot(f"preview_{cfg['export']}_yaw{yaw}", 480, 600, yaw, 760 * scale, elev * scale, center_z)
            eas.destroy_actor(actor)
    elif PREVIEW:
        for key in cfg['anims']:
            if key == 'idle':
                continue
            for frac in (0.3, 0.55, 0.8):
                actor = spawn_posed(skm, cfg, key, frac)
                shoot(f"preview_{cfg['export']}_{key}_{int(frac * 100)}", 480, 600, 140, 760 * scale, 20 * scale, center_z)
                eas.destroy_actor(actor)
    else:
        key, frac, yaw, elev = cfg['shot']
        actor = spawn_posed(skm, cfg, key, frac)
        # portrait 4:5 rendered at 2x for supersampling (downsampled outside Unreal)
        shoot(f"{cfg['export']}_beauty", 2000, 2500, yaw, 760 * scale, elev * scale, center_z)
        eas.destroy_actor(actor)

out = os.path.join(unreal.Paths.project_saved_dir(), 'step3_beauty.json')
with open(out, 'w') as f:
    json.dump(log, f, indent=1, default=str)
unreal.log('STEP3_DONE ' + out)
