from typing import Type
import functools

class UniversalType():
    _type_map = {
        1: list,
        2: tuple,
        3: set,
        4: dict,
        5: int,
        6: float,
        7: str,
        8: bool,
        9: complex,
        10: bytes,
    }

    _reverse_type_map = {
        list: 1,
        tuple: 2,
        set: 3,
        dict: 4,
        int: 5,
        float: 6,
        str: 7,
        bool: 8,
        complex: 9,
        bytes: 10,
    }

    @functools.lru_cache()
    @staticmethod
    def get_type_int(type: int) -> Type:
        return UniversalType._type_map[type] if type in UniversalType._type_map else None

    @functools.lru_cache()
    @staticmethod
    def get_int(type: Type) -> int:
        return UniversalType._reverse_type_map[type] if type in UniversalType._reverse_type_map else None

    @functools.lru_cache()
    @staticmethod
    def is_container(type: int) -> bool:
        if type is not None:
            return type <= 4
        return False