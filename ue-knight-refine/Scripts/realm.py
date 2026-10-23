"""Look-dev settings for the Realm (step5_realm_refine, step6_realm_beauty). Plain data, no Unreal imports."""
from characters import HEADER, rules, ramp, tint, keep

# ---------------------------------------------------------------- hex tiles (KayKit hexagons_medieval atlas, 8 x 4)
# swatches: 16 grass, 17 foliage, 6 wood, 2 stone, 24 roofs, 18 mountain rock, 20 sand, 11 grain, 9 water, 25 banner
TILES = HEADER + rules(
    ((16,), ramp((0.022, 0.06, 0.012), (0.33, 0.56, 0.11), 1.7, rough=0.9)),
    ((17,), ramp((0.008, 0.04, 0.018), (0.12, 0.36, 0.11), 2.2, rough=0.85)),
    ((6,), tint((0.64, 0.46, 0.36), 0.0, 0.75)),
    ((2,), tint((0.98, 0.95, 0.90), 0.0, 0.8)),
    ((24,), ramp((0.008, 0.016, 0.07), (0.10, 0.22, 0.66), 2.6, metal=0.15, rough=0.5)),
    ((18,), 'float3 rock = C * float3(0.60, 0.62, 0.70); float t = smoothstep(0.52, 0.72, l); '
            'base = lerp(rock, float3(0.90, 0.93, 0.98), t); rough = lerp(0.85, 0.55, t);'),
    ((20, 19), tint((1.0, 0.90, 0.74), 0.0, 0.9)),
    ((11,), ramp((0.22, 0.10, 0.015), (1.0, 0.70, 0.20), 1.4, rough=0.8)),
    ((9,), 'base = float3(0.010, 0.060, 0.085) + C * 0.05; rough = 0.05;'),
    ((25,), ramp((0.06, 0.004, 0.01), (0.66, 0.05, 0.06), 2.4, rough=0.75)),
    ((1, 13, 14), keep(0.7)),
)

# ---------------------------------------------------------------- skeletons (KayKit skeleton atlas, graded by colour)
# Bone stays an aged ivory, greys become dark iron, reds deep crimson cloth, browns dark leather.
SKELETON = HEADER + r'''
float mx = max(C.r, max(C.g, C.b)); float mn = min(C.r, min(C.g, C.b));
float sat = (mx - mn) / max(mx, 1e-4);
if (sat < 0.16 && l > 0.45) { base = float3(0.86, 0.79, 0.64) * (0.55 + 0.5 * l); rough = 0.55; }
else if (sat < 0.22) { base = C * float3(0.42, 0.44, 0.50); metal = 0.85; rough = 0.38; }
else if (C.r > C.g * 1.6 && C.r > C.b * 1.3) { float t = saturate(l * 3.0); base = lerp(float3(0.05, 0.004, 0.01), float3(0.48, 0.04, 0.05), t); rough = 0.8; }
else if (C.r >= C.g && C.g >= C.b) { base = C * float3(0.42, 0.33, 0.28); rough = 0.75; }
else { base = C * 0.75; rough = 0.6; }
'''
SKELETON_WEAPON = SKELETON + r'''
if (sat < 0.22 && l <= 0.45) { base = C * float3(0.55, 0.58, 0.66); metal = 0.95; rough = 0.28; }
'''
SKELETON_GLOW = ((0.30, 0.95, 1.0), 9.0)  # spectral eye glow colour and strength

ROLES = ['Warrior', 'Minion', 'Mage']
SKELETON_ANIMS = {  # export key: animation name in /Game/Realm/Skeleton_Warrior (the rig is shared by all roles)
    'idle': 'Idle_Combat', 'run': 'Running_A', 'chop': '1H_Melee_Attack_Chop', 'slice': '1H_Melee_Attack_Slice_Diagonal',
    'block': 'Block', 'taunt': 'Taunt', 'cheer': 'Cheer', 'cast': 'Spellcasting', 'summon': 'Spellcast_Summon',
    'rise': 'Spawn_Ground_Skeletons', 'collapse': 'Death_C_Skeletons', 'resurrect': 'Death_C_Skeletons_Resurrect',
}

# ---------------------------------------------------------------- dragon (Quaternius, untextured: one material per slot)
DRAGON = {
    'Main': dict(base=(0.075, 0.012, 0.016), metal=0.25, rough=0.35),             # obsidian-crimson scales
    'Wings': dict(base=(0.22, 0.025, 0.03), rough=0.55, emissive=(0.06, 0.004, 0.0)),  # membranes, faintly backlit
    'Belly': dict(base=(0.95, 0.38, 0.08), rough=0.45, emissive=(1.6, 0.42, 0.05)),    # molten underside
    'Claws': dict(base=(0.82, 0.76, 0.62), rough=0.35),                            # ivory horns and claws
    'Eyes': dict(base=(1.0, 0.75, 0.2), rough=0.2, emissive=(6.0, 3.5, 0.4)),       # burning eyes
}
DRAGON_ANIMS = {'fly': 'Dragon_Flying', 'attack': 'Dragon_Attack', 'breath': 'Dragon_Attack2', 'hit': 'Dragon_Hit'}

# ---------------------------------------------------------------- horses (Quaternius): three coats from one mesh
HORSE_COATS = {
    'chestnut': dict(coat=(0.28, 0.10, 0.035), mane=(0.02, 0.014, 0.011)),
    'grey': dict(coat=(0.62, 0.62, 0.60), mane=(0.12, 0.11, 0.11)),
    'black': dict(coat=(0.03, 0.026, 0.026), mane=(0.006, 0.005, 0.005)),
}
HORSE_ANIMS = {'run': 'Run', 'walk': 'Walk', 'idle': 'Idle'}
