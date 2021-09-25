from enum import Enum
from networking.io import Logger
from game import Game
from api import game_util
from model.position import Position
from model.decisions.move_decision import MoveDecision
from model.decisions.action_decision import ActionDecision
from model.decisions.buy_decision import BuyDecision
from model.decisions.harvest_decision import HarvestDecision
from model.decisions.plant_decision import PlantDecision
from model.decisions.do_nothing_decision import DoNothingDecision
from model.tile_type import TileType
from model.item_type import ItemType
from model.crop_type import CropType
from model.upgrade_type import UpgradeType
from model.game_state import GameState
from model.player import Player
from api.constants import Constants

import random
import math

logger = Logger()
constants = Constants()


class BotMode(Enum):
    MOVING_TO_BAND = 1
    PLANTING = 2
    WAITING_FOR_PLANTS = 3
    HARVESTING = 4
    MOVING_TO_MARKET = 5
    BUYING = 6


class BotState:
    def __init__(self) -> None:
        self.has_visited_grocer = False
        self.waiting_for_plants = False
        self.target_crop = CropType.DUCHAM_FRUIT
        self.planted_crops: dict[Position, int] = {}
        self.mode = BotMode.MOVING_TO_MARKET

    def update_planted_crop_timers(self):
        for position, timer in self.planted_crops.items():
            self.planted_crops[position] = timer - 1


state: BotState = BotState()


def move_toward_tile(current: Position, target: Position, max_steps: int) -> Position:
    """
    Returns a position that is closer to the target position.
    """
    if current.distance(target) <= max_steps:
        return target
    else:
        direction = target-current
        new_direction = direction.clamp_magnitude(max_steps)
        target_pos = current + new_direction

        if target_pos.x > current.x:
            target_pos.x = math.floor(target_pos.x)
        else:
            target_pos.x = math.ceil(target_pos.x)
        if target_pos.y > current.y:
            target_pos.y = math.floor(target_pos.y)
        else:
            target_pos.y = math.ceil(target_pos.y)

        return target_pos


def in_range_of_duchams(game_state: GameState) -> bool:
    for harvest_pos in game_util.within_harvest_range(game_state, game_state.get_my_player()):
        if game_state.tile_map.get_tile(harvest_pos).crop.type == state.target_crop:
            return True
    return False


# Plus-shaped 5 tile area
def get_nearest_fertile_area(ideal_planting_pos: Position, my_player: Player, game: Game) -> Position:
    player_pos = my_player.position

    # Ensures a plus area can be planted on
    if ideal_planting_pos.y <= 3:
        ideal_planting_pos.y = 4
    elif ideal_planting_pos.y >= constants.BOARD_HEIGHT - 1:
        ideal_planting_pos.y = constants.BOARD_HEIGHT - 2

    min_distance = constants.BOARD_HEIGHT + constants.BOARD_WIDTH
    min_position = ideal_planting_pos
    relative_poses = [Position(-1, 0), Position(0, 0),
                      Position(1, 0), Position(0, -1), Position(0, 1)]
    for x in range(1, constants.BOARD_WIDTH - 1):
        is_x_unobstructed = True
        loc = Position(x, ideal_planting_pos.y)
        for pos in relative_poses:
            if is_unobstructed(loc + pos, game):
                continue
            is_x_unobstructed = False
        if is_x_unobstructed:
            distance = ideal_planting_pos.distance(Position(x, ideal_planting_pos.y))
            if distance < min_distance:
                min_distance = distance
                min_position = loc
    return min_position


def is_unobstructed(tile_pos: Position, game: Game) -> bool:
    if game.game_state.tile_map.get_tile(tile_pos).crop.type != "NONE":
        return False
    opponent_player = game.get_game_state().get_opponent_player()
    if tile_pos.distance(opponent_player.position) <= opponent_player.protection_radius:
        return False
    return True

