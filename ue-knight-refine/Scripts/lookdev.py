"""Material and glTF-export helpers shared by step2_refine (heroes) and step5_realm_refine (the Realm)."""
import unreal

MEL = unreal.MaterialEditingLibrary
assets = unreal.AssetToolsHelpers.get_asset_tools()

OUTPUTS = [
    ('Base', 'return base;', unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.MaterialProperty.MP_BASE_COLOR),
    ('Metal', 'return metal;', unreal.CustomMaterialOutputType.CMOT_FLOAT1, unreal.MaterialProperty.MP_METALLIC),
    ('Rough', 'return rough;', unreal.CustomMaterialOutputType.CMOT_FLOAT1, unreal.MaterialProperty.MP_ROUGHNESS),
    ('Glow', 'return emi;', unreal.CustomMaterialOutputType.CMOT_FLOAT3, unreal.MaterialProperty.MP_EMISSIVE_COLOR),
]


def _fresh(out_dir, name):
    path = f'{out_dir}/{name}'
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    return assets.create_asset(name, out_dir, unreal.Material, unreal.MaterialFactoryNew())


def build_material(out_dir, name, texture, code, skeletal=True):
    """Texture-driven look-dev material: four Custom nodes run `code` (which sets base/metal/rough/emi from the
    texel C at UV) and feed base colour, metallic, roughness and emissive."""
    mat = _fresh(out_dir, name)
    mat.set_editor_property('two_sided', True)
    if skeletal:
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


def constant_material(out_dir, name, base, metal=0.0, rough=0.6, emissive=None, skeletal=True):
    """Flat PBR material for untextured models (the glTF export writes plain factors)."""
    mat = _fresh(out_dir, name)
    mat.set_editor_property('two_sided', True)
    if skeletal:
        mat.set_editor_property('used_with_skeletal_mesh', True)
    props = [(unreal.MaterialProperty.MP_BASE_COLOR, base), (unreal.MaterialProperty.MP_METALLIC, metal),
             (unreal.MaterialProperty.MP_ROUGHNESS, rough)]
    if emissive:
        props.append((unreal.MaterialProperty.MP_EMISSIVE_COLOR, emissive))
    for i, (prop, value) in enumerate(props):
        vec = isinstance(value, tuple)
        node = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector if vec else unreal.MaterialExpressionConstant, -400, -200 + 150 * i)
        if vec:
            node.set_editor_property('constant', unreal.LinearColor(*value, 1.0))
        else:
            node.set_editor_property('r', value)
        MEL.connect_material_property(node, '', prop)
    MEL.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def mesh_export_options(report, bake=True, bake_size=512):
    opts = unreal.GLTFExportOptions()
    opts.set_editor_property('bake_material_inputs', unreal.GLTFMaterialBakeMode.SIMPLE if bake else unreal.GLTFMaterialBakeMode.DISABLED)
    try:
        size = opts.get_editor_property('default_material_bake_size')
        for field, value in (('x', bake_size), ('y', bake_size), ('auto_detect', False), ('b_auto_detect', False)):
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


def make_lods(skm, fractions, report):
    """Regenerate the skeletal mesh's LOD chain at the given triangle fractions (1.0 first)."""
    try:
        lod_settings = unreal.new_object(unreal.SkeletalMeshLODSettings, outer=skm)
        groups = []
        for pct in fractions:
            group = unreal.SkeletalMeshLODGroupSettings()
            rs = group.get_editor_property('reduction_settings')
            rs.set_editor_property('num_of_triangles_percentage', pct)
            rs.set_editor_property('num_of_vert_percentage', pct)
            group.set_editor_property('reduction_settings', rs)
            groups.append(group)
        lod_settings.set_editor_property('lod_groups', groups)
        skm.set_editor_property('lod_settings', lod_settings)
    except Exception as exc:
        report['notes'].append(f'LOD settings not applied: {exc}')
    return unreal.EditorSkeletalMeshLibrary.regenerate_lod(skm, len(fractions), True, False)


def set_slots(skm, mapping):
    """Assign materials to a skeletal mesh's slots by slot name (struct elements are copies: write back by index)."""
    slots = skm.get_editor_property('materials')
    for i in range(len(slots)):
        slot = slots[i]
        name = str(slot.get_editor_property('material_slot_name'))
        if name in mapping:
            slot.set_editor_property('material_interface', mapping[name])
            slots[i] = slot
    skm.set_editor_property('materials', slots)
    return [(str(s.get_editor_property('material_slot_name')), s.get_editor_property('material_interface').get_name())
            for s in skm.get_editor_property('materials')]


def anim_export_options(lod=0):
    opts = unreal.GLTFExportOptions()
    opts.set_editor_property('bake_material_inputs', unreal.GLTFMaterialBakeMode.DISABLED)
    opts.set_editor_property('default_level_of_detail', lod)
    opts.set_editor_property('export_vertex_skin_weights', True)
    opts.set_editor_property('export_animation_sequences', True)
    return opts
