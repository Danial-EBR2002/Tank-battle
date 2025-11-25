from collections import deque
from typing import Deque, List, Optional, Set, Tuple
import random

GRID_SIZE = 15
VIEW_RANGE = 5
SHOOT_RANGE = 5
MIN_DIST = 3  # فاصله اجباری جدید

DIRECTIONS = {
    'UP': (0, -1),
    'DOWN': (0, 1),
    'LEFT': (-1, 0),
    'RIGHT': (1, 0),
}
DIR_KEYS: List[str] = list(DIRECTIONS.keys())
POSITIVE_ITEMS = {'DOUBLE_DAMAGE', 'DOUBLE_SHOT'}

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

class AgentBlue:
    def __init__(self, name="Blue"):
        self.name = name
        self.goal: Optional[Tuple[int, int]] = None
        self.path: Deque[Tuple[int, int]] = deque()
        self.known_walls: Set[Tuple[int, int]] = set()
        self.prev_zone = None
        self.prev_visible_walls = set()

    # بررسی اینکه سلول به دشمن نزدیک نشود
    def _safe_from_enemy(self, cell, enemy):
        if enemy is None:
            return True
        return manhattan(cell, enemy) >= MIN_DIST

    def decide(
        self,
        tank,
        visible_enemy,
        visible_walls,
        enemy_area,
        safe_zone,
        item_hints,
    ):

        cur = (tank.x, tank.y)
        self.known_walls.update(visible_walls)

        x1, y1, x2, y2 = safe_zone
        inside = lambda p: x1 <= p[0] <= x2 and y1 <= p[1] <= y2

        # اگر بیرون زون است، برگرد به داخل
        if not inside(cur):
            dst = self._nearest_inside(cur, safe_zone)
            self.path = deque(self._bfs(cur, dst, safe_zone, visible_enemy))
            if self.path:
                nxt = self.path.popleft()
                direction = self._dir_to(cur, nxt)
                return direction, False

        # اگر دشمن دیده می‌شود → فاصله مهم است
        if visible_enemy:
            dist_e = manhattan(cur, visible_enemy)
            if dist_e < MIN_DIST:
                # فرار کن
                escape_point = self._escape_point(cur, visible_enemy, safe_zone)
                self.path = deque(self._bfs(cur, escape_point, safe_zone, visible_enemy))
            else:
                # اگر در خط تیر و فاصله مناسب → شلیک
                aligned, aim_dir, d_e = self._line_of_fire(cur, visible_enemy)
                if aligned and d_e <= SHOOT_RANGE:
                    return aim_dir, True
                # نزدیک شو تا فاصله ≥۳ حفظ شود
                self.goal = visible_enemy
                self.path = deque(self._bfs(cur, self.goal, safe_zone, visible_enemy))
        else:
            # دنبال آیتم مثبت
            pos_items = []
            for x1_, y1_, x2_, y2_, t in item_hints:
                if t in POSITIVE_ITEMS:
                    cx, cy = (x1_+x2_)//2, (y1_+y2_)//2
                    if inside((cx, cy)):
                        pos_items.append((cx, cy))

            if pos_items:
                pos_items.sort(key=lambda p: manhattan(cur, p))
                self.goal = pos_items[0]
            else:
                # گردش مرکزی
                cx, cy = ((x1+x2)//2, (y1+y2)//2)
                self.goal = (cx, cy)

            self.path = deque(self._bfs(cur, self.goal, safe_zone, visible_enemy))

        # حرکت
        direction = tank.facing
        if self.path:
            nxt = self.path.popleft()
            direction = self._dir_to(cur, nxt)

        # دوباره چک شلیک
        if visible_enemy:
            aligned, aim_dir, d_e = self._line_of_fire(cur, visible_enemy)
            if aligned and d_e <= SHOOT_RANGE:
                return aim_dir, True

        return direction, False

    def _nearest_inside(self, p, safe):
        x, y = p
        x1, y1, x2, y2 = safe
        return (min(max(x, x1), x2), min(max(y, y1), y2))

    # انتخاب گوشه‌ای دور از دشمن
    def _escape_point(self, cur, enemy, safe):
        x1, y1, x2, y2 = safe
        corners = [(x1,y1), (x1,y2), (x2,y1), (x2,y2)]
        return max(corners, key=lambda c: manhattan(c, enemy))

    def _line_of_fire(self, src, dst):
        sx, sy = src
        dx, dy = dst
        if sx == dx:
            return True, ('DOWN' if dy > sy else 'UP'), abs(dy - sy)
        if sy == dy:
            return True, ('RIGHT' if dx > sx else 'LEFT'), abs(dx - sx)
        return False, 'UP', 99

    def _dir_to(self, src, dst):
        sx, sy = src
        dx, dy = dst
        if dx > sx: return 'RIGHT'
        if dx < sx: return 'LEFT'
        if dy > sy: return 'DOWN'
        return 'UP'

    # BFS با رعایت فاصله ایمن
    def _bfs(self, start, goal, safe, enemy):
        x1, y1, x2, y2 = safe
        q = deque([start])
        parent = {start: None}

        while q:
            cur = q.popleft()
            if cur == goal:
                break
            dirs = DIR_KEYS.copy()
            random.shuffle(dirs)
            for d in dirs:
                dx, dy = DIRECTIONS[d]
                nx, ny = cur[0]+dx, cur[1]+dy
                cell = (nx, ny)

                if cell in parent:
                    continue
                if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    continue
                if cell in self.known_walls:
                    continue
                if not (x1 <= nx <= x2 and y1 <= ny <= y2):
                    continue
                if not self._safe_from_enemy(cell, enemy):
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