def closest_market_position(pos: Position) -> Position:
    if pos.x in (13, 14, 15, 16, 17):
        target_x = pos.x
    else:
        target_x = sorted([13, pos.x, 17])[1]
    target_y = 0
    target_pos = Position(target_x, target_y)
    return target_pos


def get_move_decision(game: Game) -> MoveDecision:
    """
    Returns a move decision for the turn given the current game state.

    :param: game The object that contains the game state and other related information
    :returns: MoveDecision A location for the bot to move to this turn
    """
    state.update_planted_crop_timers()
    game_state: GameState = game.get_game_state()
    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position

    logger.debug(
        f"[Turn {game_state.turn}] Feedback received from engine: {game_state.feedback}")

    for _, timer in state.planted_crops.items():
        if timer <= 0:
            state.mode = BotMode.HARVESTING

    current_mode = state.mode
    logger.debug(f"Move stage mode: {current_mode}")

    market_dist = closest_market_position(pos).distance(pos)
    if market_dist / my_player.max_movement >= 179-game_state.turn:
        state.mode=BotMode.MOVING_TO_MARKET

    if current_mode == BotMode.MOVING_TO_MARKET:
        target_pos = closest_market_position(pos)
        decision_pos = move_toward_tile(
            pos, target_pos, my_player.max_movement)
        if decision_pos == target_pos:
            state.mode = BotMode.BUYING
        return MoveDecision(decision_pos)
    elif current_mode == BotMode.MOVING_TO_BAND or current_mode == BotMode.PLANTING:
        target_y = game_state.tile_map.get_fertility_band_level(
            target_type=TileType.F_BAND_MID, search_direction=-1)
        if target_y == -1:
            target_y = game_state.tile_map.get_fertility_band_level(
                target_type=TileType.F_BAND_OUTER, search_direction=-1)
            if target_y == -1:
                target_y = 4
        ideal_pos = Position(pos.x, target_y)
        target_pos = get_nearest_fertile_area(
            ideal_planting_pos=ideal_pos, my_player=my_player, game=game)
        decision_pos = move_toward_tile(
            pos, target_pos, my_player.max_movement)
        if decision_pos == target_pos and game_state.tile_map.get_tile(decision_pos).type.value>=TileType.F_BAND_OUTER.value:
            state.mode = BotMode.PLANTING
        return MoveDecision(decision_pos)
    elif current_mode == BotMode.HARVESTING:
        for position, timer in state.planted_crops.items():
            if timer > 0:
                continue
            target_pos = position
            decision_pos = move_toward_tile(
                pos, target_pos, my_player.max_movement)
            return MoveDecision(decision_pos)
        logger.debug(f"Error: In harvest mode with no timers set to 0")
        if len(state.planted_crops) > 0:
            state.mode = BotState.WAITING_FOR_PLANTS
        else:
            state.mode = BotState.MOVING_TO_MARKET
        return MoveDecision(pos)
    elif current_mode == BotMode.WAITING_FOR_PLANTS:
        min_timer = 100
        min_pos = pos
        for position, timer in state.planted_crops.items():
            if timer < min_timer:
                min_timer = timer
                min_pos = position
        max_dist = 0
        max_pos = pos
        for loc in game_util.within_move_range(game_state,my_player,min_pos):
            if loc.distance(min_pos)<=game_state.get_opponent_player().protection_radius:
                continue
            if loc.distance(pos)>=my_player.max_movement:
                continue
            if loc.distance(min_pos)>max_dist:
                max_dist = loc.distance(min_pos)
                max_pos = loc
        return MoveDecision(max_pos)
    else:
        logger.debug(f"Error: Invalid bot mode {current_mode}")
        return MoveDecision(pos)


