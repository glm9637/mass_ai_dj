import { PropertyHandler } from "./helper/property-handler";
import { PropertyStreamHandler } from "./helper/property-stream-handler";
/** @typedef {import('../types/dto.js').Party} Party */

/** @typedef {import('../types/dto.js').Player} Player */
/** @typedef {import('../types/home-assistant').HomeAssistant} HomeAssistant */

export class DataService {
  /** @type {import("services/api-service").ApiService}; */
  #apiService;

  #players = new PropertyHandler(/** @type {Player[]} */ ([]));

  /** @type {PropertyHandler<Party[]>} */
  #parties = new PropertyHandler(/** @type {Party[]} */ ([]));

  /** @type {PropertyHandler<Party| null> } */
  #selectedParty = new PropertyHandler(/** @type {Party | null} */ (null));

  /** @type {PropertyStreamHandler<string>} */
  #errors = new PropertyStreamHandler();

  /**
   * @param {import("services/api-service").ApiService} apiService
   */
  constructor(apiService) {
    this.#apiService = apiService;
  }

  /**
   * Updates the HomeAssistant instance.
   * @param {HomeAssistant} hass
   */
  updateHass(hass) {
    this.#apiService.updateHass(hass);
  }

  /**
   *
   * @param {Party} updatedParty
   * @returns
   */
  #updateSelectedParty(updatedParty) {
    const selectedParty = this.#selectedParty.value;
    if (!selectedParty) return;
    if (selectedParty.id === updatedParty.id) {
      this.#selectedParty.value = updatedParty;
    }
  }

  /**
   * Fetches the parties from the backend and updates all registered callbacks.
   */
  async fetchParties() {
    const parties = await this.#apiService.fetchParties();
    if (parties) {
      this.#parties.value = parties;
    } else {
      this.#errors.value = "Failed to fetch parties";
    }
  }

  /**
   * Fetches the media players from the backend and updates all registered callbacks.
   */
  async fetchMediaPlayers() {
    const players = await this.#apiService.fetchMassPlayers();
    if (!players) {
      this.#errors.value = "Failed to fetch media players";
      return;
    }
    this.#players.value = players;
  }

  /**
   * Fetches the media players from the backend.
   * @param {import("types/dto").CreatePartyData} party
   */
  async createParty(party) {
    const newParty = await this.#apiService.createParty(party);
    if (!newParty) {
      this.#errors.value = "Failed to create party";
      return;
    }
    await this.fetchParties();
    this.#selectedParty.value = newParty;
  }

  /**
   * Deletes the party with the given ID.
   * @param {string} partyId
   */
  async deleteParty(partyId) {
    if (
      !confirm(
        "Are you sure you want to delete this party? This action cannot be undone.",
      )
    ) {
      return;
    }
    const success = await this.#apiService.deleteParty({ party_id: partyId });
    if (!success) {
      this.#errors.value = "Failed to delete party";
      return;
    }
    if (this.#selectedParty.value && this.#selectedParty.value.id === partyId) {
      this.#selectedParty.value = null;
    }
    await this.fetchParties();
  }

  /**
   * Updates the party with the given data.
   * @param {import("types/dto").UpdatePartyData} data
   */
  async updateParty(data) {
    const updated = await this.#apiService.updateParty(data);
    if (!updated) {
      this.#errors.value = "Failed to update party";
      return;
    }
    await this.fetchParties();
    this.#updateSelectedParty(updated);
  }

  /**
   * Toggles the active status of the party with the given ID.
   * @param {string} partyId
   */
  async togglePartyActive(partyId) {
    const party = this.#parties.value.find((p) => p.id === partyId);
    if (!party) return;
    const updated = await this.#apiService.updateParty({
      party_id: partyId,
      active: !party.active,
    });
    if (!updated) {
      this.#errors.value = "Failed to update party status";
      return;
    }
    await this.fetchParties();
    this.#updateSelectedParty(updated);
  }

  /**
   * Removes a song from the party's history.
   * @param {string} partyId
   * @param {number} index
   */
  async removeFromHistory(partyId, index) {
    const updated = await this.#apiService.removeHistoryItem({
      party_id: partyId,
      index,
    });
    if (!updated) {
      this.#errors.value = "Failed to remove song from history";
      return;
    }
    await this.fetchParties();
    this.#updateSelectedParty(updated);
  }

  /**
   * Clears the history of the party with the given ID.
   * @param {string} partyId
   */
  async clearHistory(partyId) {
    if (
      !confirm(
        "Are you sure you want to clear the history? This action cannot be undone.",
      )
    ) {
      return;
    }
    const updated = await this.#apiService.clearHistory({ party_id: partyId });
    if (!updated) {
      this.#errors.value = "Failed to clear history";
      return;
    }
    await this.fetchParties();
    this.#updateSelectedParty(updated);
  }

  /** @param {string|null} partyId */
  selectParty(partyId) {
    if (!partyId) {
      this.#selectedParty.value = null;
      return;
    }
    const party = this.#parties.value.find((p) => p.id === partyId);
    this.#selectedParty.value = party || null;
  }

  /**
   * Registers a callback to be called whenever the media players are updated.
   * @param {(players: Player[]) => void} callback
   * @return {() => void} A function to unregister the callback
   */
  registerPlayersCallback(callback) {
    return this.#players.subscribe(callback);
  }

  /**
   * Registers a callback to be called whenever the parties are updated.
   * @param {(parties: Party[]) => void} callback
   * @return {() => void} A function to unregister the callback
   */
  registerPartyCallback(callback) {
    return this.#parties.subscribe(callback);
  }

  /**
   * Registers a callback to be called whenever an error occurs.
   * @param {(error: string) => void} callback
   * @return {() => void} A function to unregister the callback
   */
  registerErrorCallback(callback) {
    return this.#errors.subscribe(callback);
  }

  /**
   * Registers a callback to be called whenever the selected party is updated.
   * @param {(party: Party | null) => void} callback
   * @return {() => void} A function to unregister the callback
   */
  registerSelectedPartyCallback(callback) {
    return this.#selectedParty.subscribe(callback);
  }
}
