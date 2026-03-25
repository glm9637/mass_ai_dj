/**
 * @typedef {Object} VibeSession
 * @property {string} vibe
 * @property {string} from_date - ISO Date String
 * @property {string} to_date - ISO Date String
 */

/**
 * @typedef {Object} Song
 * @property {string} title
 * @property {string} artist
 */

/**
 * @typedef {Object} Party
 * @property {string} id
 * @property {string} name
 * @property {boolean} active
 * @property {string|null} media_player_id
 * @property {VibeSession[]} sessions
 * @property {Song[]} history
 */

/**
 * @typedef {Object} Player
 * @property {string} entity_id
 * @property {string} name
 */

/**
 * @typedef {Object} MediaPlayer
 * @property {string} entity_id
 * @property {string} name
 */

/**
 * @typedef {Object} VibeSessionUpdate
 * @property {string} vibe
 * @property {string} from_date
 * @property {string} to_date
 */

/**
 * @typedef {Object} UpdatePartyData
 * @property {string} party_id
 * @property {VibeSessionUpdate[]} [sessions]
 * @property {string | null} [media_player_id]
 * @property {boolean} [active]
 */

/**
 * @typedef {Object} CreatePartyData
 * @property {string} name
 */

/**
 * @typedef {Object} DeletePartyData
 * @property {string} party_id
 */

/**
 * @typedef {Object} RemoveFromHistoryData
 * @property {string} party_id
 * @property {number} index
 */

/**
 * @typedef {Object} ClearHistoryData
 * @property {string} party_id
 */

export {};
