/**
 * @template T
 * A helper class to manage a property with a value and an onChange callback.
 */
export class PropertyHandler {
  /** @type {T} */
  #value;
  /** @type {((newValue: T) => void)[]} */
  #onChange = [];

  /**
   * @param {T} initialValue
   */
  constructor(initialValue) {
    this.#value = initialValue;
  }

  set value(newValue) {
    this.#value = newValue;
    this.#onChange.forEach((cb) => cb(newValue));
  }

  /**
   * Registers a callback to be called whenever the value is updated.
   * @param {(newValue: T) => void} callback
   * @returns {() => void} A function to unregister the callback
   */
  subscribe(callback) {
    this.#onChange.push(callback);
    callback(this.#value);
    return () => {
      this.#onChange = this.#onChange.filter((cb) => cb !== callback);
    };
  }

  get value() {
    return this.#value;
  }
}
