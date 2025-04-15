const statuses = [
  {label: 'Unattempted', className: 'white', value: 0},
  {label: 'In progress', className: 'yellow', value: 1},
  {label: 'Solved', className: 'green', value: 2},
  {label: 'Failed', className: 'red', value: 3}
];

const next = [1, 3, 0, 2];

const popup = document.getElementById('status-popup');
const popupStatus = document.getElementById('popup-status');
const popupScore = document.getElementById('popup-score');

let currentCell = null;
let currentStatus = 0;

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

  // If clicking the same cell, close the popup
  if (currentCell === cell && popup.classList.contains('show')) {
    handlePopupClose(currentCell);
    popup.classList.remove('show');
    currentCell = null;
    return;
  }

  // If switching cells, commit previous popup changes
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

  // Animate open
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
    currentStatus = next[currentStatus];
    updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    if (currentStatus == 2) {
      triggerFullConfettiFall();
    }
  };

  popupScore.onblur = () => {
    let raw = popupScore.textContent.trim();
    let score = parseInt(raw);
    if (isNaN(score)) score = 0;
    score = Math.max(0, Math.min(score, 100));

    let prevScore = thisCell.dataset.score;
    let scoreChanged = prevScore != score;

    thisCell.dataset.score = score;
    popupScore.textContent = score;

    if (scoreChanged && prevScore != 0) {
      if (score != 100) {
        popupScore.classList.add('bump');
        setTimeout(() => popupScore.classList.remove('bump'), 250);
      } else {
        triggerFullConfettiFall();
      }
    }

    if (score === 100) {
      currentStatus = 2;  // Solved
      updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    } else if (score > 0 && scoreChanged) {
      currentStatus = 1;  // In progress
      updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    }

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
  };

  popupScore.addEventListener('keypress', (e) => {
    if (!/[0-9]/.test(e.key) && e.key !== 'Enter') {
      e.preventDefault();
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      popupScore.blur();
    }
  });
}

document.querySelectorAll('.problem-cell').forEach(cell => {
  const name = cell.dataset.problemId?.trim();
  const source = cell.dataset.source?.trim();
  const year = cell.dataset.year?.trim();
  if (!name || !source || !year) return;

  const statusIndex = parseInt(cell.dataset.status || '0');
  const statusObj = statuses[statusIndex];
  popupStatus.classList.remove('green', 'yellow', 'red', 'white');
  if (statusObj?.className) {
    cell.classList.add(statusObj.className);
  }

  cell.addEventListener(
      'click', (e) => handleCellClick(cell, name, source, year, e));
});


