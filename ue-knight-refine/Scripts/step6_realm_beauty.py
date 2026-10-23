"""Step 6: a beauty still of the Realm, rendered in Unreal from the level step5 saved (/Game/Realm/Map_Realm).

Adds a dusk sky (sky atmosphere, sun, sky light, height fog), a sea plane out to the horizon and torch lights,
then poses the refined creatures in the scene: the dragon over the plain, horses at a gallop, the skeleton host
attacking the heroes at the ford and the necromancer at the camp. Raw HDR scene colour is captured at 3200 x 1800
to Export/Beauty/realm_beauty.hdr; grade_beauty.py grades it (realm_beauty_final.png -> assets/realm-ue-render.webp).
Positions are given in the site's glTF space (x, y, z in tile units) and converted: Unreal = (100x, 100z, 100y).
"""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import realm  # noqa: E402

PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
OUT = os.path.join(PROJECT, 'Export', 'Beauty')
ROOT = '/Game/Realm'
eal = unreal.EditorAssetLibrary
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
log = {'notes': [], 'captures': []}


def note(msg):
    log['notes'].append(str(msg))
    unreal.log('REALM_BEAUTY ' + str(msg))


def ue(x, y, z):
    return unreal.Vector(x * 100, z * 100, y * 100)


def try_set(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:
        note(f'{prop}: {exc}')


world = unreal.EditorLoadingAndSavingUtils.load_map(f'{ROOT}/Map_Realm')
note(f'loaded {world}')
# Static meshes finish compiling asynchronously on load, which needs editor ticks a headless run never gets;
# asking each mesh for its render data makes Unreal finish it now (otherwise most tiles are missing from the capture).
tile_meshes = {a.static_mesh_component.get_editor_property('static_mesh') for a in eas.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)}
note(f'{sum(m.get_num_triangles(0) for m in tile_meshes if m)} triangles in {len(tile_meshes)} tile meshes ready')

# ---------------------------------------------------------------- sky, sun, fog, sea
sun_dir = unreal.Vector(0.82, -0.35, 0.16)  # glTF dusk sun (x, y, z) = (0.82, 0.16, -0.35) -> Unreal (x, z, y)
sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(0, 0, 0))
yaw = math.degrees(math.atan2(-sun_dir.y, -sun_dir.x))
pitch = -math.degrees(math.atan2(sun_dir.z, math.hypot(sun_dir.x, sun_dir.y)))
sun.set_actor_rotation(unreal.Rotator(0, pitch, yaw), False)
sc = sun.get_component_by_class(unreal.DirectionalLightComponent)
sc.set_editor_property('intensity', 9.0)
sc.set_light_color(unreal.LinearColor(1.0, 0.62, 0.36, 1))
try_set(sc, 'atmosphere_sun_light', True)
# the atmosphere's planet surface goes well below the diorama (by default it sits at z = 0, and anything under it
# is painted over with sky)
atmo = eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, -5000), unreal.Rotator(0, 0, 0))
try_set(atmo.get_component_by_class(unreal.SkyAtmosphereComponent), 'transform_mode', unreal.SkyAtmosphereTransformMode.PLANET_TOP_AT_COMPONENT_TRANSFORM)
sky = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000), unreal.Rotator(0, 0, 0))
slc = sky.get_component_by_class(unreal.SkyLightComponent)
try_set(slc, 'real_time_capture', True)
slc.set_editor_property('intensity', 1.2)
try:
    slc.recapture_sky()
except Exception as exc:
    note(f'recapture: {exc}')
fill = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 3000), unreal.Rotator(0, -35, yaw + 180))
fc = fill.get_component_by_class(unreal.DirectionalLightComponent)
fc.set_editor_property('intensity', 1.4)
fc.set_light_color(unreal.LinearColor(0.42, 0.40, 0.95, 1))
try_set(fc, 'cast_shadows', False)
fog = eas.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -50), unreal.Rotator(0, 0, 0))
fgc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
try_set(fgc, 'fog_density', 0.012)
try_set(fgc, 'fog_height_falloff', 0.35)
try_set(fgc, 'start_distance', 2500.0)
try_set(fgc, 'fog_inscattering_luminance', unreal.LinearColor(0.42, 0.26, 0.42, 1))

mat_dir = f'{ROOT}/Showcase'
sea_mat_path = f'{mat_dir}/M_Sea'
if eal.does_asset_exist(sea_mat_path):
    eal.delete_asset(sea_mat_path)
