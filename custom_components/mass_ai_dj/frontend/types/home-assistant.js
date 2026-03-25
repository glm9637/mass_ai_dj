/**
 * @typedef {Object} HassEntity
 * @property {string} entity_id
 * @property {string} state
 * @property {Object.<string, any>} attributes
 * @property {string} last_changed
 * @property {string} last_updated
 */

/**
 * @typedef {Object} HomeAssistant
 * @property {Object.<string, HassEntity>} states - Access any entity state
 * @property {Object} services - Available services
 * @property {Object} config - HA configuration
 * @property {string} language - User's language
 * @property {Object} themes - Theme information
 * @property {(domain: string, service: string, data?: object) => Promise<void>} callService - Call a service
 * @property {(msg: object) => Promise<any>} callWS - Call a websocket command
 */
