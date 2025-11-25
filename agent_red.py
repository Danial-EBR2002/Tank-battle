import random
from collections import deque
from typing import List, Tuple, Optional, Set

GRID_SIZE = 15
VIEW_RANGE = 5
SHOOT_RANGE = 5
MIN_DIST = 3  # فاصله اجباری جدید

DIRECTIONS = {
    'UP':    (0, -1),
    'DOWN':  (0, 1),
    'LEFT':  (-1, 0),
    'RIGHT': (1, 0),
}
DIR_KEYS = list(DIRECTIONS.keys())
POSITIVE_ITEMS = {'DOUBLE_DAMAGE', 'DOUBLE_SHOT', 'DOUBLE_COOLDOWN'}

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

class AgentRed:
    def __init__(self, name="Red"):
        self.name = name
        self.known_walls: Set[Tuple[int, int]] = set()
        self.path: deque = deque()
        self.goal: Optional[Tuple[int, int]] = None

    def _safe_dist(self, cell, enemy):
        if not enemy:
            return True
        return manhattan(cell, enemy) >= MIN_DIST

    def decide(self, tank, visible_enemy, visible_walls, enemy_area, safe_zone, item_hints):
        self.known_walls.update(visible_walls)
        cur = (tank.x, tank.y)
        x1, y1, x2, y2 = safe_zone

        inside = lambda p: x1 <= p[0] <= x2 and y1 <= p[1] <= y2

        # خروجی از زون → برگشت
        if not inside(cur):
            self.goal = self._nearest_inside(cur, safe_zone)
            self.path = deque(self._bfs(cur, self.goal, safe_zone, visible_enemy))

        # دشمن دیده می‌شود
        if visible_enemy:
            if manhattan(cur, visible_enemy) < MIN_DIST:
                escape_point = self._escape_point(cur, visible_enemy, safe_zone)
                self.path = deque(self._bfs(cur, escape_point, safe_zone, visible_enemy))
            else:
                aligned, shoot_dir, d_e = self._line_of_fire(cur, visible_enemy)
                if aligned and d_e <= SHOOT_RANGE:
                    return shoot_dir, True
                self.goal = visible_enemy
                self.path = deque(self._bfs(cur, self.goal, safe_zone, visible_enemy))
        else:
            items = []
            for x3, y3, x4, y4, t in item_hints:
                if t in POSITIVE_ITEMS:
                    cx, cy = (x3+x4)//2, (y3+y4)//2
                    if inside((cx, cy)):
                        items.append((cx, cy))

            if items:
                items.sort(key=lambda p: manhattan(cur, p))
                self.goal = items[0]
            else:
                cx, cy = ((x1+x2)//2, (y1+y2)//2)
                self.goal = (cx, cy)

            self.path = deque(self._bfs(cur, self.goal, safe_zone, visible_enemy))

        direction = tank.facing
        if self.path:
            nxt = self.path.popleft()
            direction = self._dir_to(cur, nxt)

        # دوباره check شلیک
        if visible_enemy:
            aligned, shoot_dir, d_e = self._line_of_fire(cur, visible_enemy)
            if aligned and d_e <= SHOOT_RANGE:
                return shoot_dir, True

        return direction, False

    def _nearest_inside(self, p, safe):
        x, y = p; x1, y1, x2, y2 = safe
        return (min(max(x, x1), x2), min(max(y, y1), y2))

    def _line_of_fire(self, src, dst):
        sx, sy = src; dx, dy = dst
        if sx == dx:
            return True, ('DOWN' if dy > sy else 'UP'), abs(dy - sy)
        if sy == dy:
            return True, ('RIGHT' if dx > sx else 'LEFT'), abs(dx - sx)
        return False, 'UP', 99

    def _dir_to(self, src, dst):
        sx, sy = src; dx, dy = dst
        if dx > sx: return 'RIGHT'
        if dx < sx: return 'LEFT'
        if dy > sy: return 'DOWN'
        return 'UP'

    def _escape_point(self, cur, enemy, safe):
        x1, y1, x2, y2 = safe
        corners = [(x1,y1), (x1,y2), (x2,y1), (x2,y2)]
        return max(corners, key=lambda c: manhattan(c, enemy))

    def _bfs(self, start, goal, safe, enemy):
        x1, y1, x2, y2 = safe
        q = deque([start])
        parent = {start: None}

        while q:
            cur = q.popleft()
            if cur == goal:
                break
            for d in DIR_KEYS:
                dx, dy = DIRECTIONS[d]
                nx, ny = cur[0]+dx, cur[1]+dy
                cell = (nx, ny)

                if cell in parent:
                    continue
                if not (0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE):
                    continue
                if cell in self.known_walls:
                    continue
                if not (x1<=nx<=x2 and y1<=ny<=y2):
                    continue
                if not self._safe_dist(cell, enemy):
                    continue

                parent[cell] = cur
                q.append(cell)

        # reconstruct
        path = []
        node = goal
        while node and node in parent and node != start:
            path.append(node)
            node = parent[node]
        return list(reversed(path))
