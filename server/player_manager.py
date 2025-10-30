import json
import uuid
import time
from pathlib import Path
from server.logging_setup_server import get_logger
from core.galaxy.galaxy_map import *

log = get_logger("PlayerManager")


class Player:
    def __init__(self, player_id, name, token=None, home_system_id=None, last_seen=None, galaxy_path=None):
        self.id = player_id
        self.name = name
        self.token = token or str(uuid.uuid4())
        self.home_system_id = home_system_id
        self.last_seen = last_seen
        self.galaxy=None
        self.tiles_owned = set()
        self.army = []
        self.galaxy_path=galaxy_path

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "token": self.token,
            "home_system_id": self.home_system_id,
            "last_seen": self.last_seen,
            #Galaxy path is treated separately, see save_players function
        }

    @staticmethod
    def from_dict(data):
        return Player(
            player_id=data["id"],
            name=data["name"],
            token=data.get("token"),
            home_system_id=data.get("home_system_id"),
            last_seen=data.get("last_seen"),
            galaxy_path=data.get("galaxy_path", None)
        )


class PlayerManager:
    def __init__(self, save_path="players.json"):
        self.save_path = Path(save_path)
        self.players = {}
        self.load_players()

    # --------------------------
    # Persistence
    # --------------------------
    def load_players(self):
        if not self.save_path.exists():
            log.info("No player data found. Starting fresh.")
            self.players = {}
            return

        try:
            with open(self.save_path, "r") as f:
                data = json.load(f)
                for pid, pdata in data.items():
                    self.players[pid] = Player.from_dict(pdata)
            log.info(f"Loaded {len(self.players)} players from disk.")
            for pid, player in self.players.items():
                if hasattr(player, "galaxy_path") and os.path.exists(player.galaxy_path):
                    player.galaxy = GalaxyMap.from_file(player.galaxy_path)
                    log.debug(f"Loaded galaxy for player {player.name} at {player.galaxy_path}")
                else:
                    log.warning(f"No galaxy found for {player.name}, creating new one.")
                    player.galaxy = GalaxyMap(width=20, height=20, star_density=50, authoritative=True, protected=True, owner=player)
                    player.galaxy_path = f"data/galaxies/{player.id}.json"
                    player.galaxy.save_to_file(player.galaxy_path)
        except Exception as e:
            log.exception(f"Failed to load player data: {e}")
            self.players = {}

    def save_players(self):
        """
        Save all players to disk. Each player’s galaxy is saved separately to avoid
        bloating the main players.json file.
        """
        try:
            data = {}
            for pid, player in self.players.items():
                pdata = player.to_dict()

                # --- Determine galaxy path ---
                galaxy_path = getattr(player, "galaxy_path", None)
                if galaxy_path is None:
                    galaxy_path = f"data/galaxies/{pid}.json"
                    player.galaxy_path = galaxy_path
                    pdata["galaxy_path"] = galaxy_path
                else:
                    pdata["galaxy_path"] = galaxy_path

                # --- Save galaxy separately ---
                if getattr(player, "galaxy", None) is not None:
                    player.galaxy.save_to_file(galaxy_path)

                # --- Do NOT embed the galaxy in players.json ---
                if "galaxy" in pdata:
                    pdata.pop("galaxy", None)

                data[pid] = pdata

            # --- Save the players metadata file ---
            dir_path = os.path.dirname(self.save_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            log.debug(f"Saved {len(self.players)} players to {self.save_path} and their galaxies separately.")
        except Exception as e:
            log.exception(f"Failed to save player data: {e}")

    # --------------------------
    # Player management
    # --------------------------
    def get_or_create_player(self, token=None, name=None, galaxy_template=None):
        """
        Retrieve an existing player by token or create a new one.
        Automatically assigns a protected home system.
        """
        # 1️⃣ If reconnecting
        if token:
            for player in self.players.values():
                if player.token == token:
                    log.info(f"Reconnected player '{player.name}' ({player.id}) via token.")
                    if player.galaxy is not None :
                        return player

        # 2️⃣ Create new player
        player_id = str(uuid.uuid4())
        name = name or f"Player_{len(self.players) + 1}"
        player = Player(player_id, name)
        self.players[player_id] = player

        # 3️⃣ Assign a galaxy if provided
        log.debug("Generating new galaxy for new player")
        if galaxy_template:
            player.galaxy = GalaxyMap.from_dict(galaxy_template.to_dict())
            player.home_system_id = player.galaxy.global_id
            #don\t forget to set the protected and owner attribute
            log.info(f"Created new galaxy for player '{player.name}' from template")
            galaxy_path = f"saves/galaxies/{player.id}.json"
            player.galaxy.save_to_file(galaxy_path)
            player.galaxy_path = galaxy_path   
            log.debug(f"saved the galaxy to file at {galaxy_path}")
        
        else:
            player.galaxy = GalaxyMap.generate_for_player(player, protected=True)
            log.info(f"Created persistent galaxy for {player.name} from random")
            galaxy_path = f"saves/galaxies/{player.id}.json"
            player.galaxy.save_to_file(galaxy_path)
            player.galaxy_path = galaxy_path   
            log.debug(f"saved the galaxy to file at {galaxy_path}")

        self.save_players()
        return player

    def get_player_by_token(self, token):
        for player in self.players.values():
            if player.token == token:
                return player
        return None

    def get_player_by_id(self, player_id):
        return self.players.get(player_id)

    def all_players(self):
        return list(self.players.values())
