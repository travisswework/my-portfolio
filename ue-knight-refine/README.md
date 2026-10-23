# Hero characters and the Realm (Unreal Engine 5.8)

Self-contained project that produces the 3D content of the portfolio site (`../tan-zheng-yuan`) from CC0 sources:
five **KayKit: Adventurers** heroes (steps 1 to 3), and **the Realm**, a hex-world diorama built from the KayKit Medieval
Hexagon tiles, with a Quaternius dragon and horses and a KayKit skeleton army (steps 4 to 6). Everything
here is scripted and headless, and it is isolated from the other projects on this shared machine. You can delete the
folder at any time. (The folder and project keep the name `KnightRefine` from when the knight was the only character.)

## Run it

From PowerShell in this folder:

```powershell
python Scripts\prepare_sources.py <pack>\Characters\gltf <gltf-transform>   # trim loadouts -> SourceAssets/ (plain Python, outside Unreal)
.\run.ps1 step1_import     # import SourceAssets/<Character>_Loadout.glb as one skeletal mesh each (/Game/<Character>)
.\run.ps1 step2_refine     # look-dev materials + LOD chain + glTF export to Export/
.\run.ps1 step3_beauty     # studio stills: raw HDR captures to Export/Beauty
python Scripts\grade_beauty.py   # exposure, filmic curve, bloom, backdrop -> Export/Beauty/<character>_beauty_final.png
```

Every step runs all five characters by default; pass `-Characters Barbarian,Mage` to run only some. The per-character
settings (swatch grading, weapon glow, animations, beauty pose and lights) are in `Scripts/characters.py`.
`.\run.ps1 step3_beauty -Preview poses` renders small frames of several poses per character and `-Preview angles` the
chosen pose from four sides (`python Scripts\grade_beauty.py --preview <character>` makes a contact sheet), which is
how the beauty shots were picked.

### The Realm

```powershell
python Scripts\realm_layout.py preview.png        # the generated hex map (plain Python), with a top-down preview
python Scripts\prepare_realm.py <hexagon pack> <skeletons gltf dir> <monsters FBX dir> <farm animals FBX dir> <gltf-transform>
.\run.ps1 step4_realm_import     # tiles, skeletons, dragon, horse -> /Game/Realm
.\run.ps1 step5_realm_refine     # look-dev, level assembly (/Game/Realm/Map_Realm), glTF export to Export/Realm
.\run.ps1 step6_realm_beauty     # dusk render of the level -> Export/Beauty/realm_beauty.hdr
python Scripts\grade_beauty.py   # also grades the Realm -> realm_beauty_final.png
```

`-Only world,dragon,horse,skeletons` limits step5 to some parts. The look-dev settings are in `Scripts/realm.py`.

`run.ps1` refuses to start while another Unreal Editor is running. When it finishes it puts the shared recent-projects
list back (Unreal adds every opened project to it) and removes the session logs that Unreal's crash-reporter monitor
writes to `%LOCALAPPDATA%\CrashReportClient` on every launch. Let it run to the end: don't pipe it into something that stops early
(such as `Select-Object -First 1`), which ends the script before that clean-up. If that happens anyway, the next run
notices (the shared list is empty or still names this project) and repairs it from the reference copy it keeps in
`Saved/SharedBackup`; every restore is also checked byte for byte.

