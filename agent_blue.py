# agent_blue.py
import heapq
import random

class AgentBlue:
    """
    AgentBlue with defensive behavior + item pickup:
    - Pursues nearest item hint first.
    - Then avoids enemy when vulnerable.
    - Takes cover behind walls when possible.
    - Only attacks when safe and clear shot exists.
    """
    def __init__(self, name="Blue"):
        self.name = name

    def decide(self, tank, visible_enemy, visible_walls, enemy_area, safe_zone, item_hints):
        from battlegrid import DIRECTIONS, GRID_SIZE

        walls = set(visible_walls)
        my_pos = (tank.x, tank.y)

        # --- NEW: Pursue nearest item hint ---
        if item_hints:
            # Compute approximate centers of each hint-rectangle
            targets = []
            for (x1, y1, x2, y2, _) in item_hints:  # Fixed: unpack 5 elements including item type
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                targets.append((cx, cy))
            # Choose the closest by Manhattan distance
            targets.sort(key=lambda p: abs(p[0]-tank.x) + abs(p[1]-tank.y))
            goal = targets[0]
            # Pathfinding toward the goal
            path = self.astar(my_pos, goal, walls, GRID_SIZE, DIRECTIONS)
            if path:
                next_cell = path[0]
                dx, dy = next_cell[0] - tank.x, next_cell[1] - tank.y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if (ddx, ddy) == (dx, dy):
                        return d, False

        # If outside the safe zone, move toward its center
        x1, y1, x2, y2 = safe_zone
        if not (x1 <= tank.x <= x2 and y1 <= tank.y <= y2):
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            path = self.astar(my_pos, center, walls, GRID_SIZE, DIRECTIONS)
            if path:
                next_cell = path[0]
                dx, dy = next_cell[0] - tank.x, next_cell[1] - tank.y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if (ddx, ddy) == (dx, dy):
                        return d, False

        # --- Defensive Logic ---
        if visible_enemy:
            ex, ey = visible_enemy
            dx, dy = ex - tank.x, ey - tank.y
            dist = abs(dx) + abs(dy)

            # Check if shot is possible
            can_shoot = False
            if tank.x == ex:
                step = 1 if ey > tank.y else -1
                if all((tank.x, y) not in walls for y in range(tank.y + step, ey, step)):
                    can_shoot = True
            elif tank.y == ey:
                step = 1 if ex > tank.x else -1
                if all((x, tank.y) not in walls for x in range(tank.x + step, ex, step)):
                    can_shoot = True

            if can_shoot and tank.shoot_cooldown == 0:
                # Rotate and shoot
                if dx == 0:
                    direction = 'DOWN' if dy > 0 else 'UP'
                else:
                    direction = 'RIGHT' if dx > 0 else 'LEFT'
                return direction, True
            else:
                # Avoid enemy by moving perpendicular
                threat_dir = (dx // max(1, abs(dx)), dy // max(1, abs(dy)))
                escape_dirs = [
                    d for d, (ddx, ddy) in DIRECTIONS.items()
                    if (ddx, ddy) != threat_dir and (tank.x + ddx, tank.y + ddy) not in walls
                ]
                if escape_dirs:
                    return random.choice(escape_dirs), False

        # --- Strategic Movement when no enemy is visible ---
        min_x, max_x, min_y, max_y = enemy_area
        goal = ((min_x + max_x) // 2, (min_y + max_y) // 2)
        path = self.astar(my_pos, goal, walls, GRID_SIZE, DIRECTIONS)
        if path:
            next_cell = path[0]
            dx, dy = next_cell[0] - tank.x, next_cell[1] - tank.y
            for d, (ddx, ddy) in DIRECTIONS.items():
                if (ddx, ddy) == (dx, dy):
                    return d, False

        # Fallback: try random direction
        fallback_dirs = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        random.shuffle(fallback_dirs)
        for d in fallback_dirs:
            dx, dy = DIRECTIONS[d]
            test_pos = (tank.x + dx, tank.y + dy)
            if 0 <= test_pos[0] < GRID_SIZE and 0 <= test_pos[1] < GRID_SIZE and test_pos not in walls:
                return d, False

        return 'STAY', False

    @staticmethod
    def astar(start, goal, walls, grid_size, directions):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = [(heuristic(start, goal), 0, start, [])]
        visited = {start: 0}

        while open_set:
            f, g, current, path = heapq.heappop(open_set)
            if current == goal:
                return path

            for d, (dx, dy) in directions.items():
                neighbor = (current[0] + dx, current[1] + dy)
                if 0 <= neighbor[0] < grid_size and 0 <= neighbor[1] < grid_size and neighbor not in walls:
                    new_g = g + 1
                    if neighbor not in visited or new_g < visited[neighbor]:
                        visited[neighbor] = new_g
                        new_path = path + [neighbor]
                        heapq.heappush(open_set, (new_g + heuristic(neighbor, goal), new_g, neighbor, new_path))
        return None
