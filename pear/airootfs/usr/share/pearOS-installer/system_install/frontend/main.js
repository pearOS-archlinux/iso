const electron = require('electron')
const app = electron.app
const BrowserWindow = electron.BrowserWindow
const path = require('path')
const url = require('url')
let mainWindow

function createWindow () {
  const screen = electron.screen;
  const primaryDisplay = screen.getPrimaryDisplay();
  const displayWidth = primaryDisplay.size.width;
  const displayHeight = primaryDisplay.size.height;

  mainWindow = new BrowserWindow({
      show: false,
      resizable: false,
      frame: false,
      width: displayWidth,
      height: displayHeight,
      webPreferences: {
	nodeIntegration: true,
	enableRemoteModule: true,
	contextIsolation: false
    }
  })

  // Disables F11
  mainWindow.setMenu(null);

  mainWindow.loadURL(url.format({
    pathname: path.join(__dirname, '/app/index.html'),
    protocol: 'file:',
    slashes: true
  }))

  mainWindow.once('ready-to-show', () => {
    mainWindow.setFullScreen(true)
    mainWindow.show()
  })

  // !! UNCOMMENT ONLY ON DEBUG !!
  // mainWindow.webContents.openDevTools()

  mainWindow.on('closed', function () {
    mainWindow = null
  })
}

app.on('ready', createWindow)

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', function () {
  if (mainWindow === null) {
    createWindow()
  }
})
