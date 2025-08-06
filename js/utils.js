// Shared utility functions and configuration
const apiUrl = 'https://api.checklist.spoi.org.in';
// const apiUrl = 'http://127.0.0.1:5001';
// const apiUrl = 'https://avighna.pythonanywhere.com';

function getFullOlympiadName(id) {
  const names = {
    APIO: 'Asia-Pacific Informatics Olympiad',
    EGOI: 'European Girls\' Olympiad in Informatics',
    INOI: 'Indian National Olympiad in Informatics',
    ZCO: 'Indian Zonal Computing Olympiad',
    IOI: 'International Olympiad in Informatics',
    JOIFR: 'Japanese Olympiad in Informatics: Final Round',
    JOISC: 'Japanese Olympiad in Informatics: Spring Camp',
    IOITC: 'Indian International Olympiad in Informatics: Training Camp',
    NOIPRELIM: 'Singapore NOI: Preliminary Round',
    NOIQUAL: 'Singapore NOI: Qualification Round',
    NOIFINAL: 'Singapore NOI: Final Round',
    POI: 'Polish Olympiad in Informatics',
    NOISEL: 'Singapore NOI: Selection Test',
    CEOI: 'Central European Olympiad in Informatics',
    COI: 'Croatian Olympiad in Informatics',
    BOI: 'Baltic Olympiad in Informatics',
    GKS: 'Google Kick Start',
    USACO: 'USA Computing Olympiad'
  };
  return names[id] || id;
}

function applyOlympiadContainerOrder(order) {
  const container = document.getElementById('olympiad-list');
  const allSections = Array.from(container.children);
  const sectionMap = new Map();

  // Map normalized ID → DOM element
  allSections.forEach(section => {
    const id = section.id.replace('-container', '').toLowerCase();
    sectionMap.set(id, section);
  });

  // Clear container and append based on order
  container.innerHTML = '';

  const seen = new Set();

  for (const id of order) {
    const section = sectionMap.get(id.toLowerCase());
    if (section) {
      container.appendChild(section);
      seen.add(id.toLowerCase());
    }
  }

  // Append leftover sections not in order
  for (const [id, section] of sectionMap.entries()) {
    if (!seen.has(id)) {
      container.appendChild(section);
    }
  }
}

function generateSkeletonRows(numRows) {
  let skeletonHTML = '';
  for (let i = 0; i < numRows; i++) {
    skeletonHTML += `
      <tr class="skeleton-row">
        <td class="year-cell skeleton"></td>
        <td class="problem-cell skeleton"></td>
        <td class="problem-cell skeleton"></td>
        <td class="problem-cell skeleton"></td>
      </tr>
    `;
  }
  return skeletonHTML;
}

function getPlatformFromLink(link) {
  if (!link) return 'Unknown';
  try {
    const url = new URL(link);
    const hostname = url.hostname.toLowerCase();
    
    if (hostname.includes('oj.uz')) return 'oj.uz';
    if (hostname.includes('qoj.ac')) return 'QOJ';
    if (hostname.includes('usaco.org')) return 'USACO';
    if (hostname.includes('atcoder.jp')) return 'AtCoder';
    if (hostname.includes('codeforces.com')) return 'Codeforces';
    if (hostname.includes('codechef.com')) return 'CodeChef';
    
    // Return the hostname if no specific platform detected
    return hostname.replace('www.', '');
  } catch (e) {
    return 'Unknown';
  }
}

function formatDuration(minutes) {
  if (!minutes) return 'Unknown';
  
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  
  if (hours === 0) {
    return `${remainingMinutes} minutes`;
  } else if (remainingMinutes === 0) {
    return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
  } else {
    return `${hours} ${hours === 1 ? 'hour' : 'hours'} ${remainingMinutes} minutes`;
  }
}

// Virtual Contest and Problem Cell functionality
const statuses = [
  {label: 'Unattempted', className: 'white', value: 0},
  {label: 'In progress', className: 'yellow', value: 1},
  {label: 'Solved', className: 'green', value: 2},
  {label: 'Failed', className: 'red', value: 3}
];

const next = [1, 3, 0, 2];

let currentCell = null;
let currentStatus = 0;
let isProfileMode = false;
let documentClickHandlerAdded = false;

// Add global click handler once
function addGlobalClickHandler() {
  if (documentClickHandlerAdded) return;
  
  document.addEventListener('click', (e) => {
    const popup = document.getElementById('status-popup');
    if (!popup) return;
    
    const isInsidePopup = popup.contains(e.target);
    const isSameCell = currentCell && currentCell.contains(e.target);

    if (!isInsidePopup && !isSameCell && popup.classList.contains('show')) {
      popup.classList.remove('show');
      popup.classList.add('hidden');
      if (currentCell) {
        handlePopupClose(currentCell);
        currentCell = null;
      }
    }
  });
  
  documentClickHandlerAdded = true;
}

// Call this when the page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', addGlobalClickHandler);
} else {
  addGlobalClickHandler();
}

function triggerFullConfettiFall() {
  const particleBursts = 40;
  for (let i = 0; i < particleBursts; i++) {
    confetti({
      particleCount: 5,
      angle: 270,
      spread: 180,
      startVelocity: 20,
      gravity: 1.8,
      ticks: 1000,
      scalar: 1.5,
      zIndex: 1000,
      origin: {x: Math.random(), y: 0},
    });
  }
}

