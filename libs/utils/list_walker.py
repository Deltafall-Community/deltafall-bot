from dataclasses import dataclass
from typing import Any, Dict, List, Type, Union
import itertools

@dataclass
class Child:
    parent_id: int
    value: Any
    type: Type

@dataclass
class Parent:
    parent_id: int
    id: int
    type: Type

def is_sequence(obj):
    return isinstance(obj, (list, tuple, set, dict)) and not isinstance(obj, (str, bytes, bytearray))

def walk(value, depth = -2, parent_id: int = 0, items: Dict[int, List[Union[Child, Parent]]] = None, counter: List[int] = None) -> Dict[int, List[Union[Child, Parent]]]:
    if items is None:
        items = {}
    if counter is None:
        counter = [0]

    depth += 1

    if is_sequence(value):
        current_id = counter[0]
        counter[0] += 1

        node = Parent(parent_id, current_id, type(value))
        if node.type is dict:
            value = tuple(itertools.chain.from_iterable(value.items()))

        if depth in items:
            items[depth].append(node)
        else:
            items[depth] = [node]
        
        for item in value:
            walk(item, depth, current_id, items, counter)
    else:
        node = Child(parent_id, value, type(value))
        if depth in items:
            items[depth].append(node)
        else:
            items[depth] = [node]
    
    return items