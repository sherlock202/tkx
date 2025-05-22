import pygame
import random
import math

# Initialize Pygame modules
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Game States
START_MENU = 0
PLAYING = 1
GAME_OVER_STATE = 2 # Renamed to avoid conflict with game_over boolean

# Create the game screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Set window title
pygame.display.set_caption("Ant and Food Game")

# Clock object to manage frame rate
clock = pygame.time.Clock()

# Block Size for Tetromino-like obstacles
BLOCK_SIZE = 20

# Obstacle Shapes (Tetromino-like)
# Coordinates are relative grid positions from a pivot point for each shape.
OBSTACLE_SHAPES = {
    'O': [(0, 0), (1, 0), (0, 1), (1, 1)],  # Square shape (pivot: top-left block)
    'I': [(0, -1), (0, 0), (0, 1), (0, 2)], # Vertical I-shape (pivot: (0,0))
    'L': [(0, -1), (0, 0), (0, 1), (1, 1)], # L-shape (pivot: (0,0), tail to the right-bottom)
    'J': [(0, -1), (0, 0), (0, 1), (-1, 1)],# J-shape (pivot: (0,0), tail to the left-bottom)
    'T': [(-1, 0), (0, 0), (1, 0), (0, 1)], # T-shape (pivot: (0,0), stem points "down")
    'S': [(0, 0), (1, 0), (-1, 1), (0, 1)], # S-shape (pivot: (0,0) for top-left part of "S")
    'Z': [(-1, 0), (0, 0), (0, 1), (1, 1)]  # Z-shape (pivot: (0,0) for top-left part of "Z")
}

# Obstacle Colors
OBSTACLE_COLORS = [
    (255, 0, 0),    # Red
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Cyan
    (128, 0, 128),  # Purple
]

# Ant Movement Parameters
OBSTACLE_REPULSION_RADIUS_FACTOR = 2.0  # Factor for repulsion radius
ANT_OBSTACLE_REPULSION_WEIGHT = 1.5    # Strength of repulsion vs attraction
MAX_REPULSION_VECTORS_CONSIDERED = 5   # Max closest blocks for repulsion calculation


# Fonts
title_font = pygame.font.Font(None, 100)
button_font = pygame.font.Font(None, 50)
game_over_font = pygame.font.Font(None, 74)
score_font = pygame.font.Font(None, 50)

# Button Class
class Button:
    def __init__(self, text, x, y, width, height, color, hover_color, font, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font = font
        self.action = action
        self.is_hovered = False

    def draw(self, screen):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, current_color, self.rect)
        text_surface = self.font.render(self.text, True, (255, 255, 255)) # White text
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.is_hovered:
                if self.action:
                    self.action()
                return True
        return False

