# Hero character refinement (Unreal Engine 5.8)

Self-contained project that takes five CC0 **KayKit: Adventurers** characters by Kay Lousberg (Knight, Barbarian, Mage,
Rogue, Hooded Rogue) and produces the refined characters used on the portfolio site (`../tan-zheng-yuan`). Everything
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

`run.ps1` refuses to start while another Unreal Editor is running. When it finishes it puts the shared recent-projects
list back (Unreal adds every opened project to it) and removes the session logs that Unreal's crash-reporter monitor
writes to `%LOCALAPPDATA%\CrashReportClient` on every launch.

| Step | What it does | Typical time |
|---|---|---|
| step1_import | Interchange import with all parts forced to skeletal, so headgear, cape and weapons are skinned into one mesh with the rig and 4 animations | ~5 s per character |
| step2_refine | Builds `M_<Character>_Refined` and the weapon material (`M_Knight_Blade`, `M_<Character>_Weapon`) node by node (per-swatch PBR re-grade, emissive weapon accent), regenerates LODs at 100/50/25 % triangles, exports each LOD and each animation to glTF with materials baked to 512 px textures | ~5–10 min the first time (shader compile), ~1 min per character after |
| step3_beauty | Builds a studio map (plinth with glowing rim, softbox rect lights, rim colours per character), poses each character from one of its animations on a freshly spawned actor (headless runs never tick, so a pose only applies before an actor's first render) and captures raw HDR scene colour at 2000×2500. `grade_beauty.py` meters exposure on the character, then applies a filmic curve, bloom, backdrop and a 2× downsample; `<character>_beauty_final.png` becomes `assets/<character>-ue-render.webp` on the site | ~30 s |

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
- `Scripts/`: `characters.py` (settings), `prepare_sources.py`, `step1_import.py`, `step2_refine.py`, `step3_beauty.py`,
  `grade_beauty.py`, `probe.py`.
- `Export/`: `<character>_refined_lod{0,1,2}.glb`, `<character>_anim_<key>.glb`, `Beauty/` (raw `.hdr` captures and
  graded PNGs). The knight's capture is `beauty_right.hdr` from the first, knight-only version of step3.

The site embeds compressed copies of the exports in `tan-zheng-yuan/assets/hero-<character>.js`.

## Licence and credit

Base models and animations: KayKit: Adventurers Character Pack 1.0 by Kay Lousberg, CC0 1.0
(https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0, https://kaylousberg.com).
The refinement scripts in this folder were written for the portfolio site.
