
import pygame
import random
import sys
import os

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

pygame.init()
pygame.font.init()

# Grid and display settings
GRID_SIZE   = 15
CELL_SIZE   = 60
WIDTH = HEIGHT = GRID_SIZE * CELL_SIZE

VIEW_RANGE   = 2
SHOOT_RANGE  = 3
MAX_TURNS    = 300
FPS          = 200

WHITE = (255, 255, 255)
FONT = pygame.font.SysFont(None, 36)

DIRECTIONS = {
    'UP':    (0, -1),
    'DOWN':  (0, 1),
    'LEFT':  (-1, 0),
    'RIGHT': (1, 0),
}
ANGLE_MAP = {
    'RIGHT': 0,
    'UP':    90,
    'LEFT':  180,
    'DOWN':  270,
}

# Item definitions
ITEM_TYPES = ['DOUBLE_SHOT', 'DOUBLE_DAMAGE', 'MINUS_ONE', 'DOUBLE_COOLDOWN']

# Load static images
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BattleGrid Turn-Based with Items")
clock = pygame.time.Clock()

background_img = pygame.image.load("background.png")
background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))

wall_img = pygame.image.load("wall.png")
wall_img = pygame.transform.scale(wall_img, (CELL_SIZE, CELL_SIZE))

tank_blue_img = pygame.image.load("tank_blue.png")
tank_blue_img = pygame.transform.scale(tank_blue_img, (CELL_SIZE, CELL_SIZE))
tank_blue_img = pygame.transform.rotate(tank_blue_img, -90)

tank_red_img = pygame.image.load("tank_red.png")
tank_red_img = pygame.transform.scale(tank_red_img, (CELL_SIZE, CELL_SIZE))
tank_red_img = pygame.transform.rotate(tank_red_img, -90)

# Load item icons (filenames should be e.g. "double_shot.png", "minus_one.png", etc.)
item_images = {}
for t in ITEM_TYPES:
    img = pygame.image.load(f"{t.lower()}.png")
    item_images[t] = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))

class Item:
    def __init__(self, x, y, type):
        self.x = x
        self.y = y
        self.type = type
        self.image = item_images[type]

def is_visible(tank, x, y):
    return abs(x - tank.x) <= VIEW_RANGE and abs(y - tank.y) <= VIEW_RANGE

def get_enemy_area(tank):
    area = []
    for dx in range(-1, 3):
        for dy in range(-1, 3):
            nx, ny = tank.x + dx, tank.y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                area.append((nx, ny))
    xs = [p[0] for p in area]
    ys = [p[1] for p in area]
    return (min(xs), max(xs), min(ys), max(ys))

class Tank:
    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        self.facing = 'UP'
        self.desired_direction = 'UP'
        self.prev_positions = []
        self.stay_counter = 0
        self.score = 0
        self.shoot_cooldown = 0
        self.double_shot_active = False
        self.double_damage_active = False
        self.double_cooldown_active = False

        self.original_image = image
        self.image = pygame.transform.rotate(self.original_image, ANGLE_MAP[self.facing])
        self.rect = self.image.get_rect()

    def rotate(self):
        if self.desired_direction not in ANGLE_MAP:
            return False
        if self.facing != self.desired_direction:
            self.facing = self.desired_direction
            angle = ANGLE_MAP[self.facing]
            self.image = pygame.transform.rotate(self.original_image, angle)
            return True
        return False

    def move(self, grid):
        dx, dy = DIRECTIONS[self.facing]
        nx, ny = self.x + dx, self.y + dy
        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and grid[ny][nx] != 'W':
            self.x, self.y = nx, ny
            return True
        return False

    def shoot(self, grid, enemy_tank):
        if self.shoot_cooldown > 0:
            return False
        dx, dy = DIRECTIONS[self.facing]
        bx, by = self.x + dx, self.y + dy
        distance = 0
        while 0 <= bx < GRID_SIZE and 0 <= by < GRID_SIZE and distance < SHOOT_RANGE:
            if (bx, by) == (enemy_tank.x, enemy_tank.y):
                # Hit: apply item effects
                if self.double_shot_active:
                    self.double_shot_active = False
                    self.shoot_cooldown = 0
                elif self.double_cooldown_active:
                    self.shoot_cooldown = 8
                    self.double_cooldown_active = False
                else:
                    self.shoot_cooldown = 4
                return True
            if grid[by][bx] == 'W':
                break
            bx += dx
            by += dy
            distance += 1
        # Miss: still consume shot
        if self.double_shot_active:
            self.double_shot_active = False
            self.shoot_cooldown = 0
        elif self.double_cooldown_active:
            self.shoot_cooldown = 8
            self.double_cooldown_active = False
        else:
            self.shoot_cooldown = 4
        return False