# Ant class
class Ant:
    def __init__(self, food_obj): 
        self.food_obj = food_obj
        
        # Load ant sprite
        try:
            self.original_image = pygame.image.load("ant_sprite.png").convert_alpha()
        except pygame.error as e:
            print(f"Error loading ant_sprite.png: {e}")
            # Fallback to a simple square if image loading fails
            self.original_image = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.rect(self.original_image, (0,0,0), (0,0,24,24)) # Black square
            pygame.draw.line(self.original_image, (255,0,0), (12,0), (12,5), 2) # Red line for front

        self.image = self.original_image # This is the surface that gets rotated and drawn
        
        # Initial position - center the ant sprite if possible, or use random topleft
        initial_x = random.randint(0, SCREEN_WIDTH - self.image.get_width())
        initial_y = random.randint(0, SCREEN_HEIGHT - self.image.get_height())
        self.rect = self.image.get_rect(topleft=(initial_x, initial_y))
        
        # self.x and self.y will now refer to the center of the ant for smoother rotation/movement logic
        self.x = float(self.rect.centerx) 
        self.y = float(self.rect.centery)

        self.speed = 2.0 
        self.random_strength = 0.3 # Original random strength, will be scaled down in update_movement
        # self.seeking_strength is implicitly 1.0 for food attraction in the new model.

    def update_movement(self, obstacles_list):
        ant_center_x, ant_center_y = self.rect.centerx, self.rect.centery

        # --- Food Attraction Vector ---
        food_center_x, food_center_y = self.food_obj.rect.centerx, self.food_obj.rect.centery
        attraction_dx = food_center_x - ant_center_x
        attraction_dy = food_center_y - ant_center_y
        
        norm_attr_dx, norm_attr_dy = 0.0, 0.0
        dist_to_food = math.hypot(attraction_dx, attraction_dy)
        if dist_to_food > 0:
            norm_attr_dx = attraction_dx / dist_to_food
            norm_attr_dy = attraction_dy / dist_to_food

        # --- Obstacle Repulsion Vector ---
        total_repulsion_dx, total_repulsion_dy = 0.0, 0.0
        all_blocks_with_dist = []

        for obs in obstacles_list:
            for block_rect in obs.blocks:
                block_center_x, block_center_y = block_rect.centerx, block_rect.centery
                dist_to_block = math.hypot(ant_center_x - block_center_x, ant_center_y - block_center_y)
                # Store 'rect' as well, though not strictly needed for current repulsion logic,
                # it's good practice if future repulsion might use block size/orientation.
                all_blocks_with_dist.append({
                    'dist': dist_to_block, 
                    'block_center_x': block_center_x, 
                    'block_center_y': block_center_y,
                    'rect': block_rect 
                })
        
        all_blocks_with_dist.sort(key=lambda b: b['dist'])
        
        considered_blocks = 0
        for block_info in all_blocks_with_dist:
            if considered_blocks >= MAX_REPULSION_VECTORS_CONSIDERED:
                break

            dist = block_info['dist']
            block_cx, block_cy = block_info['block_center_x'], block_info['block_center_y']
            repulsion_radius = BLOCK_SIZE * OBSTACLE_REPULSION_RADIUS_FACTOR

            if 0.01 < dist < repulsion_radius: 
                vec_from_block_dx = ant_center_x - block_cx
                vec_from_block_dy = ant_center_y - block_cy
                
                norm_rep_dx, norm_rep_dy = 0.0, 0.0
                # dist is magnitude of (vec_from_block_dx, vec_from_block_dy)
                if dist > 0: # Redundant due to 0.01 check, but safe
                    norm_rep_dx = vec_from_block_dx / dist 
                    norm_rep_dy = vec_from_block_dy / dist
                
                strength = (repulsion_radius - dist) / repulsion_radius 
                total_repulsion_dx += norm_rep_dx * strength
                total_repulsion_dy += norm_rep_dy * strength
                considered_blocks += 1
        
        # --- Combine Attraction and Repulsion ---
        combined_dx = norm_attr_dx + total_repulsion_dx * ANT_OBSTACLE_REPULSION_WEIGHT
        combined_dy = norm_attr_dy + total_repulsion_dy * ANT_OBSTACLE_REPULSION_WEIGHT

        # --- Add Randomness (scaled down) ---
        random_dx_component = random.uniform(-1, 1) * self.random_strength * 0.5
        random_dy_component = random.uniform(-1, 1) * self.random_strength * 0.5
        
        final_dx = combined_dx + random_dx_component
        final_dy = combined_dy + random_dy_component

        # --- Normalize Final Vector and Apply Speed ---
        norm_final_dx, norm_final_dy = 0.0, 0.0
        magnitude_final = math.hypot(final_dx, final_dy)
        if magnitude_final > 0:
            norm_final_dx = final_dx / magnitude_final
            norm_final_dy = final_dy / magnitude_final
            
        movement_x = norm_final_dx * self.speed
        movement_y = norm_final_dy * self.speed

        # --- Fallback Direct Collision Avoidance ---
        potential_rect = self.rect.move(int(movement_x), int(movement_y))
        
        collision_detected_fallback = False
        for obs in obstacles_list:
            if potential_rect.collidelist(obs.blocks) != -1:
                collision_detected_fallback = True
                # Simple fallback: try to reverse the component of movement that caused collision,
                # or a small random step if stuck.
                # Test horizontal movement only
                test_rect_hor = self.rect.move(int(movement_x), 0)
                if test_rect_hor.collidelist(obs.blocks) != -1: 
                    movement_x = -movement_x * 0.5 # Dampen and reverse
                
                # Test vertical movement only
                test_rect_vert = self.rect.move(0, int(movement_y))
                if test_rect_vert.collidelist(obs.blocks) != -1: 
                    movement_y = -movement_y * 0.5 # Dampen and reverse

                # If both components individually cause collision or it's still stuck
                final_check_rect = self.rect.move(int(movement_x), int(movement_y)) # Use the potentially modified movement_x/y
                if final_check_rect.collidelist(obs.blocks) != -1:
                    # Fallback to a more random, smaller step if primary deflection fails
                    rand_escape_angle = random.uniform(0, 2 * math.pi)
                    movement_x = math.cos(rand_escape_angle) * self.speed * 0.3 # Small random step
                    movement_y = math.sin(rand_escape_angle) * self.speed * 0.3
                break # React to one obstacle at a time for fallback

        # --- Update Position (logical center) ---
        self.x += movement_x
        self.y += movement_y
        
        # Screen Boundary checks (based on center)
        half_width = self.rect.width / 2.0
        half_height = self.rect.height / 2.0
        self.x = max(half_width, min(self.x, SCREEN_WIDTH - half_width))
        self.y = max(half_height, min(self.y, SCREEN_HEIGHT - half_height))

        # Update visual rect and sprite rotation based on final movement
        current_movement_angle = math.degrees(math.atan2(-movement_y, movement_x)) if movement_x != 0 or movement_y != 0 else None
        
        if current_movement_angle is not None:
            self.image = pygame.transform.rotate(self.original_image, current_movement_angle)
        # If no movement, image retains its last orientation.
        
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))


    def draw(self, screen_surface): 
        screen_surface.blit(self.image, self.rect)

