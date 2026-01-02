from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

# ================= CONFIGURATION =================
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 800
FOV_Y = 60

# --- Geometry Constants ---
BLOCK_SIZE = 40  
TOWER_LIMIT = 15 
MAX_GRID_HEIGHT = TOWER_LIMIT + 20 
WALL_HEIGHT = TOWER_LIMIT * BLOCK_SIZE 
WALL_CENTER_Y = -50
WALL_THICKNESS = 40
WALL_FRONT_FACE = WALL_CENTER_Y + (WALL_THICKNESS / 2)

TOWER_GRID_SIZE = 4
TOWER_CENTER_Y = 300
TOWER_CENTER_X = 0

# Colors
COLOR_BG = (0.05, 0.05, 0.1)
COLOR_WALL = (0.3, 0.3, 0.4)
COLOR_PLAYER = (0.0, 1.0, 0.0)
COLOR_GUN = (0.0, 0.8, 0.8)
COLOR_ENEMY = (1.0, 0.0, 0.0)
COLOR_SUMMONER = (0.8, 0.0, 0.0) 
COLOR_BULLET = (1.0, 1.0, 0.0)
COLOR_GRENADE = (0.0, 0.8, 0.0)
COLOR_ZONE = (0.5, 0.0, 0.0)
COLOR_HIGHLIGHT_VALID = (0.0, 1.0, 0.0, 0.6)    
COLOR_HIGHLIGHT_INVALID = (1.0, 0.0, 0.0, 0.3) 

# Tetris colors
TETRIS_COLORS = [
    (0.0, 0.8, 0.8), (0.0, 0.0, 1.0), (0.8, 0.4, 0.0), 
    (0.8, 0.8, 0.0), (0.5, 0.0, 0.8), (1.0, 0.0, 0.0), (0.0, 0.8, 0.0)
]

# Tetris shapes
TETRIS_SHAPES = [
    [(0,0), (1,0), (2,0), (3,0)], # I (0)
    [(0,0), (1,0), (0,1), (1,1)], # O (1)
    [(1,0), (0,1), (1,1), (2,1)], # T (2)
    [(0,0), (0,1), (1,1), (2,1)], # L (3)
    [(2,0), (0,1), (1,1), (2,1)], # J (4)
    [(1,0), (2,0), (0,1), (1,1)], # S (5)
    [(0,0), (1,0), (1,1), (2,1)]  # Z (6)
]

# Global game instance
game = None

