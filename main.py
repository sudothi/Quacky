import flet as ft
from client_api import LeagueConnector
import threading
import webbrowser
import time
import math
from datetime import datetime
import os
import sys
import ctypes 

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

BG_COLOR = "#0f0f11"
GLASS_COLOR = "#0DFFFFFF"
GLASS_BORDER = "#1AFFFFFF"
NEON_RED = "#ff3b3b"
TEXT_MUTED = "#a1a1a6"
DIVIDER_COLOR = "#1AFFFFFF"
ITEMS_PER_PAGE = 48 

all_champions_list = []

def main(page: ft.Page):
    page.title = "Quacky!"
    page.bgcolor = ft.Colors.TRANSPARENT
    page.padding = 0
    page.spacing = 0
    
    page.window.width = 1100 
    page.window.height = 800
    page.window.resizable = True
    page.window.frameless = True 
    page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = True
    page.window.bgcolor = BG_COLOR

    try: page.window_icon = resource_path("icon.ico") 
    except: pass

    page.theme_mode = ft.ThemeMode.DARK
    api = LeagueConnector()

    main_content_area = ft.Ref[ft.Container]()
    txt_log = ft.Ref[ft.Column]()
    icon_auto_accept = ft.Ref[ft.IconButton]()
    icon_autojoin = ft.Ref[ft.IconButton]() 
    
    txt_status = ft.Text("Waiting Client...", color=TEXT_MUTED, size=12)
    txt_summoner = ft.Text("Loading...", size=24, weight="bold")
    txt_rank = ft.Text("...", color=NEON_RED, size=14)
    avatar_img = ft.Image(src="https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/29.jpg", width=80, height=80, border_radius=40, opacity=0.5)

    def GlassContainer(content, width=None, height=None, padding=20, expand=False):
        return ft.Container(
            content=content, width=width, height=height, padding=padding,
            bgcolor=GLASS_COLOR, border=ft.border.all(1, GLASS_BORDER),
            border_radius=24, blur=ft.Blur(15, 15, ft.BlurTileMode.MIRROR),
            expand=expand
        )

    def AddLog(message):
        now = datetime.now().strftime("%H:%M")
        if txt_log.current:
            try:
                txt_log.current.controls.insert(0, ft.Text(f"[{now}] {message}", size=12, color=TEXT_MUTED))
                if len(txt_log.current.controls) > 8: txt_log.current.controls.pop()
                txt_log.current.update()
            except: pass

    def ShowSnack(msg, color="green"):
        page.open(ft.SnackBar(ft.Text(msg), bgcolor=color))

    def build_custom_titlebar():
        def minimize(e): page.window.minimized = True; page.update()
        def maximize(e): 
            page.window.maximized = not page.window.maximized; page.update()
        def close_app(e): page.window.close()

        return ft.Container(
            content=ft.Row([
                ft.WindowDragArea(
                    ft.Container(
                        content=ft.Row([
                            ft.Text("Quacky!", weight="bold", size=14),
                        ]),
                        bgcolor=ft.Colors.TRANSPARENT, padding=10
                    ), expand=True
                ),
                ft.Row([
                    ft.IconButton(ft.Icons.REMOVE, on_click=minimize, icon_size=14, icon_color=TEXT_MUTED, tooltip="Minimize"),
                    ft.IconButton(ft.Icons.CROP_SQUARE, on_click=maximize, icon_size=14, icon_color=TEXT_MUTED, tooltip="Maximize"),
                    ft.IconButton(ft.Icons.CLOSE, on_click=close_app, icon_size=14, icon_color=NEON_RED, tooltip="Close"),
                    ft.Container(width=5)
                ], spacing=0)
            ]),
            bgcolor="#1AFFFFFF", height=40
        )

    class PaginationController:
        def __init__(self, all_items, grid_ref, page_txt_ref, prev_btn, next_btn, create_tile_func):
            self.all_items = all_items; self.filtered_items = all_items; self.grid_ref = grid_ref; self.page_txt_ref = page_txt_ref; self.prev_btn = prev_btn; self.next_btn = next_btn; self.create_tile_func = create_tile_func; self.current_page = 1; self.total_pages = 1; self.update_batch_memory()
        def update_total_pages(self): self.total_pages = math.ceil(len(self.filtered_items) / ITEMS_PER_PAGE) or 1
        def update_batch_memory(self):
            self.update_total_pages()
            if self.current_page > self.total_pages: self.current_page = self.total_pages
            if self.current_page < 1: self.current_page = 1
            start = (self.current_page - 1) * ITEMS_PER_PAGE
            batch = self.filtered_items[start:start + ITEMS_PER_PAGE]
            if self.grid_ref.current: self.grid_ref.current.controls = [self.create_tile_func(item) for item in batch]
        def get_initial_controls(self):
            start = (self.current_page - 1) * ITEMS_PER_PAGE
            batch = self.filtered_items[start:start + ITEMS_PER_PAGE]
            return [self.create_tile_func(item) for item in batch]
        def render_ui(self):
            try:
                if self.grid_ref.current and self.page_txt_ref.current:
                    self.page_txt_ref.current.value = f"Page {self.current_page} of {self.total_pages}"
                    self.prev_btn.current.disabled = (self.current_page == 1)
                    self.next_btn.current.disabled = (self.current_page == self.total_pages)
                    self.grid_ref.current.update(); self.page_txt_ref.current.update(); self.prev_btn.current.update(); self.next_btn.current.update()
            except: pass
        def next(self, e): 
            if self.current_page < self.total_pages: self.current_page += 1; self.update_batch_memory(); self.render_ui()
        def prev(self, e): 
            if self.current_page > 1: self.current_page -= 1; self.update_batch_memory(); self.render_ui()
        def filter(self, query):
            q = query.lower()
            self.filtered_items = self.all_items if not q else [i for i in self.all_items if q in str(i.get('id','')).lower() or q in str(i.get('name','')).lower() or q in str(i.get('title','')).lower()]
            self.current_page = 1; self.update_batch_memory(); self.render_ui()

    def create_autocomplete_field(label, on_select_callback, initial_enabled=True):
        selected_id = [None]; txt_ref = ft.Ref[ft.TextField](); suggestions_ref = ft.Ref[ft.Column](); switch_ref = ft.Ref[ft.Switch]()
        def on_change(e):
            t = e.control.value.lower(); s = []
            if t and all_champions_list:
                matches = [c for c in all_champions_list if t in c['name'].lower()]
                for m in matches[:4]:
                    def click(e, x=m): 
                        txt_ref.current.value = x['name']; selected_id[0] = x['id']
                        suggestions_ref.current.controls.clear(); suggestions_ref.current.update(); txt_ref.current.update()
                        on_select_callback(x['id'])
                    s.append(ft.Container(content=ft.Row([ft.Image(src=f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{m['id']}.png", width=20, height=20, border_radius=10), ft.Text(m['name'], size=12)]), padding=5, bgcolor="#1AFFFFFF", border_radius=5, on_click=click, ink=True))
            suggestions_ref.current.controls = s; suggestions_ref.current.update()
        return ft.Column([ft.Row([ft.Text(label, color=TEXT_MUTED, size=12), ft.Container(expand=True), ft.Switch(ref=switch_ref, value=initial_enabled, active_color=NEON_RED, scale=0.7) if not label.startswith("Primário") else ft.Container()], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.TextField(ref=txt_ref, hint_text="Search...", height=35, text_size=12, content_padding=10, border_color=DIVIDER_COLOR, on_change=on_change), ft.Column(ref=suggestions_ref, spacing=2)], spacing=5), txt_ref, switch_ref, selected_id

    def build_dashboard_view():
        profile_card = GlassContainer(height=220, content=ft.Row([avatar_img, ft.Container(width=20), ft.Column([txt_status, txt_summoner, txt_rank], alignment=ft.MainAxisAlignment.CENTER, spacing=5)], alignment=ft.MainAxisAlignment.START))
        logs_area = GlassContainer(expand=True, content=ft.Column([ft.Text("ACTIVITY LOG", size=12, weight="bold", color=TEXT_MUTED), ft.Divider(color=DIVIDER_COLOR), ft.Column(ref=txt_log, spacing=10)]))
        return ft.Column([ft.Text("Dashboard", size=30, weight="w900", font_family="Inter"), profile_card, logs_area], spacing=20, expand=True)

    def build_icons_view():
        loading = ft.Column([ft.ProgressRing(color=NEON_RED), ft.Text("Downloading assets...", color=TEXT_MUTED)], alignment=ft.MainAxisAlignment.CENTER, expand=True)
        grid_ref = ft.Ref[ft.GridView](); page_txt_ref = ft.Ref[ft.Text](); prev_btn = ft.Ref[ft.IconButton](); next_btn = ft.Ref[ft.IconButton]()
        def init_load():
            time.sleep(0.1)
            try:
                icons, err = api.get_all_summoner_icons()
                if err or not icons: 
                    if main_content_area.current: main_content_area.current.content = ft.Text(f"Error: {err}"); main_content_area.current.update()
                    return
                def create_tile(icon):
                    i_id = icon['id']; url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{i_id}.jpg"
                    def show_dialog(e):
                        def close_dlg(e): page.close(dlg)
                        def do_visual(e): api.change_icon_client_only(i_id); AddLog(f"Client Only: {i_id}"); close_dlg(None)
                        def do_real(e): 
                            if api.change_icon(i_id): AddLog(f"Global Change: {i_id}")
                            else: AddLog(f"Failed to change: {i_id}")
                            close_dlg(None)
                        dlg = ft.AlertDialog(title=ft.Text(f"Select Icon ID: {i_id}"), content=ft.Column([ft.Image(src=url, width=100, height=100, border_radius=50), ft.Text(icon.get('title', 'Untitled') or 'Untitled', size=12, color=TEXT_MUTED, text_align="center")], height=150, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), actions=[ft.TextButton("Cancel", on_click=close_dlg), ft.ElevatedButton("Client Only (Visual)", on_click=do_visual), ft.ElevatedButton("Global Change (Real)", bgcolor=NEON_RED, color="white", on_click=do_real)], actions_alignment=ft.MainAxisAlignment.CENTER)
                        page.open(dlg)
                    return ft.Container(content=ft.Image(src=url, border_radius=8, fit=ft.ImageFit.COVER), on_click=show_dialog, border_radius=8, padding=2, ink=True)
                pager = PaginationController(icons, grid_ref, page_txt_ref, prev_btn, next_btn, create_tile)
                initial_controls = pager.get_initial_controls()
                nav_bar = ft.Row([ft.IconButton(ref=prev_btn, icon=ft.Icons.CHEVRON_LEFT, on_click=pager.prev, disabled=True), ft.Text(ref=page_txt_ref, value=f"Page 1 of {pager.total_pages}", weight="bold"), ft.IconButton(ref=next_btn, icon=ft.Icons.CHEVRON_RIGHT, on_click=pager.next)], alignment=ft.MainAxisAlignment.CENTER)
                final = ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to_dashboard(None)), ft.Text("Icon Gallery", size=20, weight="bold")]), ft.TextField(hint_text="Search...", height=35, text_size=12, content_padding=10, border_color=DIVIDER_COLOR, on_change=lambda e: pager.filter(e.control.value)), ft.Container(content=ft.GridView(ref=grid_ref, controls=initial_controls, expand=True, runs_count=8, max_extent=80, spacing=10, run_spacing=10), expand=True), nav_bar], expand=True)
                if main_content_area.current: main_content_area.current.content = final; main_content_area.current.update()
            except: pass
        threading.Thread(target=init_load, daemon=True).start()
        return loading

    def build_background_changer_view():
        loading = ft.Column([ft.ProgressRing(color=NEON_RED), ft.Text("Loading...", color=TEXT_MUTED)], alignment=ft.MainAxisAlignment.CENTER, expand=True)
        grid_ref = ft.Ref[ft.GridView](); page_txt_ref = ft.Ref[ft.Text](); prev_btn = ft.Ref[ft.IconButton](); next_btn = ft.Ref[ft.IconButton]()
        def init_load():
            time.sleep(0.1)
            try:
                champs, err = api.get_all_champions_minimal()
                if not champs: 
                    if main_content_area.current: main_content_area.current.content = ft.Text(f"Error: {err}"); main_content_area.current.update()
                    return
                def create_tile(c):
                    url = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/{c['id']}.png"
                    return ft.Container(content=ft.Column([ft.Image(src=url, width=50, height=50, border_radius=25), ft.Text(c['name'], size=10, text_align="center", no_wrap=True)], alignment=ft.MainAxisAlignment.CENTER, spacing=5), bgcolor="#0DFFFFFF", border_radius=10, padding=10, on_click=lambda e: go_to_skins(c['id'], c['name'], c.get('alias', c['name'])), ink=True)
                pager = PaginationController(champs, grid_ref, page_txt_ref, prev_btn, next_btn, create_tile)
                initial_controls = pager.get_initial_controls()
                nav_bar = ft.Row([ft.IconButton(ref=prev_btn, icon=ft.Icons.CHEVRON_LEFT, on_click=pager.prev, disabled=True), ft.Text(ref=page_txt_ref, value=f"Page 1 of {pager.total_pages}", weight="bold"), ft.IconButton(ref=next_btn, icon=ft.Icons.CHEVRON_RIGHT, on_click=pager.next)], alignment=ft.MainAxisAlignment.CENTER)
                final = ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to_dashboard(None)), ft.Text("Profile Background", size=20, weight="bold")]), ft.TextField(hint_text="Search...", height=35, text_size=12, content_padding=10, border_color=DIVIDER_COLOR, on_change=lambda e: pager.filter(e.control.value)), ft.Container(content=ft.GridView(ref=grid_ref, controls=initial_controls, expand=True, runs_count=5, max_extent=100, spacing=10, run_spacing=10), expand=True), nav_bar], expand=True)
                if main_content_area.current: main_content_area.current.content = final; main_content_area.current.update()
            except: pass
        threading.Thread(target=init_load, daemon=True).start()
        return loading

    def build_skins_view(champ_id, champ_name, champ_alias):
        loading = ft.Column([ft.ProgressRing()], alignment=ft.MainAxisAlignment.CENTER, expand=True)
        def load_skins_async():
            time.sleep(0.1)
            try:
                skins = api.get_champion_skins(champ_id); grid_controls = []
                for skin in skins:
                    try: sn = skin['id'] % 1000; url = f"https://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champ_alias}_{sn}.jpg"
                    except: url = ""
                    grid_controls.append(ft.Container(content=ft.Image(src=url, border_radius=10, fit=ft.ImageFit.COVER, width=float("inf"), height=float("inf")), on_click=lambda e, s=skin['id']: api.set_profile_background(s) and ShowSnack(f"Background set: {s}"), tooltip=f"{skin['name']}", border=ft.border.all(1, "#1AFFFFFF"), border_radius=10, clip_behavior=ft.ClipBehavior.HARD_EDGE))
                grid = ft.GridView(controls=grid_controls, expand=True, runs_count=2, max_extent=300, child_aspect_ratio=1.7, spacing=10, run_spacing=10)
                final = ft.Column([ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: go_to_background(None)), ft.Text(f"{champ_name}", size=20, weight="bold")]), ft.Divider(color=DIVIDER_COLOR), grid], expand=True)
                if main_content_area.current: main_content_area.current.content = final; main_content_area.current.update()
            except: pass
        threading.Thread(target=load_skins_async, daemon=True).start()
        return loading

    def build_instalock_view():
        loading = ft.Column([ft.ProgressRing(color=NEON_RED)], alignment=ft.MainAxisAlignment.CENTER, expand=True); content = ft.Column(expand=True, visible=False) 
        pick1_id = [None]; pick2_id = [None]; pick3_id = [None]; ban_id = [None]
        def cb1(v): pick1_id[0]=v; 
        def cb2(v): pick2_id[0]=v; 
        def cb3(v): pick3_id[0]=v; 
        def cbb(v): ban_id[0]=v
        cp1, _, _, _ = create_autocomplete_field("Primary Pick", cb1, True)
        cp2, _, sp2, _ = create_autocomplete_field("Secondary Pick", cb2, False)
        cp3, _, sp3, _ = create_autocomplete_field("Tertiary Pick", cb3, False)
        cb, _, sb, _ = create_autocomplete_field("Auto Ban", cbb, False)
        def save(e):
            t = []
            if pick1_id[0]: t.append(pick1_id[0])
            if sp2.current.value and pick2_id[0]: t.append(pick2_id[0])
            if sp3.current.value and pick3_id[0]: t.append(pick3_id[0])
            api.update_instalock_preferences(bool(t), t if t else [None]*3)
            api.update_autoban_preferences(sb.current.value and bool(ban_id[0]), ban_id[0])
            AddLog("Config Saved."); ShowSnack("Instalock Updated!")
        def load():
            time.sleep(0.1)
            global all_champions_list
            if not all_champions_list:
                d, _ = api.get_all_champions_minimal()
                if d: all_champions_list = d
            loading.visible=False; content.visible=True; 
            if main_content_area.current: main_content_area.current.update()
        content.controls = [
            ft.Text("Strategic Instalock", size=24, weight="bold"), ft.Divider(color=DIVIDER_COLOR),
            ft.Row([GlassContainer(expand=True, content=ft.Column([ft.Text("Picks", weight="bold", color="green"), cp1, cp2, cp3], spacing=10)), GlassContainer(expand=True, content=ft.Column([ft.Text("Bans", weight="bold", color="red"), cb]))], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Container(height=20), ft.ElevatedButton("SAVE CONFIG", width=200, bgcolor=NEON_RED, color="white", on_click=save)]
        threading.Thread(target=load, daemon=True).start()
        return ft.Stack([loading, content])

    def build_tools_view():
        name_field = ft.TextField(label="Name", width=120, height=35, text_size=12); tag_field = ft.TextField(label="Tag", width=60, height=35, text_size=12)
        def save_riot_id(e): api.change_riot_id(name_field.value, tag_field.value); AddLog("ID Request Sent."); ShowSnack("ID Request Sent!")
        def set_badges(option): 
            if api.update_badges(option, 1): AddLog("Badges updated."); ShowSnack("Badges Updated!")
        def restart_ux(e): api.restart_ux(); AddLog("Restarting UX..."); ShowSnack("Restarting Client...")
        def show_del_friends(e):
            def w(): c, _ = api.remove_all_friends(); AddLog(f"Removed: {c}")
            dlg = ft.AlertDialog(title=ft.Text("Delete ALL Friends?"), actions=[ft.TextButton("Yes", on_click=lambda _: page.close(dlg) or threading.Thread(target=w, daemon=True).start())])
            page.open(dlg)
        return ft.Column([
            ft.Text("Advanced Tools", size=24, weight="bold"), ft.Divider(color=DIVIDER_COLOR),
            ft.Row([
                ft.Column([GlassContainer(content=ft.Column([ft.Text("Riot ID", weight="bold"), ft.Row([name_field, tag_field]), ft.ElevatedButton("Save", bgcolor=NEON_RED, color="white", on_click=save_riot_id)])),
                           GlassContainer(content=ft.Row([ft.Text("Chat Status", weight="bold"), ft.Switch(active_color=NEON_RED, value=True, on_change=lambda e: api.set_chat_status(e.control.value))]))], expand=True),
                ft.Column([GlassContainer(expand=True, content=ft.Column([ft.Text("Badges (Tokens)", weight="bold"), ft.Row([ft.ElevatedButton("Clear", on_click=lambda _: set_badges(1), expand=True), ft.ElevatedButton("Glitch", on_click=lambda _: set_badges(3), expand=True)])])),
                           GlassContainer(expand=True, content=ft.Column([ft.Text("Danger Zone", weight="bold", color=NEON_RED), ft.Row([ft.ElevatedButton("Restart UX", on_click=restart_ux, expand=True), ft.ElevatedButton("Nuke Friends", bgcolor="#550000", color="white", on_click=show_del_friends, expand=True)])]))], expand=True)
            ], vertical_alignment=ft.CrossAxisAlignment.START)
        ], expand=True)

    def go_to_dashboard(e): main_content_area.current.content = build_dashboard_view(); main_content_area.current.update()
    def go_to_background(e): main_content_area.current.content = build_background_changer_view(); main_content_area.current.update()
    def go_to_skins(c_id, c_name, c_alias): main_content_area.current.content = build_skins_view(c_id, c_name, c_alias); main_content_area.current.update()
    def go_to_instalock(e): main_content_area.current.content = build_instalock_view(); main_content_area.current.update()
    def go_to_tools(e): main_content_area.current.content = build_tools_view(); main_content_area.current.update()
    def go_to_icons(e): main_content_area.current.content = build_icons_view(); main_content_area.current.update()

    def toggle_auto_accept(e): s=not icon_auto_accept.current.selected; api.set_auto_accept(s); icon_auto_accept.current.selected=s; page.update()
    def toggle_autojoin(e): s=not icon_autojoin.current.selected; api.set_autojoin(s); icon_autojoin.current.selected=s; page.update()
    def action_dodge(e): api.dodge_lobby(); AddLog("Dodge."); ShowSnack("Dodge Executed!", "red")
    def action_reveal(e): n = api.reveal_lobby(); webbrowser.open(f"https://www.op.gg/multisearch/br?summoners={','.join([x.replace('#','-') for x in n])}") if n else None

    def update_client_info_once():
        if api.connect():
            data = api.get_summoner_data()
            if data:
                txt_summoner.value = data.get('gameName', ''); txt_status.value = "ONLINE"; txt_status.color = "greenAccent"; txt_rank.value = api.get_rank()
                avatar_img.src = f"https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{data.get('profileIconId', 29)}.jpg"; avatar_img.opacity = 1
                page.update()

    blob_red = ft.Container(width=400, height=400, bgcolor=NEON_RED, border_radius=200, left=-100, top=-50, opacity=0.3, shadow=ft.BoxShadow(blur_radius=150, color=NEON_RED, spread_radius=20))
    blob_gray = ft.Container(width=300, height=300, bgcolor="blueGrey900", border_radius=150, bottom=-50, right=-50, opacity=0.3, shadow=ft.BoxShadow(blur_radius=120, color="blueGrey900", spread_radius=10))

    sidebar = GlassContainer(width=90, content=ft.Column([
            ft.Container(height=30),
            ft.IconButton(ft.Icons.DASHBOARD, icon_color="white", tooltip="Dashboard", on_click=go_to_dashboard), ft.Divider(color=DIVIDER_COLOR, height=20),
            ft.IconButton(ref=icon_auto_accept, icon=ft.Icons.CHECK_CIRCLE_OUTLINE, selected_icon=ft.Icons.CHECK_CIRCLE, style=ft.ButtonStyle(color={"": TEXT_MUTED, "selected": NEON_RED}), tooltip="Auto Accept", on_click=toggle_auto_accept),
            ft.IconButton(ref=icon_autojoin, icon=ft.Icons.LINK, selected_icon=ft.Icons.LINK_OFF, style=ft.ButtonStyle(color={"": TEXT_MUTED, "selected": NEON_RED}), tooltip="Camp Auto Joiner", on_click=toggle_autojoin),
            ft.IconButton(ft.Icons.FLASH_ON, icon_color=TEXT_MUTED, tooltip="Dodge", on_click=action_dodge),
            ft.IconButton(ft.Icons.PEOPLE_OUTLINE, icon_color=TEXT_MUTED, tooltip="Reveal", on_click=action_reveal),
            ft.IconButton(ft.Icons.IMAGE, icon_color=TEXT_MUTED, tooltip="Profile Background", on_click=go_to_background),
            ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, icon_color=TEXT_MUTED, tooltip="Summoner Icons", on_click=go_to_icons), 
            ft.IconButton(ft.Icons.GPS_FIXED, icon_color=TEXT_MUTED, tooltip="Instalock/Ban", on_click=go_to_instalock),
            ft.IconButton(ft.Icons.BUILD, icon_color=TEXT_MUTED, tooltip="Tools", on_click=go_to_tools),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), expand=False)

    main_glass = GlassContainer(expand=True, content=ft.Container(ref=main_content_area, content=build_dashboard_view()))
    
    page.add(ft.Column([
        build_custom_titlebar(),
        ft.Container(
            content=ft.Stack([
                blob_red, blob_gray, 
                ft.Container(content=ft.Row([sidebar, ft.Container(content=main_glass, padding=30, expand=True)], expand=True), padding=20)
            ], expand=True), 
            expand=True, 
            bgcolor=BG_COLOR
        )
    ], spacing=0, expand=True))
    
    threading.Thread(target=lambda: [update_client_info_once() or time.sleep(5) for _ in iter(int, 1)], daemon=True).start()

if __name__ == "__main__":
    ft.app(target=main)