sea_mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_Sea', mat_dir, unreal.Material, unreal.MaterialFactoryNew())
MEL = unreal.MaterialEditingLibrary
for i, (prop, value) in enumerate([(unreal.MaterialProperty.MP_BASE_COLOR, (0.008, 0.045, 0.07)), (unreal.MaterialProperty.MP_ROUGHNESS, 0.08),
                                   (unreal.MaterialProperty.MP_SPECULAR, 0.6)]):
    node = MEL.create_material_expression(sea_mat, unreal.MaterialExpressionConstant3Vector if isinstance(value, tuple) else unreal.MaterialExpressionConstant, -300, i * 150)
    if isinstance(value, tuple):
        node.set_editor_property('constant', unreal.LinearColor(*value, 1))
    else:
        node.set_editor_property('r', value)
    MEL.connect_material_property(node, '', prop)
MEL.recompile_material(sea_mat)
plane = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -21), unreal.Rotator(0, 0, 0))
plane_mesh = eal.load_asset('/Engine/BasicShapes/Plane')
plane_mesh.get_num_triangles(0)
plane.static_mesh_component.set_static_mesh(plane_mesh)
plane.set_actor_scale3d(unreal.Vector(800, 800, 1))
plane.static_mesh_component.set_material(0, sea_mat)

for p in [(5.2, 0.55, -2.1), (6.8, 0.55, -2.1), (11.6, 0.35, -1.1), (12.4, 0.35, -2.6), (-5.6, 0.45, -1.2)]:
    t = eas.spawn_actor_from_class(unreal.PointLight, ue(*p), unreal.Rotator(0, 0, 0))
    tc = t.get_component_by_class(unreal.PointLightComponent)
    tc.set_editor_property('intensity', 5.0)
    tc.set_light_color(unreal.LinearColor(1.0, 0.5, 0.18, 1))
    tc.set_editor_property('attenuation_radius', 260.0)


# ---------------------------------------------------------------- creatures
def compose(*rotators):
    out = rotators[0]
    for r in rotators[1:]:
        out = unreal.MathLibrary.compose_rotators(out, r)
    return out


def creature(mesh_path, anim_path, frac, pos, heading_deg, scale, yaw0=None, level=0.0, materials=None):
    """Spawn a posed skeletal mesh at glTF position `pos`, facing `heading_deg` (Unreal yaw of the travel direction).
    yaw0: the yaw the model faces in its own frame: measured from its head bone when None, from its hand slots
    with 'hands'."""
    skm = eal.load_asset(mesh_path)
    a = eas.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    skc = a.get_editor_property('skeletal_mesh_component')
    try:
        skc.set_skeletal_mesh_asset(skm)
    except Exception:
        skc.set_editor_property('skeletal_mesh_asset', skm)
    for i, m in (materials or {}).items():
        skc.set_material(i, m)
    elev = 0.0
    if yaw0 == 'hands':  # humanoids: forward = right x up, right = left hand slot -> right hand slot
        names = {str(n).replace('.', '_'): str(n) for n in skc.get_all_socket_names()}
        r = skc.get_socket_location(names['handslot_r']) - skc.get_socket_location(names['handslot_l'])
        yaw0 = math.degrees(math.atan2(-r.x, r.y))
    elif yaw0 is None:
        bones = [str(n) for n in skc.get_all_socket_names()]
        head = next((b for b in bones if 'head' in b.lower()), None)
        origin, _ = a.get_actor_bounds(False)
        h = skc.get_socket_location(head) - origin
        yaw0 = math.degrees(math.atan2(h.y, h.x))
        elev = math.degrees(math.atan2(h.z, math.hypot(h.x, h.y)))
    rot = compose(unreal.Rotator(0, 0, -yaw0), unreal.Rotator(0, -elev * level, 0), unreal.Rotator(0, 0, heading_deg))
    a.set_actor_rotation(rot, False)
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    anim = eal.load_asset(anim_path)
    skc.override_animation_data(anim, False, False, unreal.AnimationLibrary.get_sequence_length(anim) * frac, 0.0)
    # rest the feet (or centre a flier) at the requested point
    origin, extent = a.get_actor_bounds(False)
    target = ue(*pos)
    if level:
        a.set_actor_location(a.get_actor_location() + (target - origin), False, False)
    else:
        a.set_actor_location(a.get_actor_location() + unreal.Vector(target.x - origin.x, target.y - origin.y, target.z - (origin.z - extent.z)), False, False)
    return a


