# BattleGrid: Turn-Based Tank Battle Game

A competitive, turn-based tank duel on a 15×15 grid built with Pygame. Two AI agents control tanks, navigate obstacles, pick up power-ups, and survive a shrinking safe zone over 300 turns.

## Table of Contents
- [Overview](#overview)
- [Game Mechanics](#game-mechanics)
- [Agent Interface](#agent-interface)
- [Contributing](#contributing)

## Overview
BattleGrid pits two AI-controlled tanks against each other on a dynamically changing battlefield. Each tank alternates turns to move, rotate, or fire. Walls block movement and line of sight, items grant strategic bonuses, and a shrinking safe zone forces confrontation over time.

## Game Mechanics
Below is a line-by-line explanation of the core game logic in `battlegrid.py`. The code itself is not shown; each segment is described in detail.

1. **Lines 1–5:**
   - Imports: `pygame` (rendering & event handling), `random` (procedural elements), `sys` & `os` (file paths & working directory).
   - Ensures local imports work by appending the script directory to `sys.path` and changing the current working directory.

2. **Lines 6–7:**
   - Calls `pygame.init()` to initialize all Pygame modules and `pygame.font.init()` for font support.

3. **Lines 9–13:**
   - Defines display constants:
     - `GRID_SIZE = 15` (cells per side)
     - `CELL_SIZE = 60` (pixels per cell)
     - `WIDTH` & `HEIGHT` calculated as `GRID_SIZE * CELL_SIZE`.

4. **Lines 15–18:**
   - Sets game parameters:
     - `VIEW_RANGE = 5` (visibility radius in cells)
     - `SHOOT_RANGE = 5` (maximum firing distance)
     - `MAX_TURNS = 300` (turn limit)
     - `FPS = 200` (ticks per second).

5. **Lines 20–22:**
   - Defines the color `WHITE` and initializes a system font at size 36 for score rendering.

6. **Lines 24–28:**
   - Maps direction strings (`'UP'`, `'DOWN'`, `'LEFT'`, `'RIGHT'`) to `(dx, dy)` vectors and rotation angles for sprite orientation.

7. **Line 30:**
   - Lists item types: `['DOUBLE_SHOT', 'DOUBLE_DAMAGE', 'MINUS_ONE', 'DOUBLE_COOLDOWN']`.

8. **Lines 32–42:**
   - Loads and transforms static images for the grid background, tank sprites (blue & red), walls, and each item type.

9. **Lines 44–65 (Tank Class Initialization):**
   - Defines `class Tank`:
     - Constructor sets `x`, `y`, initial `facing='RIGHT'`, `desired_direction`, cooldowns (`shoot_cooldown`), item flags (`double_shot_active`, etc.), `score=0`, and `stay_counter=0`.

10. **Lines 67–75 (Tank.rotate method):**
    - `rotate()` checks if `desired_direction` is in the allowed set and differs from `facing`.
    - If so, updates `facing`, rotates the sprite image by the corresponding angle, and returns `True`; otherwise returns `False`.

11. **Lines 77–85 (Tank.move method):**
    - `move(grid)` calculates the next cell based on the `(dx, dy)` vector for `facing`.
    - If the cell is within bounds and not a wall (`grid[ny][nx] != 'W'`), updates `x, y` and returns `True`; else returns `False`.

12. **Lines 87–115 (Tank.shoot method):**
    - Checks if `shoot_cooldown > 0`; if so, returns `False` (cannot shoot yet).
    - Otherwise, casts a ray cell by cell in the `facing` direction up to `SHOOT_RANGE`.
    - If it encounters a wall, the shot stops harmlessly.
    - If the ray hits the enemy tank’s (`x, y`), applies damage:
      - If `double_damage_active`, adds 2 points and resets the flag.
      - Else, adds 1 point.
    - Sets the next `shoot_cooldown` based on active power-ups:
      - `0` if `double_shot_active`,
      - `8` if `double_cooldown_active`,
      - Otherwise `4`.
    - Returns `True` to indicate a shot was consumed (hit or miss).

13. **Lines 117–135 (Utility Functions):**
    - `generate_walls()`: randomly selects ~15% of cells as walls, then carves out one random column to create an “escape corridor.”
    - `random_spawn(top)`: chooses a spawn cell in the top third (`top=True`) or bottom third (`top=False`) of the grid, avoiding walls.

14. **Lines 137–145 (Safe Zone Initialization):**
    - `generate_initial_safe_zone()` returns the full grid bounds `(0, 0, GRID_SIZE-1, GRID_SIZE-1)`.
    - `generate_shrink_schedule()` computes turns at which the safe zone will shrink by 2 cells per side, ensuring it never goes below 6×6.

15. **Lines 147–158 (update_safe_zone method):**
    - On each turn, checks if the turn number is in `shrink_schedule`.
    - If so, decreases width and height by two cells, then randomizes the new zone’s center within the allowed area.

16. **Lines 160–164 (_can_move helper):**
    - Returns `True` if a given `(x, y)` is within the grid and not occupied by a wall.

17. **Lines 166–190 (_take_action method):**
    - Determines `visible_enemy` coordinates if within `VIEW_RANGE` using a visibility helper.
    - Gathers `visible_walls` within the same range for strategic pathfinding.
    - Generates `item_hints` as bounding boxes and types for all current items.
    - Calls `agent.decide(tank, visible_enemy, visible_walls, enemy_area, safe_zone, item_hints)` to receive `(direction, shoot_flag)`.

18. **Lines 192–215 (Applying Agent Actions):**
    - Sets `tank.desired_direction`, attempts `rotate()`.
    - If no rotation occurred, tries to move forward; if blocked, increments `stay_counter` and, after 2 stuck turns, picks a random valid direction to escape.
    - If `shoot_flag` is `True`, invokes `tank.shoot()` and applies hit logic and scoring as described above.

19. **Lines 217–247 (Main Loop & Turn Management):**
    - Loops turns `1` to `MAX_TURNS`:
      - Processes Pygame events (e.g., window close).
      - Alternates agents: Blue on odd turns, Red on even.
      - Executes one agent’s turn via `step_single_agent()`.
      - Calls `update_safe_zone(turn)`; on even turns, any tank outside the zone loses 1 point.
      - Every 70 turns, regenerates 5 random items with `generate_items()`.

20. **Lines 249–258 (Rendering & Display):**
    - Clears the screen and draws the grid background.
    - Renders walls, items (if visible), tanks (if visible), and current scores.
    - Draws a green rectangle outlining the safe zone.
    - Updates the display (`pygame.display.flip()`) and enforces the tick rate (`clock.tick(FPS)`).

21. **Line 260 (Game Conclusion):**
    - After `MAX_TURNS` iterations, the final scores are printed to the console in the format `BlueName:Score - RedName:Score`.

## Agent Interface
Clients must implement an agent class with a constructor that accepts a **name** string and a `decide(...)` method:

```python
def decide(self,
           tank,                # your Tank object
           visible_enemy,       # (x,y) or None if out of VIEW_RANGE
           visible_walls,       # list of (x,y) within VIEW_RANGE
           enemy_area,          # bounding box of enemy’s last known area
           safe_zone,           # (x1,y1,x2,y2)
           item_hints):         # list of (x1,y1,x2,y2,item_type)
    """
    Returns a tuple:
      - direction: one of 'UP', 'DOWN', 'LEFT', 'RIGHT'
      - shoot_flag: True to attempt shooting after moving/rotating
    """
    return direction, shoot_flag
```

Refer to the docstrings and parameter comments for full details on each argument.

## Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/MyStrategy`)
3. Commit your changes (`git commit -m "Add new agent strategy"`)
4. Push (`git push origin feature/MyStrategy`) and open a Pull Request
---

## Additional Game Rules and Agent Considerations

### 🔫 Shooting Rules
- A tank can **shoot without moving**, as long as it has turned toward the target.
- **Shots do not pass through walls.** If a wall is between you and the enemy, your shot will stop.
- Power-up items like `DOUBLE_SHOT` or `DOUBLE_DAMAGE` are **consumed after one use**, even if the shot misses.

### 👁️ Visibility & Item Detection
- Tanks can only see enemies, walls, and items that are within their **VIEW_RANGE = 2** Manhattan distance.
- Items outside this range are **not visible** and cannot be picked up.

### 🧱 Being Stuck
- If a tank fails to move for **more than 2 consecutive turns**, it will automatically attempt to move in a random valid direction to escape being stuck.
- This happens regardless of the agent’s decision.

### 📦 Item Pickup Effects
- `DOUBLE_SHOT`: Your next shot has zero cooldown. Consumed after one shot.
- `DOUBLE_DAMAGE`: Your next successful shot gives +2 points. Consumed on use.
- `DOUBLE_COOLDOWN`: Sets cooldown to 8 instead of 4 for the next shot. Consumed on use.
- `MINUS_ONE`: Picking this up **reduces your score by 1**.

---
