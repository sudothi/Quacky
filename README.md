<div align="center">

  <img src="assets/icon.ico" alt="Quack Assistant Logo" width="120" />

  # Quacky! - LoL Assistant

  ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
  ![Flet](https://img.shields.io/badge/Flet-UI-purple?style=for-the-badge)
  ![Status](https://img.shields.io/badge/Status-Undetected-success?style=for-the-badge)
  ![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

</div>

<div align="center">
  <a href="https://quacky-brown.vercel.app/#" target="_blank">
    <img src="https://img.shields.io/badge/Visitar_o_Site-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Visitar o Site" />
  </a>
</div>
<br />

<div align="center">
  <a href="https://www.figma.com/deck/Vnwd51szGdulh0wZrW8NIF/Sem-t%C3%ADtulo?node-id=1-45&scaling=min-zoom&content-scaling=fixed&page-id=0%3A1">
    <img src="https://i.imgur.com/T0VsdPW.png" alt="Ver Apresentação no Figma" width="100%">
  </a>
</div>

<br />

---

##  Features

###  Lobby & Game Automation
* **Auto Accept**
* **Strategic Instalock**
* **Auto Ban**
* **Camp Auto Joiner**
* **Instant Dodge**
* **Lobby Reveal**

###  Profile Customization
* **Background Changer**
* **Icon Changer**
* **Riot ID Changer**
* **Badge Manager**

###  Utility Tools
* **Chat Offline Mode**
* **UX Restart**
* **Friend List Cleaner**

---

##  Installation

### Prerequisites
* **Python 3.10** or higher.
* **League of Legends Client** must be running.

### Steps

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/sudothi/Quacky](https://github.com/sudothi/Quacky)
    cd Quacky
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the App**
    ```bash
    python main.py
    ```

---

## Building .exe

To create a standalone executable file (no Python required):

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```

2.  Run the build command:
    ```bash
    pyinstaller --noconfirm --onefile --windowed --icon="assets/icon.ico" --add-data "assets;assets" --name="Quacky!" main.py
    ```

3.  Find your app in the `dist/` folder.

---

##  Disclaimer

> **Educational Purpose Only:** This software is created for educational purposes to explore the LCU API. The developer is not responsible for any bans or penalties applied to your account. Use at your own risk.
>
> **Not Endorsed:** Quack Assistant is not endorsed by Riot Games and does not reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends.

---

<div align="center">
  Made with <b>Flet</b>
</div>

