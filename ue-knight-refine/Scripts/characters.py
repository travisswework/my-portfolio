"""Per-character settings shared by step1_import, step2_refine and step3_beauty (plain data, no Unreal imports).

Every KayKit adventurer uses an 8 x 4 atlas of gradient swatches. The grading code below re-grades each swatch id
(id = row * 8 + column) into a PBR response; the weapon material adds overrides on top, including the glow.
Pick characters for a run with the KNIGHT_REFINE_CHARACTERS environment variable (comma separated, default all).
"""
import os

# Shared start of every Custom node: work out which swatch this texel belongs to.
HEADER = r'''
float2 cuv = frac(UV);
int2 cell = int2(floor(cuv * float2(8.0, 4.0)));
int id = cell.y * 8 + cell.x;
float l = dot(C, float3(0.2126, 0.7152, 0.0722));
float3 base = C; float metal = 0.0; float rough = 0.62; float3 emi = float3(0.0, 0.0, 0.0);
'''


def v3(t):
    return 'float3({}, {}, {})'.format(*t)


def rules(*items):
    """[(swatch ids, HLSL body), ...] -> an if / else-if chain."""
    out = []
    for i, (ids, body) in enumerate(items):
        cond = ' || '.join(f'id == {k}' for k in ids)
        out.append(f"{'if' if i == 0 else 'else if'} ({cond}) {{ {body} }}")
    return '\n'.join(out) + '\n'


def overrides(*items):
    """Independent ifs, applied after the main table (used by the weapon material)."""
    return ''.join(f"if ({' || '.join(f'id == {k}' for k in ids)}) {{ {body} }}\n" for ids, body in items)


def ramp(dark, light, gain, metal=0.0, rough=0.8):
    """Recolour by luminance between two colours (keeps the swatch's painted gradient)."""
    return f'float t = saturate(l * {gain}); base = lerp({v3(dark)}, {v3(light)}, t); metal = {metal}; rough = {rough};'


def tint(mul, metal=0.0, rough=0.6):
    return f'base = saturate(C * {v3(mul)}); metal = {metal}; rough = {rough};'


def keep(rough):
    return f'rough = {rough};'


def glow(base_col, emissive, metal=0.8, rough=0.2):
    return (f'base = {v3(base_col)} * (0.6 + 0.5 * l); metal = {metal}; rough = {rough}; '
            f'emi = {v3(emissive)} * (0.5 + 2.2 * l);')


GOLD = ((0.36, 0.20, 0.05), (1.0, 0.76, 0.33))
LEATHER = (0.50, 0.36, 0.30)
DARK_LEATHER = (0.42, 0.32, 0.28)
DARK_WOOD = (0.50, 0.36, 0.28)

