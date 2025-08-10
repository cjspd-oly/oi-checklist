// Count tracking for dashboard
const count = {
  counts: {red: 0, yellow: 0, green: 0, white: 0},
  sectionCounts: {}, // Track counts per section
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
  },
  updateSection(sectionId, key, diff) {
    if (!this.sectionCounts[sectionId]) {
      this.sectionCounts[sectionId] = {red: 0, yellow: 0, green: 0, white: 0};
    }
    
    if (key in this.sectionCounts[sectionId]) {
      this.sectionCounts[sectionId][key] += diff;
      
      // Update section progress bar
      let sectionTotal = 0;
      for (const color in this.sectionCounts[sectionId]) {
        sectionTotal += this.sectionCounts[sectionId][color];
      }
      
      if (sectionTotal > 0) {
        for (const color in this.sectionCounts[sectionId]) {
          const el = document.querySelector(`#${sectionId}-container .section-progress-bar .progress-segment.${color}`);
          if (el) {
            el.style.width = `${(this.sectionCounts[sectionId][color] / sectionTotal) * 100}%`;
          }
        }
      }
    }
  }
};

function createOlympiadContainer(olympiadId) {
  const container = document.createElement('div');
  container.className = 'table-container';
  container.id = `${olympiadId.toLowerCase()}-container`;
  
  if (olympiadId === 'USACO') {
    // Special handling for USACO with tabs
    container.innerHTML = `
      <div class="usaco-header">
        <h2>${getFullOlympiadName(olympiadId)}</h2>
        <div class="usaco-tab-buttons" style="display: none;">
          <button data-tab="usacoplatinum" class="usaco-tab platinum">Platinum</button>
          <button data-tab="usacogold" class="usaco-tab gold">Gold</button>
          <button data-tab="usacosilver" class="usaco-tab silver">Silver</button>
          <button data-tab="usacobronze" class="usaco-tab bronze">Bronze</button>
        </div>
      </div>
      <div class="section-progress-bar">
        <div class="progress-segment red"></div>
        <div class="progress-segment yellow"></div>
        <div class="progress-segment green"></div>
        <div class="progress-segment white"></div>
      </div>
      <div id="usacoplatinum-container" class="usaco-tab-content">
        <table class="problem-table"></table>
      </div>
      <div id="usacogold-container" class="usaco-tab-content hidden">
        <table class="problem-table"></table>
      </div>
      <div id="usacosilver-container" class="usaco-tab-content hidden">
        <table class="problem-table"></table>
      </div>
      <div id="usacobronze-container" class="usaco-tab-content hidden">
        <table class="problem-table"></table>
      </div>
    `;
    
    // Add event listeners for USACO tabs after creating the container
    setTimeout(() => {
      container.querySelectorAll('.usaco-tab').forEach(btn => {
        btn.addEventListener('click', () => {
          const tab = btn.dataset.tab;

          container.querySelectorAll('.usaco-tab-content').forEach(el => {
            el.classList.add('hidden');
          });

          document.getElementById(`${tab}-container`).classList.remove('hidden');
        });
      });
    }, 0);
    
  } else {
    // Standard olympiad container
    const h2 = document.createElement('h2');
    h2.textContent = getFullOlympiadName(olympiadId);
    h2.style.visibility = 'hidden';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'section-progress-bar';
    progressBar.innerHTML = `
      <div class="progress-segment red"></div>
      <div class="progress-segment yellow"></div>
      <div class="progress-segment green"></div>
      <div class="progress-segment white"></div>
    `;
    
    const table = document.createElement('table');
    table.className = 'problem-table';
    table.innerHTML = generateSkeletonRows(10);
    
    container.appendChild(h2);
    container.appendChild(progressBar);
    container.appendChild(table);
  }
  
  return container;
}