REF = f'{ROOT}/Refined'
heading = lambda dx, dz: math.degrees(math.atan2(dz, dx))  # glTF travel direction (dx, dz) -> Unreal yaw
creature(f'{ROOT}/Dragon/Dragon', f'{ROOT}/Dragon/DragonDragonArmature_Dragon_Flying', 0.35, (2.6, 3.4, 1.6), heading(-0.9, -0.45), 1.13, level=0.85)
coats = ['chestnut', 'grey', 'black', 'chestnut']
for i, (x, z) in enumerate([(6.2, 4.9), (7.4, 5.6), (5.0, 5.8), (8.3, 4.6)]):
    c = coats[i]
    creature(f'{ROOT}/Horse/Horse', f'{ROOT}/Horse/HorseArmature_Run', 0.2 + i * 0.23, (x, 0, z), heading(1, -0.25), 0.103,
             materials={0: eal.load_asset(f'{REF}/M_Horse_{c}_Coat'), 1: eal.load_asset(f'{REF}/M_Horse_{c}_Mane')})
army = [(0, 0), (0.42, -0.36), (0.42, 0.36), (0.86, -0.62), (0.86, 0), (0.86, 0.62), (1.3, -0.4), (1.3, 0.4)]
for i, (back, side) in enumerate(army):
    role = 'Minion' if i % 3 == 1 else 'Warrior'
    anim = ['1H_Melee_Attack_Chop', '1H_Melee_Attack_Slice_Diagonal', 'Block'][i % 3]
    creature(f'{ROOT}/Skeleton_{role}/Skeleton_{role}_Loadout', f'{ROOT}/Skeleton_{role}/Skeleton_{role}_Loadout{anim}', 0.3 + 0.1 * (i % 4),
             (-2.15 + back, 0, -1.75 + side), heading(-1, 0.05), 0.17, yaw0='hands')
creature(f'{ROOT}/Skeleton_Mage/Skeleton_Mage_Loadout', f'{ROOT}/Skeleton_Mage/Skeleton_Mage_LoadoutSpellcast_Summon', 0.4, (10.3, 0, 2.2), heading(-1, 0.3), 0.18, yaw0='hands')
creature('/Game/Knight/Knight_Loadout', '/Game/Knight/Knight_Loadout1H_Melee_Attack_Slice_Diagonal', 0.35, (-3.75, 0, -1.35), heading(1, 0), 0.17, yaw0='hands')
creature('/Game/Barbarian/Barbarian_Loadout', '/Game/Barbarian/Barbarian_Loadout2H_Melee_Attack_Chop', 0.4, (-3.95, 0, -2.15), heading(1, 0), 0.17, yaw0='hands')

# ---------------------------------------------------------------- capture
cap_actor = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
cap = cap_actor.get_editor_property('capture_component2d')
cap.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
cap.set_editor_property('capture_every_frame', False)
cap.set_editor_property('capture_on_movement', False)
cap.set_editor_property('fov_angle', 52.0)
eye, look = ue(11.0, 15.5, 24.5), ue(-0.5, 0.0, -1.5)
d = look - eye
cap_actor.set_actor_location_and_rotation(eye, unreal.Rotator(0, math.degrees(math.atan2(d.z, math.hypot(d.x, d.y))), math.degrees(math.atan2(d.y, d.x))), False, False)
os.makedirs(OUT, exist_ok=True)
rt = unreal.RenderingLibrary.create_render_target2d(world, 3200, 1800, unreal.TextureRenderTargetFormat.RTF_RGBA16F, unreal.LinearColor(0, 0, 0, 1))
cap.set_editor_property('texture_target', rt)
for _ in range(3):  # extra passes let the sky light and atmosphere settle
    cap.capture_scene()
unreal.RenderingLibrary.export_render_target(world, rt, OUT, 'realm_beauty.hdr')
path = os.path.join(OUT, 'realm_beauty.hdr')
log['captures'].append(['realm_beauty.hdr', os.path.exists(path) and os.path.getsize(path)])

out = os.path.join(unreal.Paths.project_saved_dir(), 'step6_realm_beauty.json')
with open(out, 'w') as f:
    json.dump(log, f, indent=1, default=str)
unreal.log('STEP6_DONE ' + out)