# ================= UTILITY FUNCTIONS =================
def draw_text(x, y, text, color=(1, 1, 1), font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(*color)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# ================= PARTICLE SYSTEM =================
class Particle:
    def __init__(self, position, velocity, color, size=2.0, lifetime=1.0):
        self.position = list(position)
        self.velocity = list(velocity)
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
    
    def update(self, dt):
        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt
        self.position[2] += self.velocity[2] * dt
        self.velocity[2] -= 80 * dt # Gravity
        self.lifetime -= dt
        return self.lifetime <= 0

# ================= GAME STATE =================
class GameState:
    def __init__(self):
        # Camera
        self.yaw = 90.0   
        self.pitch = 0.0
        self.camera_pos = [0, -400, 400]
        self.camera_target = [0, 300, 100]
        self.fps_mode = False 
        
        # Player Position 
        self.player_pos = [0, WALL_FRONT_FACE - 15, WALL_HEIGHT + 20] 
        self.lives = 5
        self.max_lives = 5
        self.score = 0
        
        # Killstreak & Abilities
        self.killstreak = 0
        self.kills_without_damage = 0
        self.grenades = 0
        self.nuke_available = False
        self.nuke_active = False
        self.nuke_timer = 0
        self.nuke_scale = 0
        self.nuke_position = [0,0,0]
        
        self.game_over = False
        self.paused = False
        self.cheat_mode = False
        self.debug_mode = False 
        self.game_over_reason = ""
        
        # Abilities
        self.slice_mode = False
        self.hovered_layer = -1
        
        # Entities
        self.bullets = [] 
        self.enemies = [] 
        self.particles = []
        
        # Grid: [x][y][z]
        self.tower_grid = [[[0 for _ in range(MAX_GRID_HEIGHT)] 
                           for _ in range(TOWER_GRID_SIZE)] 
                           for _ in range(TOWER_GRID_SIZE)]
        
        # Tetris State
        self.active_tetris = None
        self.tower_height = 0
        self.last_drop_time = time.time()
        self.drop_interval = 2.0
        self.lock_delay_timer = 0 
        
        # Generator Queue
        self.generation_queue = []
        self.last_cheat_fire = 0
        
        self.keys = {'w': False, 's': False, 'a': False, 'd': False,
                     'left': False, 'right': False, 'up': False, 'down': False}
        
        self.spawn_enemies()
        print("[DEBUG] Game Initialized.")
    
    def recalculate_tower_height(self):
        max_z = 0
        for z in range(MAX_GRID_HEIGHT):
            has_block = False
            for x in range(TOWER_GRID_SIZE):
                for y in range(TOWER_GRID_SIZE):
                    if self.tower_grid[x][y][z] > 0:
                        has_block = True
                        break
            if has_block:
                max_z = z + 1
        self.tower_height = max_z

    def spawn_enemies(self):
        self.enemies = []
        for i in range(5):
            angle = (i / 5) * 2 * math.pi
            radius = 100
            x = math.cos(angle) * radius
            y = TOWER_CENTER_Y + math.sin(angle) * radius
            self.enemies.append([x, y, 0, 0, random.uniform(30,50), 0]) 

    def get_smart_piece(self):
        if not self.generation_queue:
            roll = random.random()
            if roll < 0.95:
                # 95% Chance: PERFECT FLOOR RECIPE
                recipe_type = random.randint(0, 1)
                if recipe_type == 0: 
                    # 4 Squares
                    self.generation_queue = [
                        {'shape_idx': 1, 'x': 0, 'y': 0}, {'shape_idx': 1, 'x': 2, 'y': 0},
                        {'shape_idx': 1, 'x': 0, 'y': 2}, {'shape_idx': 1, 'x': 2, 'y': 2}
                    ]
                else:
                    # 4 Lines
                    self.generation_queue = [
                        {'shape_idx': 0, 'x': 0, 'y': 0}, {'shape_idx': 0, 'x': 0, 'y': 1},
                        {'shape_idx': 0, 'x': 0, 'y': 2}, {'shape_idx': 0, 'x': 0, 'y': 3}
                    ]
            else:
                # 5% Chance: CHAOS
                print("[ARCHITECT] Spawning Chaos")
                for _ in range(4):
                    self.generation_queue.append({
                        'shape_idx': random.choice([2, 5, 6]), 
                        'x': random.randint(0, TOWER_GRID_SIZE-2),
                        'y': random.randint(0, TOWER_GRID_SIZE-2)
                    })
        
        next_piece = self.generation_queue.pop(0)
        return {
            'shape_idx': next_piece['shape_idx'], 'x': next_piece.get('x', 0), 'y': next_piece.get('y', 0),
            'rotation': 0, 'color_idx': random.randint(0, 6)
        }

    def spawn_tetris(self):
        if self.nuke_active: return
        if self.active_tetris is None:
            piece_data = self.get_smart_piece()
            spawn_z = max(self.tower_height + 4, 10) 
            self.active_tetris = {
                'shape_idx': piece_data['shape_idx'], 'rotation': piece_data['rotation'],
                'x': piece_data['x'], 'y': piece_data['y'], 'z': spawn_z,
                'color_idx': piece_data['color_idx']
            }
            self.lock_delay_timer = 0
    
    def get_shape_cells(self, shape_idx, rotation, base_x, base_y, base_z):
        shape = TETRIS_SHAPES[shape_idx]
        cells = []
        for dx, dy in shape:
            if rotation == 1: dx, dy = -dy, dx
            elif rotation == 2: dx, dy = -dx, -dy
            elif rotation == 3: dx, dy = dy, -dx
            cells.append((base_x + dx, base_y + dy, base_z))
        return cells
    
    def check_collision(self, cells):
        for x, y, z in cells:
            if z < 0: return True # Hit floor
            ix, iy, iz = int(x), int(y), int(z)
            if ix < 0 or ix >= TOWER_GRID_SIZE or iy < 0 or iy >= TOWER_GRID_SIZE: return True # Hit Walls
            if iz < MAX_GRID_HEIGHT:
                if self.tower_grid[ix][iy][iz] > 0: return True # Hit Block
        return False
    
    def check_collapse_conditions(self):
        layers_to_destroy = []
        # Scan tower
        for z in range(self.tower_height - 2):
            if self.is_layer_uneven(z):
                # If uneven and has 2 layers above it
                if self.has_blocks_in_layer(z+1) and self.has_blocks_in_layer(z+2):
                    print(f"[PHYSICS] Collapse! Layer {z} failed.")
                    layers_to_destroy.append(z)
        
        for z in sorted(layers_to_destroy, reverse=True):
            self.create_explosion(TOWER_CENTER_X, TOWER_CENTER_Y, (z+0.5)*BLOCK_SIZE, 100)
            self.remove_layer(z)
            self.score += 50

    def has_blocks_in_layer(self, z):
        for x in range(TOWER_GRID_SIZE):
            for y in range(TOWER_GRID_SIZE):
                if self.tower_grid[x][y][z] > 0: return True
        return False

    def is_layer_uneven(self, z):
        has_block = False
        has_gap = False
        for x in range(TOWER_GRID_SIZE):
            for y in range(TOWER_GRID_SIZE):
                if self.tower_grid[x][y][z] > 0: has_block = True
                else: has_gap = True
        return has_block and has_gap

    def is_layer_solid(self, z):
        for x in range(TOWER_GRID_SIZE):
            for y in range(TOWER_GRID_SIZE):
                if self.tower_grid[x][y][z] == 0: return False
        return True

    def remove_layer(self, layer_z):
        for z in range(layer_z, MAX_GRID_HEIGHT - 1):
            for x in range(TOWER_GRID_SIZE):
                for y in range(TOWER_GRID_SIZE):
                    self.tower_grid[x][y][z] = self.tower_grid[x][y][z+1]
        for x in range(TOWER_GRID_SIZE):
             for y in range(TOWER_GRID_SIZE):
                 self.tower_grid[x][y][MAX_GRID_HEIGHT-1] = 0
        self.recalculate_tower_height()

    def update_tetris(self, dt):
        current_time = time.time()
        if self.active_tetris is None:
            if current_time - self.last_drop_time > 1.0: 
                self.spawn_tetris()
                self.last_drop_time = current_time
            return
        
        fall_speed = 60
        next_z = self.active_tetris['z'] - fall_speed * dt 
        cells = self.get_shape_cells(self.active_tetris['shape_idx'], self.active_tetris['rotation'],
                                     self.active_tetris['x'], self.active_tetris['y'], next_z)
        
        if self.check_collision(cells):
            self.lock_delay_timer += dt
            if self.lock_delay_timer > 0.5:
                lock_z = round(self.active_tetris['z'])
                if lock_z < 0: lock_z = 0
                final_cells = self.get_shape_cells(self.active_tetris['shape_idx'], self.active_tetris['rotation'],
                                                   self.active_tetris['x'], self.active_tetris['y'], lock_z)
                valid_lock = True
                for x, y, z in final_cells:
                    ix, iy, iz = int(x), int(y), int(z)
                    if 0 <= ix < TOWER_GRID_SIZE and 0 <= iy < TOWER_GRID_SIZE and 0 <= iz < MAX_GRID_HEIGHT:
                        self.tower_grid[ix][iy][iz] = self.active_tetris['color_idx'] + 1
                    else: valid_lock = False
                
                if valid_lock:
                    self.recalculate_tower_height()
                    self.check_collapse_conditions()
                    if self.tower_height >= TOWER_LIMIT: 
                        self.game_over = True; self.game_over_reason = "Tower reached limit!"
                    
                self.active_tetris = None; self.last_drop_time = current_time
        else:
            self.active_tetris['z'] = next_z; self.lock_delay_timer = 0
    
    def fire_bullet(self, bullet_type=0):
        if self.game_over or self.paused: return
        rad_yaw = math.radians(self.yaw); rad_pitch = math.radians(self.pitch)
        dx = math.cos(rad_yaw) * math.cos(rad_pitch)
        dy = math.sin(rad_yaw) * math.cos(rad_pitch)
        dz = math.sin(rad_pitch)
        
        if bullet_type == 0: 
            speed = 400
            self.bullets.append([self.player_pos[0], self.player_pos[1], self.player_pos[2] + 5,
                                 dx * speed, dy * speed, dz * speed, 0])
        elif bullet_type == 1 and self.grenades > 0: 
            self.grenades -= 1
            self.bullets.append([self.player_pos[0], self.player_pos[1], self.player_pos[2] + 5,
                                 dx * 300, dy * 300, dz * 300 + 200, 1]) 
    
    def update_bullets(self, dt):
        to_remove = []
        for i, b in enumerate(self.bullets):
            b[0] += b[3] * dt; b[1] += b[4] * dt; b[2] += b[5] * dt
            if b[6] == 1: b[5] -= 500 * dt 
            if abs(b[0]) > 600 or abs(b[1]) > 600 or b[2] < 0:
                to_remove.append(i)
                if b[6] == 1: self.create_explosion(b[0], b[1], 0, 150)
        for i in sorted(to_remove, reverse=True): self.bullets.pop(i)

    def create_explosion(self, x, y, z, radius):
        for i in range(len(self.enemies) - 1, -1, -1):
            e = self.enemies[i]
            dist = math.sqrt((e[0]-x)**2 + (e[1]-y)**2 + (e[2]-z)**2)
            if dist < radius:
                self.enemies.pop(i); self.score += 20; self.killstreak += 1
        for _ in range(30):
            vx = random.uniform(-50, 50); vy = random.uniform(-50, 50); vz = random.uniform(10, 150)
            self.particles.append(Particle([x,y,z], [vx,vy,vz], (1, random.random(), 0)))

    def update_enemies(self, dt):
        to_remove = []
        for i, e in enumerate(self.enemies):
            ex, ey, ez, state, speed, offset = e
            speed = 80 
            if state == 0: 
                dy = WALL_FRONT_FACE - ey; dist = abs(dy)
                if dist > 5: ey += (dy/dist) * speed * dt
                else: ey = WALL_FRONT_FACE; state = 1
            elif state == 1: 
                dz = WALL_HEIGHT - ez
                if abs(dz) > 5: ez += speed * dt
                else: ez = WALL_HEIGHT; state = 2
            elif state == 2: 
                dx = self.player_pos[0] - ex; dy = self.player_pos[1] - ey; dist = math.sqrt(dx*dx + dy*dy)
                if dist > 5: ex += (dx/dist) * speed * dt; ey += (dy/dist) * speed * dt
                if dist < 20:
                    self.lives -= 1; self.kills_without_damage = 0; to_remove.append(i)
                    if self.lives <= 0: self.game_over = True; self.game_over_reason = "Killed by enemies!"
            e[0], e[1], e[2], e[3] = ex, ey, ez, state
        for i in sorted(to_remove, reverse=True): self.enemies.pop(i)
        while len(self.enemies) < 5 and not self.game_over and not self.nuke_active:
            angle = random.uniform(0, 2 * math.pi); radius = 120
            x = math.cos(angle) * radius; y = TOWER_CENTER_Y + math.sin(angle) * radius
            self.enemies.append([x, y, 0, 0, random.uniform(30,50), 0])

    def check_collisions(self):
        b_rem, e_rem = [], []
        for i, b in enumerate(self.bullets):
            if b[6] == 1: continue 
            for j, e in enumerate(self.enemies):
                dist = math.sqrt((b[0]-e[0])**2 + (b[1]-e[1])**2 + (b[2]-e[2])**2)
                if dist < 20:
                    if i not in b_rem: b_rem.append(i)
                    if j not in e_rem: e_rem.append(j)
                    self.score += 10; self.killstreak += 1; self.kills_without_damage += 1
        for i in sorted(b_rem, reverse=True): self.bullets.pop(i)
        for j in sorted(e_rem, reverse=True): self.enemies.pop(j)
        if self.kills_without_damage >= 10 and self.grenades < 2:
            self.grenades = 2; self.kills_without_damage = 0; print("[REWARD] Grenades added!")
        if self.killstreak >= 20 and not self.nuke_available:
            self.nuke_available = True; print("[REWARD] Nuke Available!")

    def update_cheat_mode(self):
        if not self.cheat_mode or self.game_over: return
        nearest_e = None; min_dist = 9999
        for e in self.enemies:
            d = math.sqrt((e[0]-self.player_pos[0])**2 + (e[1]-self.player_pos[1])**2 + (e[2]-self.player_pos[2])**2)
            if d < min_dist: min_dist = d; nearest_e = e
        if nearest_e:
            dx = nearest_e[0] - self.player_pos[0]; dy = nearest_e[1] - self.player_pos[1]; dz = nearest_e[2] - self.player_pos[2]
            dist_horiz = math.sqrt(dx*dx + dy*dy)
            self.yaw = math.degrees(math.atan2(dy, dx)); self.pitch = math.degrees(math.atan2(dz, dist_horiz))
            if time.time() - self.last_cheat_fire > 0.15: self.fire_bullet(0); self.last_cheat_fire = time.time()

    def update_slice_target(self):
        if not self.slice_mode: 
            self.hovered_layer = -1
            return
        
        # Calculate Ray Direction (Player Forward)
        rad_yaw = math.radians(self.yaw)
        rad_pitch = math.radians(self.pitch)
        dx = math.cos(rad_yaw) * math.cos(rad_pitch)
        dy = math.sin(rad_yaw) * math.cos(rad_pitch)
        dz = math.sin(rad_pitch)
        
        best_dist = 99999
        selected_z = -1
        
        # Ray cast against all layers
        for z in range(self.tower_height):
            # Ignore non-solid layers
            if not self.is_layer_solid(z): continue 
            
            layer_center_z = (z + 0.5) * BLOCK_SIZE
            
            # Avoid division by zero
            if abs(dz) < 0.001: continue
            
            # Calculate distance to the layer's center plane
            t = (layer_center_z - self.camera_pos[2]) / dz
            
            # Check if this layer is closer than previous find and in front of camera
            if t > 0 and t < best_dist:
                # Calculate intersection point (World Space)
                ix = self.camera_pos[0] + t * dx
                iy = self.camera_pos[1] + t * dy
                
                # Bounding Box of Tower (Relative to tower center)
                grid_half_w = (TOWER_GRID_SIZE * BLOCK_SIZE) / 2
                
                # FIX: Increased tolerance (tol) from 5 to 40 (BLOCK_SIZE)
                # This makes it much easier to select the layer
                tol = 40 
                min_x = -grid_half_w - tol
                max_x = grid_half_w + tol
                min_y = TOWER_CENTER_Y - grid_half_w - tol
                max_y = TOWER_CENTER_Y + grid_half_w + tol
                
                if min_x <= ix <= max_x and min_y <= iy <= max_y:
                    best_dist = t
                    selected_z = z
                    
        self.hovered_layer = selected_z

    def perform_slice(self):
        # Force an update right before clicking to ensure accuracy
        self.update_slice_target()
        
        if self.hovered_layer != -1:
            if self.is_layer_solid(self.hovered_layer):
                print(f"[ACTION] Sliced solid layer {self.hovered_layer}")
                # Create explosion effect
                self.create_explosion(TOWER_CENTER_X, TOWER_CENTER_Y, (self.hovered_layer+0.5)*BLOCK_SIZE, 150)
                # Remove the layer
                self.remove_layer(self.hovered_layer)
                self.score += 50
                # Reset selection immediately to prevent double clicks
                self.hovered_layer = -1
            else:
                print("[ACTION] Cannot slice uneven layer!")
        else:
            print("[ACTION] No target selected! Aim directly at the solid green blocks.")

    def use_nuke(self):
        if self.nuke_available:
            self.nuke_available = False; self.killstreak = 0; self.nuke_active = True
            self.nuke_timer = 3.0; self.nuke_scale = 0; self.nuke_position = [0, TOWER_CENTER_Y, 500] 
            self.enemies.clear(); self.tower_height = 0
            self.tower_grid = [[[0 for _ in range(MAX_GRID_HEIGHT)] for _ in range(TOWER_GRID_SIZE)] for _ in range(TOWER_GRID_SIZE)]

    def update_nuke(self, dt):
        if self.nuke_active:
            self.nuke_timer -= dt; self.nuke_scale += 300 * dt
            if self.nuke_position[2] > 0: self.nuke_position[2] -= 300 * dt
            self.enemies.clear(); self.create_explosion(0, TOWER_CENTER_Y, 0, 300) 
            if self.nuke_timer <= 0: self.nuke_active = False

    def update_particles(self, dt):
        for p in self.particles[:]:
            if p.update(dt): self.particles.remove(p)

    def update(self):
        if self.game_over or self.paused: return
        curr_time = time.time(); dt = curr_time - getattr(self, '_last_t', curr_time); self._last_t = curr_time
        
        rs = 120 * dt
        if self.keys['left']: self.yaw += rs
        if self.keys['right']: self.yaw -= rs
        if self.keys['up']: self.pitch += rs
        if self.keys['down']: self.pitch -= rs
        self.pitch = max(-89, min(89, self.pitch))
        
        ms = 150 * dt
        rad = math.radians(self.yaw)
        fx, fy = math.cos(rad), math.sin(rad)
        rx, ry = math.cos(rad - math.pi/2), math.sin(rad - math.pi/2)
        
        if self.keys['w']: self.player_pos[0] += fx * ms; self.player_pos[1] += fy * ms
        if self.keys['s']: self.player_pos[0] -= fx * ms; self.player_pos[1] -= fy * ms
        if self.keys['d']: self.player_pos[0] += rx * ms; self.player_pos[1] += ry * ms
        if self.keys['a']: self.player_pos[0] -= rx * ms; self.player_pos[1] -= ry * ms
        
        lx = math.cos(rad) * math.cos(math.radians(self.pitch))
        ly = math.sin(rad) * math.cos(math.radians(self.pitch))
        lz = math.sin(math.radians(self.pitch))

        if self.fps_mode:
            self.camera_pos = [self.player_pos[0], self.player_pos[1], self.player_pos[2] + 10]
            self.camera_target = [self.player_pos[0] + lx * 500, self.player_pos[1] + ly * 500, self.player_pos[2] + lz * 500]
        else:
            dist = 600
            self.camera_pos = [self.player_pos[0]-lx*dist, self.player_pos[1]-ly*dist, self.player_pos[2]-lz*dist+50]
            self.camera_target = self.player_pos[:]

        self.update_cheat_mode()
        self.update_slice_target() 
        self.update_tetris(dt)
        self.update_bullets(dt)
        self.update_enemies(dt)
        self.update_nuke(dt)
        self.update_particles(dt)
        self.check_collisions() 

# ================= DRAWING =================
def draw_grid():
    glBegin(GL_LINES)
    glColor3f(0.5, 0.5, 0.5)
    for i in range(-600, 601, 100):
        glVertex3f(i, -600, 0); glVertex3f(i, 600, 0)
        glVertex3f(-600, i, 0); glVertex3f(600, i, 0)
    glEnd()

def draw_wall():
    glPushMatrix()
    glColor3f(*COLOR_WALL)
    glTranslatef(0, WALL_CENTER_Y, WALL_HEIGHT/2)
    glScalef(600, WALL_THICKNESS, WALL_HEIGHT)
    glutSolidCube(1)
    glPopMatrix()

def draw_summoners():
    glPushMatrix()
    glTranslatef(0, TOWER_CENTER_Y, 0)
    glColor3f(*COLOR_ZONE)
    s = TOWER_GRID_SIZE * BLOCK_SIZE / 2 * 2.2 
    glBegin(GL_QUADS)
    glVertex3f(-s, -s, 1); glVertex3f(s, -s, 1)
    glVertex3f(s, s, 1); glVertex3f(-s, s, 1)
    glEnd()
    corners = [(-s, -s), (s, -s), (s, s), (-s, s)]
    for cx, cy in corners:
        glPushMatrix()
        glTranslatef(cx, cy, 10)
        glColor3f(*COLOR_SUMMONER)
        glutSolidSphere(10, 8, 8) 
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3f(0,0,0); glVertex3f(0,0,300)
        glEnd()
        glPopMatrix()
    glPopMatrix()

def draw_tower():
    # Draw Falling Piece
    if game.active_tetris:
        cells = game.get_shape_cells(game.active_tetris['shape_idx'], game.active_tetris['rotation'],
                                     game.active_tetris['x'], game.active_tetris['y'], game.active_tetris['z'])
        for x, y, z in cells:
            glPushMatrix()
            tx = (x - TOWER_GRID_SIZE/2 + 0.5) * BLOCK_SIZE
            ty = TOWER_CENTER_Y + (y - TOWER_GRID_SIZE/2 + 0.5) * BLOCK_SIZE
            tz = (z + 0.5) * BLOCK_SIZE
            glTranslatef(tx, ty, tz)
            glColor3f(*TETRIS_COLORS[game.active_tetris['color_idx']])
            glutSolidCube(BLOCK_SIZE - 2)
            glPopMatrix()
            
    # Draw Static Grid
    for z in range(MAX_GRID_HEIGHT):
        
        # SLICE VISUAL: Check if this layer is sliceable (Solid)
        is_solid = game.is_layer_solid(z)
        is_hovered = (z == game.hovered_layer)
        
        for x in range(TOWER_GRID_SIZE):
            for y in range(TOWER_GRID_SIZE):
                col = game.tower_grid[x][y][z]
                if col > 0:
                    glPushMatrix()
                    tx = (x - TOWER_GRID_SIZE/2 + 0.5) * BLOCK_SIZE
                    ty = TOWER_CENTER_Y + (y - TOWER_GRID_SIZE/2 + 0.5) * BLOCK_SIZE
                    tz = (z + 0.5) * BLOCK_SIZE
                    glTranslatef(tx, ty, tz)
                    
                    if game.slice_mode and is_solid:
                        # Flicker Green Logic
                        glEnable(GL_BLEND)
                        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                        
                        flicker = 0.5 + 0.5 * math.sin(time.time() * 10) # 0 to 1 pulse
                        
                        if is_hovered:
                             glColor4f(0.0, 1.0, 0.0, 0.8) # Bright Green if hovered
                        else:
                             glColor4f(0.0, 1.0, 0.0, 0.3 * flicker) # Pulsing Green
                             
                        glScalef(1.05, 1.05, 1.05)
                        glutSolidCube(BLOCK_SIZE)
                        glScalef(1/1.05, 1/1.05, 1/1.05)
                        glDisable(GL_BLEND)
                    
                    glColor3f(*TETRIS_COLORS[col-1])
                    glutSolidCube(BLOCK_SIZE - 2)
                    
                    glPopMatrix()

def draw_player():
    if game.fps_mode: return 
    glPushMatrix()
    glTranslatef(*game.player_pos)
    glRotatef(game.yaw - 90, 0, 0, 1) 
    glColor3f(*COLOR_PLAYER)
    glutSolidSphere(15, 16, 16)
    glPushMatrix()
    glColor3f(*COLOR_GUN)
    glTranslatef(0, 10, 5)
    glRotatef(90 - game.pitch, 1, 0, 0) 
    gluCylinder(gluNewQuadric(), 5, 5, 30, 8, 8)
    glPopMatrix()
    glPopMatrix()

def draw_entities():
    glColor3f(*COLOR_ENEMY)
    for e in game.enemies:
        glPushMatrix()
        glTranslatef(e[0], e[1], e[2])
        s = 1.0 + 0.2 * math.sin(time.time() * 10)
        glScalef(s, s, s)
        glutSolidSphere(12, 12, 12)
        glPopMatrix()
    
    for b in game.bullets:
        glPushMatrix()
        glTranslatef(b[0], b[1], b[2])
        if b[6] == 1: glColor3f(*COLOR_GRENADE); glutSolidSphere(6, 8, 8)
        else: glColor3f(*COLOR_BULLET); glutSolidSphere(4, 8, 8)
        glPopMatrix()

def draw_particles():
    glPointSize(3)
    glBegin(GL_POINTS)
    for p in game.particles:
        glColor3f(*p.color)
        glVertex3f(*p.position)
    glEnd()

def draw_nuke():
    if not game.nuke_active: return
    glPushMatrix()
    glTranslatef(*game.nuke_position)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glColor4f(1.0, 0.5, 0.0, 0.5)
    glutSolidSphere(game.nuke_scale, 32, 32)
    glColor4f(1.0, 1.0, 1.0, 0.8)
    glutSolidSphere(game.nuke_scale * 0.5, 32, 32)
    glDisable(GL_BLEND)
    glPopMatrix()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    gluLookAt(game.camera_pos[0], game.camera_pos[1], game.camera_pos[2],
              game.camera_target[0], game.camera_target[1], game.camera_target[2],
              0, 0, 1)
    
    draw_grid()
    draw_wall()
    draw_summoners()
    draw_tower()
    draw_player()
    draw_entities()
    draw_particles()
    draw_nuke()
    
    draw_text(10, 770, f"Score: {game.score}")
    draw_text(10, 740, f"Lives: {game.lives}")
    draw_text(10, 710, f"Tower: {game.tower_height}/{TOWER_LIMIT}")
    draw_text(10, 680, f"Killstreak: {game.killstreak}")
    
    if game.slice_mode: draw_text(10, 650, "SLICE MODE: Click FLICKERING layers!", (1,1,0))
    if game.nuke_available: draw_text(10, 620, "NUKE READY! Press O", (1, 0.5, 0))
    elif game.grenades > 0: draw_text(10, 620, f"GRENADES: {game.grenades} (Q)", (0, 1, 0))
    if game.cheat_mode: draw_text(10, 590, "CHEAT MODE ACTIVE", (1,0,1))
    
    if game.debug_mode:
        draw_text(10, 100, f"Pos: {game.player_pos[0]:.0f},{game.player_pos[1]:.0f},{game.player_pos[2]:.0f}", (1,1,1))
        
    if game.game_over: 
        draw_text(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 20, "GAME OVER", (1,0,0))
        draw_text(WINDOW_WIDTH//2 - 120, WINDOW_HEIGHT//2 - 20, f"Reason: {game.game_over_reason}", (1,1,1))
        draw_text(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 50, "Press R to Restart", (0,1,0))
    
    # Draw Crosshair if FPS mode OR Slice Mode is active
    if game.fps_mode or game.slice_mode:
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        
        if game.slice_mode: glColor3f(0, 1, 0) # Green crosshair for slice
        else: glColor3f(1, 1, 1) # White for gun
            
        glBegin(GL_LINES)
        glVertex2f(490, 400); glVertex2f(510, 400); glVertex2f(500, 390); glVertex2f(500, 410)
        glEnd()
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

    glutSwapBuffers()

# ================= MAIN =================
def idle():
    game.update()
    glutPostRedisplay()

def keyboard(key, x, y):
    try: k = key.decode("utf-8").lower()
    except: return
    if k == 'w': game.keys['w'] = True
    elif k == 's': game.keys['s'] = True
    elif k == 'a': game.keys['a'] = True
    elif k == 'd': game.keys['d'] = True
    elif k == ' ': game.fire_bullet(0)
    elif k == 'q': game.fire_bullet(1)
    elif k == 'o': game.use_nuke()
    elif k == 'r': game.__init__()
    elif k == 'p': game.paused = not game.paused
    elif k == 'c': game.cheat_mode = not game.cheat_mode
    elif k == 'e': game.slice_mode = not game.slice_mode
    elif k == 'b': game.debug_mode = not game.debug_mode

def keyboardUp(key, x, y):
    try: k = key.decode("utf-8").lower()
    except: return
    if k in game.keys: game.keys[k] = False

def special(key, x, y):
    if key == GLUT_KEY_LEFT: game.keys['left'] = True
    elif key == GLUT_KEY_RIGHT: game.keys['right'] = True
    elif key == GLUT_KEY_UP: game.keys['up'] = True
    elif key == GLUT_KEY_DOWN: game.keys['down'] = True

def specialUp(key, x, y):
    if key == GLUT_KEY_LEFT: game.keys['left'] = False
    elif key == GLUT_KEY_RIGHT: game.keys['right'] = False
    elif key == GLUT_KEY_UP: game.keys['up'] = False
    elif key == GLUT_KEY_DOWN: game.keys['down'] = False

def mouse(button, state, x, y):
    if state == GLUT_DOWN:
        if button == GLUT_RIGHT_BUTTON:
            game.fps_mode = not game.fps_mode
        elif button == GLUT_LEFT_BUTTON:
            if game.slice_mode:
                game.perform_slice()
            else:
                game.fire_bullet(0)

def main():
    global game
    game = GameState()
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutCreateWindow(b"Sky-Bridge Siege [ARCHITECT UPDATE]")
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND) 
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(*COLOR_BG, 1.0)
    
    glutDisplayFunc(showScreen)
    glutIdleFunc(idle)
    glutKeyboardFunc(keyboard)
    glutKeyboardUpFunc(keyboardUp)
    glutSpecialFunc(special)
    glutSpecialUpFunc(specialUp)
    glutMouseFunc(mouse)
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    
    print("----- Controls -----")
    print("Arrows      : Look/Aim")
    print("WASD        : Move Player")
    print("Space       : Fire Bullet")
    print("E           : Toggle Slice Mode (Click Green Layers)")
    print("Q           : Throw Grenade")
    print("O           : Use Nuke")
    print("C           : Toggle Cheat Mode")
    print("B           : Toggle Debug Info")
    print("Right Click : Toggle Camera")
    
    glutMainLoop()

if __name__ == "__main__":
    main()