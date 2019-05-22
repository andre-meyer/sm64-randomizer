from Constants import ALL_LEVELS, CAP_LEVELS, MISSION_LEVELS, BOWSER_STAGES, LVL_BOB, SPECIAL_LEVELS, LVL_MAIN_SCR, LVL_CASTLE_GROUNDS, BEHAVIOUR_NAMES
from randoutils import format_binary
import random
import sys
import numpy as np
from Entities.Object3D import Object3D
#from Parsers.LevelScript import LevelScriptParser

from random import shuffle

WHITELIST_SHUFFLING = [
  (None, 0xBC), # Bob-Omb
  (0x13003174, None), # Bob-Omb
  (0x1300472C, None), # Goomba,
  (0x13004770, None), # Goomba Triplet
  (0x13001298, None), # Coin Triplet
  (0x130001F4, None), # King Bob-Omb
  (0x13002BB8, None), # King Whomp
  (0x130039D4, None), # Moneybag
  (None, 0x68), # Koopa (The Quick, Normal, etc)
  (0x130005B4, None), # Rotating Platform WF
  (0x13002AA4, None), # Tree Behaviour
  (None, 0x65), # Scuttlebug
  (None, 0x19), # Tree (Snow)
  (None, 0x17), # Tree (In Courses)
  (None, 0x18), # Tree (Courtyard)
  (None, 0x1B), # Tree (SSL)
  (0x13001548, None), # Heave-Ho
  (None, 0x78), # Heart
  (0x13004348, None), # Red Coin
  (0x13003E8C, None), # Red Coin Star
  (0x13002EC0, None), # Mario Spawn
  (0x13005468, None), # Skeeter (WDW Bug thing)
  (0x13000BC8, None), # Thwomp
  (0x13000B8C, None), # Thwomp 2
  (0x1300525C, None), # Grindel
  (0x13001FBC, None), # Piranha
  (0x13005120, None), # Fire-Spitting
  (0x13002EF8, None), # Toad
  (0x130009A4, None), # Single Coin
  (0x13000964, None), # Coins (x3)
  (0x13000984, None), # Coins (x10)
  (0x130008EC, None), # Coins (Formations)
  (0x13005440, 0x58), # Clam in JRB
  (0x13004634, None), # Pokey
  (0x13004668, 0x55), # Pokeys Head
  (0x130030A4, None), # Blue Coin
  (None, 0x7C), # Sign
  (None, 0x74), # Coin Type 1
  (None, 0x75), # Coin Type 2
  (None, 0x74), # Coin Type 3
  (None, 0x75), # Multiple Coins
  (None, 0xD4), # One-Up
  (0x130020E8, 0x57), # Lost Penguin
  (0x13002E58, None), # Wandering Penguin
  (0x13004148, 0xD4), # Homing-One-Up
  (0x130031DC, 0xC3), # Bob-Omb Buddy (With Message)
  (0x13003228, None), # Bob-Omb Buddy (Opening Canon)
  (0x1300478C, 0x66),
  #(None, 0xDF), # Chuckya
  (0x13000054, None), # Eye-Ball
  (0x13001108, None), # Flamethrower
  (0x130046DC, 0xDC), # Fly-Guy
  (None, 0x89), # Item-Box
  (0x13004698, None), # Bat
  (0x130046DC, None), # Fly-Guy
  (0x13004918, None), # Lakitu
  (0x13004954, None), # Evil Lakitu
  (0x130049C8, None), # Spiny
  (0x13004A00, None), # Mole
  (0x13004A58, None), # Mole in Hole
  (0x13003700, 0x65), # Ice Bully (Big)
  (0x130036C8, 0x64), # Ice Bully (Small)
  (0x13001650, 0x00), # Bouncing Box
  (0x130027E4, 0x65), # Boo
  (0x130027D0, 0x00), # Boo (x3)
  (0x13002794, 0x65), # Big Boo
  (0x130007F8, 0x7A), # Star
  (0x13001B70, 0x00), # Checkerboard Elevator (Logic: DON'T TOUCH FOR VANISH CAP LEVEL)
  (0x13002F74, 0x00), # Mario Start 1
  (0x1300442C, None), # TTC: Pendulum
  (0x130054B8, None), # TTC: Pendulum
  (0x13004FD4, None), # BBH: Haunted Chair
  (0x13005024, None), # BBH: Piano
  (0x1300506C, None), # BBH: Bookend
]

BSCRIPT_START = 0x10209C

