// The VTT side of Eagle Homebrew's HomebrewWindowContext: the counterpart of v13/module.ts's
// `homebrewWindowContext`. Matt's editor talks to the outside world only through this object and through
// Flight Control's request contract (document.create, document.update, compendium.import), so the VTT
// implements that contract instead of Foundry + Flight Control. `DocumentBackend` is the seam: the Creation
// Engine page uses `RestBackend` (vtt/creation_engine/routes.py); the spike E2E uses `MemoryBackend`.
import type { JsonValue, RequestOutcome, RequestSender } from "@eagle/core/create-pair";
import type { HomebrewWindowContext } from "@eagle/v13/homebrew-application";
import type { CatalogEntry } from "@eagle/core/catalog";
import type { ActorReference, ActorResolutionResult } from "@eagle/core/actor-member-model";
import { CATALOG } from "@eagle/core/catalog";
import { shimNotify, shimRandomID } from "./foundry-shim";

export type JsonObject = Record<string, JsonValue>;
export type DocumentName = "Actor" | "Item" | "RollTable";

export interface StoredDocument {
  uuid: string;
  pack?: string | null;
  documentName: DocumentName;
  type?: string | null;
  name: string;
  source?: JsonObject;
}

export interface DocumentBackend {
  request(type: string, payload: JsonValue): Promise<RequestOutcome>;
  index(collection: string): Promise<readonly JsonObject[]>;
  read(uuid: string): Promise<StoredDocument | undefined>;
  list(documentNames?: readonly DocumentName[]): Promise<{ world: StoredDocument[]; library: StoredDocument[] }>;
  remove(uuid: string): Promise<void>;
}

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

// The document type a Library pack holds, from its collection id ("world.eagle-weapons-2024" -> Item).
export function packDocumentName(collection: string): DocumentName | undefined {
  const match = /^world\.eagle-([a-z]+)(?:-(?:2014|2024))?$/.exec(collection);
  return CATALOG.find((entry) => entry.key === match?.[1])?.worldType;
}

// ---- REST backend: vtt/creation_engine/routes.py ------------------------------------------------------------
interface AuthApi {
  makeAuthRequest(url: string, method?: string, body?: unknown): Promise<unknown>;
}
const auth = (): AuthApi => (window as unknown as { Auth: AuthApi }).Auth;

export class RestBackend implements DocumentBackend {
  constructor(private readonly world: () => string, private readonly onWrite: () => void = () => undefined) {}

  #query(params: Record<string, string | readonly string[]>): string {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      for (const entry of typeof value === "string" ? [value] : value) search.append(key, entry);
    }
    return search.toString();
  }

  async request(type: string, payload: JsonValue): Promise<RequestOutcome> {
    try {
      const outcome = (await auth().makeAuthRequest("/api/ce/authoring/request", "POST", { world: this.world(), type, payload })) as RequestOutcome | null;
      if (!outcome) return { ok: false, reason: "relay-failed", detail: "no response" };
      if (outcome.ok) this.onWrite();
      return outcome;
    } catch (error) {
      return { ok: false, reason: "relay-failed", detail: error instanceof Error ? error.message : String(error) };
    }
  }

  async index(collection: string): Promise<readonly JsonObject[]> {
    const result = (await auth().makeAuthRequest(`/api/ce/authoring/index?${this.#query({ pack: collection })}`)) as { index: JsonObject[] };
    return result.index;
  }

  async read(uuid: string): Promise<StoredDocument | undefined> {
    const result = (await auth().makeAuthRequest(`/api/ce/authoring/document?${this.#query({ world: this.world(), uuid })}`)) as { document: StoredDocument | null };
    return result.document ?? undefined;
  }

  async list(documentNames: readonly DocumentName[] = []): Promise<{ world: StoredDocument[]; library: StoredDocument[] }> {
    return (await auth().makeAuthRequest(`/api/ce/authoring/documents?${this.#query({ world: this.world(), documentName: documentNames })}`)) as {
      world: StoredDocument[];
      library: StoredDocument[];
    };
  }

  async remove(uuid: string): Promise<void> {
    await auth().makeAuthRequest(`/api/ce/authoring/document?${this.#query({ world: this.world(), uuid })}`, "DELETE");
    this.onWrite();
  }
}

