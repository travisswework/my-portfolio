"""Read-only probe: report which editor APIs this engine build exposes to Python."""
import json
import os

import unreal

out = {'engine': unreal.SystemLibrary.get_engine_version(), 'checks': {}}


def members(name):
    obj = getattr(unreal, name, None)
    if obj is None:
        return None
    return sorted(m for m in dir(obj) if not m.startswith('_'))


for name in ['GLTFExporter', 'GLTFExportOptions', 'EditorSkeletalMeshLibrary', 'SkeletalMeshEditorSubsystem',
             'MaterialEditingLibrary', 'InterchangeManager', 'AssetImportTask', 'InterchangeGenericAssetsPipeline',
             'GeometryScript_SkeletalMesh', 'GeometryScriptLibrary_SkeletalMeshFunctions', 'SkeletalMeshLODSettings',
             'SkeletalMeshOptimizationSettings', 'SkeletalMeshLODInfo', 'MaterialExpressionCustom', 'CustomInput',
             'GLTFMaterialBakeMode', 'GLTFMaterialBakeSizePOT', 'MaterialExpressionPreSkinnedPosition']:
    out['checks'][name] = members(name)

path = os.path.join(unreal.Paths.project_saved_dir(), 'probe.json')
with open(path, 'w') as f:
    json.dump(out, f, indent=1)
unreal.log('PROBE_WRITTEN ' + path)