class Game:
    def __init__(self, agent1, agent2):
        self.agent1 = agent1
        self.agent2 = agent2
        self.walls = self.generate_walls()
        self.grid = [['E'] * GRID_SIZE for _ in range(GRID_SIZE)]
        for (x, y) in self.walls:
            self.grid[y][x] = 'W'
        # Safe zone & schedule
        self.safe_zone = self.generate_initial_safe_zone()
        self.shrink_schedule = self.generate_shrink_schedule()
        # Spawn tanks
        x2, y2 = self.random_spawn(top=False)
        self.agent2_tank = Tank(x2, y2, tank_red_img)
        x1, y1 = self.random_spawn(top=True)
        self.agent1_tank = Tank(x1, y1, tank_blue_img)
        # Items
        self.items = self.generate_items()

    def generate_walls(self):
        walls = set()
        count = int(GRID_SIZE * GRID_SIZE * 0.15)
        while len(walls) < count:
            x = random.randrange(GRID_SIZE)
            y = random.randrange(GRID_SIZE)
            walls.add((x, y))
        # carve escape corridor
        col = random.randrange(GRID_SIZE)
        for y in range(GRID_SIZE):
            walls.discard((col, y))
        return walls

    def random_spawn(self, top=True):
        while True:
            x = random.randrange(GRID_SIZE)
            y = random.randrange(0, GRID_SIZE//3) if top else random.randrange(2*GRID_SIZE//3, GRID_SIZE)
            if (x, y) not in self.walls:
                return x, y

    def generate_initial_safe_zone(self):
        return (0, 0, GRID_SIZE-1, GRID_SIZE-1)

    def generate_shrink_schedule(self):
        steps = (GRID_SIZE - 6) // 2
        interval = (MAX_TURNS - 100) // (steps * 2)
        return [interval * turn * 2 for turn in range(1, steps+1)]
    
    def update_safe_zone(self, turn):
        if turn in self.shrink_schedule:
            x1, y1, x2, y2 = self.safe_zone
            width  = x2 - x1 + 1
            height = y2 - y1 + 1

            # Compute the new dimensions, but don’t let it shrink below 6×6
            new_w = max(width  - 2, 6)
            new_h = max(height - 2, 6)

            # Determine the valid range for the new center so the new zone stays inside the old one
            cx_min = x1 + new_w // 2
            cx_max = x2 - new_w // 2
            cy_min = y1 + new_h // 2
            cy_max = y2 - new_h // 2

            # Pick a random center within those bounds
            cx = random.randint(cx_min, cx_max)
            cy = random.randint(cy_min, cy_max)

            # Recompute the new zone’s corners based on that center
            nx1 = cx - new_w // 2
            ny1 = cy - new_h // 2
            nx2 = nx1 + new_w - 1
            ny2 = ny1 + new_h - 1

            self.safe_zone = (nx1, ny1, nx2, ny2)



    def generate_items(self):
        items = []
        for _ in range(5):
            while True:
                x = random.randrange(GRID_SIZE)
                y = random.randrange(GRID_SIZE)
                if self.grid[y][x] != 'W' and (x, y) not in [(self.agent1_tank.x, self.agent1_tank.y), (self.agent2_tank.x, self.agent2_tank.y)]:
                    t = random.choice(ITEM_TYPES)
                    items.append(Item(x, y, t))
                    break
        return items

    def draw(self):
        screen.fill((0, 0, 0))
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                px, py = x*CELL_SIZE, y*CELL_SIZE
                if is_visible(self.agent1_tank, x, y) or is_visible(self.agent2_tank, x, y):
                    screen.blit(background_img, (px, py))
                    if (x, y) in self.walls:
                        screen.blit(wall_img, (px, py))
                else:
                    pygame.draw.rect(screen, (30, 30, 30), (px, py, CELL_SIZE, CELL_SIZE))
        # draw items
        for item in self.items:
            if is_visible(self.agent1_tank, item.x, item.y) or is_visible(self.agent2_tank, item.x, item.y):
                screen.blit(item.image, (item.x*CELL_SIZE, item.y*CELL_SIZE))
        # draw tanks
        if is_visible(self.agent1_tank, self.agent1_tank.x, self.agent1_tank.y):
            screen.blit(self.agent1_tank.image, (self.agent1_tank.x*CELL_SIZE, self.agent1_tank.y*CELL_SIZE))
        if is_visible(self.agent2_tank, self.agent2_tank.x, self.agent2_tank.y):
            screen.blit(self.agent2_tank.image, (self.agent2_tank.x*CELL_SIZE, self.agent2_tank.y*CELL_SIZE))
        # scores
        blue_text = FONT.render(f"{self.agent1.name}: {self.agent1_tank.score}", True, WHITE)
        red_text  = FONT.render(f"{self.agent2.name}: {self.agent2_tank.score}", True, WHITE)
        screen.blit(blue_text, (10, 10))
        screen.blit(red_text, (WIDTH - red_text.get_width() - 10, 10))
        # draw safe zone
        x1, y1, x2, y2 = self.safe_zone
        rect = pygame.Rect(x1*CELL_SIZE, y1*CELL_SIZE, (x2-x1+1)*CELL_SIZE, (y2-y1+1)*CELL_SIZE)
        pygame.draw.rect(screen, (0,255,0), rect, 4)
        pygame.display.flip()

    def _can_move(self, x, y):
        return 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE and (x, y) not in self.walls

    def _take_action(self, agent, tank, enemy_tank, enemy_area):
        # visibility
        visible_enemy = (enemy_tank.x, enemy_tank.y) if is_visible(tank, enemy_tank.x, enemy_tank.y) else None
        visible_walls = [(nx, ny) for dx in range(-VIEW_RANGE, VIEW_RANGE+1) for dy in range(-VIEW_RANGE, VIEW_RANGE+1)
                         if 0 <= (nx:=tank.x+dx) < GRID_SIZE and 0 <= (ny:=tank.y+dy) < GRID_SIZE and (nx, ny) in self.walls]
        item_hints = []
        for item in self.items:
            hx = min(item.x, GRID_SIZE-2)
            hy = min(item.y, GRID_SIZE-2)
            item_hints.append((hx, hy, hx+1, hy+1, item.type))
        
        direction, shoot_flag = agent.decide(tank, visible_enemy, visible_walls, enemy_area, self.safe_zone,item_hints)
        tank.desired_direction = direction
        rotated = tank.rotate()
        moved = False
        dx, dy = DIRECTIONS[tank.facing]
        nx, ny = tank.x+dx, tank.y+dy
        if not rotated and self._can_move(nx, ny) and (nx, ny) != (enemy_tank.x, enemy_tank.y):
            tank.x, tank.y = nx, ny
            moved = True
        if not moved:
            tank.stay_counter += 1
            if tank.stay_counter > 2:
                dirs = list(DIRECTIONS.keys()); random.shuffle(dirs)
                for d in dirs:
                    dx, dy = DIRECTIONS[d]
                    if self._can_move(nx:=tank.x+dx, ny:=tank.y+dy) and (nx, ny) != (enemy_tank.x, enemy_tank.y):
                        tank.desired_direction = d; tank.rotate(); tank.x, tank.y = nx, ny
                        tank.stay_counter = 0; break
        else:
            tank.stay_counter = 0
        # item pickup
        for item in list(self.items):
            if (tank.x, tank.y) == (item.x, item.y):
                if item.type == 'DOUBLE_SHOT': tank.double_shot_active = True
                elif item.type == 'DOUBLE_DAMAGE': tank.double_damage_active = True
                elif item.type == 'MINUS_ONE': tank.score -= 1
                elif item.type == 'DOUBLE_COOLDOWN': tank.double_cooldown_active = True
                self.items.remove(item)
        # shooting
        if shoot_flag:
            return tank.shoot(self.grid, enemy_tank)
        return False

    def step_single_agent(self, agent_id):
        tank = self.agent1_tank if agent_id==1 else self.agent2_tank
        tank.shoot_cooldown = max(0, tank.shoot_cooldown - 1)
        enemy = self.agent2_tank if agent_id==1 else self.agent1_tank
        hit = self._take_action(self.agent1 if agent_id==1 else self.agent2, tank, enemy, get_enemy_area(enemy))
        return hit, (self.agent1.name if agent_id==1 else self.agent2.name)

if __name__ == "__main__":
    from agent_blue import AgentBlue
    from agent_red import AgentRed

    game = Game(AgentBlue("Blue"), AgentRed("Red"))
    for turn in range(1, MAX_TURNS+1):
        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                pygame.quit(); sys.exit()
        current = 1 if turn%2 else 2
        hit, hitter = game.step_single_agent(current)
        if hit:
            tank = game.agent1_tank if hitter==game.agent1.name else game.agent2_tank
            if tank.double_damage_active:
                tank.score += 2; tank.double_damage_active = False
            else:
                tank.score += 1
        game.update_safe_zone(turn)  # if safe-zone update logic elsewhere
        # penalty for outside safe zone
        if turn % 70 == 0:
            game.items = game.generate_items()
        x1,y1,x2,y2 = game.safe_zone
        for tnk in (game.agent1_tank, game.agent2_tank):
            if not (x1<=tnk.x<=x2 and y1<=tnk.y<=y2) and turn%2==0:
                tnk.score -= 1
        game.draw()
        clock.tick(FPS)
    print(f"Final Score: {game.agent1.name}:{game.agent1_tank.score} - {game.agent2.name}:{game.agent2_tank.score}")