# Food class
class Food:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH - 15) 
        self.y = random.randint(0, SCREEN_HEIGHT - 15) 
        self.size = 15
        self.color = (0, 255, 0)  # Green
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self, screen_surface): # Renamed screen to screen_surface
        pygame.draw.rect(screen_surface, self.color, self.rect)

# Obstacle class
class Obstacle:
    def __init__(self, x, y, shape_key, color): 
        self.x = x  # Anchor position (e.g., pivot or top-left of shape's local (0,0) block)
        self.y = y
        self.shape_key = shape_key
        self.shape_definition = OBSTACLE_SHAPES[shape_key]
        self.color = color
        
        self.angle = 0.0
        self.blocks = []  # List to store pygame.Rect for each individual block
        
        # self.rect will be the overall bounding box, updated by _update_blocks
        # Initialize with a placeholder, will be correctly set by _update_blocks
        self.rect = pygame.Rect(x, y, 0, 0) 

        # Dragging and rotation state
        self.is_being_dragged = False
        self.drag_offset_x = 0 # Offset from self.x to mouse click
        self.drag_offset_y = 0 # Offset from self.y to mouse click
        self.drag_start_time = 0 
        self.is_rotating = False
        
        self._update_blocks() # Calculate initial block positions and bounding box

    def _update_blocks(self):
        self.blocks.clear()
        if not self.shape_definition:
            return

        angle_rad = math.radians(self.angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)

        min_x_coord, max_x_coord = float('inf'), float('-inf')
        min_y_coord, max_y_coord = float('inf'), float('-inf')

        for rel_x_idx, rel_y_idx in self.shape_definition:
            # These are grid indices, so multiply by BLOCK_SIZE for pixel coords
            local_x = rel_x_idx * BLOCK_SIZE
            local_y = rel_y_idx * BLOCK_SIZE

            # Rotate relative coordinates around (0,0) local pivot
            rotated_rel_x = local_x * cos_angle - local_y * sin_angle
            rotated_rel_y = local_x * sin_angle + local_y * cos_angle

            # Translate to world position based on obstacle's main (x,y) anchor
            world_x = self.x + rotated_rel_x
            world_y = self.y + rotated_rel_y
            
            block_rect = pygame.Rect(world_x, world_y, BLOCK_SIZE, BLOCK_SIZE)
            self.blocks.append(block_rect)

            # Update bounding box extents based on actual block positions
            min_x_coord = min(min_x_coord, block_rect.left)
            min_y_coord = min(min_y_coord, block_rect.top)
            max_x_coord = max(max_x_coord, block_rect.right)
            max_y_coord = max(max_y_coord, block_rect.bottom)
        
        if self.blocks:
            # Set the overall bounding rect for the obstacle
            self.rect = pygame.Rect(min_x_coord, min_y_coord, 
                                     max_x_coord - min_x_coord, max_y_coord - min_y_coord)
        else: # Should not happen if shape_definition is valid
            self.rect = pygame.Rect(self.x, self.y, 0, 0)


    def update(self):
        # Obstacles are static unless dragged or rotated. 
        # All updates to position/rotation and subsequent _update_blocks calls
        # are handled in the main event loop (MOUSEMOTION).
        pass

    def draw(self, screen_surface): 
        for block_rect in self.blocks:
            pygame.draw.rect(screen_surface, self.color, block_rect)
            # Optional: draw a border for each block
            pygame.draw.rect(screen_surface, (50, 50, 50), block_rect, 1) # Dark grey border

