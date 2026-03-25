export class ApiService {
  /** @type {import("types/home-assistant").HomeAssistant | null}; */
  #hass = null;

  /**
   * Updates the HomeAssistant instance.
   * @param {import("types/home-assistant").HomeAssistant} hass
   */
  updateHass(hass) {
    this.#hass = hass;
  }

  /**
   * Fetches all parties from the backend.
   * @returns {Promise<import("types/dto").Party[] | null>}
   */
  async fetchParties() {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return null;
    }
    try {
      const parties = await this.#hass.callWS({
        type: "mass_ai_dj/parties/get",
      });
      return parties || [];
    } catch (err) {
      console.error("Failed to fetch parties:", err);
    }
    return null;
  }

  /**
   * Fetches all media players from Music Assistant
   * @returns {Promise<import("types/dto").Player[] | null>}
   */
  async fetchMassPlayers() {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return null;
    }
    try {
      const players = await this.#hass.callWS({
        type: "mass_ai_dj/players/get",
      });
      return players || [];
    } catch (err) {
      console.error("Failed to fetch mass players:", err);
    }
    return null;
  }

  /**
   * Creates a new party with the given name.
   * @param {import("types/dto").CreatePartyData} party
   * @returns {Promise<import("types/dto").Party | null>} the newly created party, or null if creation failed
   */
  async createParty(party) {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return null;
    }
    if (!party.name.trim()) return null;
    try {
      const result = await this.#hass.callWS({
        type: "mass_ai_dj/parties/create",
        ...party,
      });
      return result;
    } catch (err) {
      console.error("Failed to create party:", err);
    }
    return null;
  }

  /**
   *  Updates the specified party with new data. Only include fields that should be updated.
   * @param {import("types/dto").UpdatePartyData} updates
   * @returns {Promise<import("types/dto").Party | null>} the updated party, or null if update failed
   */
  async updateParty(updates) {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return null;
    }
    try {
      const updatedParty = await this.#hass.callWS({
        type: "mass_ai_dj/parties/update",
        ...updates,
      });

      return updatedParty;
    } catch (err) {
      console.error("Failed to update party:", err);
    }
    return null;
  }

  /**
   * Deletes the specified party
   * @param {import("types/dto").DeletePartyData} party
   * @returns {Promise<{result: 'success'| 'error', error?: string}>}
   */
  async deleteParty(party) {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return { result: "error", error: "Home Assistant instance not set" };
    }
    try {
      const response = await this.#hass.callWS({
        type: "mass_ai_dj/parties/delete",
        ...party,
      });
      if (response.success) {
        return { result: "success" };
      }
      return { result: "error", error: response.error };
    } catch (err) {
      console.error("Failed to delete party:", err);
      if (err instanceof Error) {
        return { result: "error", error: err.message };
      }
      return { result: "error", error: "unknown error" };
    }
  }

  /**
   *  Removes a song from the party's history
   * @param {import("types/dto").RemoveFromHistoryData} dto
   * @returns {Promise<import("types/dto").Party | null>} the updated party, or null if update failed
   */
  async removeHistoryItem(dto) {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return null;
    }
    try {
      const updatedParty = await this.#hass.callWS({
        type: "mass_ai_dj/history/delete",
        ...dto,
      });
      return updatedParty;
    } catch (err) {
      console.error("Failed to remove history item:", err);
    }
    return null;
  }

  /**
   * Clears the play history for a party
   * @param {import("types/dto").ClearHistoryData} dto
   * @returns {Promise<import("types/dto").Party | null>} the updated party, or null if update failed
   */
  async clearHistory(dto) {
    if (!this.#hass) {
      console.error("Home Assistant instance not set in ApiService");
      return null;
    }
    try {
      const updatedParty = await this.#hass.callWS({
        type: "mass_ai_dj/history/clear",
        ...dto,
      });
      return updatedParty;
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
    return null;
  }
}
