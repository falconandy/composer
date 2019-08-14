"""Converts JSON representations of XML from the format used by Harpo990 to the format used by Polytropos."""
from datetime import datetime

def convert(json_in: dict) -> dict:
    _convert(json_in, "")
    return json_in

def _convert(json_in: dict, parent: str) -> (dict, dict):
    parent_dict = {}

    if isinstance(json_in, dict):
        for key in list(json_in.keys()):
            value = json_in[key]
            if isinstance(value, str) or isinstance(value, int) or isinstance(value, datetime):
                if key.startswith("@"):
                    parent_dict[parent + key] = value
                    del json_in[key]
                elif key == "_":
                    parent_dict[parent] = value
                    del json_in[key]
            elif isinstance(value, dict):
                _parent_dict = _convert(value, key)
                if value:
                    json_in[key] = value
                else:
                    del json_in[key]
                json_in.update(_parent_dict)
            elif isinstance(value, list):
                ret_list = []
                for el in value:
                    _convert(el, "")
                    ret_list.append(el)
                json_in[key] = ret_list
            else:
                raise TypeError

    return parent_dict
