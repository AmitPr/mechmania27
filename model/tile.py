from model.player import Player
from model.crop_type import CropType
from model.item_type import ItemType
from model.tile_type import TileType
from model.crop import Crop
class Tile:
    def __init__(self, tile_dict) -> None:
        self.type = TileType[tile_dict['type']]
        self.crop = Crop(tile_dict['crop'])
        self.p1_item = ItemType[tile_dict['p1_item']]
        self.p2_item = ItemType[tile_dict['p2_item']]
        self.turns_left_to_grow = tile_dict['turnsLeftToGrow']
        self.rain_totem_effect = tile_dict['rainTotemEffect']
        self.fertility_idol_effect = tile_dict['fertilityIdolEffect']
        self.scarecrow_effect = tile_dict['scarecrowEffect']
    
    def is_harvestable_crop(self, logger) -> bool:
        if self.crop.type != "NONE" and self.crop.growth_timer <= 0:
            return True
        return False

    def has_scarecrow_effect(self, player_id: int) -> bool:
        return self.scarecrow_effect >= 0 and self.scarecrow_effect +1 !=player_id