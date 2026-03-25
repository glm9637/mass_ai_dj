import { LitElement, html } from "https://unpkg.com/lit@3.3.2/index.js?module";

import { sharedStyles } from "./shared-style.js";
import { ApiService } from "services/api-service.js";
import { DataService } from "services/data-service.js";

class MassAiDjPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      _selectedParty: { type: Object },
    };
  }

  static get styles() {
    return sharedStyles;
  }

  constructor() {
    super();
    const api = new ApiService();
    this.service = new DataService(api);
    /**
     * @type {import('./types/dto').Party | null}
     */
    this._selectedParty = null;

    /**
     * @type {import('./types/home-assistant.js').HomeAssistant | null}
     */
    this.hass = null;
  }

  /** @type {(() => void)[]} */
  #unsubs = [];

  connectedCallback() {
    super.connectedCallback();
    this.#unsubs = [
      this.service.registerSelectedPartyCallback((p) => {
        this._selectedParty = p;
      }),
    ];

    this.service.fetchParties();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#unsubs.forEach((unsub) => unsub());
  }

  /**
   *
   * @param {any} changedProps
   */
  updated(changedProps) {
    if (changedProps.has("hass") && this.hass) {
      this.service.updateHass(this.hass);
    }
  }

  firstUpdated() {
    this.service.fetchParties();
  }

  render() {
    if (!this.hass) {
      return html`<ha-circular-progress active></ha-circular-progress>`;
    }
    return html`
      <div class="app-container">
        <mass-ai-dj-sidebar .service=${this.service}></mass-ai-dj-sidebar>

        <main class="content">
          ${this._selectedParty
            ? html`<mass-ai-dj-party
                .service=${this.service}
              ></mass-ai-dj-party>`
            : html`<div class="welcome">Select a Party</div>`}
        </main>
      </div>
    `;
  }
}

customElements.define("mass-ai-dj-panel", MassAiDjPanel);