function updateStatus(status, cell, name, source, year) {
  const sessionToken = localStorage.getItem('sessionToken');
  const statusObj = statuses[status];

  cell.dataset.status = status;

  // Remove previous status color classes
  cell.classList.remove('green', 'yellow', 'red', 'white');
  if (statusObj.className) {
    cell.classList.add(statusObj.className);
  }
  popupStatus.textContent = statusObj.label;
  popupStatus.dataset.status = statusObj.label;

  popupStatus.classList.remove('green', 'yellow', 'red', 'white');
  if (statusObj.className) {
    popupStatus.classList.add(statusObj.className);
  }

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

function handlePopupClose(cell) {
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
    popupScore.textContent = finalScore;
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

let cachedProblemsData = null;
async function loadProblems(from) {
  const yearMap = cachedProblemsData[from] || {};
  const container = document.getElementById(`${from.toLowerCase()}-container`);
  const table = container.querySelector('table');
  table.innerHTML = '';

  const tbody = document.createElement('tbody');

  for (const [year, problems] of Object.entries(yearMap)) {
    const row = document.createElement('tr');

    const yearCell = document.createElement('td');
    yearCell.className = 'year-cell';
    let prefix = from;
    if (prefix === 'JOIFR') {
      prefix = 'JOI';
    } else if (
        prefix === 'NOIPRELIM' || prefix === 'NOIQUAL' ||
        prefix === 'NOIFINAL') {
      prefix = 'NOI';
    }
    yearCell.textContent = `${prefix} ${year}`;
    row.appendChild(yearCell);

    for (const problem of problems) {
      const cell = document.createElement('td');
      const status = statuses.find(s => s.value === problem.status);
      cell.className = 'problem-cell';
      cell.dataset.status = problem.status;
      cell.dataset.problemId = problem.name;
      cell.dataset.source = problem.source;
      cell.dataset.year = problem.year;
      cell.dataset.score = problem.score;

      if (status?.className) {
        cell.classList.add(status.className);
      }

      const link = document.createElement('a');
      link.href = problem.link;
      link.target = '_blank';
      link.textContent = problem.name;

      cell.appendChild(link);
      cell.addEventListener(
          'click',
          (e) => handleCellClick(cell, problem.name, from, problem.year, e));
      row.appendChild(cell);
    }
    tbody.appendChild(row);
  }
  table.appendChild(tbody);
}

function loadProblemsWithDay(source, numDays) {
  const yearMap = cachedProblemsData[source] || {};
  const container =
      document.getElementById(`${source.toLowerCase()}-container`);
  const table = container.querySelector('table');
  table.innerHTML = '';

  const tbody = document.createElement('tbody');

  for (const [year, problems] of Object.entries(yearMap)) {
    const yearRow = document.createElement('tr');
    const yearCell = document.createElement('td');
    yearCell.className = 'year-cell';
    yearCell.textContent = `${source} ${year}`;
    yearRow.appendChild(yearCell);
    tbody.appendChild(yearRow);

    const problemMap = {};
    for (const problem of problems) {
      problemMap[problem.number] = problem;
    }

    for (let day = 0; day < numDays; day++) {
      const dayRow = document.createElement('tr');
      const dayCell = document.createElement('td');
      dayCell.className = 'day-cell';
      dayCell.textContent = `Day ${day + 1}`;
      dayRow.appendChild(dayCell);

      for (let i = 1; i <= 3; i++) {
        const problem = problemMap[day * 3 + i];
        const cell = document.createElement('td');
        cell.className = 'problem-cell';

        if (problem) {
          const status = statuses.find(s => s.value === problem.status);
          if (status?.className) {
            cell.classList.add(status.className);
          }

          cell.dataset.status = problem.status;
          cell.dataset.problemId = problem.name;
          cell.dataset.source = problem.source;
          cell.dataset.year = problem.year;
          cell.dataset.score = problem.score;

          const link = document.createElement('a');
          link.href = problem.link;
          link.target = '_blank';
          link.textContent = problem.name;
          cell.appendChild(link);

          cell.addEventListener(
              'click',
              (e) =>
                  handleCellClick(cell, problem.name, source, problem.year, e));
        } else {
          cell.classList.add('empty');
        }

        dayRow.appendChild(cell);
      }

      const hasProblem = [...dayRow.children].some(
          td =>
              td.classList.contains('problem-cell') && td.children.length > 0);
      if (hasProblem) {
        tbody.appendChild(dayRow);
      }
    }
  }

  table.appendChild(tbody);
}

window.onload = async () => {
  const sessionToken = localStorage.getItem('sessionToken');
  const sources = [
    'APIO', 'EGOI', 'INOI', 'ZCO', 'IOI', 'JOIFR', 'JOISC', 'IOITC',
    'NOIPRELIM', 'NOIQUAL', 'NOIFINAL', 'POI'
  ];

  // Show skeleton loading for all Olympiads
  sources.forEach(source => {
    const container =
        document.getElementById(`${source.toLowerCase()}-container`);
    const table = container.querySelector('table');
    table.innerHTML = generateSkeletonRows(10);
  });

  // Display username
  let res = await fetch(apiUrl + `/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: {'Authorization': `Bearer ${sessionToken}`}
  });
  if (res.ok) {
    const data = await res.json();
    document.getElementById('welcome-message').textContent =
        `Welcome, ${data.username}`;
  } else {
    window.location.href = 'login.html';
    return;
  }

  // Fetch problems data
  res = await fetch(apiUrl + `/api/problems?names=${sources.join(',')}`, {
    method: 'GET',
    credentials: 'include',
    headers: {'Authorization': `Bearer ${sessionToken}`}
  });
  if (res.status !== 200) {
    window.location.href = 'login.html';
    return;
  }

  cachedProblemsData = await res.json();

  // Clear skeleton
  sources.forEach(source => {
    const container =
        document.getElementById(`${source.toLowerCase()}-container`);
    const table = container.querySelector('table');
    table.innerHTML = '';  // Clear skeleton rows

    // Load actual problems
    if (source === 'JOISC') {
      loadProblemsWithDay('JOISC', 4);
    } else if (source === 'IOITC') {
      loadProblemsWithDay('IOITC', 3);
    } else {
      loadProblems(source);
    }
  });
};

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

document.getElementById('logout-button')
    .addEventListener('click', async (event) => {
      const sessionToken = localStorage.getItem('sessionToken');
      event.preventDefault();  // Prevents the default behavior of the <a> tag

      const res = await fetch(apiUrl + '/api/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {'Authorization': `Bearer ${sessionToken}`}
      });

      if (res.status === 200) {
        // Successfully logged out, you can redirect the user or update the UI
        window.location.href =
            'login.html';  // Redirect to login page after logout
      } else {
        // Handle error if something goes wrong
        console.error('Logout failed');
      }
    });

// Dark mode
document.addEventListener('DOMContentLoaded', function() {
  const toggleSwitch = document.getElementById('dark-mode-switch');
  const currentTheme = localStorage.getItem('theme');
  if (currentTheme) {
    if (currentTheme === 'dark-mode') {
      document.body.classList.add(currentTheme);
      toggleSwitch.checked = true;
    }
  } else {
    currentTheme = 'light-mode';
  }
  toggleSwitch.addEventListener('change', function(e) {
    if (e.target.checked) {
      document.body.classList.add('dark-mode');
      localStorage.setItem('theme', 'dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
      localStorage.setItem('theme', 'light-mode');
    }
  });
});