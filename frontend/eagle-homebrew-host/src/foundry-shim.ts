// Replaces exactly the Foundry v13 surface Eagle Homebrew's unmodified v13/homebrew-application.ts touches:
// ApplicationV2 (window frame, render cycle, data-action dispatch), foundry.applications.fields (six input
// factories), foundry.applications.elements.HTMLDocumentTagsElement, foundry.utils, game.i18n/settings/user,
// ui.notifications, CONFIG.DND5E and dnd5e.documents.Trait.getBaseItem. Nothing here redesigns Matt's editor:
// every element produces the same DOM shape (form-group > label + form-fields) Foundry would, so his markup,
// class names and reading order stay as he built them. Must be imported before homebrew-application.ts,
// which destructures `foundry.applications.api` at module load.

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

export interface ShimHost {
  mount: HTMLElement;
  translations: Record<string, Json>;
  dnd5eConfig: Record<string, Json>;
  baseItems: Record<string, { name?: string; system?: { type?: { value?: string } } }>;
  rulesVersion: "modern" | "legacy";
  isGM: boolean;
  documentOptions(type: "Actor" | "Item"): Promise<readonly { uuid: string; name: string }[]>;
  documentName(uuid: string): Promise<string | undefined>;
}

let host: ShimHost | undefined;
const requireHost = (): ShimHost => {
  if (!host) throw new Error("Eagle Homebrew host not installed");
  return host;
};

// ---- i18n -------------------------------------------------------------------------------------------------
const flatTranslations = new Map<string, string>();
function flatten(source: Record<string, Json>, prefix = ""): void {
  for (const [key, value] of Object.entries(source)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) flatten(value as Record<string, Json>, path);
    else if (typeof value === "string") flatTranslations.set(path, value);
  }
}
const i18n = {
  lang: "en",
  localize: (key: string): string => flatTranslations.get(key) ?? key,
  format: (key: string, data: Record<string, string> = {}): string =>
    (flatTranslations.get(key) ?? key).replace(/{([^}]+)}/g, (match, name: string) => (name in data ? String(data[name]) : match)),
  has: (key: string): boolean => flatTranslations.has(key),
};

// ---- notifications (Foundry's toast stack) ----------------------------------------------------------------
function notify(level: "info" | "warn" | "error", message: string): void {
  let stack = document.getElementById("eh-notifications");
  if (!stack) {
    stack = document.createElement("ol");
    stack.id = "eh-notifications";
    document.body.append(stack);
  }
  const item = document.createElement("li");
  item.className = `eh-notification ${level}`;
  item.setAttribute("role", level === "error" ? "alert" : "status");
  item.textContent = message;
  stack.append(item);
  setTimeout(() => item.remove(), level === "error" ? 8000 : 5000);
}
const notifications = {
  info: (message: string) => notify("info", message),
  warn: (message: string) => notify("warn", message),
  error: (message: string) => notify("error", message),
};

// ---- utils ------------------------------------------------------------------------------------------------
const ID_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
function randomID(length = 16): string {
  const bytes = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(bytes, (byte) => ID_ALPHABET[byte % ID_ALPHABET.length]).join("");
}
const deepClone = <T>(value: T): T => (value === undefined ? value : structuredClone(value));
const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);
function mergeOptions(target: Record<string, unknown>, source: Record<string, unknown>): Record<string, unknown> {
  for (const [key, value] of Object.entries(source)) {
    target[key] = isPlainObject(value) && isPlainObject(target[key]) ? mergeOptions({ ...(target[key] as Record<string, unknown>) }, value) : value;
  }
  return target;
}

// ---- fields -----------------------------------------------------------------------------------------------
interface SelectOption { value: string; label: string; group?: string; disabled?: boolean; selected?: boolean }

function setName(input: HTMLElement, name?: string): void {
  if (name) input.setAttribute("name", name);
}