function handleCellClick(cell, name, source, year, e) {
  if (e.target.tagName.toLowerCase() === 'a') return;

  const popup = document.getElementById('status-popup');
  const popupStatus = document.getElementById('popup-status');
  const popupScore = document.getElementById('popup-score');

  if (currentCell === cell && popup.classList.contains('show')) {
    handlePopupClose(currentCell);
    popup.classList.remove('show');
    currentCell = null;
    return;
  }

  if (popup.classList.contains('show')) {
    handlePopupClose(currentCell);
    popup.classList.remove('show');
  }

  currentCell = cell;
  currentStatus = parseInt(cell.dataset.status || '0');

  popupStatus.textContent = statuses[currentStatus].label;
  popupStatus.dataset.status = statuses[currentStatus].label;
  popupStatus.classList.remove('green', 'yellow', 'red', 'white');
  if (statuses[currentStatus].className != 'white') {
    popupStatus.classList.add(statuses[currentStatus].className);
  }

  popupScore.textContent = cell.dataset.score || '0';

  const rect = cell.getBoundingClientRect();
  popup.style.top = `${window.scrollY + rect.bottom + 5}px`;
  popup.style.left = `${window.scrollX + rect.left + (rect.width / 2) - 60}px`;

  popup.classList.remove('hidden');
  setTimeout(() => popup.classList.add('show'), 10);

  popupScore.focus();
  const range = document.createRange();
  range.selectNodeContents(popupScore);
  range.collapse(false);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);

  const thisCell = cell;
  const thisName = name;
  const thisSource = source;
  const thisYear = parseInt(year);

  popupStatus.onclick = () => {
    if (isProfileMode) return;
    currentStatus = next[currentStatus];
    updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    if (currentStatus == 2) {
      triggerFullConfettiFall();
    }
  };

  popupScore.onblur = () => {
    if (isProfileMode) return;

    let raw = popupScore.textContent.trim();
    let score = parseInt(raw);
    if (isNaN(score)) score = 0;
    score = Math.max(0, Math.min(score, 100));

    let prevScore = thisCell.dataset.score;
    let scoreChanged = prevScore != score;

    thisCell.dataset.score = score;
    popupScore.textContent = score;

    if (scoreChanged && score == 100) {
      triggerFullConfettiFall();
    }
    if (scoreChanged && score != 100 && prevScore != 0) {
      popupScore.classList.add('bump');
      setTimeout(() => popupScore.classList.remove('bump'), 250);
    }

    if (score === 100) {
      currentStatus = 2;
      updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    } else if (score > 0 && scoreChanged) {
      currentStatus = 1;
      updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    }

    // Only sync to server if not in virtual contest mode
    if (!window.isVirtualContestMode) {
      const sessionToken = localStorage.getItem('sessionToken');
      fetch(apiUrl + '/api/update-problem-score', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({
          problem_name: thisName,
          source: thisSource,
          year: thisYear,
          score: score
        })
      });
    }
  };

  popupScore.addEventListener('keypress', (e) => {
    if (isProfileMode) {
      e.preventDefault();
      return;
    }
    if (!/[0-9]/.test(e.key) && e.key !== 'Enter') {
      e.preventDefault();
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      popupScore.blur();
    }
  });
}

function updateStatus(status, cell, name, source, year) {
  const statusObj = statuses[status];

  cell.dataset.status = status;

  cell.classList.remove('green', 'yellow', 'red', 'white');
  if (statusObj.className) {
    cell.classList.add(statusObj.className);
  }

  const popup = document.getElementById('status-popup');
  const popupStatus = document.getElementById('popup-status');
  
  if (popup && popupStatus) {
    popupStatus.textContent = statusObj.label;
    popupStatus.dataset.status = statusObj.label;

    popupStatus.classList.remove('green', 'yellow', 'red', 'white');
    if (statusObj.className != 'white') {
      popupStatus.classList.add(statusObj.className);
    }
  }

  // Only sync to server if not in virtual contest mode
  if (!window.isVirtualContestMode) {
    const sessionToken = localStorage.getItem('sessionToken');
    fetch(apiUrl + '/api/update-problem-status', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`
      },
      body: JSON.stringify(
          {problem_name: name, source: source, year: year, status: status})
    });
  }
}

function handlePopupClose(cell) {
  if (isProfileMode) return;

  const score = parseInt(cell.dataset.score || '0');
  const status = parseInt(cell.dataset.status || '0');
  const name = cell.dataset.problemId;
  const source = cell.dataset.source;
  const year = parseInt(cell.dataset.year);

  if (status === 2 || status === 0) {
    const finalScore = status === 2 ? 100 : 0;
    if (cell.dataset.score == finalScore) {
      return;
    }
    cell.dataset.score = finalScore;
    
    const popupScore = document.getElementById('popup-score');
    if (popupScore) {
      popupScore.textContent = finalScore;
    }

    // Only sync to server if not in virtual contest mode
    if (!window.isVirtualContestMode) {
      const sessionToken = localStorage.getItem('sessionToken');
      fetch(apiUrl + '/api/update-problem-score', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify(
            {problem_name: name, source: source, year: year, score: finalScore})
      });
    }
  }
}