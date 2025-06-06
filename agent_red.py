# agent_red.py
import random
import math

class AgentRed:
    """
    Defensive AgentRed + item pursuit:
    - Pursues nearest item hint first.
    - Uses potential-field navigation.
    - Retreats when vulnerable (enemy in sight but cooldown active).
    - Avoids open space when uncertain.
    """
    def __init__(self, name="Red"):
        self.name = name

    def decide(self, tank, visible_enemy, visible_walls, enemy_area, safe_zone, item_hints):
        from battlegrid import DIRECTIONS, GRID_SIZE

        walls = set(visible_walls)
        my_pos = (tank.x, tank.y)

        # --- NEW: Pursue nearest item hint ---
        if item_hints:
            targets = []
            for (x1, y1, x2, y2) in item_hints:
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                targets.append((cx, cy))
            targets.sort(key=lambda p: abs(p[0]-tank.x) + abs(p[1]-tank.y))
            goal = targets[0]
            # simple greedy step toward goal
            best_move = None
            best_dist = float('inf')
            for direction, (dx, dy) in DIRECTIONS.items():
                nx, ny = tank.x + dx, tank.y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
                    dist = abs(nx - goal[0]) + abs(ny - goal[1])
                    if dist < best_dist:
                        best_dist = dist
                        best_move = direction
            if best_move:
                return best_move, False

        x1, y1, x2, y2 = safe_zone
        # if outside safe zone, move back toward center
        if not (x1 <= tank.x <= x2 and y1 <= tank.y <= y2):
            tx = (x1 + x2) // 2
            ty = (y1 + y2) // 2
            best_move = None
            best_dist = float('inf')
            for direction, (dx, dy) in DIRECTIONS.items():
                nx, ny = tank.x + dx, tank.y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
                    dist = abs(nx - tx) + abs(ny - ty)
                    if dist < best_dist:
                        best_dist = dist
                        best_move = direction
            if best_move:
                return best_move, False

        # existing enemy logic unchanged...
        if visible_enemy:
            ex, ey = visible_enemy
            dx, dy = ex - tank.x, ey - tank.y
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
                # Face and shoot
                if dx == 0:
                    direction = 'DOWN' if dy > 0 else 'UP'
                else:
                    direction = 'RIGHT' if dx > 0 else 'LEFT'
                return direction, True
            else:
                # Run away from enemy
                threat_dir = (dx // max(1, abs(dx)), dy // max(1, abs(dy)))
                escape_dirs = [
                    d for d, (ddx, ddy) in DIRECTIONS.items()
                    if (ddx, ddy) != threat_dir and (tank.x + ddx, tank.y + ddy) not in walls
                ]
                if escape_dirs:
                    return random.choice(escape_dirs), False

        # existing no-enemy potential field logic unchanged...
        min_x, max_x, min_y, max_y = enemy_area
        tx = (min_x + max_x) // 2
        ty = (min_y + max_y) // 2

        best_move = None
        best_potential = float('inf')

        for direction, (dx, dy) in DIRECTIONS.items():
            nx, ny = tank.x + dx, tank.y + dy
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE) or (nx, ny) in walls:
                continue

            att = abs(nx - tx) + abs(ny - ty)

            rep = 0.0
            for wx, wy in walls:
                dist = math.hypot(nx - wx, ny - wy)
                if 0 < dist <= 3:
                    rep += 1.0 / (dist * dist)

            risk_penalty = 0
            if not visible_enemy:
                surrounding = [(nx + ddx, ny + ddy) for ddx, ddy in DIRECTIONS.values()]
                open_count = sum(1 for sx, sy in surrounding if 0 <= sx < GRID_SIZE and 0 <= sy < GRID_SIZE and (sx, sy) not in walls)
                risk_penalty = open_count * 0.1

            total_potential = att + 2.0 * rep + risk_penalty + random.uniform(0, 0.1)
            if total_potential < best_potential:
                best_potential = total_potential
                best_move = direction

        if best_move:
            return best_move, False

        # Fallback
        fallback_dirs = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        random.shuffle(fallback_dirs)
        for d in fallback_dirs:
            dx, dy = DIRECTIONS[d]
            nx, ny = tank.x + dx, tank.y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
                return d, False

        return 'STAY', False
