// @ts-check
import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit@3.3.2/index.js?module";
import { sharedStyles } from "../shared-style.js";

/** @typedef {import('../types/dto').VibeSessionUpdate} VibeSession */

export const VIBE_CHANGE_EVENT = "mass-ai-dj-vibe-change";

export class MassAiDjVibeCard extends LitElement {
  static get properties() {
    return {
      session: { type: Object },
    };
  }

  constructor() {
    super();
    /** @type {VibeSession} */
    this.session = { vibe: "", from_date: "", to_date: "" };
  }

  /**
   * Internal helper to dispatch the full updated session object.
   * @param {VibeSession} updatedSession
   */
  #dispatchChange(updatedSession) {
    this.dispatchEvent(
      new CustomEvent(VIBE_CHANGE_EVENT, {
        detail: updatedSession,
        bubbles: true,
        composed: true,
      }),
    );
  }

  /**
   * @param {string} val
   */
  _onVibeInput(val) {
    this.#dispatchChange({
      ...this.session,
      vibe: val,
    });
  }

  /**
   * @param {string} val
   */
  _onFromInput(val) {
    this.#dispatchChange({
      ...this.session,
      from_date: val,
    });
  }

  /**
   * @param {string} val
   */
  _onToInput(val) {
    this.#dispatchChange({
      ...this.session,
      to_date: val,
    });
  }

  render() {
    return html`
      <div class="vibe-card">
        <div class="vibe-main">
          <div class="form-group">
            <label>Vibe Description</label>
            <input
              type="text"
              .value=${this.session.vibe || ""}
              placeholder="e.g. Melodic Techno, sunset vibes..."
              @input=${(/** @type {{ target: { value: string; }; }} */ e) =>
                this._onVibeInput(e.target.value)}
            />
          </div>
        </div>

        <div class="vibe-times">
          <div class="form-group">
            <label>From</label>
            <input
              type="datetime-local"
              .value=${this.session.from_date || ""}
              @input=${(/** @type {{ target: { value: string; }; }} */ e) =>
                this._onFromInput(e.target.value)}
            />
          </div>
          <div class="form-group">
            <label>To</label>
            <input
              type="datetime-local"
              .value=${this.session.to_date || ""}
              @input=${(/** @type {{ target: { value: string; }; }} */ e) =>
                this._onToInput(e.target.value)}
            />
          </div>
        </div>

        <button
          class="remove-btn"
          @click=${() => this.dispatchEvent(new CustomEvent("remove"))}
        >
          &times;
        </button>
      </div>
    `;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        margin-bottom: 12px;
      }
      .vibe-card {
        display: flex;
        gap: 16px;
        align-items: flex-end;
        padding: 16px;
        background: var(--secondary-background-color, #f9f9f9);
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: var(--ha-card-border-radius, 8px);
        position: relative;
      }
      .vibe-main {
        flex: 2;
      }
      .vibe-times {
        flex: 3;
        display: flex;
        gap: 8px;
      }
      .form-group {
        display: flex;
        flex-direction: column;
        flex: 1;
      }
      .remove-btn {
        background: transparent;
        border: none;
        color: var(--error-color, #f44336);
        font-size: 24px;
        cursor: pointer;
        line-height: 1;
        padding: 0 4px;
        align-self: center;
      }
      .remove-btn:hover {
        color: #d32f2f;
      }

      @media (max-width: 600px) {
        .vibe-card {
          flex-direction: column;
          align-items: stretch;
        }
        .vibe-times {
          flex-direction: column;
        }
        .remove-btn {
          position: absolute;
          top: 8px;
          right: 8px;
        }
      }
    `
  ];
}

customElements.define("mass-ai-dj-vibe-card", MassAiDjVibeCard);
