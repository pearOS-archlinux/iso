function createNavbar() {
    // Verifică dacă navbar-ul există deja
    if (document.getElementById('dynamic-navbar')) {
        return;
    }

    // Creează elementul navbar
    const navbar = document.createElement('div');
    navbar.id = 'dynamic-navbar';
    navbar.className = 'taskbar';
    
    navbar.innerHTML = `
        <div class="taskbar-button">
            <div id="logo-button">
                <img alt="" src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyBpZD0iTGF5ZXJfMSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB2ZXJzaW9uPSIxLjEiIHZpZXdCb3g9IjAgMCAzMCA0NCI+CiAgPCEtLSBHZW5lcmF0b3I6IEFkb2JlIElsbHVzdHJhdG9yIDI5LjcuMSwgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246IDIuMS4xIEJ1aWxkIDgpICAtLT4KICA8ZGVmcz4KICAgIDxzdHlsZT4KICAgICAgLnN0MCB7CiAgICAgICAgZmlsbDogI2ZmZjsKICAgICAgfQogICAgPC9zdHlsZT4KICA8L2RlZnM+CiAgPHBhdGggY2xhc3M9InN0MCIgZD0iTTE1LjcyLDcuNTljMy41Ny0uNzIsNS44NS0zLjU3LDUuODYtNy4xLTMuMzYuMDMtNi44MiwzLjczLTUuODYsNy4xWk0yOC44OCwzMS45M2MtNi4wNiwwLTEwLjY0LTUuNDUtOS4xMS0xMS4zLjMyLTEuMjQsMS4wMS0yLjM3LDEuOC0zLjM4LjM4LS40OCwxLjEzLS45OCwxLjE3LTEuNjMuMTQtMi4zMy0xLjk5LTQuNTMtMy45MS01LjU1LTMuNjUtMS45NC05LjIzLS44OC0xMS4xMiwyLjk5LS44NCwxLjczLS4zMywzLjYxLS45OCw1LjM2LS45MywyLjUxLTIuODEsNC4xNS00LjEzLDYuNDEtMS44MiwzLjA5LTIuMjUsNy40NC0uNzMsMTAuNzIsNC4zOCw5LjQ2LDE5LjA4LDEwLjU1LDI1LjAyLDEuOTgsMS4xNC0xLjY1LDEuOTktMy41NywyLTUuNTloLS4wMVoiLz4KPC9zdmc+" />
            </div>
            <div id="app-name-button"><b>pearOS Installer</b></div>
        </div>
        <div class="date-time">
            <div id="date">Oct 19</div>
            <div id="time">9:41 AM</div>
        </div>
    `;

    // Adaugă navbar-ul la începutul body-ului
    document.body.insertBefore(navbar, document.body.firstChild);

    // Creează meniul dropdown pentru logo
    const logoMenu = document.createElement('div');
    logoMenu.id = 'logo-menu';
    logoMenu.className = 'logo-menu';
    logoMenu.innerHTML = `
        <div class="logo-menu-item" onclick="handleShutdown()">Shutdown</div>
        <div class="logo-menu-item" onclick="handleRestart()">Restart</div>
        <div class="logo-menu-item" onclick="handleLiveEnvironment()">Go to Live Environment</div>
    `;
    document.body.appendChild(logoMenu);

    // Creează meniul dropdown pentru app name
    const appMenu = document.createElement('div');
    appMenu.id = 'app-menu';
    appMenu.className = 'logo-menu';
    appMenu.innerHTML = `
        <div class="logo-menu-item" onclick="handleAbout()">About pearOS Installer</div>
        <div class="logo-menu-item" onclick="handleShowLog()">Show Log</div>
        <div class="logo-menu-item" onclick="handleShowDisks()">Show Disks</div>
        <div class="logo-menu-item" onclick="handleQuit()">Quit pearOS Installer</div>
    `;
    document.body.appendChild(appMenu);

    // Creează modalul About
    const aboutModal = document.createElement('div');
    aboutModal.id = 'about-modal';
    aboutModal.className = 'modal';
    aboutModal.innerHTML = `
        <div class="modal-content">
            <h2>About pearOS Installer</h2>
            <p><strong>Build:</strong> 2025.10.27</p>
            <p><strong>Author:</strong> Pear Software and Services</p>
            <p><strong>Email:</strong> alex@pear-software.com</p>
            <button class="button" onclick="closeAboutModal()">Close</button>
        </div>
    `;
    document.body.appendChild(aboutModal);

    // Adaugă event listener pentru logo
    const logoButton = document.getElementById('logo-button');
    logoButton.addEventListener('click', toggleLogoMenu);

    // Adaugă event listener pentru app name
    const appNameButton = document.getElementById('app-name-button');
    appNameButton.addEventListener('click', toggleAppMenu);

    // Închide meniurile când se dă click în altă parte
    document.addEventListener('click', function(event) {
        const logoMenu = document.getElementById('logo-menu');
        const appMenu = document.getElementById('app-menu');
        const logo = document.getElementById('logo-button');
        const appName = document.getElementById('app-name-button');
        
        if (logoMenu && !logoMenu.contains(event.target) && !logo.contains(event.target)) {
            logoMenu.classList.remove('show');
        }
        
        if (appMenu && !appMenu.contains(event.target) && !appName.contains(event.target)) {
            appMenu.classList.remove('show');
        }
    });

    // Închide modalul când se dă click pe fundal
    const aboutModal2 = document.getElementById('about-modal');
    aboutModal2.addEventListener('click', function(event) {
        if (event.target === aboutModal2) {
            aboutModal2.classList.remove('show');
        }
    });

    // Inițializează actualizarea datei și orei
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

function toggleLogoMenu(event) {
    event.stopPropagation();
    const logoMenu = document.getElementById('logo-menu');
    const appMenu = document.getElementById('app-menu');
    
    // Închide app menu dacă e deschis
    if (appMenu) {
        appMenu.classList.remove('show');
    }
    
    logoMenu.classList.toggle('show');
}

function toggleAppMenu(event) {
    event.stopPropagation();
    const logoMenu = document.getElementById('logo-menu');
    const appMenu = document.getElementById('app-menu');
    
    // Închide logo menu dacă e deschis
    if (logoMenu) {
        logoMenu.classList.remove('show');
    }
    
    appMenu.classList.toggle('show');
}

function handleShutdown() {
    if (typeof require !== 'undefined') {
        const { ipcRenderer } = require('electron');
        ipcRenderer.send('system-action', 'shutdown');
    }
}

function handleRestart() {
    if (typeof require !== 'undefined') {
        const { ipcRenderer } = require('electron');
        ipcRenderer.send('system-action', 'restart');
    }
}

function handleLiveEnvironment() {
    if (typeof require !== 'undefined') {
        const { ipcRenderer } = require('electron');
        ipcRenderer.send('system-action', 'live-environment');
    }
}

function handleAbout() {
    const modal = document.getElementById('about-modal');
    const appMenu = document.getElementById('app-menu');
    
    if (appMenu) {
        appMenu.classList.remove('show');
    }
    
    if (modal) {
        modal.classList.add('show');
    }
}

function closeAboutModal() {
    const modal = document.getElementById('about-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function handleShowLog() {
    if (typeof require !== 'undefined') {
        const { ipcRenderer } = require('electron');
        ipcRenderer.send('app-action', 'show-log');
    }
}

function handleShowDisks() {
    if (typeof require !== 'undefined') {
        const { ipcRenderer } = require('electron');
        ipcRenderer.send('app-action', 'show-disks');
    }
}

function handleQuit() {
    if (typeof require !== 'undefined') {
        const { ipcRenderer } = require('electron');
        ipcRenderer.send('app-action', 'quit');
    }
}

// Funcție pentru actualizarea datei și orei
function updateDateTime() {
    const now = new Date();
    
    // Formatare dată în stil macOS (ex: "Oct 19")
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[now.getMonth()];
    const day = now.getDate();
    const dateString = `${month} ${day}`;
    
    // Formatare oră în stil macOS (ex: "9:41 AM")
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // 0 becomes 12
    const timeString = `${hours}:${minutes} ${ampm}`;
    
    // Actualizare elemente DOM
    const dateElement = document.getElementById('date');
    const timeElement = document.getElementById('time');
    
    if (dateElement) {
        dateElement.textContent = dateString;
    }
    if (timeElement) {
        timeElement.textContent = timeString;
    }
}

// Inițializează navbar-ul când se încarcă pagina
document.addEventListener('DOMContentLoaded', createNavbar);

// Pentru pagini care se încarcă dinamic
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createNavbar);
} else {
    createNavbar();
}