// ---- In-memory backend (spike/E2E without a server) ---------------------------------------------------------
// Same rules as the server: each dotted path's value is replaced, "-=" deletes, ids are idempotent.
export function applyUpdate(source: JsonObject, changes: JsonObject): string[] {
  const changed: string[] = [];
  for (const [path, value] of Object.entries(changes)) {
    const parts = path.split(".");
    const last = parts.pop()!;
    let node: JsonObject = source;
    for (const part of parts) {
      if (!node[part] || typeof node[part] !== "object" || Array.isArray(node[part])) node[part] = {};
      node = node[part] as JsonObject;
    }
    if (last.startsWith("-=")) delete node[last.slice(2)];
    else node[last] = clone(value);
    changed.push(path);
  }
  return changed;
}

export class MemoryBackend implements DocumentBackend {
  readonly documents = new Map<string, StoredDocument & { source: JsonObject }>();

  #put(uuid: string, pack: string | undefined, documentName: DocumentName, source: JsonObject): void {
    this.documents.set(uuid, { uuid, pack, documentName, type: (source.type as string) ?? null, name: String(source.name), source });
  }

  async request(type: string, payload: JsonValue): Promise<RequestOutcome> {
    const body = payload as JsonObject;
    if (type === "document.create") {
      const target = body.target as { pack?: string; world?: DocumentName };
      const id = String(body.id);
      const documentName = target.pack ? packDocumentName(target.pack) : target.world;
      if (!documentName) return { ok: false, reason: "invalid-payload", detail: `unknown target ${JSON.stringify(target)}` };
      const uuid = target.pack ? `Compendium.${target.pack}.${documentName}.${id}` : `${documentName}.${id}`;
      if (this.documents.has(uuid)) return { ok: true, value: { created: false, uuid } };
      this.#put(uuid, target.pack, documentName, { ...clone(body.data as JsonObject), _id: id });
      return { ok: true, value: { created: true, uuid } };
    }
    if (type === "document.update") {
      const stored = this.documents.get(String(body.uuid));
      if (!stored) return { ok: false, reason: "invalid-payload", detail: `no document ${String(body.uuid)}` };
      const changes = body.changes as JsonObject;
      if (Object.keys(changes).length > 50) return { ok: false, reason: "invalid-payload", detail: "more than 50 paths" };
      const changed = applyUpdate(stored.source, changes);
      stored.name = String(stored.source.name);
      return { ok: true, value: { changed } };
    }
    if (type === "compendium.import") {
      const pack = String(body.pack);
      const created: JsonObject[] = [];
      const existed: JsonObject[] = [];
      for (const raw of body.sources as JsonObject[]) {
        const world = this.documents.get(String(raw.source));
        if (!world) return { ok: false, reason: "invalid-payload", detail: "world document not found" };
        const uuid = `Compendium.${pack}.${world.documentName}.${String(raw.id)}`;
        if (this.documents.has(uuid)) {
          existed.push({ uuid });
          continue;
        }
        const source = clone(world.source);
        if (raw.changes) applyUpdate(source, raw.changes as JsonObject);
        this.#put(uuid, pack, world.documentName, source);
        created.push({ uuid });
      }
      return { ok: true, value: { created, existed } };
    }
    return { ok: false, reason: "unknown-request", detail: type };
  }

  async index(collection: string): Promise<readonly JsonObject[]> {
    return [...this.documents.values()]
      .filter((document) => document.pack === collection)
      .map((document) => ({ _id: document.source._id, name: document.name, type: document.type ?? null, requirements: (document.source.system as JsonObject | undefined)?.requirements ?? null }));
  }

  async read(uuid: string): Promise<StoredDocument | undefined> {
    const stored = this.documents.get(uuid);
    return stored ? clone(stored) : undefined;
  }

  async list(documentNames: readonly DocumentName[] = []): Promise<{ world: StoredDocument[]; library: StoredDocument[] }> {
    const rows = [...this.documents.values()].filter((document) => documentNames.length === 0 || documentNames.includes(document.documentName));
    return { world: rows.filter((row) => !row.pack), library: rows.filter((row) => row.pack) };
  }

  async remove(uuid: string): Promise<void> {
    this.documents.delete(uuid);
  }
}

// ---- HomebrewWindowContext (v13/module.ts `homebrewWindowContext`) -----------------------------------------
const idOf = (uuid: string): string => uuid.split(".").pop() ?? uuid;

