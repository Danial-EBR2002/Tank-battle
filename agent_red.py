# agent_red.py
import random
import math

class AgentRed:
    """
    Defensive AgentRed + item pursuit:
    - Pursues nearest item hint first.
    - Uses potential‑field navigation.
    - Retreats when vulnerable (enemy in sight but cooldown active).
    - Avoids open space when uncertain.
    """
    def __init__(self, name="Red"):
        self.name = name

    def decide(self, tank, visible_enemy, visible_walls, enemy_area, safe_zone, item_hints):
        """Return (direction, shoot_flag) each turn.
        Args:
            tank:      Our Tank object.
            visible_enemy: (x,y) or None.
            visible_walls: list[(x,y)] within VIEW_RANGE.
            enemy_area: (min_x,max_x,min_y,max_y) likely enemy region.
            safe_zone: 4‑tuple bounding current safe zone.
            item_hints: list of (x1,y1,x2,y2,type) rectangles; we ignore type.
        """
        from battlegrid import DIRECTIONS, GRID_SIZE

        walls = set(visible_walls)
        my_pos = (tank.x, tank.y)

        # 1) Pursue nearest item hint --------------------------------------
        if item_hints:
            targets = []
            # FIX: unpack 5‑element tuple, ignore last (item type)
            for (x1, y1, x2, y2, _) in item_hints:
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                targets.append((cx, cy))
            # Choose closest target (Manhattan)
            targets.sort(key=lambda p: abs(p[0]-tank.x) + abs(p[1]-tank.y))
            goal = targets[0]
            # Greedy step toward goal
            best_move, best_dist = None, float('inf')
            for direction, (dx, dy) in DIRECTIONS.items():
                nx, ny = tank.x + dx, tank.y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
                    dist = abs(nx - goal[0]) + abs(ny - goal[1])
                    if dist < best_dist:
                        best_dist = dist
                        best_move = direction
            if best_move:
                return best_move, False

        # 2) Return to safe zone if outside --------------------------------
        x1, y1, x2, y2 = safe_zone
        if not (x1 <= tank.x <= x2 and y1 <= tank.y <= y2):
            tx, ty = (x1 + x2) // 2, (y1 + y2) // 2
            best_move, best_dist = None, float('inf')
            for direction, (dx, dy) in DIRECTIONS.items():
                nx, ny = tank.x + dx, tank.y + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
                    dist = abs(nx - tx) + abs(ny - ty)
                    if dist < best_dist:
                        best_dist, best_move = dist, direction
            if best_move:
                return best_move, False

        # 3) Engage or evade enemy ----------------------------------------
        if visible_enemy:
            ex, ey = visible_enemy
            dx, dy = ex - tank.x, ey - tank.y
            can_shoot = False
            # Same row
            if tank.x == ex:
                step = 1 if ey > tank.y else -1
                if all((tank.x, y) not in walls for y in range(tank.y + step, ey, step)):
                    can_shoot = True
            # Same column
            elif tank.y == ey:
                step = 1 if ex > tank.x else -1
                if all((x, tank.y) not in walls for x in range(tank.x + step, ex, step)):
                    can_shoot = True

            if can_shoot and tank.shoot_cooldown == 0:
                # Face enemy & shoot
                if dx == 0:
                    direction = 'DOWN' if dy > 0 else 'UP'
                else:
                    direction = 'RIGHT' if dx > 0 else 'LEFT'
                return direction, True
            else:
                # No clear shot → flee opposite / perpendicular
                threat_vec = (dx // max(1, abs(dx)), dy // max(1, abs(dy)))
                escape_dirs = [d for d,(ddx,ddy) in DIRECTIONS.items()
                               if (ddx,ddy) != threat_vec and (tank.x+ddx, tank.y+ddy) not in walls]
                if escape_dirs:
                    return random.choice(escape_dirs), False

        # 4) Potential‑field navigation toward enemy area center ----------
        min_x, max_x, min_y, max_y = enemy_area
        tx, ty = (min_x + max_x)//2, (min_y + max_y)//2
        best_move, best_potential = None, float('inf')
        for direction, (dx, dy) in DIRECTIONS.items():
            nx, ny = tank.x + dx, tank.y + dy
            if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE) or (nx, ny) in walls:
                continue
            # Attractive term: distance to target center
            att = abs(nx - tx) + abs(ny - ty)
            # Repulsive term: close walls
            rep = sum(1.0/(math.hypot(nx-wx, ny-wy)**2)
                      for wx,wy in walls if 0 < math.hypot(nx-wx, ny-wy) <= 3)
            # Risk penalty: open spaces when enemy unseen
            open_cnt = 0
            if not visible_enemy:
                for ddx,ddy in DIRECTIONS.values():
                    sx,sy = nx+ddx, ny+ddy
                    if 0 <= sx < GRID_SIZE and 0 <= sy < GRID_SIZE and (sx,sy) not in walls:
                        open_cnt += 1
            risk = open_cnt * 0.1
            total = att + 2.0*rep + risk + random.uniform(0, 0.1)
            if total < best_potential:
                best_potential, best_move = total, direction
        if best_move:
            return best_move, False

        # 5) Fallback random move ----------------------------------------
        for d in random.sample(list(DIRECTIONS.keys()), k=4):
            dx, dy = DIRECTIONS[d]
            nx, ny = tank.x + dx, tank.y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE and (nx, ny) not in walls:
                return d, False

        return 'STAY', False
