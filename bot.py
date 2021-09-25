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


class BotState:
    def __init__(self) -> None:
        self.has_visited_grocer = False
        self.waiting_for_plants = False


state = BotState()


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


# TODO: Move one turn from market (or similar for multiple turns)
def move_from_market(my_player: Player, game: Game) -> Position:
    player_pos = my_player.position
    if game.get_game_state().tile_map.get_tile(player_pos) == TileType.GREEN_GROCER:
        if my_player.player_num == 1:
            return player_pos + (-7, 3)
        else:
            return player_pos + (7, 3)
    else:
        return player_pos + move_toward_tile(player_pos, (15, 0), constants.MAX_MOVEMENT)


def get_move_decision(game: Game) -> MoveDecision:
    """
    Returns a move decision for the turn given the current game state.

    :param: game The object that contains the game state and other related information
    :returns: MoveDecision A location for the bot to move to this turn
    """
    game_state: GameState = game.get_game_state()
    logger.debug(
        f"[Turn {game_state.turn}] Feedback received from engine: {game_state.feedback}")

    # Select your decision here!
    my_player: Player = game_state.get_my_player()
    pos: Position = my_player.position
    logger.info(f"Currently at {my_player.position}")
    # logger.debug(f"LENGHTLENGHTLENGHTLENGHT: {len(my_player.harvested_inventory)}")
    # If we have something to sell that we harvested, then try to move towards the green grocer tiles
    if state.waiting_for_plants:
        logger.debug("Waiting for plants to grow")
        decision = MoveDecision(pos)
    elif (not state.has_visited_grocer) or (len(my_player.harvested_inventory) > 0 or game_state.turn > 174):
        logger.debug(f"Moving towards green grocer")
        pos = move_toward_tile(pos, Position(
            constants.BOARD_WIDTH // 2, 0), constants.MAX_MOVEMENT)
        decision = MoveDecision(pos)
    else:
        target_y = game_state.tile_map.get_fertility_band_level(
            TileType.F_BAND_INNER)
        if target_y != -1 and len(my_player.seed_inventory) > 0:
            logger.debug("Moving towards fertile band")
            pos = move_toward_tile(pos, Position(
                pos.x, target_y), constants.MAX_MOVEMENT)
            decision = MoveDecision(pos)
        else:
            logger.debug("Not moving")
            if game_state.turn < 5:
                decision = MoveDecision(Position(pos.x, 1))
            else:
                decision = MoveDecision(pos)

    logger.debug(f"[Turn {game_state.turn}] Sending MoveDecision: {decision}")
    return decision


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
    seeds = sum(my_player.seed_inventory.values())
    # Let the crop of focus be the one we have a seed for, if not just choose a random crop
    crop = CropType.DUCHAM_FRUIT

    # Get a list of possible harvest locations for our harvest radius
    possible_harvest_locations = []
    for harvest_pos in game_util.within_harvest_range(game_state, my_player.name):
        if game_state.tile_map.get_tile(harvest_pos).turns_left_to_grow == 0 \
                and game_state.tile_map.get_tile(harvest_pos).crop.value > 0:
            possible_harvest_locations.append(harvest_pos)

    # If we can harvest something, try to harvest it
    if len(possible_harvest_locations) > 0:
        state.waiting_for_plants = False
        return HarvestDecision(possible_harvest_locations)
    # If not but we have that seed, then try to plant it in an inner fertility band
    if game_state.tile_map.get_tile(pos).type.value > TileType.F_BAND_OUTER.value\
            and seeds > 0 and not state.waiting_for_plants:
        logger.debug(f"Deciding to try to plant at position {pos}")
        possible_plant_locations: list[Position] = [Position(0, 0), Position(
            1, 0), Position(-1, 0), Position(0, 1), Position(0, -1)]
        chosen_plant_locations: list[Position] = []
        for i in range(seeds):
            for j in possible_plant_locations:
                loc = pos + j
                if not game_state.tile_map.valid_position(loc) or game_state.get_opponent_player().position.distance(loc) < 3:
                    possible_plant_locations.remove(j)
                    continue
                if game_state.tile_map.get_tile(loc).type.value > TileType.F_BAND_OUTER.value:
                    chosen_plant_locations.append(loc)
                    possible_plant_locations.remove(j)
                    break
        state.waiting_for_plants = True
        return PlantDecision([crop]*len(chosen_plant_locations), chosen_plant_locations)

    if my_player.money >= crop.get_seed_price() and \
            game_state.tile_map.get_tile(pos).type == TileType.GREEN_GROCER:
        logger.debug(
            f"Buy as much as we can of {crop}")
        state.has_visited_grocer = True
        return BuyDecision([crop], [min(my_player.money // crop.get_seed_price(), 5-seeds)])

    logger.debug(f"Couldn't find anything to do, waiting for move step")
    return DoNothingDecision()


def main():
    """
    Competitor TODO: choose an item and upgrade for your bot
    """
    game = Game(ItemType.COFFEE_THERMOS, UpgradeType.SCYTHE)

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
