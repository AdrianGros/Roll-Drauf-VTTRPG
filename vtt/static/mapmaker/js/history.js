// Bounded undo/redo stack. Budget: at most 60 steps and 64 MB of retained
// pixel data (raster steps keep before/after ImageData of their dirty
// rectangle only; vector and layer steps are a few hundred bytes).

export const HISTORY_MAX_STEPS = 60;
export const HISTORY_MAX_BYTES = 64 * 1024 * 1024;

export class History {
    constructor({ maxSteps = HISTORY_MAX_STEPS, maxBytes = HISTORY_MAX_BYTES, onChange } = {}) {
        this.maxSteps = maxSteps;
        this.maxBytes = maxBytes;
        this.onChange = onChange || (() => {});
        this.clear(false);
    }

    clear(notify = true) {
        this.undoStack = [];
        this.redoStack = [];
        this.bytes = 0;
        if (notify) this.onChange(null);
    }

    get canUndo() {
        return this.undoStack.length > 0;
    }

    get canRedo() {
        return this.redoStack.length > 0;
    }

    /**
     * Record an already-applied command {label, bytes, undo(), redo()}.
     * Returns false when the step alone exceeds the budget (history is
     * cleared because older steps could no longer be replayed safely).
     */
    push(command) {
        const bytes = command.bytes || 256;
        for (const dropped of this.redoStack) this.bytes -= dropped.bytes || 256;
        this.redoStack = [];
        if (bytes > this.maxBytes) {
            this.undoStack = [];
            this.bytes = 0;
            this.onChange(command);
            return false;
        }
        this.undoStack.push(command);
        this.bytes += bytes;
        while (this.undoStack.length > this.maxSteps || this.bytes > this.maxBytes) {
            const oldest = this.undoStack.shift();
            this.bytes -= oldest.bytes || 256;
        }
        this.onChange(command);
        return true;
    }

    undo() {
        const command = this.undoStack.pop();
        if (!command) return null;
        command.undo();
        this.redoStack.push(command);
        this.onChange(command);
        return command;
    }

    redo() {
        const command = this.redoStack.pop();
        if (!command) return null;
        command.redo();
        this.undoStack.push(command);
        this.onChange(command);
        return command;
    }
}