CHARACTERS = {
    # The knight's table is kept exactly as it was first built (hand-written), so re-running reproduces it.
    'Knight': dict(
        export='knight', texture='knight_texture', weapon_material='M_Knight_Blade', main_material='M_Knight_Refined',
        anims={'idle': 'Idle', 'attack': '1H_Melee_Attack_Slice_Diagonal', 'block': 'Blocking', 'cheer': 'Cheer'},
        main=r'''
if (id == 3 || id == 7 || id == 10) { base = saturate(C * float3(1.80, 1.90, 2.05)); metal = 0.92; rough = 0.30; }
else if (id == 4 || id == 15) { base = saturate(C * float3(1.90, 1.90, 2.10)); metal = 0.85; rough = 0.42; }
else if (id == 5 || id == 6) { base = C * float3(0.50, 0.36, 0.30); rough = 0.72; }
else if (id == 8 || id == 18) { float t = saturate(l * 3.2); base = lerp(float3(0.045, 0.012, 0.13), float3(0.42, 0.20, 0.86), t); rough = 0.82; }
else if (id == 9) { float t = saturate(l * 1.6); base = lerp(float3(0.36, 0.20, 0.05), float3(1.0, 0.76, 0.33), t); metal = 1.0; rough = 0.26; }
else if (id == 0 || id == 1) { rough = 0.55; }
else if (id == 2) { rough = 0.45; }
else if (id == 11) { base = saturate(C * float3(1.85, 1.95, 2.10)); metal = 0.95; rough = 0.24; }
else if (id == 13) { float t = saturate(l * 3.0); base = lerp(float3(0.05, 0.015, 0.14), float3(0.36, 0.17, 0.74), t); metal = 0.3; rough = 0.30; }
else if (id == 14) { float t = saturate(l * 3.5); base = lerp(float3(0.36, 0.20, 0.05), float3(1.0, 0.76, 0.33), t); metal = 1.0; rough = 0.28; }
''',
        weapon=r'''
if (id == 11) { base = float3(0.78, 0.86, 0.95) * (0.6 + 0.6 * l); metal = 1.0; rough = 0.16; emi = float3(0.12, 0.78, 1.0) * (0.5 + 2.2 * l); }
if (id == 13) { float t = saturate(l * 2.4); base = lerp(float3(0.36, 0.20, 0.05), float3(1.0, 0.76, 0.33), t); metal = 1.0; rough = 0.30; }
'''),

    # Ember warrior: crimson cloth, dark fur, iron axe with a glowing edge, bronze bands, auburn beard.
    'Barbarian': dict(
        export='barbarian', texture='barbarian_texture', weapon_material='M_Barbarian_Weapon', main_material='M_Barbarian_Refined',
        anims={'idle': '2H_Melee_Idle', 'attack': '2H_Melee_Attack_Chop', 'special': '2H_Melee_Attack_Spin', 'cheer': 'Cheer'},
        main=rules(
            ((0,), keep(0.55)),
            ((1,), ramp((0.06, 0.015, 0.005), (0.62, 0.20, 0.06), 2.0, rough=0.7)),
            ((2,), keep(0.45)),
            ((3,), tint((1.45, 1.45, 1.55), 0.85, 0.38)),
            ((6,), tint((0.55, 0.40, 0.33), 0.0, 0.72)),
            ((7,), ramp((0.02, 0.012, 0.008), (0.30, 0.18, 0.10), 3.0, rough=0.92)),
            ((8, 9), ramp((0.06, 0.004, 0.008), (0.62, 0.07, 0.05), 3.0, rough=0.85)),
            ((10,), tint((0.98, 0.90, 0.76), 0.0, 0.45)),
            ((15,), tint((0.45, 0.38, 0.34), 0.0, 0.75)),
            ((19,), tint((0.60, 0.45, 0.38), 0.0, 0.70)),
            ((23,), ramp((0.20, 0.09, 0.03), (0.85, 0.50, 0.22), 2.0, metal=0.9, rough=0.35)),
        ),
        weapon=overrides(
            ((11,), tint((1.6, 1.6, 1.7), 0.92, 0.30)),
            ((18,), tint((1.1, 1.1, 1.2), 0.85, 0.35)),
            ((16,), glow((1.0, 0.55, 0.25), (1.0, 0.32, 0.04), metal=0.6, rough=0.25)),
            ((13,), tint(DARK_WOOD, 0.0, 0.70)),
        )),

    # Arcane scholar: royal violet robe, gold trim, silver fittings, teal accents, glowing staff crystal.
    'Mage': dict(
        export='mage', texture='mage_texture', weapon_material='M_Mage_Weapon', main_material='M_Mage_Refined',
        anims={'idle': 'Idle', 'attack': 'Spellcast_Shoot', 'special': 'Spellcasting', 'cheer': 'Cheer'},
        main=rules(
            ((0, 23), keep(0.55)),
            ((1,), keep(0.40)),
            ((2,), keep(0.45)),
            ((3, 4), tint((1.8, 1.85, 2.0), 0.9, 0.28)),
            ((5,), ramp(*GOLD, 2.0, metal=1.0, rough=0.26)),
            ((8, 9), ramp((0.03, 0.01, 0.09), (0.40, 0.18, 0.85), 4.0, metal=0.05, rough=0.75)),
            ((15,), ramp((0.01, 0.005, 0.03), (0.12, 0.05, 0.30), 5.0, rough=0.70)),
            ((10,), ramp((0.05, 0.005, 0.04), (0.62, 0.08, 0.45), 3.0, rough=0.80)),
            ((16,), keep(0.50)),
            ((18,), ramp((0.0, 0.04, 0.05), (0.06, 0.60, 0.62), 4.0, metal=0.2, rough=0.50)),
            ((19,), tint(LEATHER, 0.0, 0.72)),
        ),
        weapon=overrides(
            ((22,), glow((0.30, 0.85, 1.0), (0.20, 0.85, 1.0), metal=0.1, rough=0.15)),
            ((11,), tint((1.8, 1.85, 2.0), 0.9, 0.28)),
            ((13,), tint(DARK_WOOD, 0.0, 0.70)),
        )),

    # Shadow blade: midnight-teal leathers, gunmetal, twin knives with a venom-teal glow.
    'Rogue': dict(
        export='rogue', texture='rogue_texture', weapon_material='M_Rogue_Weapon', main_material='M_Rogue_Refined',
        anims={'idle': 'Idle', 'attack': 'Dualwield_Melee_Attack_Slice', 'special': 'Dualwield_Melee_Attack_Stab', 'cheer': 'Cheer'},
        main=rules(
            ((0,), keep(0.55)),
            ((1,), tint((0.55, 0.42, 0.38), 0.0, 0.60)),
            ((2,), keep(0.45)),
            ((3,), tint((1.3, 1.35, 1.45), 0.85, 0.38)),
            ((5, 19), tint(DARK_LEATHER, 0.0, 0.70)),
            ((6, 15, 21), tint((0.40, 0.30, 0.27), 0.0, 0.72)),
            ((8,), ramp((0.004, 0.015, 0.02), (0.02, 0.16, 0.18), 5.0, rough=0.75)),
            ((9,), ramp((0.0, 0.03, 0.04), (0.02, 0.32, 0.34), 3.5, rough=0.70)),
            ((16,), tint((0.85, 0.72, 0.55), 0.0, 0.60)),
        ),
        weapon=overrides(
            ((10,), glow((0.70, 0.95, 0.95), (0.05, 0.90, 0.75), metal=1.0, rough=0.18)),
            ((11,), tint((1.3, 1.35, 1.45), 0.85, 0.38)),
            ((14,), tint(DARK_LEATHER, 0.0, 0.70)),
        )),

    # Night variant of the rogue: plum and violet leathers, silver crossbow with a glowing violet bolt.
    'RogueHooded': dict(
        export='roguehooded', texture='rogue_texture', weapon_material='M_RogueHooded_Weapon', main_material='M_RogueHooded_Refined',
        anims={'idle': 'Idle', 'attack': '1H_Ranged_Shoot', 'special': '1H_Ranged_Reload', 'cheer': 'Cheer'},
        main=rules(
            ((0,), keep(0.55)),
            ((1,), tint((0.55, 0.42, 0.38), 0.0, 0.60)),
            ((2,), keep(0.45)),
            ((3,), tint((1.3, 1.35, 1.45), 0.85, 0.38)),
            ((5, 19), tint(DARK_LEATHER, 0.0, 0.70)),
            ((6, 15, 21), tint((0.40, 0.30, 0.27), 0.0, 0.72)),
            ((8,), ramp((0.008, 0.003, 0.018), (0.10, 0.035, 0.21), 5.0, rough=0.75)),
            ((9,), ramp((0.012, 0.004, 0.04), (0.26, 0.09, 0.52), 3.5, rough=0.75)),
        ),
        weapon=overrides(
            ((11, 10), tint((1.8, 1.85, 2.0), 0.9, 0.28)),
            ((14,), tint(DARK_WOOD, 0.0, 0.70)),
            ((13,), ramp(*GOLD, 2.0, metal=0.9, rough=0.35)),
            ((16,), glow((0.85, 0.70, 1.0), (0.55, 0.20, 1.0), metal=0.3, rough=0.25)),
        )),
}

