from model.tile_type import TileType
from model.tile import Tile

from model.position import Position


class TileMap:
    def __init__(self, tilemap_dict) -> None:
        self.map_height = tilemap_dict['mapHeight']
        self.map_width = tilemap_dict['mapWidth']
        self.tiles: list[list[Tile]] = []
        for row_list in tilemap_dict['tiles']:
            tile_row = []
            for tile in row_list:
                tile_row.append(Tile(tile))
            self.tiles.append(tile_row)

    def get_tile_xy(self, x: int, y: int) -> Tile:
        return self.tiles[y][x]

    def get_tile(self, pos: Position) -> Tile:
        return self.get_tile_xy(pos.x, pos.y)

    def valid_position(self, pos:Position) -> bool:
        return 0 <= pos.x < self.map_width and 0 <= pos.y < self.map_height

    def get_fertility_band_level(self, target_type: TileType = TileType.F_BAND_MID, search_direction: int = -1) -> int:
        """
        Returns the level of the target_type in the fertility band.

        :param: target_type: The type of tile to search for.
        :param: search_direction: The direction to search in. -1 is from the bottom up, 1 is from the top down.
        :return: The level of the target_type in the fertility band.
        """
        rows = list(enumerate(self.tiles))
        if search_direction == -1:
            rows.reverse()
        for y, row in rows:
            if row[0].type == target_type:
                return y
        return -1