const fields = {
  createFormGroup(config: { label?: string; input: HTMLElement; hint?: string; units?: string; classes?: string[]; stacked?: boolean; localize?: boolean }): HTMLDivElement {
    const group = document.createElement("div");
    group.className = ["form-group", ...(config.stacked ? ["stacked"] : []), ...(config.classes ?? [])].join(" ");
    if (config.label) {
      const label = document.createElement("label");
      label.textContent = config.localize ? i18n.localize(config.label) : config.label;
      if (!config.input.id) config.input.id = `eh-${randomID(8)}`;
      label.htmlFor = config.input.id;
      group.append(label);
    }
    const inputs = document.createElement("div");
    inputs.className = "form-fields";
    inputs.append(config.input);
    if (config.units) {
      const units = document.createElement("span");
      units.className = "units";
      units.textContent = config.units;
      inputs.append(units);
    }
    group.append(inputs);
    if (config.hint) {
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.textContent = config.hint;
      group.append(hint);
    }
    return group;
  },

  createTextInput(config: { name?: string; value?: string; placeholder?: string }): HTMLInputElement {
    const input = document.createElement("input");
    input.type = "text";
    setName(input, config.name);
    input.value = config.value ?? "";
    if (config.placeholder) input.placeholder = config.placeholder;
    return input;
  },

  createNumberInput(config: { name?: string; value?: number; min?: number; max?: number; step?: number | "any"; placeholder?: string }): HTMLInputElement {
    const input = document.createElement("input");
    input.type = "number";
    setName(input, config.name);
    input.step = String(config.step ?? "any");
    if (config.min !== undefined) input.min = String(config.min);
    if (config.max !== undefined) input.max = String(config.max);
    if (config.placeholder) input.placeholder = config.placeholder;
    input.value = config.value === undefined || config.value === null ? "" : String(config.value);
    return input;
  },

  createCheckboxInput(config: { name?: string; value?: boolean }): HTMLInputElement {
    const input = document.createElement("input");
    input.type = "checkbox";
    setName(input, config.name);
    input.checked = config.value === true;
    return input;
  },

  createSelectInput(config: { name?: string; value?: string; options: SelectOption[]; blank?: string }): HTMLSelectElement {
    const select = document.createElement("select");
    setName(select, config.name);
    if (config.blank !== undefined) select.append(new Option(config.blank, ""));
    const groups = new Map<string, HTMLOptGroupElement>();
    for (const option of config.options) {
      const node = new Option(option.label, option.value);
      node.disabled = option.disabled === true;
      if (option.group) {
        let group = groups.get(option.group);
        if (!group) {
          group = document.createElement("optgroup");
          group.label = option.group;
          groups.set(option.group, group);
          select.append(group);
        }
        group.append(node);
      } else select.append(node);
    }
    select.value = config.value ?? (config.blank !== undefined ? "" : config.options[0]?.value ?? "");
    return select;
  },

  createMultiSelectInput(config: { name?: string; value?: readonly string[]; options: SelectOption[] }): HTMLElement {
    const multi = document.createElement("multi-select") as MultiSelectElement;
    setName(multi, config.name);
    multi.configure(config.options, config.value ?? []);
    return multi;
  },
};

// ---- <multi-select>: Foundry's tag-list multi-select (value is a string[]) ---------------------------------
class MultiSelectElement extends HTMLElement {
  #options: SelectOption[] = [];
  #selected: string[] = [];
  #select = document.createElement("select");
  #tags = document.createElement("div");

  configure(options: SelectOption[], value: readonly string[]): void {
    this.#options = options;
    this.#selected = value.filter((entry) => options.some((option) => option.value === entry));
    this.#draw();
  }