# Beauty still (step3): the posed frame (animation key, fraction of its length), camera yaw / elevation, the
# colours of the two rim lights, picked to echo each character's accent, and how much specular the key softbox
# gives (full on the knight's chrome; lower on cloth and skin, where its broad sheen washes the colour out).
CYAN, VIOLET = (0.37, 0.90, 0.94), (0.65, 0.45, 1.0)
BEAUTY = {
    'Knight': dict(shot=('cheer', 0.55, 150, 20), rims=(CYAN, VIOLET), key_specular=1.0),
    'Barbarian': dict(shot=('special', 0.3, 120, 20), rims=((1.0, 0.50, 0.22), VIOLET), key_specular=0.3),
    'Mage': dict(shot=('attack', 0.55, 130, 20), rims=(CYAN, (0.80, 0.40, 1.0)), key_specular=0.3),
    'Rogue': dict(shot=('cheer', 0.55, 110, 20), rims=((0.22, 0.95, 0.78), VIOLET), key_specular=0.3),
    'RogueHooded': dict(shot=('attack', 0.55, 115, 20), rims=((0.55, 0.72, 1.0), (0.80, 0.40, 1.0)), key_specular=0.3),
}

for _name, _cfg in CHARACTERS.items():
    _cfg.update(BEAUTY[_name])
    _cfg['folder'] = f'/Game/{_name}'
    _cfg['asset'] = f'{_name}_Loadout'
    _cfg['source'] = f'{_name}_Loadout.glb'


def selected():
    wanted = os.environ.get('KNIGHT_REFINE_CHARACTERS', '').strip()
    names = [n.strip() for n in wanted.split(',') if n.strip()] or list(CHARACTERS)
    unknown = set(names) - set(CHARACTERS)
    if unknown:
        raise ValueError(f'unknown characters: {sorted(unknown)}')
    return [(n, CHARACTERS[n]) for n in names]
