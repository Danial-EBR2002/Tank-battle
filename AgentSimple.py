from collections import deque
from typing import List, Tuple, Optional, Set

# ثابت‌ها (Engine هم این‌ها را دارد، ولی داخل Agent دوباره تعریف می‌کنیم)
GRID_SIZE   = 15
VIEW_RANGE  = 2
SHOOT_RANGE = 5       # برد شلیک
MIN_DIST    = 3       # حداقل فاصله امن (اگر بخواهی)

# جهت‌های حرکت
DIRECTIONS = {
    'UP':    (0, -1),
    'DOWN':  (0, 1),
    'LEFT':  (-1, 0),
    'RIGHT': (1, 0),
}
DIR_KEYS = list(DIRECTIONS.keys())


# تابع کمکی برای محاسبه فاصله منهتن
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class AgentSimple:
    """
    این Agent یک نسخهٔ خیلی ساده، قابل فهم و آموزشی است.
    - اگر دشمن دیده شود، بررسی می‌کند آیا می‌تواند شلیک کند یا نه.
    - اگر نتواند شلیک کند، کمی به سمتش نزدیک می‌شود.
    - اگر دشمن دیده نشود، یکی از آیتم‌های مثبت را هدف می‌گیرد.
    - اگر آیتمی نبود، به وسط safe zone می‌رود.
    """

    def __init__(self, name="SimpleAgent"):
        self.name = name

        # هدفی که Agent دارد (یک نقطهٔ گرید مثل (x,y))
        self.goal: Optional[Tuple[int, int]] = None

        # مسیر BFS که Agent باید قدم‌به‌قدم طی کند
        self.path: deque = deque()

        # دیوارهایی که Agent دیده و در حافظه نگه می‌دارد
        self.known_walls: Set[Tuple[int, int]] = set()


    # ============================
    #     تابع اصلی Agent
    # ============================
    def decide(
        self,
        tank,
        visible_enemy: Optional[Tuple[int, int]],
        visible_walls: List[Tuple[int, int]],
        enemy_area: Tuple[int, int, int, int],
        safe_zone: Tuple[int, int, int, int],
        item_hints
    ):
        """
        این تابع در هر نوبت صدا زده می‌شود.
        باید (direction, shoot_flag) برگرداند.
        """

        cur = (tank.x, tank.y)     # موقعیت فعلی ما
        self.known_walls.update(visible_walls)    # دیوارهای جدید دیده شده را ذخیره کن

        # ============================
        # ۱) اگر دشمن دیده می‌شود
        # ============================
        if visible_enemy is not None:

            # بررسی کنید آیا در خط تیر قرار دارد؟
            aligned, aim_dir, dist = self._line_of_fire(cur, visible_enemy)

            if aligned and dist <= SHOOT_RANGE:
                # دشمن در تیررس است → شلیک کن
                return aim_dir, True

            # اگر نمی‌توانیم شلیک کنیم → کمی نزدیک شو
            self.goal = visible_enemy
            self.path = deque(self._bfs(cur, self.goal, safe_zone))

            # اگر مسیری داریم → قدم بعدی را برو
            return self._step_toward(cur), False


        # ======================================================
        # ۲) اگر دشمن دیده نمی‌شود → دنبال آیتم مثبت برو
        # ======================================================
        positive_items = []
        for x1,y1,x2,y2,t in item_hints:
            if t in {"DOUBLE_SHOT", "DOUBLE_DAMAGE"}:
                cx = (x1+x2)//2
                cy = (y1+y2)//2
                positive_items.append((cx, cy))

        if positive_items:
            # نزدیکترین آیتم مثبت را انتخاب کن
            positive_items.sort(key=lambda pos: manhattan(cur, pos))
            self.goal = positive_items[0]
        else:
            # اگر هیچ آیتمی نبود → برو به مرکز safe zone
            x1,y1,x2,y2 = safe_zone
            cx, cy = (x1+x2)//2, (y1+y2)//2
            self.goal = (cx, cy)

        # تولید مسیر به سمت goal
        self.path = deque(self._bfs(cur, self.goal, safe_zone))

        return self._step_toward(cur), False



    # ============================
    #       قدم بعدی مسیر
    # ============================
    def _step_toward(self, cur):
        """
        اگر مسیری در دست باشد، قدم بعدی را بردار،
        و جهت لازم را برگردان.
        """

        if not self.path:
            # اگر مسیر خالی بود، یک جهت پیش‌فرض بده
            return 'UP'

        nxt = self.path.popleft()
        return self._dir_to(cur, nxt)



    # ============================
    #   تعیین جهت بین دو نقطه
    # ============================
    def _dir_to(self, src, dst):
        """
        از src به dst باید کدام جهت را نگاه کنیم؟
        """

        sx, sy = src
        dx, dy = dst

        if dx > sx: return 'RIGHT'
        if dx < sx: return 'LEFT'
        if dy > sy: return 'DOWN'
        return 'UP'



    # ============================
    #   تشخیص خط تیر
    # ============================
    def _line_of_fire(self, src, dst):
        """
        بررسی می‌کند دشمن در یک خط مستقیم قرار دارد یا نه.
        اگر بله → جهت لازم برای شلیک + فاصله را می‌دهد.
        """

        sx, sy = src
        dx, dy = dst

        # در ستون مشترک
        if sx == dx:
            if dy > sy:
                return True, 'DOWN', abs(dy-sy)
            else:
                return True, 'UP', abs(dy-sy)

        # در ردیف مشترک
        if sy == dy:
            if dx > sx:
                return True, 'RIGHT', abs(dx-sx)
            else:
                return True, 'LEFT', abs(dx-sx)

        return False, 'UP', 99    # دشمن در خط تیر نیست



    # ============================
    #            BFS
    # ============================
    def _bfs(self, start, goal, safe_zone):
        """
        پیدا کردن مسیر کوتاه از start تا goal،
        فقط داخل safe zone و دوری از دیوارها.
        """

        x1,y1,x2,y2 = safe_zone

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

                # چک خارج از گرید
                if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
                    continue

                # اگر قبلاً دیده شده
                if cell in parent:
                    continue

                # اگر دیواره
                if cell in self.known_walls:
                    continue

                # اگر خارج safe zone
                if not (x1 <= nx <= x2 and y1 <= ny <= y2):
                    continue

                parent[cell] = cur
                q.append(cell)

        # بازسازی مسیر از goal به start
        path = []
        node = goal
        while node and node != start:
            path.append(node)
            node = parent.get(node)

        return list(reversed(path))