  get value(): string[] {
    return [...this.#selected];
  }

  set value(next: readonly string[]) {
    this.#selected = [...next];
    this.#draw();
  }

  connectedCallback(): void {
    if (!this.#select.isConnected) this.#draw();
  }

  #emit(): void {
    this.#draw();
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  #draw(): void {
    this.#tags.className = "tags input-element-tags";
    this.#tags.replaceChildren(
      ...this.#selected.map((value) => {
        const tag = document.createElement("div");
        tag.className = "tag";
        tag.dataset.key = value;
        tag.append(this.#options.find((option) => option.value === value)?.label ?? value);
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "remove";
        remove.setAttribute("aria-label", `${i18n.localize("Remove")} ${value}`);
        remove.textContent = "×";
        remove.addEventListener("click", (event) => {
          event.stopPropagation();
          this.#selected = this.#selected.filter((entry) => entry !== value);
          this.#emit();
        });
        tag.append(remove);
        return tag;
      }),
    );
    this.#select.replaceChildren(new Option("", ""));
    for (const option of this.#options) {
      if (!this.#selected.includes(option.value)) this.#select.append(new Option(option.label, option.value));
    }
    this.#select.value = "";
    this.#select.onchange = () => {
      if (this.#select.value === "") return;
      this.#selected.push(this.#select.value);
      this.#emit();
    };
    if (!this.contains(this.#select)) this.replaceChildren(this.#tags, this.#select);
  }
}

// ---- <document-tags>: Foundry's document reference picker (single: string, multiple: string[]) -------------
// Foundry fills it by dragging a document from the sidebar or pasting a UUID. The VTT has no Foundry sidebar,
// so the drag source is replaced by a searchable list of the VTT's own Library/world documents of that type;
// pasting a UUID still works as before.
class DocumentTagsElement extends HTMLElement {
  static create(config: { name?: string; type?: "Actor" | "Item"; single?: boolean; value?: string | readonly string[] }): DocumentTagsElement {
    const element = document.createElement("document-tags") as DocumentTagsElement;
    setName(element, config.name);
    element.#type = config.type ?? "Item";
    element.#single = config.single === true;
    const initial = config.value === undefined ? [] : typeof config.value === "string" ? [config.value] : [...config.value];
    element.#uuids = initial.filter((uuid) => uuid !== "");
    element.#draw();
    return element;
  }

  #type: "Actor" | "Item" = "Item";
  #single = false;
  #uuids: string[] = [];
  #input = document.createElement("input");
  #list = document.createElement("datalist");
  #tags = document.createElement("div");

  get value(): string | string[] {
    return this.#single ? (this.#uuids[0] ?? "") : [...this.#uuids];
  }

  set value(next: string | readonly string[]) {
    this.#uuids = (typeof next === "string" ? [next] : [...next]).filter((uuid) => uuid !== "");
    this.#draw();
  }

  #add(uuid: string): void {
    if (uuid === "") return;
    this.#uuids = this.#single ? [uuid] : [...new Set([...this.#uuids, uuid])];
    this.#draw();
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  #draw(): void {
    this.#tags.className = "tags input-element-tags";
    this.#tags.replaceChildren(
      ...this.#uuids.map((uuid) => {
        const tag = document.createElement("div");
        tag.className = "tag";
        tag.dataset.key = uuid;
        const label = document.createElement("span");
        label.textContent = uuid;
        void requireHost().documentName(uuid).then((name) => {
          if (name) label.textContent = name;
          label.title = uuid;
        });
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "remove";
        remove.textContent = "×";
        remove.addEventListener("click", (event) => {
          event.stopPropagation();
          this.#uuids = this.#uuids.filter((entry) => entry !== uuid);
          this.#draw();
          this.dispatchEvent(new Event("change", { bubbles: true }));
        });
        tag.append(label, remove);
        return tag;
      }),
    );
    this.#list.id ||= `eh-docs-${randomID(8)}`;
    this.#input.type = "text";
    this.#input.setAttribute("list", this.#list.id);
    this.#input.placeholder = this.#type === "Actor" ? "Actor.… / Compendium.…" : "Item.… / Compendium.…";
    this.#input.onfocus = () => {
      void requireHost().documentOptions(this.#type).then((options) => {
        this.#list.replaceChildren(...options.map((option) => new Option(option.name, option.uuid)));
      });
    };
    this.#input.onchange = () => {
      const uuid = this.#input.value.trim();
      this.#input.value = "";
      this.#add(uuid);
    };
    const showInput = !this.#single || this.#uuids.length === 0;
    this.#input.hidden = !showInput;
    if (!this.contains(this.#tags)) this.replaceChildren(this.#tags, this.#input, this.#list);
  }
}

// ---- ApplicationV2 ----------------------------------------------------------------------------------------
// As in Foundry, handlers are bound to the concrete application subclass, hence `this: any`.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ActionHandler = (this: any, event: PointerEvent, target: HTMLElement) => unknown;
interface ApplicationOptions {
  id?: string;
  window?: { title?: string; icon?: string; resizable?: boolean; contentClasses?: string[] };
  position?: { width?: number | "auto"; height?: number | "auto" };
  actions?: Record<string, ActionHandler>;
}

export class ApplicationV2 {
  static DEFAULT_OPTIONS: ApplicationOptions = {};
  options: ApplicationOptions;
  #element: HTMLElement | undefined;
  #content: HTMLElement | undefined;
  #rendering: Promise<this> | undefined;

  constructor(options: ApplicationOptions = {}) {
    const chain: ApplicationOptions[] = [];
    for (let cls = this.constructor as typeof ApplicationV2 | undefined; cls && (cls as unknown) !== Function.prototype; cls = Object.getPrototypeOf(cls)) {
      if (Object.prototype.hasOwnProperty.call(cls, "DEFAULT_OPTIONS")) chain.unshift(cls.DEFAULT_OPTIONS);
    }
    this.options = [...chain, options].reduce<Record<string, unknown>>((merged, next) => mergeOptions(merged, next as Record<string, unknown>), {}) as ApplicationOptions;
  }

  get id(): string {
    return this.options.id ?? "app";
  }

  get element(): HTMLElement | undefined {
    return this.#element;
  }

  get rendered(): boolean {
    return !!this.#element?.isConnected;
  }

  get title(): string {
    return i18n.localize(this.options.window?.title ?? "");
  }

