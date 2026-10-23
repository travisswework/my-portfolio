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

## The Realm

| Asset | Used for | Source | Licence |
|---|---|---|---|
| KayKit: Medieval Hexagon Pack 1.0 by Kay Lousberg (48 tiles: grass, coasts, rivers, roads, mountains, hills, trees, buildings, props) | The hex-map terrain, water, village, castle and camp | https://github.com/KayKit-Game-Assets/KayKit-Medieval-Hexagon-Pack-1.0 | CC0 1.0 |
| KayKit: Character Pack Skeletons 1.0 by Kay Lousberg (Warrior, Minion, Mage, weapons, 12 animations) | The skeleton host | https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Skeletons-1.0 | CC0 1.0 |
| Animated Monster Pack by Quaternius (Dragon) | The dragon | https://opengameart.org/content/lowpoly-animated-monsters · https://quaternius.com | CC0 1.0 |
| Farm Animal Pack by Quaternius (Horse) | The horses | https://opengameart.org/content/lowpoly-animated-farm-animal-pack · https://quaternius.com | CC0 1.0 |

All of it went through the same isolated Unreal Engine 5.8 project (`../../ue-knight-refine`, steps 4 to 6): the map is
generated (rivers, roads and coasts fitted by their open edges), assembled in Unreal as a level of 291 tile actors and
exported to glTF with a re-graded, baked atlas; the dragon, horses and skeletons get new Unreal materials (the skeletons
also weapons, LODs and a spectral eye glow) and are exported with their animations. `realm-assets.js` embeds the exports;
`realm-ue-render.webp` is the level rendered in Unreal at dusk (sky atmosphere, raw HDR capture, graded). The knight and
barbarian defending the ford are the hero exports above (LOD 2).

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
