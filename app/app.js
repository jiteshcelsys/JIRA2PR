"use strict";

const rainbowGradients = [
  'linear-gradient(135deg, red, orange)',
  'linear-gradient(135deg, orange, yellow)',
  'linear-gradient(135deg, yellow, green)',
  'linear-gradient(135deg, green, blue)',
  'linear-gradient(135deg, blue, indigo)',
  'linear-gradient(135deg, indigo, violet)',
  'linear-gradient(135deg, violet, red)',
];

let bgIndex = 0;
document.body.style.background = rainbowGradients[bgIndex];

setInterval(function () {
  bgIndex = (bgIndex + 1) % rainbowGradients.length;
  document.body.style.background = rainbowGradients[bgIndex];
}, 5 * 60 * 1000);

function saveToHistory(text) {
  const history = JSON.parse(localStorage.getItem('taskHistory') || '[]');
  history.push({ text: text, timestamp: Date.now() });
  localStorage.setItem('taskHistory', JSON.stringify(history));
}

function getRecentHistory() {
  const history = JSON.parse(localStorage.getItem('taskHistory') || '[]');
  const twoDaysAgo = Date.now() - (2 * 24 * 60 * 60 * 1000);
  return history.filter(function(item) { return item.timestamp >= twoDaysAgo; });
}

function renderHistoryPopup() {
  const list = document.getElementById('history-list');
  const items = getRecentHistory();
  list.innerHTML = '';
  if (items.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'history-empty';
    empty.textContent = 'No completed tasks in the last 2 days.';
    list.appendChild(empty);
    return;
  }
  items.slice().reverse().forEach(function(item) {
    const li = document.createElement('li');
    const taskText = document.createElement('span');
    taskText.textContent = item.text;
    const dateSpan = document.createElement('span');
    dateSpan.className = 'history-date';
    dateSpan.textContent = new Date(item.timestamp).toLocaleString();
    li.appendChild(taskText);
    li.appendChild(dateSpan);
    list.appendChild(li);
  });
}

const historyBtn = document.getElementById('history-btn');
const historyPopup = document.getElementById('history-popup');

if (historyBtn && historyPopup) {
  historyBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    if (historyPopup.classList.contains('hidden')) {
      renderHistoryPopup();
      historyPopup.classList.remove('hidden');
    } else {
      historyPopup.classList.add('hidden');
    }
  });

  document.addEventListener('click', function(e) {
    if (!historyPopup.classList.contains('hidden') &&
        !historyBtn.contains(e.target) &&
        !historyPopup.contains(e.target)) {
      historyPopup.classList.add('hidden');
    }
  });
}

function showToast() {
  const toast = document.getElementById('task-toast');
  if (!toast) return;
  toast.classList.remove('hidden');
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(function () {
    toast.classList.add('hidden');
  }, 2000);
}

const taskInput = document.querySelector('input.task');
const lists = document.querySelector('.lists');

const favsSection = document.querySelector('.favs');
const favTitle = document.querySelector('.favs h3');
const favs = document.querySelector('.favs ul');
const favsItems = favs.children;

const tasksSection = document.querySelector('.tasks');
const tasksTitle = document.querySelector('.tasks h3');
const tasks = document.querySelector('.tasks ul');
const taskItems = tasks.children;

if ( favsItems.length === 0 ) {
  favsSection.style.display = 'none';
};

if ( taskItems.length === 0 ) {
  tasksSection.style.display = "none";
};

taskInput.addEventListener('keyup', (e) => {
  if (e.keyCode === 13) {
    let li = document.createElement('li');
    if (taskInput.value === "") {
      alert("Please add a task");
    } else {
      li.textContent = taskInput.value;
      attachButton(li);
      tasks.appendChild(li);
      tasksTitle.style.display = '';
      taskInput.value = '';

      tasksTitle.textContent = "Inbox";
      tasksSection.style.display = "";
      showToast();
    }
  }
});

lists.addEventListener('click', (event) => {

  const tag = event.target.tagName;
  const basevalue = event.target.className.baseVal;

  const clickArea1 = event.target.parentNode.parentNode.parentNode.parentNode.className;
  const clickArea2 = event.target.parentNode.parentNode.parentNode.parentNode.parentNode.className;
  const clickArea3 = event.target.parentNode.parentNode.parentNode.parentNode.parentNode.parentNode.className;

  // Checking if buttons inside tasks section is clicked=
  if ( clickArea1 === 'tasks' || clickArea2 === 'tasks' || clickArea3 === 'tasks' ) {
    if (tag === 'svg') {
      if (basevalue  === 'delete' || basevalue  === 'can' || basevalue  === 'cap' || basevalue  === 'bin') {
        let li = event.target.parentNode.parentNode;
        let ul = li.parentNode;
        saveToHistory(li.childNodes[0].textContent.trim());
        ul.removeChild(li);
      } else if ( basevalue === 'fav') {
        let li = event.target.parentNode.parentNode;
        let ul = li.parentNode;
        favsSection.style.display = '';
        favs.appendChild(li);
        favTitle.textContent = "Favorites";
      }

      if ( taskItems.length === 0 ) {
        tasksSection.style.display = "none";
      };

    } else if (tag === 'path') {
      if (basevalue  === 'delete' || basevalue  === 'can' || basevalue  === 'cap' || basevalue  === 'bin') {
        let li = event.target.parentNode.parentNode.parentNode.parentNode;
        let ul = li.parentNode;
        saveToHistory(li.childNodes[0].textContent.trim());
        ul.removeChild(li);
      } else if ( basevalue === 'favPath') {
        let li = event.target.parentNode.parentNode.parentNode;
        let ul = li.parentNode;
        favsSection.style.display = '';
        favs.appendChild(li);
        favTitle.textContent = "Favorites";
      }

      if ( taskItems.length === 0 ) {
        tasksSection.style.display = "none";
      };
    }

    // Checking if buttons inside favs section is clicked
  } else if ( clickArea1 === 'favs' || clickArea2 === 'favs' || clickArea3 === 'favs' ) {
    if (tag === 'svg') {
      if (basevalue  === 'delete' || basevalue  === 'can' || basevalue  === 'cap' || basevalue  === 'bin') {
        let li = event.target.parentNode.parentNode;
        let ul = li.parentNode;
        ul.removeChild(li);
      } else if ( basevalue === 'fav') {
        let li = event.target.parentNode.parentNode;
        let ul = li.parentNode;
        tasksSection.style.display = '';
        tasks.appendChild(li);
        tasksTitle.textContent = "Inbox";
      }

      if ( favsItems.length === 0 ) {
        favsSection.style.display = 'none';
      };

    } else if (tag === 'path') {
      if (basevalue  === 'delete' || basevalue  === 'can' || basevalue  === 'cap' || basevalue  === 'bin') {
        let li = event.target.parentNode.parentNode.parentNode.parentNode;
        let ul = li.parentNode;
        ul.removeChild(li);
      } else if ( basevalue === 'favPath') {
        let li = event.target.parentNode.parentNode.parentNode;
        let ul = li.parentNode;
        tasksSection.style.display = '';
        tasks.appendChild(li);
        tasksTitle.textContent = "Inbox";
      }

      if ( favsItems.length === 0 ) {
        favsSection.style.display = 'none';
      };
    }
  }
});
