// roll drauf vtt - Frontend Main Application
// Canvas-based map rendering with Socket.IO real-time sync

console.log('main.js loaded');

const API_BASE = 'http://localhost:5000';
const GRID_SIZE = 32; // pixels per grid square

class GameState {
    constructor() {
        this.tokens = [];
        this.mapWidth = 20;
        this.mapHeight = 20;
        this.selectedToken = null;
        this.zoom = 1;
    }

    addToken(token) {
        this.tokens.push(token);
    }

    updateToken(id, updates) {
        const token = this.tokens.find(t => t.id === id);
        if (token) {
            Object.assign(token, updates);
        }
    }

    removeToken(id) {
        this.tokens = this.tokens.filter(t => t.id !== id);
    }

    getToken(id) {
        return this.tokens.find(t => t.id === id);
    }
}

class MapRenderer {
    constructor(canvas, gameState) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.gameState = gameState;
        this.offsetX = 0;
        this.offsetY = 0;
    }

    render() {
        const { canvas, ctx, gameState } = this;

        // Clear canvas
        ctx.fillStyle = '#f0f0f0';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw grid
        this.drawGrid();

        // Draw tokens
        this.drawTokens();
    }

    drawGrid() {
        const { ctx, gameState } = this;
        const gridSize = GRID_SIZE * this.gameState.zoom;

        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 1;

        // Vertical lines
        for (let x = 0; x < gameState.mapWidth * gridSize; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x + this.offsetX, 0);
            ctx.lineTo(x + this.offsetX, this.canvas.height);
            ctx.stroke();
        }

        // Horizontal lines
        for (let y = 0; y < gameState.mapHeight * gridSize; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y + this.offsetY);
            ctx.lineTo(this.canvas.width, y + this.offsetY);
            ctx.stroke();
        }
    }

    drawTokens() {
        const { ctx, gameState } = this;
        const gridSize = GRID_SIZE * this.gameState.zoom;

        gameState.tokens.forEach(token => {
            const x = token.x * gridSize + gridSize / 2 + this.offsetX;
            const y = token.y * gridSize + gridSize / 2 + this.offsetY;
            const radius = gridSize / 2 - 2;

            // Draw circle
            ctx.fillStyle = token.type === 'player' ? '#4caf50' : '#ff6b6b';
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, Math.PI * 2);
            ctx.fill();

            // Draw border if selected
            if (gameState.selectedToken?.id === token.id) {
                ctx.strokeStyle = '#ffeb3b';
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Draw name
            ctx.fillStyle = '#000';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'bottom';
            ctx.fillText(token.name, x, y + radius + 5);
        });
    }

    worldToScreen(worldX, worldY) {
        const gridSize = GRID_SIZE * this.gameState.zoom;
        return {
            x: worldX * gridSize + this.offsetX,
            y: worldY * gridSize + this.offsetY
        };
    }

    screenToWorld(screenX, screenY) {
        const gridSize = GRID_SIZE * this.gameState.zoom;
        return {
            x: Math.floor((screenX - this.offsetX) / gridSize),
            y: Math.floor((screenY - this.offsetY) / gridSize)
        };
    }
}

class InputHandler {
    constructor(canvas, gameState, renderer, socket) {
        this.canvas = canvas;
        this.gameState = gameState;
        this.renderer = renderer;
        this.socket = socket;
        this.draggingToken = null;

        this.setupEventListeners();
    }

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', () => this.handleMouseUp());
        this.canvas.addEventListener('wheel', (e) => this.handleZoom(e));
    }

    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const world = this.renderer.screenToWorld(screenX, screenY);

        // Find token at click position
        const token = this.gameState.tokens.find(t => {
            const dist = Math.sqrt(
                Math.pow(t.x - world.x, 2) + Math.pow(t.y - world.y, 2)
            );
            return dist < 1;
        });

        if (token) {
            this.draggingToken = token;
            this.gameState.selectedToken = token;
            this.renderer.render();
        }
    }

    handleMouseMove(e) {
        if (!this.draggingToken) return;

        const rect = this.canvas.getBoundingClientRect();
        const screenX = e.clientX - rect.left;
        const screenY = e.clientY - rect.top;
        const world = this.renderer.screenToWorld(screenX, screenY);

        // Update token position
        this.draggingToken.x = world.x;
        this.draggingToken.y = world.y;
        this.renderer.render();
    }

    handleMouseUp() {
        if (this.draggingToken) {
            // Emit token update to server
            this.socket.emit('token_update', this.draggingToken);
            this.draggingToken = null;
        }
    }

    handleZoom(e) {
        e.preventDefault();
        const zoomSpeed = 0.1;
        this.gameState.zoom += e.deltaY > 0 ? -zoomSpeed : zoomSpeed;
        this.gameState.zoom = Math.max(0.5, Math.min(2, this.gameState.zoom));
        this.renderer.render();
    }
}

