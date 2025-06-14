import random
from collections import deque
from typing import Deque, List, Optional, Set, Tuple

# === Game constants ===
GRID_SIZE    = 15
VIEW_RANGE   = 2
SHOOT_RANGE  = 3
DIRECTIONS   = {
    'UP':    (0, -1),
    'DOWN':  (0, 1),
    'LEFT':  (-1, 0),
    'RIGHT': (1, 0),
}
DIR_KEYS: List[str] = list(DIRECTIONS.keys())

# === Item types ===
POSITIVE_ITEMS = {'DOUBLE_DAMAGE', 'DOUBLE_SHOT', 'DOUBLE_COOLDOWN'}

class AgentBlue:
    def __init__(self, name: str = "Blue"):
        self.name = name
        self.goal: Optional[Tuple[int, int]] = None
        self.path: Deque[Tuple[int, int]] = deque()
        self.known_walls: Set[Tuple[int, int]] = set()

    def decide(
        self,
        tank,
        visible_enemy: Optional[Tuple[int, int]],
        visible_walls: List[Tuple[int, int]],
        enemy_area: Tuple[int, int, int, int],
        safe_zone: Tuple[int, int, int, int],
        item_hints: List[Tuple[int, int, int, int, str]],
    ) -> Tuple[str, bool]:
        """
        Strategy:
        1. Always stay inside safe_zone.
        2. If enemy inside zone, pursue and shoot.
        3. Collect positive items that are deep inside zone (at least 1 cell from border).
        4. Defensive/escape: if enemy too close without line-of-fire or low HP, flee.
        """
        # Update known walls
        self.known_walls.update(visible_walls)
        x1, y1, x2, y2 = safe_zone
        cur = (tank.x, tank.y)
        # Helper lambdas
        inside = lambda p: x1 <= p[0] <= x2 and y1 <= p[1] <= y2
        dist = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])

        # Ensure stay inside zone
        if not inside(cur):
            self.goal = self._nearest_inside(cur, safe_zone)
        else:
            # Parse positive items deep inside zone
            deep_items = []
            for x3, y3, x4, y4, t in item_hints:
                if t in POSITIVE_ITEMS:
                    cx, cy = (x3 + x4) // 2, (y3 + y4) // 2
                    # at least 1 cell from zone border
                    if x1 + 1 <= cx <= x2 - 1 and y1 + 1 <= cy <= y2 - 1:
                        deep_items.append((cx, cy))

            # Enemy inside zone?
            pursue_enemy = False
            esc = False
            shoot_flag = False
            if visible_enemy and inside(visible_enemy):
                pursue_enemy = True
                aligned, aim_dir, d_e = self._line_of_fire(cur, visible_enemy)
                # If can shoot now
                if aligned and d_e <= SHOOT_RANGE:
                    self.goal = None
                    shoot_flag = True
                else:
                    # too close without LOF => escape
                    if d_e <= SHOOT_RANGE:
                        esc = True
                    else:
                        # pursue enemy
                        self.goal = visible_enemy
            # If no enemy priority or fleeing
            if not pursue_enemy or esc:
                if esc:
                    # defensive: flee to farthest corner inside zone
                    self.goal = self._escape_point(cur, visible_enemy, safe_zone)
                elif deep_items:
                    # go to nearest deep positive item
                    deep_items.sort(key=lambda p: dist(cur, p))
                    self.goal = deep_items[0]
                else:
                    # no immediate task: hold center
                    self.goal = ((x1 + x2)//2, (y1 + y2)//2)
        # Plan path
        if self.goal != cur:
            self.path = deque(self._bfs(cur, self.goal, safe_zone))
        else:
            self.path.clear()

        # Decide movement
        direction = tank.facing
        if self.path:
            nxt = self.path.popleft()
            direction = self._dir_to(cur, nxt)

        # Decide shooting
        if visible_enemy and inside(visible_enemy):
            aligned, aim_dir, d_e = self._line_of_fire(cur, visible_enemy)
            if aligned and d_e <= SHOOT_RANGE:
                return aim_dir, True
        return direction, False

    # --- Helper functions ---
    def _nearest_inside(self, p: Tuple[int,int], safe: Tuple[int,int,int,int]) -> Tuple[int,int]:
        x, y = p; x1, y1, x2, y2 = safe
        return (min(max(x, x1), x2), min(max(y, y1), y2))

    def _line_of_fire(self, src: Tuple[int,int], dst: Tuple[int,int]) -> Tuple[bool,str,int]:
        sx, sy = src; dx, dy = dst
        if sx == dx:
            return True, 'DOWN' if dy>sy else 'UP', abs(dy-sy)
        if sy == dy:
            return True, 'RIGHT' if dx>sx else 'LEFT', abs(dx-sx)
        return False, 'UP', 99

    def _dir_to(self, src: Tuple[int,int], dst: Tuple[int,int]) -> str:
        sx, sy = src; dx, dy = dst
        if dx > sx: return 'RIGHT'
        if dx < sx: return 'LEFT'
        if dy > sy: return 'DOWN'
        return 'UP'

    def _escape_point(
        self,
        cur: Tuple[int,int],
        enemy: Tuple[int,int],
        safe: Tuple[int,int,int,int]
    ) -> Tuple[int,int]:
        # choose corner of safe_zone farthest from enemy
        x1, y1, x2, y2 = safe
        corners = [(x1,y1),(x1,y2),(x2,y1),(x2,y2)]
        best = max(corners, key=lambda c: abs(c[0]-enemy[0])+abs(c[1]-enemy[1]))
        return best

    def _bfs(self,
        start: Tuple[int,int],
        goal: Tuple[int,int],
        safe: Tuple[int,int,int,int]
    ) -> List[Tuple[int,int]]:
        x1, y1, x2, y2 = safe
        q = deque([start])
        parent = {start: None}
        while q:
            cur = q.popleft()
            if cur == goal: break
            for d in DIR_KEYS:
                dx, dy = DIRECTIONS[d]
                nx, ny = cur[0]+dx, cur[1]+dy
                cell = (nx, ny)
                if cell in parent: continue
                if not (0<=nx<GRID_SIZE and 0<=ny<GRID_SIZE): continue
                if cell in self.known_walls: continue
                if not (x1<=nx<=x2 and y1<=ny<=y2): continue
                parent[cell] = cur; q.append(cell)
        # reconstruct
        path, node = [], goal
        while node and node!= start:
            path.append(node); node = parent.get(node)
        return list(reversed(path))
