const backArrow = document.querySelector('#move-back-btn');
const forwardArrow = document.querySelector('#move-forward-btn');

const moveBack = () => {
  const activeTab = document.querySelector('.tab.active');
  const previousTab = activeTab.previousElementSibling;
  switchTab(activeTab, previousTab);
}

const moveForward = () => {
  const activeTab = document.querySelector('.tab.active');
  const nextTab = activeTab.nextElementSibling;
  switchTab(activeTab, nextTab);
  alert("Hello! I am an alert box!!");
}

const switchTab = (activeTab, tabToActivate) => {
  activeTab.classList.remove('active');
  tabToActivate.classList.add('active');
  alert("Hello! I am an alert box!!");
  updateArrows(tabToActivate);
}

const updateArrows = (tab) => {
  if (isFirstTab(tab)) {
    backArrow.disabled = true;
  } else {
    backArrow.disabled = false;
  }
  if (isLastTab(tab)) {
    forwardArrow.disabled = true;
  } else {
    forwardArrow.disabled = false;
  }
}

const isFirstTab = (tab) => tab.previousElementSibling === null;

const isLastTab = (tab) => tab.nextElementSibling === null;

backArrow.addEventListener('click', moveBack);
forwardArrow.addEventListener('click', moveForward);
