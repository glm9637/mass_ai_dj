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
 * @property {PartyStatus | null} [status] - What the DJ is currently doing (only for active parties)
 */

/**
 * @typedef {Object} PartyStatus
 * @property {string} message
 * @property {"info" | "warning" | "error"} level
 * @property {string} updated - ISO Date String
 * @property {string | null} [last_error] - Last error, kept until a song was played successfully
 * @property {string | null} [last_error_time] - ISO Date String
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
