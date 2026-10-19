// Creation Engine page: Matt's unmodified Eagle Homebrew editor inside the VTT.
// This file is the VTT counterpart of v13/module.ts. It replaces only the Foundry pieces around the editor:
// the world (Foundry: chosen at login) becomes a world selector, the Flight Control hub's "open" becomes the
// "Neu erstellen" button, and the sidebar directory with its "Edit with Eagle Homebrew" context entry becomes
// a document list. Opening an existing document runs module.ts's prepareEdit logic unchanged in substance.
import { installHost } from "./foundry-shim";
import { createHomebrewApplicationClass, type EditSession } from "@eagle/v13/homebrew-application";
import { currentRulesVersion } from "@eagle/core/creation-target";
import { allowedLibraryPacks, routeEditableDocument } from "@eagle/core/edit-routing";
import { executePairRetrofit, planPairRetrofit, type PairDocument, type PairPackState } from "@eagle/core/pair-retrofit";
import { valueAt } from "@eagle/core/edit-projection";
import { createVttContext, RestBackend, type DocumentName, type JsonObject, type StoredDocument } from "./vtt-context";
import translations from "@eagle/v13/lang/en.json";
import dnd5eConfig from "../data/dnd5e-config.en.json";
import baseItems from "../data/dnd5e-base-items.json";

interface World {
  id: string;
  label: string;
  kind: "personal" | "campaign";
}

const DOCUMENT_LABEL: Record<DocumentName, string> = { Actor: "Actors", Item: "Items", RollTable: "Roll Tables" };

const page = {
  worldSelect: document.getElementById("ce-world") as HTMLSelectElement,
  createButton: document.getElementById("ce-create") as HTMLButtonElement,
  worldList: document.getElementById("ce-world-documents") as HTMLElement,
  libraryList: document.getElementById("ce-library-documents") as HTMLElement,
  status: document.getElementById("ce-status") as HTMLElement,
  mount: document.getElementById("ce-eagle-mount") as HTMLElement,
};

let refreshTimer: number | undefined;
const backend = new RestBackend(
  () => page.worldSelect.value || "personal",
  () => {
    window.clearTimeout(refreshTimer);
    refreshTimer = window.setTimeout(() => void renderDirectory(), 250);
  },
);

function rememberWorld(id: string): void {
  try {
    localStorage.setItem("ce.world", id);
  } catch {
    /* storage may be unavailable; the selector still works for this visit */
  }
}

function rememberedWorld(): string | null {
  try {
    return localStorage.getItem("ce.world");
  } catch {
    return null;
  }
}

async function start(): Promise<void> {
  const auth = (window as unknown as { Auth: { makeAuthRequest(url: string): Promise<unknown> } }).Auth;
  const { worlds, rulesVersion } = (await auth.makeAuthRequest("/api/ce/authoring/worlds")) as { worlds: World[]; rulesVersion: "modern" | "legacy" };

  installHost({
    mount: page.mount,
    translations: translations as never,
    dnd5eConfig: dnd5eConfig as never,
    baseItems: baseItems as never,
    rulesVersion,
    // Foundry's GM gate: the server only resolves worlds this user leads, so whoever reaches the page is the GM.
    isGM: true,
    documentOptions: async (type) => {
      const { world, library } = await backend.list([type]);
      return [...world, ...library].map((entry) => ({ uuid: entry.uuid, name: entry.pack ? `${entry.name} (Library)` : entry.name }));
    },
    documentName: async (uuid) => (await backend.read(uuid).catch(() => undefined))?.name,
  });

  const params = new URLSearchParams(window.location.search);
  const requested = params.get("world") ?? rememberedWorld();
  page.worldSelect.replaceChildren(...worlds.map((world) => new Option(world.label, world.id)));
  page.worldSelect.value = worlds.some((world) => world.id === requested) ? requested! : "personal";
  page.worldSelect.addEventListener("change", () => {
    rememberWorld(page.worldSelect.value);
    void openWindow?.close();
    void renderDirectory();
  });

  const context = createVttContext(backend);
  const EagleHomebrewApplication = createHomebrewApplicationClass(context);
  type Window = { render(force: boolean): Promise<unknown>; close(): Promise<unknown> };
  let openWindow: Window | undefined;
  const show = (session?: EditSession): void => {
    void openWindow?.close();
    openWindow = new EagleHomebrewApplication(session) as unknown as Window;
    void openWindow.render(true);
  };

  page.createButton.addEventListener("click", () => show());

  // v13/module.ts `pairDocument`.
  const pairDocument = (entry: StoredDocument): PairDocument => {
    const pair = ((entry.source?.flags as JsonObject | undefined)?.["eagle-homebrew"] as JsonObject | undefined)?.pair as
      | { pack?: string; world?: string }
      | undefined;
    return { id: entry.uuid.split(".").pop()!, uuid: entry.uuid, documentName: entry.documentName, type: entry.type ?? undefined, ...(pair ? { pair } : {}) };
  };

  // v13/module.ts `readPackState`: every Library pack exists and is writable in the VTT.
  const readPackState = async (collection: string, documentName: string, id: string): Promise<PairPackState> => {
    const entry = await backend.read(`Compendium.${collection}.${documentName}.${id}`);
    return { collection, available: true, writable: true, ...(entry ? { entry: pairDocument(entry) } : {}) };
  };

  // v13/module.ts `prepareEdit`.
  const prepareEdit = async (uuid: string): Promise<EditSession | undefined> => {
    const world = await backend.read(uuid);
    if (!world?.source) throw new Error("The world document could not be read.");
    const entry = routeEditableDocument({ documentName: world.documentName, type: world.type ?? undefined, pack: null });
    if (!entry) return undefined;
    const worldSourceBefore = world.source;
    const id = pairDocument(world).id;
    const packs = await Promise.all(allowedLibraryPacks(entry).map((collection) => readPackState(collection, world.documentName, id)));
    const sourceRules = valueAt(worldSourceBefore, "system.source.rules");
    const hasSourceRules = sourceRules === "2014" || sourceRules === "2024";
    const rulesVersion = hasSourceRules ? sourceRules : currentRulesVersion(context.readRulesVersion);
    const planned = planPairRetrofit(entry, pairDocument(world), packs, rulesVersion, entry.versioned && !hasSourceRules);
    if (!planned.ok) throw new Error(`${planned.reason}: ${planned.detail}`);
    const result = await executePairRetrofit(context.sender, entry, pairDocument(world), planned);
    if (!result.ok) throw new Error(`${result.reason}: ${result.detail}`);
    const [librarySource, worldSource] = await Promise.all([context.readDocumentSource(result.libraryUuid), context.readDocumentSource(world.uuid)]);
    if (!librarySource || !worldSource) throw new Error("The paired documents could not be read after retrofit.");
    return { entry, worldUuid: world.uuid, libraryUuid: result.libraryUuid, pack: result.pack, fallbackUsed: planned.fallbackUsed, librarySource, worldSource };
  };

  // v13/module.ts `openExisting`.
  const openExisting = async (uuid: string): Promise<void> => {
    try {
      const session = await prepareEdit(uuid);
      if (session) show(session);
    } catch (error) {
      context.notify("error", (window as unknown as { game: { i18n: { format(k: string, d: Record<string, string>): string } } }).game.i18n.format(
        "EAGLEHOMEBREW.window.notify.editOpenFailed",
        { detail: error instanceof Error ? error.message : String(error) },
      ));
    }
  };

  directoryActions = { edit: openExisting, remove: removeDocument };
  await renderDirectory();
  const editUuid = params.get("edit");
  if (editUuid) await openExisting(editUuid);
}

