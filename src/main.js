const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const waitOn = require('wait-on');

let mainWindow;
let flaskProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1280,
        height: 720,
        minWidth: 960,
        minHeight: 540,
        title: "Home Theater",
        icon: path.join(__dirname, '..', 'build', 'icon.png'),
        autoHideMenuBar: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    // Load the Flask app URL
    mainWindow.loadURL('http://127.0.0.1:5000');

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startFlaskBackend() {
    // Path to backend/app.py
    const scriptPath = path.join(__dirname, '..', 'backend', 'app.py');

    // Start the Python process
    flaskProcess = spawn('python3', [scriptPath], {
        cwd: path.dirname(scriptPath),
        env: { ...process.env, PYTHONUNBUFFERED: "1" }
    });

    flaskProcess.stdout.on('data', (data) => {
        console.log(`[Flask] ${data.toString().trim()}`);
    });

    flaskProcess.stderr.on('data', (data) => {
        console.error(`[Flask Error] ${data.toString().trim()}`);
    });

    flaskProcess.on('close', (code) => {
        console.log(`[Flask] Process exited with code ${code}`);
    });
}

app.whenReady().then(() => {
    startFlaskBackend();

    // Wait for Flask server to respond
    console.log("Waiting for Flask server on port 5000...");
    waitOn({
        resources: ['http://127.0.0.1:5000'],
        timeout: 30000 // give it 30s to start
    }).then(() => {
        console.log("Flask server is ready. Starting UI.");
        createWindow();
    }).catch((err) => {
        console.error("Failed to connect to Flask server:", err);
        // You could show an error dialog here if you wanted
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    // Kill Flask server when app closes
    if (flaskProcess) {
        flaskProcess.kill('SIGINT');
    }
});
