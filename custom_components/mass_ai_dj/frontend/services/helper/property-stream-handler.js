/**
 * @template T
 * A helper class to manage a property with a value and an onChange callback.
 */
export class PropertyStreamHandler {
  /** @type {((newValue: T) => void)[]} */
  #onChange = [];

  /**
   * @param {T} newValue
   */
  set value(newValue) {
    this.#onChange.forEach((cb) => cb(newValue));
  }

  /**
   * Registers a callback to be called whenever the value is updated.
   * @returns {() => void} A function to unregister the callback
   * @param {(newValue: T) => void} callback
   */
  subscribe(callback) {
    this.#onChange.push(callback);
    return () => {
      this.#onChange = this.#onChange.filter((cb) => cb !== callback);
    };
  }
}
