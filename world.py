import json

class SpaceStructure:
    def __init__(self, id, name, hp, build_cost_credits, build_cost_resources, special_ability, description):
        self.id = id
        self.name = name
        self.hp = hp
        self.build_cost_credits = build_cost_credits
        self.build_cost_resources = build_cost_resources or {}
        self.special_ability = special_ability
        self.description = description

    @classmethod
    def from_dict(cls, data):
        return cls(
            data.get('id'),
            data.get('name'),
            data.get('hp'),
            data.get('build_cost_credits'),
            data.get('build_cost_resources'),
            data.get('special_ability'),
            data.get('description')
        )


def load_space_structures(filepath="space_structures.json"):
    with open(filepath, "r") as f:
        data = json.load(f)
    return [SpaceStructure.from_dict(entry) for entry in data]