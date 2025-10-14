import pygame
import os
import json

class AssetsManager:
    def __init__(self):
        self.assets = {}

    def load_image(self, key, path, size=None):
        try:
            img = pygame.image.load(path).convert_alpha()
        except FileNotFoundError:
            print(f"[AssetManager] Warning: Missing {path}, using fallback.")
            img = pygame.image.load("assets/resources/question.png").convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        self.assets[key] = img
    
    def load_animation(self, key, folder, size=None):
        frames = []
        for filename in sorted(os.listdir(folder)):
            if filename.endswith(".png"):
                path = os.path.join(folder, filename)
                img = pygame.image.load(path).convert_alpha()
                if size:
                    img = pygame.transform.scale(img, size)
                frames.append(img)
        self.assets[key] = frames  # list of frames

    def get(self, key):
        return self.assets.get(key)
    
    def load_resource_icons(self, resources_data, size=(32, 32)):
        for resource_name, resource_info in resources_data.items():
            # Base resource icon
            resource = resource_name
            icon_path = resource_info.get("resource_icon")
            if resource and icon_path:
                self.load_image(f"resource_{resource}", icon_path, size=size)
    
    def load_unit_icons(self, army_data, size=(48, 48)):
        for category, unit_dict in army_data.items():
            for unit_name in unit_dict:
                path = f"assets/units/{category.lower()}/{unit_name}.png"
                self.load_image(f"unit_{unit_name}", path, size)

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


def load_resources_data():
    with open("resources.json") as f:
        return json.load(f)

RESOURCES_DATA=load_resources_data()