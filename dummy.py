from model.decisions.use_item_decision import UseItemDecision
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
        self.has_used_item = False
        self.is_using_coffee_thermos = False

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

def get_opponent_pos(game: Game) -> Position:
    opponent_player = game.get_game_state().get_opponent_player()
    return opponent_player.position

def get_distance_from_opponent(my_player: Player, game: Game) -> int:
    return my_player.position.distance(get_opponent_pos(game))

def get_move_decision(game: Game) -> MoveDecision:
    my_player = game.game_state.get_my_player()
    distance_from_opponent = get_distance_from_opponent(my_player, game)
    pos = my_player.position
    if (distance_from_opponent > my_player.max_movement):
        state.is_using_coffee_thermos = True  # TODO: Check if coffee thermos is already used
    pos = move_toward_tile(pos, get_opponent_pos(game), my_player.max_movement)
    decision = MoveDecision(pos)
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

    # Get a list of possible harvest locations for our harvest radius
    possible_harvest_locations = []
    for harvest_pos in game_util.within_harvest_range(game_state, my_player):
        if game_state.tile_map.get_tile(harvest_pos).turns_left_to_grow == 0 \
                and game_state.tile_map.get_tile(harvest_pos).crop.value > 0:
            possible_harvest_locations.append(harvest_pos)

    if state.is_using_coffee_thermos and not state.has_used_item:
        state.is_using_coffee_thermos = False
        state.has_used_item = True
        return UseItemDecision()

    # If we can harvest something, try to harvest it
    if len(possible_harvest_locations) > 0:
        state.waiting_for_plants = False
        return HarvestDecision(possible_harvest_locations)
    return DoNothingDecision()


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