def get_action_decision(game: Game) -> ActionDecision:
    """
    Returns an action decision for the turn given the current game state.

    There are multiple action decisions that you can return here: BuyDecision,
    HarvestDecision, PlantDecision, or UseItemDecision.

    :param: game The object that contains the game state and other related information
    :returns: ActionDecision A decision for the bot to make this turn
    """
    game_state: GameState = game.get_game_state()
    logger.debug(
        f"[Turn {game_state.turn}] Feedback received from engine: {game_state.feedback}")

    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position
    current_mode = state.mode
    logger.debug(f"Action stage mode: {current_mode}")
    seed_inventory = []
    for seed_type, count in my_player.seed_inventory.items():
        seed_inventory.extend([seed_type] * count)
    seeds = len(seed_inventory)

    if current_mode == BotMode.MOVING_TO_MARKET or current_mode == BotMode.MOVING_TO_BAND:
        logger.debug(f"Moving to market or band - No actions to take.")
        return DoNothingDecision()
    # Let the crop of focus be the one we have a seed for, if not just choose a random crop
    if my_player.money >= 1000:
        state.target_crop = CropType.GOLDEN_CORN
        logger.debug(f"Crop of focus: {state.target_crop}")

    if current_mode == BotMode.BUYING:
        if game_state.turn > 170:
            return DoNothingDecision()
        state.mode = BotMode.MOVING_TO_BAND
        return BuyDecision([state.target_crop], [min(my_player.carring_capacity,my_player.money // state.target_crop.get_seed_price())])
    elif current_mode == BotMode.PLANTING:
        all_possible_plant_locations = game_util.within_plant_range(game_state,my_player)
        logger.debug(f"how many locs: {len(all_possible_plant_locations)}")
        possible_plant_locations = []
        for loc in all_possible_plant_locations:
            if not is_unobstructed(loc, game):
                continue
            possible_plant_locations.append(loc)
        
        seeds_to_plant: list[CropType] = []
        chosen_plant_locations: list[Position] = []
        how_many_we_can_plant: int = min(seeds, len(possible_plant_locations))
        logger.debug(f"How many we can plant: {how_many_we_can_plant}, {len(possible_plant_locations)}")
        for i in range(how_many_we_can_plant):
            seeds_to_plant.append(seed_inventory[i])
            chosen_plant_locations.append(possible_plant_locations[i])
            state.planted_crops[pos] = seed_inventory[i].get_growth_time()+1
        if len(seeds_to_plant)==seeds:
            state.mode = BotMode.WAITING_FOR_PLANTS
        if how_many_we_can_plant==0:
            state.mode = BotMode.MOVING_TO_BAND
            return DoNothingDecision()
        logger.debug(f"Planting {len(seeds_to_plant)} seeds")
        return PlantDecision(seeds_to_plant, chosen_plant_locations)
    else:
        all_possible_harvest_locations = game_util.within_harvest_range(game_state,my_player)
        possible_harvest_locations = []
        for loc in all_possible_harvest_locations:
            if game_state.tile_map.get_tile(loc).is_harvestable_crop(logger):
                possible_harvest_locations.append(loc)
        if len(possible_harvest_locations) == 0:
            logger.debug(f"No crops to harvest")
            return DoNothingDecision()
        else:
            logger.debug(f"Harvesting {len(possible_harvest_locations)} crops")
            del state.planted_crops[pos]
            if len(state.planted_crops) == 0:
                if seeds == 0:
                    state.mode = BotMode.MOVING_TO_MARKET
                else:
                    state.mode = BotMode.PLANTING
            return HarvestDecision(possible_harvest_locations)


def main():
    """
    Competitor TODO: choose an item and upgrade for your bot
    """
    game = Game(ItemType.COFFEE_THERMOS, UpgradeType.LONGER_LEGS)

    while (True):
        try:
            game.update_game()
        except IOError:
            exit(-1)
        game.send_move_decision(get_move_decision(game))

        try:
            game.update_game()
        except IOError:
            exit(-1)
        game.send_action_decision(get_action_decision(game))


if __name__ == "__main__":
    main()