// module.ts `actorLibraryCollections`.
const actorLibraryCollections = (type: string): readonly string[] => {
  if (type === "npc") return ["world.eagle-npcs-2014", "world.eagle-npcs-2024"];
  if (type === "vehicle") return ["world.eagle-vehicles-2014", "world.eagle-vehicles-2024"];
  return [];
};

function actorReference(document: StoredDocument, source: ActorReference["source"]): ActorReference {
  const id = idOf(document.uuid);
  return { id, uuid: document.uuid, name: document.name ?? id, type: document.type ?? "", source };
}

// module.ts `resolveActorMember`, with Foundry's fromUuid/game.actors/pack index replaced by backend reads.
async function resolveActorMember(backend: DocumentBackend, uuid: string): Promise<ActorResolutionResult> {
  let selected: StoredDocument | undefined;
  try {
    selected = await backend.read(uuid);
  } catch (error) {
    return { ok: false, reason: "not-found", detail: error instanceof Error ? error.message : String(error) };
  }
  if (!selected) return { ok: false, reason: "not-found", detail: uuid };
  if (selected.documentName !== "Actor") return { ok: false, reason: "not-actor", detail: uuid };

  const type = selected.type ?? "";
  const id = idOf(selected.uuid);
  const expectedCollections = actorLibraryCollections(type);
  const selectedSource: ActorReference["source"] = !selected.pack
    ? "world"
    : expectedCollections.includes(selected.pack)
      ? "eagle-library"
      : "other-compendium";
  const selectedReference = actorReference(selected, selectedSource);

  const worldActor = selected.pack ? await backend.read(`Actor.${id}`) : selected;
  const world = worldActor?.type === type ? actorReference(worldActor, "world") : undefined;
  if (selectedSource === "eagle-library") return { ok: true, selected: selectedReference, world, library: selectedReference };

  const indexedActor = async (collection: string): Promise<ActorReference | undefined> => {
    const library = await backend.read(`Compendium.${collection}.Actor.${id}`);
    return library && library.type === type ? actorReference(library, "eagle-library") : undefined;
  };

  const pair = (selectedSource === "world" ? ((selected.source?.flags as JsonObject | undefined)?.["eagle-homebrew"] as JsonObject | undefined)?.pair : undefined) as
    | { pack?: unknown }
    | undefined;
  if (typeof pair?.pack === "string" && expectedCollections.includes(pair.pack)) {
    const library = await indexedActor(pair.pack);
    if (library) return { ok: true, selected: selectedReference, world, library };
  }

  const matches = (await Promise.all(expectedCollections.map(indexedActor))).filter((entry): entry is ActorReference => entry !== undefined);
  if (matches.length > 1) return { ok: false, reason: "ambiguous-library", detail: matches.map((entry) => entry.uuid).join(", ") };
  return { ok: true, selected: selectedReference, world, library: matches[0] };
}

export function createVttContext(
  backend: DocumentBackend,
  defaults: Record<string, Record<string, JsonObject>> = {},
): HomebrewWindowContext {
  const sender: RequestSender = { request: (type, payload) => backend.request(type, payload) };
  return {
    sender,
    readRulesVersion: () => (globalThis as unknown as { game: { settings: { get(a: string, b: string): unknown } } }).game.settings.get("dnd5e", "rulesVersion"),
    // In the VTT every Library pack exists (it is a filter over the author's Library), so never `undefined`.
    async readIndex(collection) {
      const rows = await backend.index(collection);
      return rows.map((row) => ({ name: String(row.name ?? ""), requirements: row.requirements ?? undefined }));
    },
    resolveActorMember: (uuid) => resolveActorMember(backend, uuid),
    async readDocumentSource(uuid) {
      const stored = await backend.read(uuid);
      return stored?.source ? clone(stored.source) : undefined;
    },
    // module.ts reads Foundry's `game.model` defaults here. Without Foundry the defaults come from a parity
    // snapshot when one is provided (docs: Eagle Homebrew parity snapshot); otherwise an empty system object,
    // which is exactly module.ts's own fallback.
    defaultDocumentSource(entry: CatalogEntry): JsonObject {
      if (entry.art === "RollTable") return { name: "" };
      return { name: "", system: clone(defaults[entry.art]?.[entry.subtype ?? ""] ?? {}) };
    },
    newId: () => shimRandomID(),
    notify: (level, message) => shimNotify(level, message),
  };
}
