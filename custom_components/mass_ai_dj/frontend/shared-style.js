import { css } from "https://unpkg.com/lit@3.3.2/index.js?module";

export const sharedStyles = css`
  * {
    box-sizing: border-box;
  }
  button.btn {
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, white);
    border: none;
    padding: 8px 16px;
    border-radius: var(--ha-card-border-radius, 4px);
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    font-family: var(--paper-font-body1_-_font-family, inherit);
    transition: background-color 0.2s, filter 0.2s;
  }
  button.btn:hover {
    filter: brightness(110%);
  }
  button.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  button.btn.danger {
    background: var(--error-color, #f44336);
  }
  button.btn.success {
    background: var(--success-color, #4caf50);
  }
  button.btn.secondary {
    background: transparent;
    color: var(--primary-color);
    border: 1px solid var(--primary-color);
  }
  button.btn.text {
    background: transparent;
    color: var(--primary-color);
    padding: 8px;
    border: none;
  }
  button.btn.text.danger {
    color: var(--error-color, #f44336);
  }
  
  input[type="text"],
  input[type="datetime-local"],
  select {
    width: 100%;
    padding: 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: var(--ha-card-border-radius, 4px);
    background: var(--card-background-color, #fff);
    color: var(--primary-text-color, #212121);
    font-size: 14px;
    font-family: inherit;
    margin-top: 4px;
  }
  input:focus, select:focus {
    outline: none;
    border-color: var(--primary-color);
  }

  .card {
    background: var(--ha-card-background, var(--card-background-color, #fff));
    padding: 16px;
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(
      --ha-card-box-shadow, 
      0px 2px 1px -1px rgba(0, 0, 0, 0.2), 
      0px 1px 1px 0px rgba(0, 0, 0, 0.14), 
      0px 1px 3px 0px rgba(0, 0, 0, 0.12)
    );
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, transparent);
    margin-bottom: 16px;
  }

  h1, h2, h3 {
    color: var(--primary-text-color, #212121);
    margin-top: 0;
    font-family: var(--paper-font-title_-_font-family, inherit);
  }
  p, span {
    color: var(--primary-text-color, #212121);
    font-family: var(--paper-font-body1_-_font-family, inherit);
    margin: 0;
  }
  label {
    color: var(--secondary-text-color, #727272);
    font-size: 12px;
    font-weight: 500;
  }
`;
