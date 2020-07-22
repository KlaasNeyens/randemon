import ctypes
import datetime
import os
import random
import sys
import time
from threading import Thread

from PIL import Image

import inputs
import spriteSheetManager as ssm
# from worldMap import image_grayscale_to_dict
from buildingGenerator import spawn_house, add_random_ends
from decorationGenerator import spawn_truck, spawn_rocks
# from worldMap import image_grayscale_to_dict
from heightMapGenerator import create_hills, create_hill_edges
from npcGenerator import spawn_npc
from pathGenerator import apply_path_sprites, generate_dijkstra_path, create_lanterns
from plantGenerator import create_trees, grow_grass, create_rain
from pokemonGenerator import spawn_pokemon
from waterGenerator import create_rivers, create_beach


def render2(pmap, layer, draw_sheet):
    for tile_x, tile_y in getattr(pmap, layer)["tiles"].keys():
        try:
            current_tile = pmap.get_tile(layer, tile_x, tile_y)
            sheet_writer = sheet_writers[current_tile[0]]
            correction = 6 if "npc_" in current_tile else 0  # npc's are slightly larger than a tile
            sheet_writer.draw_tile(current_tile[1], current_tile[2], draw_sheet, tile_x * 16, tile_y * 16)
        except Exception:
            pass


class Map:

    TILE_SIZE = 16  # Length of 1 tile in pixels

    def __init__(self, width, height, max_hill_height, tall_grass_coverage, tree_coverage, rain_rate,
                 seed=random.randint(0, sys.maxsize)):
        self.seed = seed
        self.width = width
        self.height = height
        self.max_hill_height = max_hill_height
        self.tall_grass_coverage = tall_grass_coverage
        self.tree_coverage = tree_coverage
        self.rain_rate = rain_rate

        self.raining = False
        self.front_doors = []
        self.end_points = []
        self.tile_heights = dict()
        self.ground_layer = {"pa": Image.open(os.path.join("resources", "path.png")), "tiles": dict()}
        self.secondary_ground = {"de": Image.open(os.path.join("resources", "path.png")), "tiles": dict()}
        self.buildings = {"ho": Image.open(os.path.join("resources", "houses.png")), "tiles": dict()}
        self.rain = dict()
        self.decoration_layer = {"tiles": dict()}
        self.npc_layer = dict()
        self.height_map = dict()
        self.grass_layer = {"na": Image.open(os.path.join("resources", "nature.png")), "tiles": dict()}

        self.highest_path = 0

        random.seed(seed)

    def out_of_bounds(self, x, y):
        return x < 0 or y < 0 or x >= self.width or y >= self.height

    def get_tile(self, layer, x, y, default=""):
        try:
            return getattr(self, layer)["tiles"][(x, y)]
        except KeyError:
            return default
        except AttributeError as a:
            print(a)

    def get_tile_type(self, layer, x, y, default=""):
        try:
            return self.get_tile(layer, x, y, default)[0]
        except Exception:
            return default


# get command line options
parser = inputs.make_parser()
args = parser.parse_args()

# This is the main program
sheet_writers = {
    "pa": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "path.png"))),
    "wa": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "water.png"))),
    "na": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "nature.png"))),
    "hi": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "hills.png"))),
    "ro": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "road.png"))),
    "ho": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "houses.png"))),
    "de": ssm.SpriteSheetWriter(Image.open(os.path.join("resources", "decoration.png")))
}

# full hd -> 120,68; my phone -> 68,147
map_size_x = args.map_size_x or 50  # The horizontal amount of tiles the map consists of
map_size_y = args.map_size_y or 50  # The vertical amount of tiles the map consists of
all_pokemon = False
random_map = Map(args.map_size_x, args.map_size_y, 5, 40, 20, 20, args.seed_opt)
screen_Size_X = Map.TILE_SIZE * args.map_size_x
screen_Size_Y = Map.TILE_SIZE * args.map_size_y
x_offset = random.randint(0, 1000000)
y_offset = random.randint(0, 1000000)

if args.headless_opt: os.environ["SDL_VIDEODRIVER"] = "dummy"

visual = ssm.DrawSheet(screen_Size_X, screen_Size_Y)

to_time = time.time()
print("*creating landscape*")
create_hills(random_map, x_offset, y_offset)
create_rivers(random_map)
create_beach(random_map, x_offset, y_offset)
add_random_ends(random_map, ("pa", 0, 0))
create_hill_edges(random_map)
print("*builing houses*")
spawn_house(random_map, "pokecenter", ("pa", 0, 0))
spawn_house(random_map, "pokemart", ("pa", 0, 0))
spawn_house(random_map, "gym", ("pa", 0, 0))
spawn_house(random_map, "powerplant", ("pa", 0, 0))
for house_type in range(22):
    for x in range(1):
        spawn_house(random_map, house_type, ("pa", 0, 0))
# for house in range(2):
#     spawn_house(random_map, random.randint(1, 9), "p_1")
random.shuffle(random_map.front_doors)
random_map.front_doors += random_map.end_points
print("*dijkstra*")
generate_dijkstra_path(random_map, ("pa", 0, 0))
apply_path_sprites(random_map)

create_hill_edges(random_map, update=True)
create_lanterns(random_map)
print("*growing trees*")
create_trees(random_map, 30, x_offset, y_offset)
print("*spawning pokemon*")
all_pokemon = spawn_pokemon(random_map)
print("*spawning npc*")
spawn_npc(random_map, 1)
print("*spawning decorations")
spawn_truck(random_map, 0.05)
spawn_rocks(random_map, 0.01)
print("*growing grass*")
grow_grass(random_map, random_map.tall_grass_coverage, x_offset, y_offset)
print("*checking the weather forecast*")
create_rain(random_map, 10, random_map.rain_rate)

print("*rendering*")
render2(random_map, "grass_layer", visual.drawable())
render2(random_map, "ground_layer", visual.drawable())
render2(random_map, "secondary_ground", visual.drawable())
render2(random_map, "buildings", visual.drawable())
# render(random_map.npc_layer)
render2(random_map, "decoration_layer", visual.drawable())
# render(random_map.rain)

# generate_height_map(random_map)
# random_map.render(random_map.height_map)
print("time = " + str(time.time() - to_time) + " seconds")
print("Seed: " + str(random_map.seed))

if not args.headless_opt: visual.show()


def prompt():
    save = "y" if args.save_opt else input("Save this image? (y/n/w): ")
    file_name = datetime.datetime.now().strftime("%G-%m-%d %H-%M-%S")
    if save == "y" or save == "w":
        if not os.path.isdir("saved images"):
            os.mkdir("saved images")
        visual.save(file_name)
        cwd = os.getcwd()
        if save == "w":
            ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.join(cwd, "saved images", file_name + ".png"), 0)


t = Thread(target=prompt)
t.daemon = True
t.start()
t.join()

quit()
