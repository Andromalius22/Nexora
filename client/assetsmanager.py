import os
import json
import pygame
import time
from PIL import Image
from logger_setup import get_logger
from core.registry import REGISTRY

log = get_logger("assets")

# -------------------------------------------------------------------
# Animated Asset class (represents an animation, not a loader)
# -------------------------------------------------------------------
class AnimatedAsset:
    """Holds preloaded GIF frames and manages playback timing."""

    def __init__(self, frames, frame_duration=0.1):
        self.frames = frames
        self.frame_duration = frame_duration
        self.time_acc = 0.0
        self.index = 0

    def update(self, dt):
        """Advance the frame index based on delta time."""
        self.time_acc += dt
        if self.time_acc >= self.frame_duration:
            self.time_acc = 0
            self.index = (self.index + 1) % len(self.frames)

    def get_frame(self):
        """Return the current frame surface."""
        return self.frames[self.index]


# -------------------------------------------------------------------
# Asset Manager (handles all static + animated asset loading)
# -------------------------------------------------------------------
class AssetsManager:
    def __init__(self, base_path="", online_mode=False):
        self.assets = {}
        self.base_path = base_path
        self.online_mode = online_mode

    # ------------------------------
    # 🎞️ GIF Loader
    # ------------------------------
    def load_gif_as_frames(self, key, path, size=(128, 128), frame_duration=0.1):
        """Load an animated GIF into an AnimatedAsset."""
        start_time = time.time()

        if not os.path.exists(path):
            log.warning(f"[GIF Loader] ❌ Missing file: {path}")
            return None

        log.info(f"[GIF Loader] ⏳ Loading GIF '{key}' from '{path}'")

        try:
            img = Image.open(path)
        except Exception as e:
            log.error(f"[GIF Loader] ❌ Failed to open GIF '{path}': {e}")
            return None

        frames = []
        frame_count = 0

        try:
            while True:
                frame = img.copy().convert("RGBA")
                pygame_frame = pygame.image.fromstring(frame.tobytes(), frame.size, "RGBA")

                if size:
                    pygame_frame = pygame.transform.smoothscale(pygame_frame, size)

                frames.append(pygame_frame)
                frame_count += 1

                if frame_count % 10 == 0:
                    log.debug(f"[GIF Loader] Decoded {frame_count} frames from '{key}'...")
                img.seek(img.tell() + 1)

        except EOFError:
            pass  # End of GIF
        except Exception as e:
            log.exception(f"[GIF Loader] ⚠️ Error decoding '{key}': {e}")

        if not frames:
            log.warning(f"[GIF Loader] ⚠️ No frames found in '{path}'")
            return None

        duration_ms = (time.time() - start_time) * 1000
        log.info(f"[GIF Loader] ✅ Loaded '{key}' ({frame_count} frames, {frame_duration:.3f}s each) in {duration_ms:.1f} ms")

        animated_asset = AnimatedAsset(frames, frame_duration)
        self.assets[key] = animated_asset
        return animated_asset

    # ------------------------------
    # 🖼️ Static Image Loader
    # ------------------------------
    def load_image(self, key, path, size=(32, 32)):
        """Load and optionally scale a static image."""
        try:
            img = pygame.image.load(path).convert_alpha()
            log.debug(f"[AssetManager] Loaded image '{key}' from '{path}'.")
        except FileNotFoundError:
            log.warning(f"[AssetManager] Missing image '{path}' for key '{key}', using fallback.")
            try:
                img = pygame.image.load("client/assets/resources/question.png").convert_alpha()
            except FileNotFoundError:
                log.error("[AssetManager] Fallback image missing! Check 'assets/resources/question.png'.")
                return
        if size:
            img = pygame.transform.smoothscale(img, size)
            log.debug(f"[AssetManager] Scaled image '{key}' to {size}.")
        self.assets[key] = img

    # ------------------------------
    # 🔍 Getters
    # ------------------------------
    def get(self, key):
        """Retrieve a loaded asset (image or animated)."""
        return self.assets.get(key)

    # ------------------------------
    # 📦 Resource/Unit/Planet Loaders
    # ------------------------------
    def _load_from_json_file(self, filename):
        try:
            with open(filename) as f:
                return json.load(f)
        except FileNotFoundError:
            log.warning(f"JSON file not found: {filename}")
        except Exception as e:
            log.error(f"Error loading {filename}: {e}", exc_info=True)
        return []

    def _load_from_registry(self, category):
        return list(REGISTRY.get(category, {}).values())

    def _get_source_data(self, filename, registry_category):
        if self.online_mode and registry_category in REGISTRY:
            return self._load_from_registry(registry_category)
        else:
            return self._load_from_json_file(filename)

    # ------------------------------
    # 💎 Specific loaders (examples)
    # ------------------------------
    def load_resource_icons(self, filename="resources.json", registry_category="resources", default_size=(32, 32)):
        resources_data = self._get_source_data(filename, registry_category)
        if not resources_data:
            log.warning(f"[AssetManager] No resource data for '{registry_category}'.")
            return

        for entry in resources_data:
            if isinstance(entry, dict):
                resource_id = entry.get("id")
                icon_path = entry.get("resource_icon")
                icon_size = entry.get("icon_size", default_size)
            else:
                log.warning(f"[AssetManager] Unexpected format: {entry}")
                continue

            if not resource_id or not icon_path:
                log.warning(f"[AssetManager] Skipping invalid resource: {entry}")
                continue

            self.load_image(f"resource_{resource_id}", icon_path, size=icon_size)

    def load_planet_icons(self, size=(48, 48)):
        planets = self._get_source_data("data/planet_types.json", "planets")
        for planet in planets:
            planet_id = planet.get("id")
            icon_path = planet.get("icon")
            if not planet_id:
                continue
            if icon_path:
                self.load_image(f"planet_{planet_id}", icon_path, size)
            else:
                self.load_image(f"planet_{planet_id}", "assets/resources/question.png", size)
    
    # ------------------------------ # Resource-type loaders # ------------------------------
    def load_unit_icons(self, size=(48, 48)):
        units = self._get_source_data("data/defense_units.json", "defense_units")
        for unit in units: 
            name = unit.get("id") 
            icon_path = unit.get("icon") 
            if not name: 
                log.warning(f"No name for unit, continue.") 
                continue 
            if icon_path: 
                self.load_image(f"unit_{name}", icon_path, size) 
            else: 
                log.warning(f"No path defined for unit '{name}', using fallback.") 
                self.load_image(f"unit_{name}", "assets/resources/question.png", size)

    def load_icons_from_folder(self, folder="icons", size_map=None, recursive=True):
        folder_path = os.path.join(self.base_path, folder)
        size_map = size_map or {}
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg")):
                    name = os.path.splitext(file)[0]
                    full_path = os.path.join(root, file)
                    self.load_image(f"icon_{name}", full_path, size=size_map.get(name))
            if not recursive:
                break

    def load_all_icons(self):
        log.info(f"[AssetManager] Loading all game icons (online_mode={self.online_mode})...")
        self.load_unit_icons()
        self.load_planet_icons()
        self.load_resource_icons()
        size_overrides = { 
            "ore": (32,32), 
            "gas": (32,32), 
            "organics": (32,32), 
            "liquid": (32,32), 
            "plus": (18,18), 
            "plus_02": (18,18), 
            "moins": (18,18), 
            "hammer": (10,10),
            "science":(18, 18) } 
        self.load_icons_from_folder("assets/icons", size_map=size_overrides)
        log.info(f"[AssetManager] ✅ Loaded {len(self.assets)} total assets.")