class DiceRoller {
    constructor(socket) {
        this.socket = socket;
        this.setupUI();
    }

    setupUI() {
        const diceInput = document.getElementById('dice-input');
        const diceButton = document.getElementById('dice-button');

        diceButton.addEventListener('click', () => {
            const dice = diceInput.value.trim();
            if (dice) {
                this.roll(dice);
                diceInput.value = '';
            }
        });

        diceInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                diceButton.click();
            }
        });
    }

    roll(dice) {
        // Emit to server for centralized rolling
        this.socket.emit('roll_dice', { dice }, (result) => {
            this.displayResult(dice, result);
        });
    }

    displayResult(dice, result) {
        const resultDiv = document.getElementById('dice-result');
        if (result.error) {
            resultDiv.innerHTML = `<strong>Error:</strong> ${result.error}`;
            return;
        }
        const rolls = result.rolls.join(', ');
        const total = result.total;
        resultDiv.innerHTML = `<strong>${dice}</strong><br>Rolls: ${rolls}<br>Total: ${total}`;
    }
}

// Main initialization
async function initialize() {
    console.log('Initializing game...');
    const canvas = document.getElementById('game-canvas');
    if (!canvas) {
        console.error('Canvas element not found!');
        return;
    }

    canvas.width = window.innerWidth - 300 - 20;
    canvas.height = window.innerHeight - 20;
    console.log(`Canvas initialized: ${canvas.width}x${canvas.height}`);

    const gameState = new GameState();
    const renderer = new MapRenderer(canvas, gameState);
    const socket = io(API_BASE, { reconnection: true });
    const inputHandler = new InputHandler(canvas, gameState, renderer, socket);
    const diceRoller = new DiceRoller(socket);

    // Setup Socket.IO listeners
    socket.on('connect', () => {
        console.log('Connected to server');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
    });

    socket.on('token_update', (token) => {
        gameState.updateToken(token.id, token);
        renderer.render();
    });

    socket.on('token_create', (token) => {
        gameState.addToken(token);
        renderer.render();
    });

    socket.on('token_delete', (tokenId) => {
        gameState.removeToken(tokenId);
        renderer.render();
    });

    socket.on('map_sync', (state) => {
        gameState.tokens = state.tokens || [];
        gameState.mapWidth = state.width;
        gameState.mapHeight = state.height;
        renderer.render();
    });

    // Emit request for current map state
    socket.emit('get_map_state', {}, (state) => {
        if (state) {
            gameState.tokens = state.tokens || [];
            gameState.mapWidth = state.width || 20;
            gameState.mapHeight = state.height || 20;
            renderer.render();
        }
    });

    // Add some test tokens
    gameState.addToken({
        id: 'player_1',
        x: 5,
        y: 5,
        type: 'player',
        name: 'Aragorn',
        color: '#4caf50'
    });
    gameState.addToken({
        id: 'npc_1',
        x: 10,
        y: 10,
        type: 'npc',
        name: 'Goblin Boss',
        color: '#ff6b6b'
    });

    renderer.render();

    // Handle window resize
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth - 300 - 20;
        canvas.height = window.innerHeight - 20;
        renderer.render();
    });
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    if (connected) {
        status.textContent = '🟢 Connected';
        status.classList.remove('disconnected');
    } else {
        status.textContent = '🔴 Disconnected';
        status.classList.add('disconnected');
    }
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', initialize);