let directoryActions: { edit(uuid: string): Promise<void>; remove(entry: StoredDocument): Promise<void> } | undefined;
// Delete confirmations that are open; they survive the directory refresh that follows any save.
const pendingDeletes = new Set<string>();

async function removeDocument(entry: StoredDocument): Promise<void> {
  pendingDeletes.add(entry.uuid);
  await renderDirectory();
}

function directoryGroup(entries: readonly StoredDocument[], editable: boolean): HTMLElement {
  const wrapper = document.createElement("div");
  if (entries.length === 0) {
    const empty = document.createElement("p");
    empty.className = "ce-empty";
    empty.textContent = editable ? "In dieser Welt gibt es noch keine Homebrew-Inhalte." : "Deine Bibliothek ist noch leer.";
    wrapper.append(empty);
    return wrapper;
  }
  for (const documentName of ["Item", "Actor", "RollTable"] as const) {
    const group = entries.filter((entry) => entry.documentName === documentName);
    if (group.length === 0) continue;
    const heading = document.createElement("h3");
    heading.textContent = DOCUMENT_LABEL[documentName];
    const list = document.createElement("ul");
    list.className = "ce-directory-list";
    for (const entry of group) {
      const item = document.createElement("li");
      item.dataset.uuid = entry.uuid;
      const label = document.createElement("span");
      label.className = "ce-directory-name";
      label.textContent = entry.name;
      const meta = document.createElement("span");
      meta.className = "ce-directory-meta";
      meta.textContent = [entry.type, entry.pack?.match(/-(2014|2024)$/)?.[1]].filter(Boolean).join(" · ");
      item.append(label, meta);
      if (editable) {
        const edit = document.createElement("button");
        edit.type = "button";
        edit.textContent = "Edit with Eagle Homebrew";
        edit.addEventListener("click", () => void directoryActions?.edit(entry.uuid));
        item.append(edit);
      }
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Löschen";
      remove.addEventListener("click", () => void directoryActions?.remove(entry));
      const confirmBox = document.createElement("span");
      confirmBox.className = "ce-confirm";
      confirmBox.hidden = !pendingDeletes.has(entry.uuid);
      const confirm = document.createElement("button");
      confirm.type = "button";
      confirm.className = "ce-danger";
      confirm.textContent = `„${entry.name}“ endgültig löschen`;
      confirm.addEventListener("click", () => {
        pendingDeletes.delete(entry.uuid);
        void backend.remove(entry.uuid);
      });
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "Abbrechen";
      cancel.addEventListener("click", () => {
        pendingDeletes.delete(entry.uuid);
        confirmBox.hidden = true;
      });
      confirmBox.append(confirm, cancel);
      item.append(remove, confirmBox);
      list.append(item);
    }
    wrapper.append(heading, list);
  }
  return wrapper;
}

async function renderDirectory(): Promise<void> {
  try {
    const { world, library } = await backend.list();
    page.worldList.replaceChildren(directoryGroup(world, true));
    page.libraryList.replaceChildren(directoryGroup(library, false));
    page.status.textContent = "";
  } catch (error) {
    page.status.textContent = `Die Inhalte konnten nicht geladen werden: ${error instanceof Error ? error.message : String(error)}`;
  }
}

void start().catch((error) => {
  page.status.textContent = `Die Creation Engine konnte nicht gestartet werden: ${error instanceof Error ? error.message : String(error)}`;
});
