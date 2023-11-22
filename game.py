import arcade
import arcade.gui as gui

import json
import timeit

import code_input
import npc
import utils
import entities

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 563
SCREEN_TITLE = "Game"
LAYER_NAME_NPC = "Npc"
GRAVITY = 1.5
TILE_SIZE = 16

# Constants used to track if the player is facing left or right
RIGHT_FACING = 0
LEFT_FACING = 1


class Game(arcade.Window):
    """ Main application class. """

    def __init__(self, connection):
        """ Initializer for the game"""
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Our textboxes
        self.textbox = None
        self.show_textbox = False

        # gui manager to create and add gui elements
        self.manager = None

        # Set background color
        arcade.set_background_color(arcade.color.BEAU_BLUE)

        # Track the current state of what key is pressed
        self.enter_pressed = False
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.p_pressed = False

        # arcade_game.jump_needs_reset = False

        # Our TileMap Object
        self.tile_map = None

        # Our Scene Object
        self.scene = None

        # Create sprite lists here, and set them to None
        self.player_sprite = None
        self.npc_sprite = None
        self.walls_list = None

        # Our 'physics' engine
        self.physics_engine = None

        # A Camera that can be used for scrolling the screen
        self.camera = None

        # A Camera that can be used to draw GUI elements (menu, score)
        self.gui_camera = None

        # Keep track of the score
        self.score = 0

        # Do we need to reset the score?
        self.reset_score = True

        # Where is the right edge of the map?
        self.end_of_map = 0

        # Connection to kivy interface
        self.connection = connection

        # Screen resolution
        self.screen_resolution = (SCREEN_WIDTH, SCREEN_HEIGHT)

        # Default tile size
        self.tile_size = TILE_SIZE

        # Open save file
        with open('save.json', 'r') as read_save_file:
            self.save = json.loads(read_save_file.read())

        self.levels = {}

        # TODO add save & close somewhere ; save unsuppported as of today

        # Level data, loaded later on
        self.level_data = None

        # Load collisions with npc
        self.player_collision_list = None

        # Initialize fall timer, used for fall damage
        self.fall_timer = 0.
        self.show_timer = False     # If true, prints the timer at every update, useful for setting up levels

    def setup(self):
        """ Set up the game here. Call this function to restart the game."""

        # Set up the Cameras
        self.camera = arcade.Camera(self.width, self.height)
        self.gui_camera = arcade.Camera(self.width, self.height)

        # Reload level data

        # Reset positions available to precomputed values
        with open("assets/levels.json", "r") as read_levels_file:
            self.levels = json.loads(read_levels_file.read())

        self.level_data = self.levels[self.save["current_level"]]
        map_path = self.level_data["tilemap_path"]

        # Initialize map

        layer_options = {  # options specific to each layer
            "Platforms": {
                "use_spatial_hash": True,
            },
            "Background": {
                "use_spatial_hash": True,
            },
        }
        self.tile_map = arcade.load_tilemap(map_path, self.level_data["scaling"], layer_options)
        if self.tile_map.background_color:
            arcade.set_background_color(self.tile_map.background_color)

        # Gui elements
        self.manager = gui.UIManager()
        self.manager.enable()

        # reset button
        reset_button = gui.UIFlatButton(color=arcade.color.DARK_BLUE_GRAY, text='Reset level', width=100)
        reset_button.on_click = self.on_click_reset
        padd = gui.UIPadding(bg_color=arcade.color.APRICOT, child=reset_button, padding=(0.3, 0.3, 0.3, 0.3))
        self.manager.add(arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top", child=padd))

        # Initialize Scene
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        # End of map value
        self.end_of_map = 1000

        # Initialize Player Sprite
        image_source = "assets/characters/chara.png"
        self.player_sprite = entities.PlayerCharacter(image_source)
        self.player_sprite.scale = 1.2 * self.level_data["player_scaling"] * self.level_data["scaling"]
        self.player_sprite.center_x = self.level_data["spawn_x"]
        self.player_sprite.center_y = self.level_data["spawn_y"]

        # Initialize NPC sprite
        if self.level_data["name"] == "La super maisonnette":
            image_source = "assets/characters/npc_chara.png"
            self.npc_sprite = arcade.Sprite(image_source)
            self.npc_sprite.scale = 1.5
            self.npc_sprite.center_x = 740
            self.npc_sprite.center_y = 215
            self.scene.add_sprite("Npc", self.npc_sprite)

        self.scene.add_sprite("Player", self.player_sprite)
        self.scene.add_sprite_list("Walls", True, self.walls_list)

        # Blue tile showing the place_block() offset to the player
        if self.level_data["offset"] != -1:
            offset_block = arcade.Sprite("assets/tiled/tiles/Minecraft tiles/beacon.png")
            offset_block.width = offset_block.height = TILE_SIZE * self.level_data["scaling"]
            offset_block.left = self.level_data["offset"] * TILE_SIZE * self.level_data["scaling"]
            offset_block.bottom = 0
            self.scene["Background"].append(offset_block)

        # Keep track of the score, make sure we keep the score if the player finishes a level
        if self.reset_score:
            self.score = 0
        self.reset_score = True

        # Create the physics engine

        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, self.scene["Platforms"],
                                                             gravity_constant=GRAVITY)

    def on_draw(self):
        """ Render the screen. """

        # Clear the screen to the background color
        self.clear()

        # Activate the game camera
        self.camera.use()

        # Draw our Scene

        self.scene.draw()
        self.manager.draw()

        # Activate the GUI camera before drawing GUI elements
        self.gui_camera.use()

        # Indicate level number
        nb_level = f"Level: {self.levels[self.save['current_level']]['name']}"
        arcade.draw_text(nb_level, 10, 600, arcade.csscolor.WHITE, 18)

        # Draw the NPC textbox

        if self.show_textbox:
            self.textbox = npc.TextBox(400, 500, 700, 100,
                                       "Bienvenue dans cette demo pour apprendre les boucles en python ! ^^ "
                                       "\nUtilise la deuxième fenêtre ouverte pour faire apparaitre des éléments de "
                                       "décors !"
                                       "\nLa fonction place_block(x) fait tomber un bloc du ciel à la position x. "
                                       "Tu peux les empiler !"
                                       "\nUtilise les blocs du jeu comme repère pour placer les tiens ! ")
            self.textbox.show()

    def on_update(self, delta_time):
        """
        All the logic to move goes here.
        Normally, you'll call update() on the sprite lists that need it.
        """
        # Move the player with the physics engine
        self.physics_engine.update()

        # Update animations

        # Check if the player is (still) jumping
        if self.player_sprite.jumping:
            if self.physics_engine.can_jump():
                self.player_sprite.jumping = False
                # Has he fallen for too long ?
                # if max_fall_time == -1, it means the level has no fall damage
                if self.level_data["max_fall_time"] != -1 and self.fall_timer >= self.level_data['max_fall_time']:
                    self.setup()    # reset the level
                self.fall_timer = 0
            else:
                self.fall_timer += delta_time

        # TODO remove this
        if self.show_timer:
            print(self.fall_timer)

        # Did the player fall off the map?
        if self.player_sprite.center_y < -100:
            self.player_sprite.center_x = self.level_data["spawn_x"]
            self.player_sprite.center_y = self.level_data["spawn_y"]

        # See if the user got to the end of the level
        if self.player_sprite.center_x >= self.end_of_map:
            # Advance to the next level
            self.save["current_level"] += 1

            # Make sure to keep the score from this level when setting up the next level
            self.reset_score = False

            # Load the next level
            self.setup()

        # Check if kivy sent something
        if self.connection.poll():
            kivy_message = self.connection.recv()

            # The self parameter allows us to have access to the game object inside the function user_instructions
            res = code_input.user_instructions(self, kivy_message, [])
            if res:
                self.connection.send(res)

    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed."""

        if key == arcade.key.ENTER:
            self.enter_pressed = True
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True
        elif key == arcade.key.P:
            self.p_pressed = True

        self.process_keychange()

    def on_key_release(self, key, key_modifiers):
        """ Called whenever the user lets off a previously pressed key. """

        if key == arcade.key.ENTER:
            self.enter_pressed = False
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.P:
            self.p_pressed = False

        self.process_keychange()

    def process_keychange(self):
        """ Called when we change a key """

        # Process jump
        if self.up_pressed and not self.down_pressed:
            if self.physics_engine.can_jump(y_distance=10):
                self.player_sprite.change_y = self.level_data["player_jump_speed"]
                self.player_sprite.jumping = True

        # Process left/right
        if self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = (-self.level_data["player_movement_speed"] * self.level_data["scaling"])
        elif self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = (self.level_data["player_movement_speed"] * self.level_data["scaling"])
        else:
            self.player_sprite.change_x = 0

        if self.enter_pressed:
            if self.show_textbox:
                self.show_textbox = False
            elif npc.dist_between_sprites(self.player_sprite, self.npc_sprite) < 100:
                self.show_textbox = True

        if self.p_pressed:
            utils.save_free_slots(self)

    def on_click_reset(self, event):
        # garder coordonnées joueur
        self.setup()
