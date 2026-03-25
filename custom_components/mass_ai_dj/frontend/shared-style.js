import { css } from "https://unpkg.com/lit@3.3.2/index.js?module";

export const sharedStyles = css`
  button {
    background: var(--primary-color, #03a9f4);
    color: white;
    border: none;
    padding: 10px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }
  input[type="text"],
  input[type="datetime-local"] {
    width: 100%;
    padding: 10px;
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 4px;
  }
  .card {
    background: var(--card-background-color, #fff);
    padding: 24px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
`;
