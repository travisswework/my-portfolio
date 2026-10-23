# Asset credits

## Hero characters

| Asset | Used for | Source | Licence |
|---|---|---|---|
| Knight, Barbarian, Mage, Rogue and Rogue (Hooded), from KayKit: Adventurers Character Pack 1.0 by Kay Lousberg | Base models and animations for the five hero characters | https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0 · https://kaylousberg.com | CC0 1.0 |

Each character was refined in an isolated Unreal Engine 5.8 project (`../../ue-knight-refine`): loadout trimmed to one
weapon set, props skinned into one skeletal mesh, new look-dev materials (swatch-by-swatch PBR re-grade, plus an emissive
weapon material), an LOD chain generated with Unreal's skeletal mesh reduction, and a glTF export with baked materials and
four animations. `hero-<character>.js` embeds one character's exported files (plus the untouched original for the
before/after view); the page loads it when that character is picked. `<character>-ue-render.webp` is a still rendered in
the same Unreal project (scripted studio scene, raw HDR capture, graded), and `thumb-<character>.webp` is cropped from it.

## Environment

All 3D environment assets are from [Poly Haven](https://polyhaven.com) and released under CC0 (public domain).
They were resized, recompressed and simplified for the web, then embedded in `world-assets.js`.

| Asset | Used for | Source |
|---|---|---|
| Gothic Statue | Portal guardians and island statues | https://polyhaven.com/a/gothic_statue |
| Fern 02 | Ground cover on the islands | https://polyhaven.com/a/fern_02 |
| Rock Moss Set 01 | Boulders and drifting rock debris | https://polyhaven.com/a/rock_moss_set_01 |
| Dead Quiver Trunk | Gnarled trees | https://polyhaven.com/a/dead_quiver_trunk |
| Cliff Side (texture) | Island cliffs and the portal stone | https://polyhaven.com/a/cliff_side |
| Leafy Grass (texture) | Island tops | https://polyhaven.com/a/leafy_grass |
