// Spike entry: Matt's unmodified editor class on top of the Foundry shim and an in-memory backend.
import { installHost } from "./foundry-shim";
import { createHomebrewApplicationClass } from "@eagle/v13/homebrew-application";
import { createVttContext, MemoryBackend } from "./vtt-context";
import translations from "@eagle/v13/lang/en.json";
import dnd5eConfig from "../data/dnd5e-config.en.json";
import baseItems from "../data/dnd5e-base-items.json";

const backend = new MemoryBackend();
installHost({
  mount: document.getElementById("eh-mount")!,
  translations: translations as never,
  dnd5eConfig: dnd5eConfig as never,
  baseItems: baseItems as never,
  rulesVersion: "modern",
  isGM: true,
  documentOptions: async (type) => {
    const { world, library } = await backend.list([type]);
    return [...world, ...library].map((doc) => ({ uuid: doc.uuid, name: doc.name }));
  },
  documentName: async (uuid) => {
    const doc = await backend.read(uuid);
    return doc?.name;
  },
});
const EagleHomebrewApplication = createHomebrewApplicationClass(createVttContext(backend));
(window as unknown as Record<string, unknown>).__eagle = {
  backend,
  // Matt's class extends the shim's ApplicationV2; without Foundry's .d.ts the inherited render() is untyped here.
  open: () => (new EagleHomebrewApplication() as unknown as { render(force: boolean): Promise<unknown> }).render(true),
};