# Game variables (will be managed by reset_game and state changes)
ant = None
food = None
obstacles = [] 
score = None
start_time = 0
game_is_over_flag = False 
ant_killed_by_obstacle = False 

# Timer variables for timed spawning
obstacle_spawn_interval = 5000  # Default, can be set in reset_game
last_obstacle_spawn_time = 0    # Will be initialized in reset_game

# reset_game function
def reset_game():
    global ant, food, obstacles, score, start_time, game_is_over_flag, ant_killed_by_obstacle
    global last_obstacle_spawn_time, obstacle_spawn_interval # Add timer globals
    
    food_item = Food()
    ant_instance = Ant(food_item)
    
    obstacles_list = []
    num_obstacles = 5 # Initial obstacles
    max_placement_attempts = 100 

    existing_entities_rects = [ant_instance.rect, food_item.rect]

    for _ in range(num_obstacles):
        placed = False
        for attempt in range(max_placement_attempts):
            shape_k = random.choice(list(OBSTACLE_SHAPES.keys()))
            col = random.choice(OBSTACLE_COLORS)
            initial_angle = random.choice([0, 90, 180, 270]) 
            
            dummy_obs_for_bounds = Obstacle(0, 0, shape_k, col)
            dummy_obs_for_bounds.angle = initial_angle
            dummy_obs_for_bounds._update_blocks()
            
            min_pivot_offset_x = -dummy_obs_for_bounds.rect.left
            max_pivot_offset_x = SCREEN_WIDTH - (dummy_obs_for_bounds.rect.left + dummy_obs_for_bounds.rect.width)
            min_pivot_offset_y = -dummy_obs_for_bounds.rect.top
            max_pivot_offset_y = SCREEN_HEIGHT - (dummy_obs_for_bounds.rect.top + dummy_obs_for_bounds.rect.height)

            if max_pivot_offset_x < min_pivot_offset_x or max_pivot_offset_y < min_pivot_offset_y:
                continue 

            potential_pivot_x = random.randint(min_pivot_offset_x, max_pivot_offset_x)
            potential_pivot_y = random.randint(min_pivot_offset_y, max_pivot_offset_y)
            
            temp_obs = Obstacle(potential_pivot_x, potential_pivot_y, shape_k, col)
            temp_obs.angle = initial_angle 
            temp_obs._update_blocks()      
            
            collision_with_existing = False
            for existing_rect in existing_entities_rects:
                if temp_obs.rect.colliderect(existing_rect.inflate(10, 10)): 
                    collision_with_existing = True
                    break
            
            if not collision_with_existing:
                obstacles_list.append(temp_obs)
                existing_entities_rects.append(temp_obs.rect) 
                placed = True
                break
        if not placed:
            print(f"Warning: Could not place initial obstacle after {max_placement_attempts} attempts.")

    current_score = None
    game_start_time = pygame.time.get_ticks()
    game_is_over_flag = False
    ant_killed_by_obstacle = False 
    
    # Initialize timed spawning variables
    obstacle_spawn_interval = 5000  # milliseconds
    last_obstacle_spawn_time = pygame.time.get_ticks()
    
    return (ant_instance, food_item, obstacles_list, current_score, 
            game_start_time, game_is_over_flag, 
            # No need to return last_obstacle_spawn_time and obstacle_spawn_interval as they are global
           )


