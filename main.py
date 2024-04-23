import json
import os
import time
from datetime import datetime

import requests
import yaml


class Player:
    def __init__(self, steamid, personaname, uncertainty=-1):
        self.steamid = steamid
        self.data_file = f"{steamid}.json"
        self.uncertainty = uncertainty
        if not os.path.exists(self.data_file):
            data = {
                "steam_id": steamid,
                "persona_name": personaname,
                "game_sessions": [],
            }
            with open(self.data_file, "w") as file:
                json.dump(data, file, indent=4)

    def get_running_games(self):
        with open(self.data_file, "r") as file:
            games = json.load(file)["game_sessions"]
        return [g for g in games if g["offline_time"] == ""]

    def start_game(self, gameid, gameextrainfo):
        session = {
            "game_extra_info": gameextrainfo,
            "game_id": gameid,
            "online_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "offline_time": "",
            "uncertainty": self.uncertainty,
        }
        with open(self.data_file, "r") as file:
            data = json.load(file)
            if "game_sessions" not in data:
                data["game_sessions"] = []
            data["game_sessions"].append(session)
        with open(self.data_file, "w") as file:
            json.dump(data, file, indent=4)

    def stop_game(self, gameid):
        with open(self.data_file, "r") as file:
            data = json.load(file)

        for s in data["game_sessions"]:
            if s["game_id"] == gameid and s["offline_time"] == "":
                s["offline_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break

        with open(self.data_file, "w") as file:
            json.dump(data, file, indent=4)


class Peeker:
    def __init__(self, config_file="config.yaml"):
        config = yaml.safe_load(open(config_file, "r", encoding="utf-8"))
        self.update_interval = config["update_interval"]
        self.api_key = config["api_key"]
        self.steam_ids = config["steam_ids"]
        self.last_update = -1

    @property
    def uncertainty(self):
        return time.time() - self.last_update

    def get_players_gaming_status(self):
        if not self.steam_ids:
            return None
        elif len(self.steam_ids) == 1:
            api_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.api_key}&steamids={self.steam_ids[0]}"
        else:
            api_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.api_key}&steamids={','.join(str(id) for id in self.steam_ids)}"
        response = requests.get(api_url)
        if response.status_code == 200:
            self.last_update = time.time()
        try:
            players_data = response.json()["response"]["players"]
        except KeyError:
            players_data = []
        return players_data

    def run(self):
        while True:
            try:
                status = self.get_players_gaming_status()
                for s in status:
                    steamid = s["steamid"]
                    personaname = s["personaname"]
                    gameid = s.get("gameid", "")
                    gameextrainfo = s.get("gameextrainfo", "")

                    player = Player(steamid, personaname, self.uncertainty)
                    last_runnings = player.get_running_games()

                    if gameid and gameextrainfo is not None:
                        # If there are multiple running games, only the latest one will be reported
                        if gameid not in [r["game_id"] for r in last_runnings]:
                            player.start_game(gameid, gameextrainfo)
                        print(
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: User {steamid} ({personaname}) is playing game {gameid} ({gameextrainfo})."
                        )
                    else:
                        for r in last_runnings:
                            if r["game_id"] != gameid:
                                player.stop_game(r["game_id"])
                        print(
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: User {steamid} ({personaname}) is not playing any game."
                        )

                time.sleep(self.update_interval)

            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    pass
                else:
                    print(f"An error occurred: {e}")
                    raise


if __name__ == "__main__":
    peeker = Peeker()
    peeker.run()
