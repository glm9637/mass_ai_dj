# Music Assistant AI DJ (Home Assistant Integration)

Music Assistant AI DJ (formerly YTM AI DJ) is a custom Home Assistant integration that acts as an automated, gapless DJ for your smart home. Powered by Google's Gemini LLM and the Music Assistant (MASS) engine, it dynamically curates and plays music in real-time based on a user-defined vibe and a scheduled energy curve. 

Because it leverages Music Assistant's universal search, this integration works automatically with Spotify, Apple Music, YouTube Music, Tidal, or even your local NAS—whichever providers you have linked to Music Assistant.

### Features

* **Plug-and-Play Setup:** No complex cookies or header scraping required. Simply paste your free Gemini API Key into the native Home Assistant integrations page.
* **Universal Provider Support:** Bypasses specific API limitations by feeding text searches directly into Music Assistant. If MASS can play it, the AI DJ can spin it.
* **Smart Local Queue Engine:** Operates entirely within your local network's memory. It monitors your active MASS queue every 30 seconds and seamlessly queries Gemini for the next track only when the music is about to run out.
* **Dynamic Energy Curves:** Adjusts its song selections based on the "party progress %" to naturally manage the energy of the room (e.g., warm-up, peak energy, cooldown).
* **Live History Syncing:** Watches the actual state of your smart speakers. If you manually skip a song or queue one up yourself, the AI DJ reads the live player data and updates its context instantly to prevent duplicates and hallucinations.
* **Party Management Dashboard:** A custom sidebar UI to create parties, select your target speakers, set vibes (e.g., "90s upbeat techno"), and schedule start/end times.

---

### Setup Requirements

**1. Music Assistant (Mandatory)**
This integration acts as the "brain," but Music Assistant acts as the "hands." You must have the [Music Assistant Home Assistant Integration](https://www.music-assistant.io/) installed, with at least one music provider (Spotify, YTM, etc.) configured.

**2. Gemini API Key**
You need a free API key from [Google AI Studio](https://aistudio.google.com/) to power the DJ's decision-making. 

---

### Installation (via HACS)

The easiest way to install this integration is through HACS (Home Assistant Community Store).

1. Open **HACS** in your Home Assistant sidebar.
2. Navigate to **Integrations**.
3. Click the three dots in the top right corner and select **Custom repositories**.
4. Paste the URL of this GitHub repository into the repository field.
5. Select **Integration** as the category and click **Add**.
6. Search for **Music Assistant AI DJ** in HACS, click it, and select **Download**.
7. **Restart Home Assistant** to apply the changes.

*(Alternatively, for manual installation, copy the `custom_components/mass_ai_dj` folder from this repository into your Home Assistant `custom_components/` directory and restart).*

---

### Configuration & Usage

1. Go to **Settings** -> **Devices & Services** -> **Add Integration** -> Search for **AI DJ**.
2. Paste your **Gemini API Key**.
3. Open the new **AI DJ** panel in your Home Assistant sidebar.
4. Create a new Party and set your desired vibe.
5. Select your target Music Assistant speaker from the dropdown (the list is strictly filtered to show only valid MASS players to prevent routing errors).
6. Click **Start AI DJ** and let the engine take over!

---

### Technologies Used

* **Home Assistant Core:** ConfigFlow, Data Store, WebSockets API, and native AIOHTTP.
* **Frontend:** Lit Elements with real-time WebSocket polling.
* **AI:** Google Gemini API (gemini-2.5-flash).
* **Music Engine:** Music Assistant (MASS) Universal Search & Queueing.