# Current game state
current_state = START_MENU

# Button actions
def start_game_action():
    global current_state, ant, food, obstacles, score, start_time, game_is_over_flag, ant_killed_by_obstacle
    # No need to declare last_obstacle_spawn_time, obstacle_spawn_interval as global here if only set in reset_game
    current_state = PLAYING
    # reset_game now handles setting the global timer variables directly
    ant, food, obstacles, score, start_time, game_is_over_flag = reset_game() 
    ant_killed_by_obstacle = False 

def restart_game_action():
    # Same as starting the game for now, could go to START_MENU or directly to PLAYING
    start_game_action()

def go_to_menu_action():
    global current_state
    current_state = START_MENU


# Button instances
start_button = Button("Start Game", SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2 - 50, 200, 50, 
                      (0, 150, 0), (0, 200, 0), button_font, action=start_game_action)
restart_button = Button("Restart", SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2 + 75, 200, 50, 
                        (150, 0, 0), (200, 0, 0), button_font, action=restart_game_action)
# Potentially a quit button for menu/game over
quit_button_menu = Button("Quit", SCREEN_WIDTH/2 - 100, SCREEN_HEIGHT/2 + 25, 200, 50,
                           (100, 100, 100), (150, 150, 150), button_font, action=pygame.quit)


# Initialize game for the first time if starting directly in PLAYING state (not used if START_MENU is first)
# ant, food, obstacles, score, start_time, last_obstacle_spawn, game_is_over_flag = reset_game()


