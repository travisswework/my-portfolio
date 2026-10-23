"""The Realm: a hex-map diorama built from KayKit Medieval Hexagon tiles (plain data, no Unreal imports).

Pointy-top hexes 2 units across the flats, axial coordinates (q, r). In glTF space (y up) a hex sits at
x = 2q + r, z = sqrt(3) r, and edge e (0..5) faces the angle 60 * e measured as atan2(z, x):
e0 (+1, 0), e1 (0, +1), e2 (-1, +1), e3 (-1, 0), e4 (0, -1), e5 (+1, -1). Negative r is north (the back of the view).

Each tile is placed with a turn k (0..5): a local edge e ends up facing edge (e + k) % 6, which is a rotation of
-60 * k degrees about +y in glTF space.

    python Scripts/realm_layout.py [preview.png]    # prints the tile counts and draws a top-down preview
"""
import math
import random

SQRT3 = math.sqrt(3)
DIRS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]

# open edges of the connecting tiles, in the tile's own frame (measured from the tile geometry)
RIVER = {'hex_river_A': {0, 3}, 'hex_river_B': {3, 5}, 'hex_river_C': {3, 4}}
ROAD = {'hex_road_A': {0, 3}, 'hex_road_B': {3, 5}, 'hex_road_C': {3, 4}, 'hex_road_D': {1, 3, 5}}
COAST = {'hex_coast_E': {1, 2}, 'hex_coast_A': {0, 1, 2}, 'hex_coast_B': {0, 1, 2, 3}, 'hex_coast_C': {5, 0, 1, 2, 3}}
CROSSING = {'river': {0, 3}, 'road': {1, 4}}  # hex_river_crossing_A: a ford where a road crosses the river

RADIUS = 8  # the map, including the sea ring


def world(q, r):
    return 2 * q + r, SQRT3 * r


def dist(q, r):
    return max(abs(q), abs(r), abs(-q - r))


def neighbour(q, r, e):
    dq, dr = DIRS[e]
    return q + dq, r + dr


def edge_between(a, b):
    return DIRS.index((b[0] - a[0], b[1] - a[1]))


def fit(catalog, edges):
    """Pick the tile and turn whose open edges match exactly."""
    edges = set(edges)
    for name, local in catalog.items():
        for k in range(6):
            if {(e + k) % 6 for e in local} == edges:
                return name, k
    return None


