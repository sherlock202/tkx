import pygame
import random
import math

# Initialize Pygame modules
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Create the game screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

# Set window title
pygame.display.set_caption("Ant and Food Game")

# Clock object to manage frame rate
clock = pygame.time.Clock()

# Ant class
class Ant:
    def __init__(self, food):
        self.food = food
        self.x = random.randint(0, SCREEN_WIDTH - 10) # Ensure ant is fully visible
        self.y = random.randint(0, SCREEN_HEIGHT - 10) # Ensure ant is fully visible
        self.size = 10
        self.color = (0, 0, 0)  # Black
        self.speed = 2
        self.seeking_strength = 0.7
        self.random_strength = 0.3
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def update_movement(self, obstacles):
        # Calculate direction to food
        dx_food = self.food.x - self.x
        dy_food = self.food.y - self.y

        # Normalize direction vector to food
        distance_to_food = math.sqrt(dx_food**2 + dy_food**2)
        
        norm_dx_food = 0
        norm_dy_food = 0
        if distance_to_food > 0: # Avoid division by zero if ant is on food
            norm_dx_food = dx_food / distance_to_food
            norm_dy_food = dy_food / distance_to_food

        # Random movement component
        random_dx = random.choice([-1, 0, 1])
        random_dy = random.choice([-1, 0, 1])
        
        # If random movement is zero, pick a direction to ensure it moves
        if random_dx == 0 and random_dy == 0:
            random_dx = random.choice([-1, 1]) 
            random_dy = random.choice([-1, 1])


        # Combine seeking and random movement
        # Final dx/dy for this frame
        final_dx = (norm_dx_food * self.seeking_strength + random_dx * self.random_strength)
        final_dy = (norm_dy_food * self.seeking_strength + random_dy * self.random_strength)

        # Normalize the final combined vector to maintain constant speed
        magnitude_final = math.sqrt(final_dx**2 + final_dy**2)
        if magnitude_final > 0:
            final_dx_normalized = final_dx / magnitude_final
            final_dy_normalized = final_dy / magnitude_final
        else: # Ant is at food and random choice was (0,0)
            final_dx_normalized = 0
            final_dy_normalized = 0


        self.x += final_dx_normalized * self.speed
        self.y += final_dy_normalized * self.speed
        
        # Clamp x and y to be integers for pixel positions
        self.x = int(self.x)
        self.y = int(self.y)
        self.rect.topleft = (self.x, self.y)

        # Obstacle Avoidance
        # Calculate intended movement for this frame
        intended_dx = final_dx_normalized * self.speed
        intended_dy = final_dy_normalized * self.speed

        next_x = self.x + intended_dx
        next_y = self.y + intended_dy
        
        potential_rect = self.rect.copy()
        potential_rect.x = next_x
        potential_rect.y = next_y

        collision_detected = False
        for obs in obstacles:
            if potential_rect.colliderect(obs.rect):
                collision_detected = True
                # Simple avoidance: try to reverse direction from obstacle
                # This is a very basic approach and can lead to getting stuck or jittering
                
                # Check collision with horizontal movement
                check_rect_hor = self.rect.copy()
                check_rect_hor.x += intended_dx
                if check_rect_hor.colliderect(obs.rect):
                    intended_dx *= -1 # Reverse horizontal component
                    # also add a small push away
                    if self.x < obs.rect.centerx: intended_dx -= self.speed * 0.5 
                    else: intended_dx += self.speed * 0.5


                # Check collision with vertical movement
                check_rect_vert = self.rect.copy()
                check_rect_vert.y += intended_dy
                if check_rect_vert.colliderect(obs.rect):
                    intended_dy *= -1 # Reverse vertical component
                     # also add a small push away
                    if self.y < obs.rect.centery: intended_dy -= self.speed * 0.5
                    else: intended_dy += self.speed * 0.5
                
                # If still colliding after trying to reverse (e.g. corner), then make a small random jump
                final_check_rect = self.rect.copy()
                final_check_rect.x += intended_dx
                final_check_rect.y += intended_dy
                if final_check_rect.colliderect(obs.rect):
                    intended_dx = random.choice([-self.speed, self.speed, 0])
                    intended_dy = random.choice([-self.speed, self.speed, 0])
                    if intended_dx == 0 and intended_dy == 0: intended_dx = self.speed # ensure some movement


        # Update position with (potentially modified) intended_dx, intended_dy
        self.x += intended_dx
        self.y += intended_dy
        
        # Clamp x and y to be integers for pixel positions
        self.x = int(self.x)
        self.y = int(self.y)
        
        # Bounce off screen edges (Boundary checks)
        if self.x <= 0:
            self.x = 0
        elif self.x + self.size >= SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.size
            
        if self.y <= 0:
            self.y = 0
        elif self.y + self.size >= SCREEN_HEIGHT:
            self.y = SCREEN_HEIGHT - self.size
        
        self.rect.topleft = (self.x, self.y)


    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)

# Food class
class Food:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH - 15) # Ensure food is fully visible
        self.y = random.randint(0, SCREEN_HEIGHT - 15) # Ensure food is fully visible
        self.size = 15
        self.color = (0, 255, 0)  # Green
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)

# Create a Food instance
food = Food()

# Create an Ant instance and pass the food to it
ant = Ant(food)