# Main game loop
running = True
while running:
    # --------------------------------------------------------------------------
    # Event Handling
    # --------------------------------------------------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False  # Exit the game loop
        
        if current_state == START_MENU:
            start_button.handle_event(event)
            quit_button_menu.handle_event(event) # Allow quitting from menu
        elif current_state == PLAYING:
            # Mouse events for dragging obstacles (only during PLAYING state)
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not game_is_over_flag: 
                    if event.button == 1: 
                        for obs_item in obstacles: 
                            if obs_item.rect.collidepoint(event.pos): # Check against overall bounding box
                                # More precise check: iterate through obs_item.blocks if needed,
                                # but for initiating drag, bounding box is usually fine.
                                obs_item.is_being_dragged = True
                                # Offset is from the obstacle's main anchor (self.x, self.y) to the mouse
                                obs_item.drag_offset_x = obs_item.x - event.pos[0] 
                                obs_item.drag_offset_y = obs_item.y - event.pos[1] 
                                obs_item.drag_start_time = pygame.time.get_ticks()
                                obs_item.is_rotating = False
                                break 
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: 
                    for obs_item in obstacles:
                        if obs_item.is_being_dragged: 
                             obs_item.is_rotating = False
                        obs_item.is_being_dragged = False 
            elif event.type == pygame.MOUSEMOTION:
                if not game_is_over_flag: 
                    for obs_item in obstacles:
                        if obs_item.is_being_dragged:
                            if not obs_item.is_rotating and \
                               pygame.time.get_ticks() - obs_item.drag_start_time > 500: 
                                obs_item.is_rotating = True
                            
                            if obs_item.is_rotating:
                                # Keep the pivot point (obs_item.x, obs_item.y) fixed during rotation
                                # The rotation happens around the local (0,0) of the shape_definition,
                                # and self.x, self.y is the world coordinate of that local (0,0).
                                obs_item.angle += 2 
                                obs_item.angle %= 360
                                obs_item._update_blocks() # Recalculate block positions and bounding rect
                            else: # Just dragging, not rotating
                                # Update the main anchor position
                                obs_item.x = event.pos[0] + obs_item.drag_offset_x
                                obs_item.y = event.pos[1] + obs_item.drag_offset_y
                                obs_item._update_blocks() # Recalculate block positions and bounding rect
                            
                            # Check for collision with ant after any rect update (drag or rotate)
                            # Use collidelist for more precise collision with the ant's rect against obstacle blocks
                            if ant and ant.rect.collidelist(obs_item.blocks) != -1: # Ensure ant exists
                                ant_killed_by_obstacle = True
                                game_is_over_flag = True # Signal game over
        elif current_state == GAME_OVER_STATE:
            restart_button.handle_event(event)
            # quit_button_game_over.handle_event(event) # If you want a separate quit for game over

    # --------------------------------------------------------------------------
    # Game State Updates
    # --------------------------------------------------------------------------
    if current_state == PLAYING:
        if not game_is_over_flag:
            ant.update_movement(obstacles) 

            # Check for ant-food collision (winning condition)
            if ant.rect.colliderect(food.rect):
                game_is_over_flag = True  # Signal game over
            
            # Obstacle dragging collision is checked in MOUSEMOTION
            
            # Timed Obstacle Spawning
            current_time_ticks = pygame.time.get_ticks()
            if current_time_ticks - last_obstacle_spawn_time > obstacle_spawn_interval:
                shape_k = random.choice(list(OBSTACLE_SHAPES.keys()))
                col = random.choice(OBSTACLE_COLORS)
                
                # Spawn near top edge: random x, y slightly off-screen or at edge
                # Ensure pivot is chosen so part of the shape appears on screen quickly.
                # Max width of a shape could be around 4 blocks.
                spawn_x = random.randint(0, SCREEN_WIDTH - BLOCK_SIZE * 4) 
                spawn_y = -BLOCK_SIZE # Anchor y slightly above screen top
                
                initial_angle = random.choice([0, 90, 180, 270])
                
                new_obstacle = Obstacle(spawn_x, spawn_y, shape_k, col)
                new_obstacle.angle = initial_angle
                new_obstacle._update_blocks()
                
                # Optional: Basic validity check (e.g., not directly on ant/food)
                # For simplicity, we'll skip a detailed collision check for timed spawns here,
                # assuming they mostly appear from top and won't immediately cause issues.
                # A more robust game might check for overlap with ant/food.
                
                obstacles.append(new_obstacle)
                last_obstacle_spawn_time = current_time_ticks # Update last spawn time

        # Centralized game over handling (score calculation and state transition)
        if game_is_over_flag: 
            if score is None: 
                 score = (pygame.time.get_ticks() - start_time) / 1000.0
            current_state = GAME_OVER_STATE 


    # --------------------------------------------------------------------------
    # Drawing / Rendering
    # --------------------------------------------------------------------------
    screen.fill((255, 255, 255)) # White background
    
    if current_state == START_MENU:
        title_text_surface = title_font.render("Ant and Food Game", True, (0,0,0)) # Black
        title_text_rect = title_text_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 150))
        screen.blit(title_text_surface, title_text_rect)
        start_button.draw(screen)
        quit_button_menu.draw(screen)

    elif current_state == PLAYING:
        for obstacle_item in obstacles:
            obstacle_item.draw(screen)
        ant.draw(screen)
        food.draw(screen)
        # Optionally, display live score/time during PLAYING state
        current_playing_time = (pygame.time.get_ticks() - start_time) / 1000.0
        time_surface = score_font.render(f"Time: {current_playing_time:.2f}", True, (0,0,0))
        screen.blit(time_surface, (10, 10))


    elif current_state == GAME_OVER_STATE:
        # Draw game elements from the last frame of PLAYING
        for obstacle_item in obstacles:
            obstacle_item.draw(screen)
        if ant: ant.draw(screen) 
        if food: food.draw(screen)

        message_color = (200, 0, 0) # Default to red for game over
        if ant_killed_by_obstacle:
            game_over_message = "Ant Squished!"
        else: # Ant found food
            game_over_message = "Food Found!"
            message_color = (0, 150, 0) # Green for success
        
        game_over_text_surface = game_over_font.render(game_over_message, True, message_color)
        game_over_text_rect = game_over_text_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50))
        screen.blit(game_over_text_surface, game_over_text_rect)

        if score is not None:
            score_display_text = f"Score: {score:.2f} seconds"
            score_surface = score_font.render(score_display_text, True, (0, 0, 150))
            score_rect = score_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 25))
            screen.blit(score_surface, score_rect)
        restart_button.draw(screen)
        # quit_button_game_over.draw(screen)


    pygame.display.flip()
    clock.tick(60)

pygame.quit()