def build(seed=7):
    rnd = random.Random(seed)
    cells = {}
    for q in range(-RADIUS, RADIUS + 1):
        for r in range(-RADIUS, RADIUS + 1):
            if dist(q, r) <= RADIUS:
                cells[(q, r)] = {'kind': 'sea'}

    def kind(p):
        return cells[p]['kind'] if p in cells else 'sea'

    # island with a wobbly coastline, leaving at least one ring of sea
    for (q, r), c in cells.items():
        x, z = world(q, r)
        a = math.atan2(z, x)
        if dist(q, r) <= min(7, 6.9 + 0.6 * math.sin(3 * a + 0.6) + 0.35 * math.sin(5 * a + 2.1)):
            c['kind'] = 'land'
    # mountain range across the north
    for (q, r), c in cells.items():
        if c['kind'] == 'land' and r <= -4:
            c['kind'] = 'mountain'

    # lake in the west-centre
    lake = [(-2, 0), (-3, 0), (-3, 1), (-4, 1), (-4, 0)]
    for p in lake:
        cells[p]['kind'] = 'lake'

    # river: from under the mountains, straight south-west into the lake, then from the lake to the south coast
    upper = [(1, -3), (0, -2), (-1, -1)]
    lower = [(-3, 2), (-4, 3), (-4, 4), (-5, 5)]
    for p in upper + lower:
        cells[p]['kind'] = 'river'
    mouth = neighbour(*lower[-1], 2)
    cells[mouth]['kind'] = 'sea'

    def lay_river(seq):
        for i in range(1, len(seq) - 1):
            t = fit(RIVER, [edge_between(seq[i], seq[i - 1]), edge_between(seq[i], seq[i + 1])])
            assert t, f'no river tile fits at {seq[i]}'
            cells[seq[i]]['tile'], cells[seq[i]]['turn'] = t
    lay_river([(2, -4)] + upper + [(-2, 0)])
    lay_river([(-3, 1)] + lower + [mouth])

    # road: village in the west, across the river at a ford, to the castle in the east
    road = [(-4, -1), (-3, -1), (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1), (3, -1)]
    ford = (-1, -1)
    river_edges = {edge_between(ford, (0, -2)), edge_between(ford, (-2, 0))}
    road_edges = {edge_between(ford, (-2, -1)), edge_between(ford, (0, -1))}
    turn = [k for k in range(6) if {(e + k) % 6 for e in CROSSING['river']} == river_edges
            and {(e + k) % 6 for e in CROSSING['road']} == road_edges]
    assert turn, 'the ford does not line up with the road'
    cells[ford]['tile'], cells[ford]['turn'] = 'hex_river_crossing_A', turn[0]
    for i, p in enumerate(road):
        if p == ford:
            continue
        es = [edge_between(p, road[j]) for j in (i - 1, i + 1) if 0 <= j < len(road)]
        if len(es) == 1:  # the road runs on out of the far edge
            es.append((es[0] + 3) % 6)
        t = fit(ROAD, es)
        assert t, f'no road tile fits at {p}'
        cells[p]['kind'] = 'road'
        cells[p]['tile'], cells[p]['turn'] = t

    # coasts around the sea and the lake
    for (q, r), c in cells.items():
        if c['kind'] == 'land':
            water = [e for e in range(6) if kind(neighbour(q, r, e)) in ('sea', 'lake')]
            t = fit(COAST, water) if len(water) >= 2 else None
            if t:
                c['kind'] = 'coast'
                c['tile'], c['turn'] = t

    for c in cells.values():
        if 'tile' not in c:
            c['tile'] = 'hex_water' if c['kind'] in ('sea', 'lake') else 'hex_grass'
            c['turn'] = 0

    def deco(p, name, turn=None, kind_=None):
        if p not in cells:
            return
        c = cells[p]
        c.setdefault('deco', []).append({'name': name, 'turn': rnd.randrange(6) if turn is None else turn})
        if kind_:
            c['kind'] = kind_

    # mountains: bare peaks at the back, grassy and wooded slopes in front
    for (q, r), c in sorted(cells.items()):
        if c['kind'] == 'mountain':
            names = (['mountain_A', 'mountain_B', 'mountain_C'] if r <= -5 else
                     ['mountain_A_grass', 'mountain_B_grass_trees', 'mountain_C_grass', 'mountain_A_grass_trees', 'mountain_C_grass_trees'])
            deco((q, r), rnd.choice(names))

    # castle district in the east, at the road's end
    for p, name, turn in [((4, -2), 'building_castle_blue', 4), ((5, -3), 'building_tower_A_blue', 3), ((3, -2), 'building_barracks_blue', 5),
                          ((4, -1), 'building_archeryrange_blue', 2), ((3, 0), 'building_blacksmith_blue', 1), ((5, -2), 'building_tower_B_blue', 3)]:
        deco(p, name, turn, 'town')
    # village west of the ford
    for p, name, turn in [((-3, -2), 'building_church_blue', 1), ((-2, -2), 'building_home_A_blue', 1), ((-5, -1), 'building_tavern_blue', 0),
                          ((-4, -2), 'building_market_blue', 1), ((-5, 0), 'building_home_B_blue', 0), ((-1, 0), 'building_watermill_blue', 3),
                          ((-1, -2), 'building_well_blue', 0), ((-6, 0), 'building_home_A_blue', 2)]:
        deco(p, name, turn, 'town')
    # farmland and windmill in the south-west
    for p in [(-2, 3), (-1, 3), (-2, 4), (-1, 4), (-3, 4), (-2, 5)]:
        if kind(p) == 'land':
            deco(p, 'building_grain', rnd.choice([0, 3]), 'farm')
    deco((-2, 2), 'building_windmill_blue', 2, 'farm')
    deco((-1, 2), 'building_home_B_blue', 1, 'farm')
    # forests in the west and on the east flank, hills in the foothills
    for p in [(-6, 2), (-5, 2), (-6, 3), (-5, 3), (-6, 1), (-5, 4), (-6, 4), (6, -3), (6, -4), (6, -2), (-2, -3), (-5, -2), (-6, -1)]:
        if kind(p) == 'land':
            deco(p, rnd.choice(['trees_A_large', 'trees_B_large', 'trees_A_medium', 'trees_B_medium', 'hills_A_trees', 'hills_B_trees']), None, 'forest')
    for p in [(0, -3), (2, -3), (3, -3), (-1, -3)]:
        if kind(p) == 'land':
            deco(p, rnd.choice(['hills_A', 'hills_B', 'hills_C', 'hill_single_A']), None, 'forest')
    # the skeleton camp in the far east: tents, a red banner, rocks
    for p, name in [((6, -1), 'tent'), ((7, -2), 'tent'), ((6, 0), 'flag_red'), ((5, 0), 'rock_single_D')]:
        if kind(p) == 'land':
            deco(p, name, None, 'camp')
    # scattered trees and rocks; the southern plain stays open for the horses
    for (q, r), c in sorted(cells.items()):
        if c['kind'] == 'land' and 'deco' not in c:
            plain = r >= 1 and q >= -1
            roll = rnd.random()
            if not plain and roll < 0.35:
                deco((q, r), rnd.choice(['tree_single_A', 'tree_single_B', 'trees_A_small', 'trees_B_small']))
            elif roll < (0.12 if plain else 0.2):
                deco((q, r), rnd.choice(['rock_single_A', 'rock_single_B', 'rock_single_C']))
    for p in lake[:3]:
        deco(p, rnd.choice(['waterlily_A', 'waterlily_B', 'waterplant_A']))

    tiles = []
    for (q, r), c in sorted(cells.items()):
        x, z = world(q, r)
        tiles.append({'q': q, 'r': r, 'x': x, 'z': z, 'kind': c['kind'], 'tile': c['tile'], 'turn': c['turn'],
                      'deco': c.get('deco', [])})
    meta = {
        'radius': RADIUS,
        'river': [world(*p) for p in [(2, -4)] + upper + lake[:1] + [(-3, 1)] + lower + [mouth]],
        'road': [world(*p) for p in road],
        'ford': world(*ford),
        'castle': world(4, -2),
        'camp': world(6, -1),
        'plain': [world(q, r) for (q, r), c in sorted(cells.items()) if c['kind'] == 'land' and r >= 1 and q >= -1],
        'peaks': [world(q, r) for (q, r), c in sorted(cells.items()) if c['kind'] == 'mountain' and r <= -5],
    }
    return tiles, meta