class LevelRandomizer:
  def __init__(self, rom : 'ROM'):
    self.rom = rom

  @staticmethod
  def can_shuffle(obj : Object3D):
    if obj.source == "MARIO_SPAWN":
      return True
    else:
      for (target_bscript_address, target_model_id) in WHITELIST_SHUFFLING:
        if (target_model_id is None or target_model_id == obj.model_id) and (target_bscript_address is None or target_bscript_address == obj.behaviour):
          return True
      return False

  def is_valid_position(self, level_geometry, object3d, position):
    # count intersections below ( % 2 == 1 to ensure it's never oob, in walls, etc)
    ray_start = np.array(position)
    ray_start[2] += 1 # to ensure we're above the floor

    ray_end = np.array(position)
    ray_end[2] -= 1e10 # far down

    intersection_count = 0
    intersection_points = []
    for triangle in level_geometry.get_triangles():
      [p1, p2, p3] = triangle
      tri_edge_1 = p2 - p1
      tri_edge_2 = p3 - p1

      edge_crs = np.cross(tri_edge_1, tri_edge_2)
      edge_off = np.dot(edge_crs, p1) * -1

      line_edge = ray_end - ray_start
      line_dot = np.dot(edge_crs, line_edge)

      if abs(line_dot) < 1e-20:
        # this triangle is parallel to the line
        continue

      intersect_mag = ((np.dot(edge_crs, ray_start) + edge_off) / line_dot) * -1
      intersect_point = ray_start + intersect_mag * line_dot

      edge_a = np.cross(edge_crs, tri_edge_1)
      edge_a_dot = np.dot(edge_a, p1) * -1

      if np.dot(edge_a, intersect_point) + edge_a_dot <= 0:
        #print("outside edge a")
        # outside edge_a
        continue

      tri_edge_3 = p3 - p2
      edge_b = np.cross(edge_crs, tri_edge_3)
      edge_b_dot = np.dot(edge_b, p2) * -1

      if np.dot(edge_b, intersect_point) + edge_b_dot <= 0:
        #print("outside edge b")
        # outside edge_b
        continue

      edge_c = np.cross(edge_crs, -tri_edge_2)
      edge_c_dot = np.dot(edge_c, p3) * -1

      if np.dot(edge_c, intersect_point) + edge_c_dot <= 0:
        #print("outside edge c")
        # outside edge_c
        continue
      
      intersection_count += 1
      intersection_points.append(intersect_point)

    print(intersection_count, intersection_points)

    
    return True

  def shuffle_objects(self):
    for (level, parsed) in self.rom.levelscripts.items():
      if level in SPECIAL_LEVELS:
        continue

      floor_triangles = parsed.level_geometry.get_floor_triangles()
      shufflable_objects = list(filter(LevelRandomizer.can_shuffle, parsed.objects))

      while len(shufflable_objects) > 0:
        obj = shufflable_objects.pop()

        [p1, p2, p3] = random.choice(floor_triangles)
        
        r1 = random.random()
        r2 = random.random()

        if r1 + r2 > 1:
          r1 = r1 - 1
          r2 = r2 - 1
        
        point = p1 + (r1 * (p2 - p1)) + (r2 * (p3 - p1))

        if not self.is_valid_position(parsed.level_geometry, obj, point):
          shufflable_objects.append(obj)
        else:
          point[2] += 100
          obj.set(self.rom, 'position', tuple([int(p) for p in list(point)]))

      # randomize positions
      for obj in parsed.objects:
        if LevelRandomizer.can_shuffle(obj):
          [p1, p2, p3] = random.choice(floor_triangles)
          #print(p1, p2, p3)
          
          r1 = random.random()
          r2 = random.random()

          if r1 + r2 > 1:
            r1 = r1 - 1
            r2 = r2 - 1
          
          point = p1 + (r1 * (p2 - p1)) + (r2 * (p3 - p1))
          #print(point)
          #print(tuple(point))
          point[2] += 100
          obj.set(self.rom, 'position', tuple([int(p) for p in list(point)]))

          #print(obj.position)
          #positions.append(obj.position)
          #objects.append(obj)

      #print(f'randomized {len(positions)} in {level.name}')
      #shuffle(positions)
      #for idx, obj in enumerate(objects):
        #position = positions[idx]
        #print(hex(obj.behaviour) if obj.behaviour else "None", BEHAVIOUR_NAMES[hex(obj.behaviour)] if obj.behaviour and hex(obj.behaviour) in BEHAVIOUR_NAMES else "Unknown Behaviour", hex(obj.model_id) if obj.model_id else "None")
        #obj.set(self.rom, 'position', position)
    '''
    for level in self.level_scripts:
      positions = []
      objects = []

      if self.level_scripts[level].mario_spawn:
        mario_spawn = self.level_scripts[level].mario_spawn
        positions.append(mario_spawn[1])
        objects.append(mario_spawn)
      
      for obj in self.level_scripts[level].objects:
        if LevelRandomizer.can_shuffle(obj.model_id, obj.behaviour):
          positions.append(obj.position)
          objects.append(obj)
      
      shuffle(positions)
      for idx, obj in enumerate(objects):
        position = positions[idx]

        if type(obj) is Object3D:
          obj.change_position(self.rom, position)
        elif type(obj) is tuple: # temp mario thing:
          #print(level.name, "rando mario")
          (area_id, translate, rotation, mem_address) = obj
          #print("changing", translate, "to", position)
          #print(position)
          self.rom.write_integer(mem_address + 4, position[0], 2, True)
          self.rom.write_integer(mem_address + 6, position[1], 2, True)
          self.rom.write_integer(mem_address + 8, position[2], 2, True)

    pass

    '''  