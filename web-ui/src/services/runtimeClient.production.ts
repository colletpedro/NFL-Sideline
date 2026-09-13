import { StaticNflDataClient } from "./staticDataClient";

export const dataClient = new StaticNflDataClient(window.fetch.bind(window));
