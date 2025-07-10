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

const count = {
  counts: {red: 0, yellow: 0, green: 0, white: 0},
  update(key, diff) {
    if (key in this.counts) {
      this.counts[key] += diff;
      const el = document.getElementById(`${key}-count`);
      if (el) el.textContent = this.counts[key];
      let total = 0;
      for (const color in this.counts) {
        total += this.counts[color];
      }
      for (const color in this.counts) {
        const el = document.querySelector(`.progress-segment.${color}`);
        if (el) {
          el.style.width = `${(this.counts[color] / total) * 100}%`;
        }
      }
    }
  }
};

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

let isProfileMode = false;

function handleCellClick(cell, name, source, year, e) {
  if (e.target.tagName.toLowerCase() === 'a') return;

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

document.querySelectorAll('.problem-cell').forEach(cell => {
  const name = cell.dataset.problemId?.trim();
  const source = cell.dataset.source?.trim();
  const year = cell.dataset.year?.trim();
  if (!name || !source || !year) return;

  const statusIndex = parseInt(cell.dataset.status || '0');
  const statusObj = statuses[statusIndex];
  popupStatus.classList.remove('green', 'yellow', 'red', 'white');
  count.update(statusObj.className, 1);
  if (statusObj?.className && statusObj.className != 'white') {
    cell.classList.add(statusObj.className);
  }

  cell.addEventListener(
      'click', (e) => handleCellClick(cell, name, source, year, e));
});

function updateStatus(status, cell, name, source, year) {
  const sessionToken = localStorage.getItem('sessionToken');
  const statusObj = statuses[status];

  const oldStatus = statuses[parseInt(cell.dataset.status || '0')];
  if (oldStatus) count.update(oldStatus.className, -1);

  cell.dataset.status = status;

  cell.classList.remove('green', 'yellow', 'red', 'white');
  if (statusObj.className) {
    cell.classList.add(statusObj.className);
    count.update(statusObj.className, 1);
  }
  popupStatus.textContent = statusObj.label;
  popupStatus.dataset.status = statusObj.label;

  popupStatus.classList.remove('green', 'yellow', 'red', 'white');
  if (statusObj.className != 'white') {
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
    let prefix = from;
    if (prefix === 'JOIFR') {
      prefix = 'JOI';
    } else if (
      prefix === 'NOIPRELIM' || prefix === 'NOIQUAL' ||
      prefix === 'NOIFINAL' || prefix === 'NOISEL'
    ) {
      prefix = 'NOI';
    }

    if (prefix === 'GKS') {
      // --- Year header row ---
      const yearRow = document.createElement('tr');
      const yearCell = document.createElement('td');
      yearCell.className = 'year-cell';
      yearCell.textContent = `${prefix} ${year}`;
      yearRow.appendChild(yearCell);
      tbody.appendChild(yearRow);

      // --- Group by `extra` ---
      const extraMap = {};
      for (const problem of problems) {
        const key = problem.extra || 'No Extra';
        if (!extraMap[key]) extraMap[key] = [];
        extraMap[key].push(problem);
      }

      // --- Sort extras lexically ---
      const sortedExtras = Object.keys(extraMap).sort();

      // --- One row per extra category ---
      for (const extra of sortedExtras) {
        const extraRow = document.createElement('tr');

        // extra label cell (reusing 'day-cell' class)
        const extraCell = document.createElement('td');
        extraCell.className = 'day-cell';
        extraCell.textContent = extra;
        extraRow.appendChild(extraCell);

        // problem cells, as many as there are in this extra group
        for (const problem of extraMap[extra]) {
          const cell = document.createElement('td');
          cell.className = 'problem-cell';

          // apply status class & count
          const status = statuses.find(s => s.value === problem.status);
          if (status?.className) {
            cell.classList.add(status.className);
            count.update(status.className, 1);
          }

          // data attributes
          cell.dataset.status = problem.status;
          cell.dataset.problemId = problem.name;
          cell.dataset.source = problem.source;
          cell.dataset.year = problem.year;
          cell.dataset.score = problem.score;

          // link
          const link = document.createElement('a');
          link.href = problem.link;
          link.target = '_blank';
          link.textContent = problem.name;
          cell.appendChild(link);

          // click handler
          cell.addEventListener(
            'click',
            e => handleCellClick(cell, problem.name, from, problem.year, e)
          );

          extraRow.appendChild(cell);
        }

        tbody.appendChild(extraRow);
      }

    } else {
      // --- Original logic for other prefixes ---
      const row = document.createElement('tr');
      const yearCell = document.createElement('td');
      yearCell.className = 'year-cell';
      yearCell.textContent = `${prefix} ${year}`;
      row.appendChild(yearCell);

      for (const problem of problems) {
        const cell = document.createElement('td');
        cell.className = 'problem-cell';

        const status = statuses.find(s => s.value === problem.status);
        if (status?.className) {
          cell.classList.add(status.className);
          count.update(status.className, 1);
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
          e => handleCellClick(cell, problem.name, from, problem.year, e)
        );

        row.appendChild(cell);
      }

      tbody.appendChild(row);
    }
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
            count.update(status.className, 1);
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
  const fullPath = window.location.pathname;
  const basePath = document.querySelector('base')?.getAttribute('href') || '/';
  const relativePath = fullPath.startsWith(basePath) ? fullPath.slice(basePath.length) : fullPath;

  const isProfilePage = relativePath.startsWith('profile/');
  
  // Default order
  let sources = [
    'APIO', 'EGOI', 'INOI', 'ZCO', 'IOI', 'JOIFR', 'JOISC', 'IOITC',
    'NOIPRELIM', 'NOIQUAL', 'NOIFINAL', 'POI', 'NOISEL', 'CEOI', 'COI', 'BOI',
    'GKS'
  ];

  // Render containers immediately with skeletons and hidden <h2>s
  const olympiadList = document.getElementById('olympiad-list');
  sources.forEach(src => {
    const container = document.getElementById(`${src.toLowerCase()}-container`);
    if (container) {
      container.querySelector('h2').style.visibility = 'hidden';
      container.querySelector('table').innerHTML = generateSkeletonRows(10);
      olympiadList.appendChild(container);
    }
  });

  // Fetch user info
  const whoamiRes = await fetch(`${apiUrl}/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });

  let username = '';
  if (whoamiRes.ok) {
    const { username: uname } = await whoamiRes.json();
    username = uname;
  }

  if (!isProfilePage && !whoamiRes.ok) {
    return window.location.href = 'login.html';
  }

  // Attempt to fetch saved order
  try {
    let req = `${apiUrl}/api/get-olympiad-order`;
    const uname = isProfilePage ? relativePath.split('/')[1] : username;
    req += `?username=${uname}`;

    const orderResponse = await fetch(req, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Authorization': `Bearer ${sessionToken}` }
    });

    if (orderResponse.ok) {
      const { olympiad_order } = await orderResponse.json();
      if (Array.isArray(olympiad_order) && olympiad_order.length > 0) {
        sources = olympiad_order.map(id => id.toUpperCase());
        // Reorder existing DOM nodes
        sources.forEach(src => {
          const container = document.getElementById(`${src.toLowerCase()}-container`);
          if (container) olympiadList.appendChild(container);
        });
      }
    }
  } catch (err) {
    console.error('Failed to fetch olympiad order:', err);
  }

  // Set title
  if (isProfilePage) {
    const uname = relativePath.split('/')[1];
    document.getElementById('page-title').textContent = `${uname}'s OI Checklist`;
  } else {
    document.getElementById('page-title').textContent = `OI Checklist`;
  }

  // Fetch and render actual data
  if (isProfilePage) {
    document.getElementById('welcome-message').style.display = 'none';
    document.getElementById('logout-button').style.display = 'none';
    document.getElementById('settings-container').style.display = 'none';

    const uname = relativePath.split('/')[1];
    const namesParam = sources.join(',');

    const res = await fetch(
      `${apiUrl}/api/user?username=${uname}&problems=${namesParam}`,
      { method: 'GET', credentials: 'include' });

    if (res.status === 404) {
      document.body.innerHTML = `<h2 style="text-align:center;margin-top:2em;">
        Error: user “${uname}” does not exist.
      </h2>`;
      return;
    }
    if (res.status === 403) {
      document.body.innerHTML = `<h2 style="text-align:center;margin-top:2em;">
        ${uname}'s checklist is private.
      </h2>`;
      return;
    }
    if (!res.ok) {
      document.body.innerHTML = `<h2 style="text-align:center;margin-top:2em;">
        Unexpected error (${res.status})
      </h2>`;
      return;
    }

    const profileData = await res.json();
    count.update('red', 0);
    count.update('yellow', 0);
    count.update('green', 0);
    count.update('white', 0);

    isProfileMode = true;
    cachedProblemsData = profileData.problems;

    sources.forEach(src => {
      const tbl = document.getElementById(`${src.toLowerCase()}-container`)
                      .querySelector('table');
      tbl.innerHTML = '';
      if (src === 'JOISC')
        loadProblemsWithDay('JOISC', 4);
      else if (src === 'IOITC')
        loadProblemsWithDay('IOITC', 3);
      else
        loadProblems(src);
    });

  } else {
    document.getElementById('welcome-message').textContent = `Welcome, ${username}`;
    count.update('red', 0);
    count.update('yellow', 0);
    count.update('green', 0);
    count.update('white', 0);

    const res = await fetch(`${apiUrl}/api/problems?names=${sources.join(',')}`, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Authorization': `Bearer ${sessionToken}` }
    });

    if (!res.ok) return window.location.href = 'login.html';

    cachedProblemsData = await res.json();

    sources.forEach(src => {
      const tbl = document.getElementById(`${src.toLowerCase()}-container`)
                      .querySelector('table');
      tbl.innerHTML = '';
      if (src === 'JOISC')
        loadProblemsWithDay('JOISC', 4);
      else if (src === 'IOITC')
        loadProblemsWithDay('IOITC', 3);
      else
        loadProblems(src);
    });
  }

  // Reveal headers now that loading is done
  document.querySelectorAll('#olympiad-list h2').forEach(h2 => {
    h2.style.visibility = 'visible';
  });
};

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
    GKS: 'Google Kick Start'
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

const settingsButton = document.getElementById('settings-button');
const dropdown = document.getElementById('settings-dropdown');
const settingsContainer =
    settingsButton
        .parentElement;  // Get the parent container (.settings-container)
// Correctly reference the visibility item div by its new ID
const checklistVisibilityItem =
    document.getElementById('checklist-visibility-item');

// Helper: Update the text content, data-state, and color classes of the
// visibility item
function updateVisibilityUI(itemElement, isPublic) {
  // Find the label span within the item element
  const labelSpan = itemElement.querySelector('.settings-label');
  if (labelSpan) {
    // Update the text content of the span
    labelSpan.textContent =
        `Checklist Visibility: ${isPublic ? 'Public' : 'Private'}`;
  }

  // Set the data-state attribute on the item element itself
  itemElement.setAttribute('data-state', isPublic ? 'public' : 'private');

  // Remove existing color classes and add the new one
  // Include any color classes you might use for items here
  itemElement.classList.remove('red', 'green', 'yellow', 'white');
  if (isPublic) {
    itemElement.classList.add('green');  // Add 'green' class for public state
  } else {
    itemElement.classList.add('red');  // Add 'red' class for private state
  }
  // If you have other states/colors for items, add logic here
}

// Outside click handler - Simplified permanent listener
function handleOutsideClick(e) {
  // If the click target is NOT inside the settings container
  if (!settingsContainer.contains(e.target)) {
    // Only close if the dropdown is currently active to avoid unnecessary calls
    if (settingsContainer.classList.contains('active')) {
      settingsContainer.classList.remove('active');
      settingsButton.setAttribute('aria-expanded', 'false');
    }
  }
}

// Attach the outside click handler once to the document
document.addEventListener('click', handleOutsideClick);


// Settings button click
settingsButton.addEventListener('click', async (event) => {
  event.stopPropagation();  // Prevent click from bubbling up to document
                            // listener

  const isActive = settingsContainer.classList.contains('active');
  // Toggle the active state of the container
  settingsContainer.classList.toggle('active', !isActive);
  // Update aria-expanded state for accessibility
  settingsButton.setAttribute('aria-expanded', !isActive);

  // If we are opening the dropdown, fetch the current setting
  if (!isActive) {
    try {
      const sessionToken = localStorage.getItem('sessionToken');
      const response = await fetch(`${apiUrl}/api/settings`, {
        method: 'GET',
        credentials: 'include',  // Include cookies if necessary
        headers: {'Authorization': `Bearer ${sessionToken}`}
      });

      if (!response.ok) {
        // Handle HTTP errors (e.g., 401, 404, 500)
        console.error(
            'Error fetching settings:', response.status, response.statusText);
        // Optional: Close dropdown and revert button state on fetch failure
        settingsContainer.classList.remove('active');
        settingsButton.setAttribute('aria-expanded', 'false');
        // Optional: Show an error state or message in the UI (e.g., on the
        // settings button or item)
        return;  // Stop execution
      }

      const data = await response.json();
      // Update the UI based on the fetched state (using the
      // checklistVisibilityItem element)
      updateVisibilityUI(checklistVisibilityItem, data.checklist_public);

    } catch (err) {
      // Handle network errors or errors parsing JSON
      console.error('Error fetching settings:', err);
      // Optional: Close dropdown and revert button state on fetch failure
      settingsContainer.classList.remove('active');
      settingsButton.setAttribute('aria-expanded', 'false');
      // Optional: Show an error state or message in the UI
    }
  }
  // If we are closing the dropdown, no extra action is needed here
});


// Toggle checklist visibility on item click
// Listen for clicks on the entire checklistVisibilityItem div
checklistVisibilityItem.addEventListener('click', async () => {
  // Get the current state from the data attribute on the item div
  const currentState = checklistVisibilityItem.getAttribute('data-state');
  // Determine the new state (invert the current state)
  const newStateIsPublic = currentState ===
      'private';  // If currently private, the new state is public

  // Optimistically update the UI immediately (pass the item element)
  updateVisibilityUI(checklistVisibilityItem, newStateIsPublic);

  try {
    const sessionToken = localStorage.getItem('sessionToken');
    const response = await fetch(`${apiUrl}/api/settings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`  // Correctly adding the token
      },
      // Send the new boolean state in the request body
      body: JSON.stringify({checklist_public: newStateIsPublic})
    });

    if (!response.ok) {
      console.error(
          'Error updating settings:', response.status, response.statusText);
      // Revert the UI state if the save failed (pass the item element)
      updateVisibilityUI(
          checklistVisibilityItem,
          !newStateIsPublic);  // Go back to the previous state
      // Optional: Show a temporary error message next to the item
      return;  // Stop execution
    }
    // Optional: Add visual feedback for successful save (e.g., brief background
    // flash, checkmark icon)
    console.log(
        'Settings updated successfully:',
        newStateIsPublic ? 'Public' : 'Private');

  } catch (err) {
    console.error('Error updating settings:', err);
    // Revert the UI state if the save failed due to network error etc. (pass
    // the item element)
    updateVisibilityUI(
        checklistVisibilityItem,
        !newStateIsPublic);  // Go back to the previous state
                             // Optional: Show a temporary error message next to
                             // the item
  }
});