from typing import Dict
import math


class Position:
    def from_dict(self, pos_dict: Dict):
        self.x = pos_dict['x']
        self.y = pos_dict['y']
        return self

    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y

    def getpos(self, x, y):
        return x, y

    def __eq__(self, o: object) -> bool:
        if object is None:
            return False
        if not isinstance(o, Position):
            return False
        return self.x == o.x and self.y == o.y

    def __str__(self) -> str:
        return f"({self.x},{self.y})"

    def engine_str(self) -> str:
        return f"{int(self.x)} {int(self.y)}"

    def __sub__(self, other):
        return Position(self.x - other.x, self.y - other.y)
    
    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)
    
    def __mul__(self, other):
        return Position(self.x * other, self.y * other)

    def __truediv__(self, other):
        return Position(self.x / other, self.y / other)
    
    def distance(self, other):
        """
        Manhattan distance
        """
        return abs(self.x - other.x) + abs(self.y - other.y)

    def magnitude(self):
        return abs(self.x) + abs(self.y)
    
    def normalize(self):
        mag = self.magnitude()
        return Position(self.x / mag, self.y / mag)

    def round(self):
        return Position(int(self.x//1), int(self.y//1))
    
    def clamp_magnitude(self, max_magnitude):
        mag = self.magnitude()
        if mag > max_magnitude:
            return self.normalize() * max_magnitude
        return self

    def __hash__(self):
        return hash((self.x, self.y))