# Obstacle class
class Obstacle:
    def __init__(self):
        self.is_being_dragged = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.width = random.randint(20, 50)
        self.height = random.randint(20, 50)
        self.color = (100, 100, 100)  # Grey
        self.speed = random.randint(1, 3)

        # Determine spawn edge and initial position/direction
        edge = random.choice(['left', 'right', 'top', 'bottom'])
        if edge == 'left':
            self.x = -self.width # Spawn just off the left edge
            self.y = random.randint(0, SCREEN_HEIGHT - self.height)
            self.dx = self.speed # Move right
            self.dy = random.choice([-self.speed / 2, 0, self.speed / 2]) # Slight vertical movement
        elif edge == 'right':
            self.x = SCREEN_WIDTH # Spawn just off the right edge
            self.y = random.randint(0, SCREEN_HEIGHT - self.height)
            self.dx = -self.speed # Move left
            self.dy = random.choice([-self.speed / 2, 0, self.speed / 2])
        elif edge == 'top':
            self.x = random.randint(0, SCREEN_WIDTH - self.width)
            self.y = -self.height # Spawn just off the top edge
            self.dx = random.choice([-self.speed / 2, 0, self.speed / 2]) # Slight horizontal movement
            self.dy = self.speed # Move down
        else:  # bottom
            self.x = random.randint(0, SCREEN_WIDTH - self.width)
            self.y = SCREEN_HEIGHT # Spawn just off the bottom edge
            self.dx = random.choice([-self.speed / 2, 0, self.speed / 2])
            self.dy = -self.speed # Move up
        
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self):
        if not self.is_being_dragged:
            self.x += self.dx
            self.y += self.dy
            self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)

# Initialize obstacles list and spawn timer
obstacles = []
obstacle_spawn_time = 5000  # 5 seconds
last_obstacle_spawn = pygame.time.get_ticks()

# Game state
game_over = False
font = pygame.font.Font(None, 74) # Initialize font for game over message
score_font = pygame.font.Font(None, 50) # Font for the score
start_time = pygame.time.get_ticks()
score = None # Will store the final score

# Game loop
running = True
while running:
    # --------------------------------------------------------------------------
    # Event Handling
    # --------------------------------------------------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False  # Exit the game loop
        
        # Mouse events for dragging obstacles
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if not game_over:  # Only allow interaction if the game is active
                if event.button == 1:  # Left mouse button clicked
                    for obs in obstacles:
                        if obs.rect.collidepoint(event.pos):
                            obs.is_being_dragged = True
                            # Calculate offset from obstacle's top-left to mouse click position
                            obs.drag_offset_x = obs.x - event.pos[0]
                            obs.drag_offset_y = obs.y - event.pos[1]
                            break  # Drag only one obstacle at a time
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left mouse button released
                for obs in obstacles:
                    obs.is_being_dragged = False # Stop dragging all obstacles
        elif event.type == pygame.MOUSEMOTION:
            if not game_over:  # Only allow interaction if the game is active
                for obs in obstacles:
                    if obs.is_being_dragged:
                        # Update obstacle position based on mouse motion and initial offset
                        obs.x = event.pos[0] + obs.drag_offset_x
                        obs.y = event.pos[1] + obs.drag_offset_y
                        obs.rect.topleft = (int(obs.x), int(obs.y))

    # --------------------------------------------------------------------------
    # Game State Updates (only if game is not over)
    # --------------------------------------------------------------------------
    if not game_over:
        # Ant movement and behavior
        ant.update_movement(obstacles) # Ant reacts to food and obstacles

        # Check for ant-food collision (winning condition)
        if ant.rect.colliderect(food.rect):
            if not game_over:  # Ensure score is calculated only once
                score = (pygame.time.get_ticks() - start_time) / 1000.0
            game_over = True  # Set game over state

        # Obstacle spawning logic
        current_time = pygame.time.get_ticks()
        if current_time - last_obstacle_spawn > obstacle_spawn_time:
            obstacles.append(Obstacle())
            last_obstacle_spawn = current_time  # Reset spawn timer
        
        # Obstacle updates (movement and off-screen removal)
        for obstacle_obj in list(obstacles):  # Iterate over a copy for safe removal
            obstacle_obj.update()  # Update obstacle position (if not dragged)
            
            # Remove obstacles that have moved far off-screen
            if obstacle_obj.rect.right < -100 or \
               obstacle_obj.rect.left > SCREEN_WIDTH + 100 or \
               obstacle_obj.rect.bottom < -100 or \
               obstacle_obj.rect.top > SCREEN_HEIGHT + 100:
                obstacles.remove(obstacle_obj)

    # --------------------------------------------------------------------------
    # Drawing / Rendering
    # --------------------------------------------------------------------------
    # Clear screen (fill with white each frame)
    screen.fill((255, 255, 255))
    
    # Draw all active obstacles
    for obstacle_obj in obstacles:
        obstacle_obj.draw(screen)

    # Draw the ant and the food
    ant.draw(screen)
    food.draw(screen) # Food's draw method now uses self.rect

    # Display Game Over message and score if game is over
    if game_over:
        # Render "Game Over" text
        game_over_text_surface = font.render("Game Over", True, (200, 0, 0)) # Red color
        game_over_text_rect = game_over_text_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
        screen.blit(game_over_text_surface, game_over_text_rect)

        # Render final score if available
        if score is not None:
            score_display_text = f"Score: {score:.2f} seconds"
            score_surface = score_font.render(score_display_text, True, (0, 0, 150)) # Dark blue
            score_rect = score_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 50)) # Position below "Game Over"
            screen.blit(score_surface, score_rect)

    # Update the full display
    pygame.display.flip()

    # Maintain the desired frame rate (e.g., 60 FPS)
    clock.tick(60)

# Quit Pygame modules when the game loop ends
pygame.quit()
