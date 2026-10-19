// Matt's v13/homebrew-application.ts is written against Foundry's own type package, which the VTT does not ship.
// At runtime these globals come from src/foundry-shim.ts. ApplicationV2 is typed by that implementation, so the
// typecheck proves Matt's overrides fit the stand-in; the remaining Foundry surface stays untyped.
/* eslint-disable no-var, @typescript-eslint/no-explicit-any */
declare var foundry: {
  applications: { api: { ApplicationV2: typeof import("./foundry-shim").ApplicationV2 }; fields: any; elements: any };
  utils: any;
};
declare var game: any;
declare var CONFIG: any;
declare var ui: any;