document.querySelectorAll('.problem-cell').forEach(cell => {
  const name = cell.dataset.problemId?.trim();
  const source = cell.dataset.source?.trim();
  const year = cell.dataset.year?.trim();
  if (!name || !source || !year) return;

  const statusIndex = parseInt(cell.dataset.status || '0');
  const statusObj = statuses[statusIndex];
  count.update(statusObj.className, 1);
  if (statusObj?.className && statusObj.className != 'white') {
    cell.classList.add(statusObj.className);
  }

  cell.addEventListener(
      'click', (e) => handleCellClick(cell, name, source, year, e));
});

function updateStatusWithCount(status, cell, name, source, year) {
  const sessionToken = localStorage.getItem('sessionToken');
  const statusObj = statuses[status];

  const oldStatus = statuses[parseInt(cell.dataset.status || '0')];
  if (oldStatus) count.update(oldStatus.className, -1);

  // Use the shared updateStatus function
  updateStatus(status, cell, name, source, year);
  
  // Update count for dashboard
  count.update(statusObj.className, 1);

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

function handlePopupCloseWithServer(cell) {
  if (isProfileMode) return;

  const score = parseFloat(cell.dataset.score) || 0;
  const status = parseInt(cell.dataset.status || '0');
  const name = cell.dataset.problemId;
  const source = cell.dataset.source;
  const year = parseInt(cell.dataset.year);

  // Use the shared handlePopupClose function
  handlePopupClose(cell);

  if (status === 2 || status === 0) {
    const finalScore = status === 2 ? 100 : 0;
    if (Math.abs(parseFloat(cell.dataset.score) - finalScore) < 0.001) { // Handle floating point comparison
      return;
    }
    
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

  const monthOrder = {
    January: 1, February: 2, March: 3, April: 4,
    May: 5, June: 6, July: 7, August: 8,
    September: 9, October: 10, November: 11, December: 12,
    "First Contest": 13, "Second Contest": 14, "Third Contest": 15,
    Open: 16
  };

  // Get year sort order from localStorage
  const yearSortOrder = localStorage.getItem('yearSortOrder') || 'asc';
  const sortedYears = Object.keys(yearMap).sort((a, b) => {
    return yearSortOrder === 'asc' ? a - b : b - a;
  });

  for (const year of sortedYears) {
    const problems = yearMap[year];

    let prefix = from;
    let was_joioc = false;
    if (prefix === 'JOIFR' || prefix === 'JOIOC') {
      if (prefix === 'JOIOC') {
        was_joioc = true;
      }
      prefix = 'JOI';
    } else if (
      prefix === 'NOIPRELIM' || prefix === 'NOIQUAL' ||
      prefix === 'NOIFINAL' || prefix === 'NOISEL'
    ) {
      prefix = 'NOI';
    }

    const isUsaco = prefix.startsWith('USACO');
    if (isUsaco) {
      if (prefix === 'USACOGOLD') {
        prefix = 'Gold';
      } else if (prefix === 'USACOSILVER') {
        prefix = 'Silver';
      } else if (prefix === 'USACOBRONZE') {
        prefix = 'Bronze';
      } else {
        prefix = 'Platinum';
      }
    }
    const isGroupedByExtra = prefix === 'GKS' || isUsaco || was_joioc;

    if (isGroupedByExtra) {
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

      // --- Sort extras ---
      const sortedExtras = Object.keys(extraMap).sort((a, b) => {
        // Handle Day X pattern
        const dayRegex = /^Day\s+(\d+)$/;
        const matchA = a.match(dayRegex);
        const matchB = b.match(dayRegex);
        if (matchA && matchB) {
          return parseInt(matchA[1]) - parseInt(matchB[1]);
        }
        // Normal monthOrder-based sorting
        const orderA = monthOrder[a] || 99;
        const orderB = monthOrder[b] || 99;
        if (orderA !== orderB) {
          return orderA - orderB;
        }
        // Fallback: alphabetical
        return a.localeCompare(b);
      });

      for (const extra of sortedExtras) {
        if (extra === 'No Extra') {
          // CHANGE: Add these problems directly to the year row instead of a new row
          for (const problem of extraMap[extra]) {
            const cell = document.createElement('td');
            cell.className = 'problem-cell';

            const status = statuses.find(s => s.value === problem.status);
            if (status?.className) {
              cell.classList.add(status.className);
              count.update(status.className, 1);
              count.updateSection(from.toLowerCase(), status.className, 1);
              if (from.startsWith('USACO')) {
                count.updateSection('usaco', status.className, 1);
              }
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
            link.addEventListener('click', e => e.stopPropagation());
            cell.appendChild(link);

            cell.addEventListener(
              'click',
              e => handleCellClick(cell, problem.name, from, problem.year, e)
            );

            yearRow.appendChild(cell);
          }
        } else {
          // --- Regular extra row ---
          const extraRow = document.createElement('tr');
          const extraCell = document.createElement('td');
          extraCell.className = 'day-cell';
          extraCell.textContent = extra;
          extraRow.appendChild(extraCell);

          for (const problem of extraMap[extra]) {
            const cell = document.createElement('td');
            cell.className = 'problem-cell';

            const status = statuses.find(s => s.value === problem.status);
            if (status?.className) {
              cell.classList.add(status.className);
              count.update(status.className, 1);
              count.updateSection(from.toLowerCase(), status.className, 1);
              if (from.startsWith('USACO')) {
                count.updateSection('usaco', status.className, 1);
              }
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
            link.addEventListener('click', e => e.stopPropagation());
            cell.appendChild(link);

            cell.addEventListener(
              'click',
              e => handleCellClick(cell, problem.name, from, problem.year, e)
            );

            extraRow.appendChild(cell);
          }

          tbody.appendChild(extraRow);
        }
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
          count.updateSection(from.toLowerCase(), status.className, 1);
          
          // Also update the parent USACO container if this is a USACO division
          if (from.startsWith('USACO')) {
            count.updateSection('usaco', status.className, 1);
          }
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
        
        // Prevent cell click handler from firing when link is clicked
        link.addEventListener('click', (e) => {
          e.stopPropagation();
        });
        
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

  // Get year sort order from localStorage
  const yearSortOrder = localStorage.getItem('yearSortOrder') || 'asc';
  const sortedYears = Object.keys(yearMap).sort((a, b) => {
    return yearSortOrder === 'asc' ? a - b : b - a;
  });

  for (const year of sortedYears) {
    const problems = yearMap[year];
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
            count.updateSection(source.toLowerCase(), status.className, 1);
            
            // Also update the parent USACO container if this is a USACO division
            if (source.startsWith('USACO')) {
              count.updateSection('usaco', status.className, 1);
            }
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
          
          // Prevent cell click handler from firing when link is clicked
          link.addEventListener('click', (e) => {
            e.stopPropagation();
          });
          
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

      const hasProblem = [...dayRow.children].some(td =>
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
  let sources = olympiadIds.flatMap(id =>
    id === 'USACO'
      ? ['USACOPLATINUM', 'USACOGOLD', 'USACOSILVER', 'USACOBRONZE']
      : id
  );
  // Create and render containers dynamically with skeletons
  const olympiadList = document.getElementById('olympiad-list');
  sources.forEach(src => {
    if (src === 'USACO') {
      // Create USACO container with all its sub-containers
      const usacoContainer = createOlympiadContainer('USACO');
      olympiadList.appendChild(usacoContainer);
    } else if (!src.startsWith('USACO')) {
      // Create regular olympiad containers
      const container = createOlympiadContainer(src);
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
    return window.location.href = 'home';
  }

  // Attempt to fetch saved order
  try {
    let req = `${apiUrl}/api/get-olympiad-order`;
    const uname = isProfilePage ? relativePath.split('/')[1] : username;
    req += `?username=${uname}`;

    const orderResponse = await fetch(req, {
      method: 'GET',
      credentials: 'include',
    });

    if (orderResponse.ok) {
      const { olympiad_order } = await orderResponse.json();
      if (Array.isArray(olympiad_order) && olympiad_order.length > 0) {
        sources = olympiad_order.map(id => id.toUpperCase());
        // Clear and recreate containers in the new order
        olympiadList.innerHTML = '';
        sources.forEach(src => {
          if (src === 'USACO') {
            // Create USACO container with all its sub-containers
            const usacoContainer = createOlympiadContainer('USACO');
            olympiadList.appendChild(usacoContainer);
          } else if (!src.startsWith('USACO')) {
            // Create regular olympiad containers
            const container = createOlympiadContainer(src);
            olympiadList.appendChild(container);
          }
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
    sources = sources.flatMap(src => {
      if (src === 'USACO') {
        return ['USACOPLATINUM', 'USACOGOLD', 'USACOSILVER', 'USACOBRONZE'];
      }
      return src;
    });
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
      let tbl;
      if (src.startsWith('USACO')) {
        // For USACO divisions, look inside the nested container
        const container = document.getElementById(`${src.toLowerCase()}-container`);
        tbl = container?.querySelector('table');
      } else {
        // For regular olympiads, look in the main container
        const container = document.getElementById(`${src.toLowerCase()}-container`);
        tbl = container?.querySelector('table');
      }
      
      if (tbl) {
        tbl.innerHTML = '';
        if (src === 'JOISC')
          loadProblemsWithDay('JOISC', 4);
        else if (src === 'IOITC')
          loadProblemsWithDay('IOITC', 3);
        else
          loadProblems(src);
      }
    });
  } else {
    document.getElementById('welcome-message').textContent = `Welcome, ${username}`;
    count.update('red', 0);
    count.update('yellow', 0);
    count.update('green', 0);
    count.update('white', 0);

    sources = sources.flatMap(src => {
      if (src === 'USACO') {
        return ['USACOPLATINUM', 'USACOGOLD', 'USACOSILVER', 'USACOBRONZE'];
      }
      return src;
    });
    const res = await fetch(`${apiUrl}/api/problems?names=${sources.join(',')}`, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Authorization': `Bearer ${sessionToken}` }
    });

    if (!res.ok) return window.location.href = 'home';

    cachedProblemsData = await res.json();

    sources.forEach(src => {
      let tbl;
      if (src.startsWith('USACO')) {
        // For USACO divisions, look inside the nested container
        const container = document.getElementById(`${src.toLowerCase()}-container`);
        tbl = container?.querySelector('table');
      } else {
        // For regular olympiads, look in the main container
        const container = document.getElementById(`${src.toLowerCase()}-container`);
        tbl = container?.querySelector('table');
      }
      
      if (tbl) {
        tbl.innerHTML = '';
        if (src === 'JOISC')
          loadProblemsWithDay('JOISC', 4);
        else if (src === 'IOITC')
          loadProblemsWithDay('IOITC', 3);
        else
          loadProblems(src);
      }
    });
  }

  // Reveal headers now that loading is done
  document.querySelectorAll('#olympiad-list h2').forEach(h2 => {
    h2.style.visibility = 'visible';
  });
  // Reveal USACO tab buttons
  document.querySelectorAll('.usaco-tab-buttons').forEach(el => {
    el.style.display = 'flex';
  });
};

// Settings dropdown toggle
document.addEventListener('DOMContentLoaded', function() {
  const settingsButton = document.getElementById('settings-button');
  const settingsContainer = document.getElementById('settings-container');
  const settingsDropdown = document.getElementById('settings-dropdown');
  
  if (settingsButton && settingsContainer && settingsDropdown) {
    settingsButton.addEventListener('click', function(e) {
      e.stopPropagation();
      settingsContainer.classList.toggle('active');
      settingsButton.setAttribute('aria-expanded', settingsContainer.classList.contains('active'));
    });
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
      if (!settingsContainer.contains(e.target)) {
        settingsContainer.classList.remove('active');
        settingsButton.setAttribute('aria-expanded', 'false');
      }
    });
  }
});