| Step | What it does | Typical time |
|---|---|---|
| step1_import | Interchange import with all parts forced to skeletal, so headgear, cape and weapons are skinned into one mesh with the rig and 4 animations | ~5 s per character |
| step2_refine | Builds `M_<Character>_Refined` and the weapon material (`M_Knight_Blade`, `M_<Character>_Weapon`) node by node (per-swatch PBR re-grade, emissive weapon accent), regenerates LODs at 100/50/25 % triangles, exports each LOD and each animation to glTF with materials baked to 512 px textures | ~5–10 min the first time (shader compile), ~1 min per character after |
| step3_beauty | Builds a studio map (plinth with glowing rim, softbox rect lights, rim colours per character), poses each character from one of its animations on a freshly spawned actor (headless runs never tick, so a pose only applies before an actor's first render) and captures raw HDR scene colour at 2000×2500. `grade_beauty.py` meters exposure on the character, then applies a filmic curve, bloom, backdrop and a 2× downsample; `<character>_beauty_final.png` becomes `assets/<character>-ue-render.webp` on the site | ~30 s |

| step4_realm_import | Imports the 48 tile meshes (one merged GLB, so the atlas comes in once), the three equipped skeletons, and the dragon and horse FBX files | ~35 s |
| step5_realm_refine | Re-grades the tile atlas (`M_Realm_Tiles`), turns Nanite off on the tiles, places the 217-hex map as 291 tile actors and exports the level to glTF (each tile mesh written once and instanced, atlas baked at 1024 px); new materials for the dragon (`M_Dragon_*`), three horse coats and the skeletons (graded atlas, iron weapons, emissive eyes, LODs at 100/50 %), exported with their animations | ~3 min the first time, ~1 min after |
| step6_realm_beauty | Loads `Map_Realm`, adds a sky atmosphere (planet top moved below the diorama), sun, sky light, height fog, a sea plane and torch lights, poses the creatures (facing from their head bone or hand slots) and captures raw HDR at 3200×1800 | ~20 s |

Two things that matter for headless renders: static meshes finish compiling asynchronously after a map loads, so step6
asks every tile mesh for its triangle count first (that completes it; otherwise most tiles are missing), and Nanite
pages never stream in without ticks, so the tiles are plain meshes.

## Isolation on the shared machine

- **Derived data stays in this folder.** `Config/DefaultEngine.ini` defines the `KnightIsolated` cache graph:
  the engine's read-only pak plus `DerivedDataCache/Local` here. Always launch with `-DDC=KnightIsolated`
  (the wrapper does). Nothing is written to the team's shared caches under `%LOCALAPPDATA%\UnrealEngine`.
- **No pip installs** (`bRunPipInstallOnStartup=False`) and **no trace server** (`-notraceserver`).
- **Shaders are compiled in step2.** Headless runs never tick the engine, so step2 sets the skeletal-mesh usage flag
  on the materials and its glTF bake waits for the whole shader map, which is then cached in this folder for step3.
  Do not set `bAllowAsynchronousShaderCompiling=False` to force this: UE 5.8 asserts on startup with it.
- If you open the project in the editor by hand, add `-DDC=KnightIsolated` to the command line; otherwise it uses
  the shared cache like any other project. Opening it will also add it to the shared recent-projects list.

## Files

- `SourceAssets/<Character>_Loadout.glb`: the KayKit character with the loadout trimmed to one weapon set (knight:
  1-handed sword and badge shield; barbarian: great axe; mage: staff; rogue: twin knives; hooded rogue: crossbow and
  knife), the weapons given their own material slot, and 4 animations kept. Made by `Scripts/prepare_sources.py`.
- `SourceAssets/Realm/`: `Realm_Tiles.glb` (every tile the map uses), `Skeleton_<Role>_Loadout.glb` (weapons on the
  hand slots, 12 animations), `Dragon.fbx`, `Horse.fbx`. Made by `Scripts/prepare_realm.py`.
- `Scripts/`: `characters.py` and `realm.py` (settings), `realm_layout.py` (the map), `lookdev.py` (shared material and
  export helpers), `prepare_sources.py`, `prepare_realm.py`, `step1_import.py` to `step6_realm_beauty.py`,
  `grade_beauty.py`, `probe.py`, `probe_realm.py`.
- `Export/`: `<character>_refined_lod{0,1,2}.glb`, `<character>_anim_<key>.glb`, `Beauty/` (raw `.hdr` captures and
  graded PNGs). The knight's capture is `beauty_right.hdr` from the first, knight-only version of step3.

- `Export/Realm/`: `realm_world.glb`, `realm_layout.json`, `dragon*.glb`, `horse_<coat>.glb`, `skeleton_<role>_lod{0,1}.glb`
  and the animation files.

The site embeds compressed copies of the exports in `tan-zheng-yuan/assets/hero-<character>.js` and `realm-assets.js`.

## Licence and credit

Base models and animations, all CC0 1.0: KayKit: Adventurers Character Pack 1.0, Medieval Hexagon Pack 1.0 and Character
Pack Skeletons 1.0 by Kay Lousberg (https://github.com/KayKit-Game-Assets, https://kaylousberg.com); Animated Monster Pack
and Farm Animal Pack by Quaternius (https://quaternius.com, via https://opengameart.org).
The refinement scripts in this folder were written for the portfolio site.
