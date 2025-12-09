import psutil
import base64
import requests
import json
import time
import threading
import urllib3
import pyperclip

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LeagueConnector:
    def __init__(self):
        self.port = None
        self.password = None
        self.headers = {}
        self.session = requests.Session()
        self.connected = False
        self.base_url = ""
        
        self.auto_accept_active = False
        self.autojoin_active = False
        self.instalock_active = False
        self.instalock_targets = [None, None, None] 
        self.autoban_target = None
        self.autoban_active = False
        
        self.champions_cache = []
        self.icons_cache = []
        
        self._stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=self._background_loop, daemon=True)
        self.monitor_thread.start()
        self.autojoin_thread = threading.Thread(target=self._autojoin_loop, daemon=True)
        self.autojoin_thread.start()

    def connect(self):
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                if proc.info['name'] == 'LeagueClientUx.exe':
                    args = proc.info['cmdline']
                    for arg in args:
                        if '--app-port=' in arg:
                            self.port = arg.split('=')[1]
                        if '--remoting-auth-token=' in arg:
                            self.password = arg.split('=')[1]
                    
                    if self.port and self.password:
                        auth = base64.b64encode(f'riot:{self.password}'.encode()).decode()
                        self.headers = {
                            'Authorization': f'Basic {auth}',
                            'Content-Type': 'application/json'
                        }
                        self.base_url = f"https://127.0.0.1:{self.port}"
                        self.connected = True
                        return True
            self.connected = False
            return False
        except Exception:
            self.connected = False
            return False

    def request(self, method, endpoint, data=None):
        if not self.connected:
            if not self.connect(): return None
        url = f"{self.base_url}{endpoint}"
        try:
            res = self.session.request(method, url, headers=self.headers, json=data, verify=False)
            if res.status_code == 401: self.connect()
            return res
        except:
            self.connected = False
            return None

    def get_summoner_data(self):
        res = self.request('GET', '/lol-summoner/v1/current-summoner')
        return res.json() if res and res.status_code == 200 else None

    def get_rank(self):
        res = self.request('GET', '/lol-ranked/v1/current-ranked-stats')
        if res and res.status_code == 200:
            queues = res.json().get('queues', [])
            solo = next((q for q in queues if q['queueType'] == 'RANKED_SOLO_5x5'), None)
            if solo: return f"{solo['tier']} {solo['division']} - {solo['leaguePoints']} LP"
        return "Unranked"

    def get_all_champions_minimal(self):
        if self.champions_cache: return self.champions_cache, None
        try:
            url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-summary.json"
            res = requests.get(url)
            if res.status_code != 200: return [], f"Web Error: HTTP {res.status_code}"
            data = res.json()
            champs = [c for c in data if c['id'] != -1 and c['id'] < 2000]
            champs.sort(key=lambda x: x['name'])
            self.champions_cache = champs
            return champs, None
        except Exception as e:
            return [], f"Connection Error: {str(e)}"

    def get_all_summoner_icons(self):
        if self.icons_cache: return self.icons_cache, None
        try:
            url = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/summoner-icons.json"
            res = requests.get(url)
            if res.status_code != 200: return [], f"Web Error: HTTP {res.status_code}"
            data = res.json()
            data.sort(key=lambda x: x['id'], reverse=True)
            self.icons_cache = data
            return data, None
        except Exception as e:
            return [], f"Connection Error: {str(e)}"

    def get_champion_skins(self, champ_id):
        try:
            url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champions/{champ_id}.json"
            res = requests.get(url)
            if res.status_code == 200: return res.json().get('skins', [])
            return []
        except: return []

    def auto_accept_logic(self):
        check = self.request('GET', '/lol-lobby/v2/lobby/matchmaking/search-state')
        if check and check.status_code == 200:
            if check.json().get('searchState') == 'Found':
                self.request('POST', '/lol-matchmaking/v1/ready-check/accept')

    def champ_select_logic(self):
        session = self.request('GET', '/lol-champ-select/v1/session')
        if not session or session.status_code != 200: return
        data = session.json()
        local_cell_id = data.get('localPlayerCellId')
        forbidden_ids = []
        
        bans = data.get('bans', {}) or {}
        if bans:
            forbidden_ids.extend(bans.get('myTeamBans', []) or [])
            forbidden_ids.extend(bans.get('theirTeamBans', []) or [])
            forbidden_ids.extend(bans.get('numBans', []) or [])
            
        if 'myTeam' in data:
            for p in data['myTeam']:
                if p['championId'] != 0: forbidden_ids.append(p['championId'])
        if 'theirTeam' in data:
            for p in data['theirTeam']:
                if p['championId'] != 0: forbidden_ids.append(p['championId'])

        if 'actions' in data:
            for action_group in data['actions']:
                for action in action_group:
                    if action['actorCellId'] == local_cell_id and not action['completed']:
                        if action['type'] == 'pick' and self.instalock_active:
                            for target_id in self.instalock_targets:
                                if target_id and target_id not in forbidden_ids:
                                    self.request('PATCH', f"/lol-champ-select/v1/session/actions/{action['id']}", 
                                                 {"championId": target_id, "completed": True})
                                    return 
                        elif action['type'] == 'ban' and self.autoban_active and self.autoban_target:
                             self.request('PATCH', f"/lol-champ-select/v1/session/actions/{action['id']}", 
                                         {"championId": self.autoban_target, "completed": True})

    def change_icon(self, icon_id):
        res = self.request("PUT", "/lol-summoner/v1/current-summoner/icon", data={"profileIconId": int(icon_id)})
        return res.status_code == 201 or res.status_code == 200

    def change_icon_client_only(self, icon_id):
        res = self.request("PUT", "/lol-chat/v1/me", data={"icon": int(icon_id)})
        return res.status_code == 200 or res.status_code == 201

    def update_badges(self, option, specific_id=0):
        data = self.request("GET", "/lol-challenges/v1/summary-player-data/local-player").json()
        if not data: return False
        
        title_id = data.get("title", {}).get("itemId", -1)
        banner_id = data.get("bannerId", "")
        new_ids = []

        if option == 1: new_ids = []
        elif option == 3: new_ids = [specific_id] * 3

        payload = {"challengeIds": new_ids}
        if title_id != -1: payload["title"] = str(title_id)
        if banner_id: payload["bannerAccent"] = banner_id

        res = self.request("POST", "/lol-challenges/v1/update-player-preferences/", data=payload)
        return res.status_code in (200, 201, 204)

    def restart_ux(self):
        self.request("POST", '/riotclient/kill-and-restart-ux')

    def set_profile_background(self, skin_id):
        res = self.request('POST', '/lol-summoner/v1/current-summoner/summoner-profile', data={"key": "backgroundSkinId", "value": int(skin_id)})
        return res and res.status_code == 200

    def dodge_lobby(self):
        self.request('POST', '/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&args=["","teambuilder-draft","quitV2",""]')

    def reveal_lobby(self):
        session = self.request('GET', '/lol-champ-select/v1/session')
        if not session or session.status_code != 200: return []
        names = []
        data = session.json()
        if 'myTeam' in data:
            for player in data['myTeam']:
                if player.get('summonerId', 0) != 0:
                    summ_res = self.request('GET', f"/lol-summoner/v1/summoners/{player['summonerId']}")
                    if summ_res and summ_res.status_code == 200:
                        p_data = summ_res.json()
                        names.append(f"{p_data['gameName']}#{p_data['tagLine']}")
        return names

    def change_riot_id(self, name, tag):
        res = self.request("POST", "/lol-summoner/v1/save-alias", data={"gameName": name, "tagLine": tag})
        return res.status_code == 200 if res else False

    def set_chat_status(self, enabled: bool):
        if not enabled: res = self.request("POST", "/chat/v1/suspend", data={"config": "disable"})
        else: res = self.request("POST", "/chat/v1/resume", data={"config": "enable"})
        return res.status_code == 200 if res else False

    def remove_all_friends(self):
        res = self.request("GET", "/lol-friends/v1/friends")
        if not res or res.status_code != 200: return 0, "List Error"
        friends = res.json()
        count = 0
        for friend in friends:
            fid = friend.get("summonerId")
            del_res = self.request("DELETE", f"/lol-friends/v1/friends/{fid}")
            if del_res and del_res.status_code in [200, 204]: count += 1
            time.sleep(0.05)
        return count, None

    def set_auto_accept(self, active: bool): self.auto_accept_active = active
    def set_autojoin(self, active: bool): self.autojoin_active = active
    def update_instalock_preferences(self, enabled, targets):
        self.instalock_active = enabled
        self.instalock_targets = targets
    def update_autoban_preferences(self, enabled, target_id):
        self.autoban_active = enabled
        self.autoban_target = target_id

    def _background_loop(self):
        while not self._stop_event.is_set():
            if self.connected:
                if self.auto_accept_active: self.auto_accept_logic()
                if self.instalock_active or self.autoban_active: self.champ_select_logic()
            else: self.connect()
            time.sleep(0.5)

    def _autojoin_loop(self):
        last_clip = ""
        while not self._stop_event.is_set():
            if self.connected and self.autojoin_active:
                try:
                    clip = pyperclip.paste().strip()
                    if clip and clip != last_clip:
                        last_clip = clip
                        res = self.request("POST", f"/lol-lobby/v1/tournaments/{clip}/join")
                except: pass
            time.sleep(1)