def meshes_used(tiles):
    names = set()
    for t in tiles:
        names.add(t['tile'])
        names.update(d['name'] for d in t['deco'])
    return sorted(names)


if __name__ == '__main__':
    import sys
    from collections import Counter
    tiles, meta = build()
    print(Counter(t['kind'] for t in tiles))
    print(len(tiles), 'hexes;', len(meshes_used(tiles)), 'distinct meshes:', meshes_used(tiles))
    if len(sys.argv) > 1:
        from PIL import Image, ImageDraw
        S = 26
        img = Image.new('RGB', (S * 2 * (RADIUS * 2 + 2), S * 2 * (RADIUS * 2 + 2)), (20, 16, 40))
        d = ImageDraw.Draw(img)
        cx, cy = img.width / 2, img.height / 2
        col = {'sea': (40, 90, 170), 'lake': (60, 130, 200), 'river': (70, 150, 220), 'land': (120, 170, 80),
               'coast': (210, 190, 130), 'mountain': (130, 125, 130), 'road': (170, 140, 100), 'town': (200, 90, 80),
               'farm': (220, 200, 90), 'forest': (40, 110, 60), 'camp': (120, 40, 120)}
        for t in tiles:
            px, py = cx + t['x'] * S, cy + t['z'] * S
            pts = [(px + math.cos(math.radians(30 + 60 * i)) * S * 1.12, py + math.sin(math.radians(30 + 60 * i)) * S * 1.12) for i in range(6)]
            d.polygon(pts, fill=col[t['kind']], outline=(15, 12, 30))
            label = t['tile'].replace('hex_', '')[:8] if t['kind'] in ('river', 'road', 'coast') else (t['deco'][0]['name'].replace('building_', '')[:8] if t['deco'] else '')
            if label:
                d.text((px - 20, py - 6), label, fill=(0, 0, 0))
            if t['kind'] in ('river', 'road', 'coast') or t['tile'].startswith('hex_river'):
                d.text((px - 3, py + 4), str(t['turn']), fill=(255, 255, 255))
        img.save(sys.argv[1])
        print('preview', sys.argv[1])