  async render(_options?: boolean | Record<string, unknown>): Promise<this> {
    // Serialize renders like Foundry's render semaphore, so two quick clicks never interleave DOM swaps.
    const previous = this.#rendering;
    const next = (async () => {
      await previous;
      if (!this.#element) this.#element = this.#buildFrame();
      const result = await this._renderHTML({}, {});
      this._replaceHTML(result, this.#content!, {});
      return this;
    })();
    this.#rendering = next.catch(() => this);
    return next;
  }

  async close(): Promise<this> {
    this.#element?.remove();
    this.#element = undefined;
    this.#content = undefined;
    document.body.classList.toggle("eh-window-open", !!document.querySelector(".eh-window"));
    return this;
  }

  protected async _renderHTML(_context: unknown, _options: unknown): Promise<unknown> {
    return document.createElement("div");
  }

  protected _replaceHTML(result: unknown, content: HTMLElement, _options: unknown): void {
    content.replaceChildren(result as Node);
  }

  #buildFrame(): HTMLElement {
    document.getElementById(this.id)?.remove();
    const frame = document.createElement("div");
    frame.id = this.id;
    frame.className = "application eh-window";
    frame.setAttribute("role", "dialog");
    frame.setAttribute("aria-label", this.title);
    const { width, height } = this.options.position ?? {};
    if (typeof width === "number") frame.style.width = `${width}px`;
    if (typeof height === "number") frame.style.height = `${height}px`;
    if (this.options.window?.resizable) frame.classList.add("resizable");

    const header = document.createElement("header");
    header.className = "window-header";
    const title = document.createElement("h1");
    title.className = "window-title";
    title.textContent = this.title;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "header-control";
    close.dataset.action = "close";
    close.setAttribute("aria-label", i18n.localize("Close"));
    close.textContent = "×";
    header.append(title, close);
    this.#makeDraggable(frame, header);

    const content = document.createElement("section");
    content.className = ["window-content", ...(this.options.window?.contentClasses ?? [])].join(" ");
    frame.append(header, content);
    this.#content = content;

    frame.addEventListener("click", (event) => {
      const target = (event.target as HTMLElement).closest<HTMLElement>("[data-action]");
      if (!target || !frame.contains(target) || (target as HTMLButtonElement).disabled) return;
      const action = target.dataset.action!;
      if (action === "close") {
        void this.close();
        return;
      }
      const handler = this.options.actions?.[action];
      if (!handler) return;
      event.preventDefault();
      void Promise.resolve(handler.call(this, event as PointerEvent, target)).catch((error: unknown) => {
        console.error(error);
        notifications.error(error instanceof Error ? error.message : String(error));
      });
    });
    requireHost().mount.append(frame);
    document.body.classList.add("eh-window-open");
    return frame;
  }

  // Foundry windows move by their title bar. Once moved, the window leaves its docked default position.
  #makeDraggable(frame: HTMLElement, header: HTMLElement): void {
    header.addEventListener("pointerdown", (start) => {
      if ((start.target as HTMLElement).closest("button") || start.button !== 0) return;
      const box = frame.getBoundingClientRect();
      const offsetX = start.clientX - box.left;
      const offsetY = start.clientY - box.top;
      header.setPointerCapture(start.pointerId);
      const move = (event: PointerEvent): void => {
        const left = Math.min(Math.max(0, event.clientX - offsetX), window.innerWidth - 80);
        const top = Math.min(Math.max(0, event.clientY - offsetY), window.innerHeight - 40);
        frame.classList.add("eh-moved");
        frame.style.left = `${left}px`;
        frame.style.top = `${top}px`;
      };
      const stop = (): void => {
        header.removeEventListener("pointermove", move);
        header.removeEventListener("pointerup", stop);
        header.removeEventListener("pointercancel", stop);
      };
      header.addEventListener("pointermove", move);
      header.addEventListener("pointerup", stop);
      header.addEventListener("pointercancel", stop);
    });
  }
}

// ---- install ----------------------------------------------------------------------------------------------
const globals = globalThis as unknown as Record<string, unknown>;
globals.foundry = {
  applications: { api: { ApplicationV2 }, fields, elements: { HTMLDocumentTagsElement: DocumentTagsElement } },
  utils: { deepClone, randomID, mergeObject: (a: Record<string, unknown>, b: Record<string, unknown>) => mergeOptions(a, b) },
};
globals.CONFIG = { DND5E: {} };
globals.ui = { notifications };
globals.game = {
  i18n,
  settings: { get: (namespace: string, key: string) => (namespace === "dnd5e" && key === "rulesVersion" ? requireHost().rulesVersion : undefined) },
  get user() {
    return { isGM: requireHost().isGM };
  },
};
globals.dnd5e = {
  documents: {
    Trait: {
      getBaseItem: async (uuid: string) => requireHost().baseItems[uuid],
    },
  },
};
if (!customElements.get("multi-select")) customElements.define("multi-select", MultiSelectElement);
if (!customElements.get("document-tags")) customElements.define("document-tags", DocumentTagsElement);

export function installHost(next: ShimHost): void {
  host = next;
  flatTranslations.clear();
  flatten(next.translations as Record<string, Json>);
  (globals.CONFIG as { DND5E: unknown }).DND5E = next.dnd5eConfig;
}

export const shimNotify = notify;
export const shimRandomID = randomID;
