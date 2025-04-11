const statuses = [
  {label: 'Unattempted', color: '', value: 0},
  {label: 'In progress', color: '#ffd966', value: 1},
  {label: 'Solved', color: '#7dbf7d', value: 2},
  {label: 'Failed', color: '#f47174', value: 3}
];

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

document.querySelectorAll('.problem-cell').forEach(cell => {
  const name = cell.dataset.problemId?.trim();
  const source = cell.dataset.source?.trim();
  const year = cell.dataset.year?.trim();
  if (!name || !source || !year) return;

  cell.style.backgroundColor =
      statuses[parseInt(cell.dataset.status || '0')].color;

  cell.addEventListener('click', (e) => {
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
    popupStatus.style.backgroundColor = statuses[currentStatus].color;

    popupScore.textContent = cell.dataset.score || '0';

    const rect = cell.getBoundingClientRect();
    popup.style.top = `${window.scrollY + rect.bottom + 5}px`;
    popup.style.left =
        `${window.scrollX + rect.left + (rect.width / 2) - 60}px`;

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
      currentStatus = (currentStatus + 1) % statuses.length;
      updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
    };

    popupScore.onblur = () => {
      let raw = popupScore.textContent.trim();
      let score = parseInt(raw);
      if (isNaN(score)) score = 0;
      score = Math.max(0, Math.min(score, 100));

      let scoreChanged =
          thisCell.dataset.score != score && thisCell.dataset.score != 0;

      thisCell.dataset.score = score;
      popupScore.textContent = score;

      if (scoreChanged) {
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
      } else if (score > 0 && currentStatus != 3) {
        currentStatus = 1;  // In progress
        updateStatus(currentStatus, thisCell, thisName, thisSource, thisYear);
      }

      fetch('/api/update-problem-score', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
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
  });
});

function updateStatus(status, cell, name, source, year) {
  cell.dataset.status = status;
  cell.style.backgroundColor = statuses[status].color;
  popupStatus.textContent = statuses[status].label;
  popupStatus.style.backgroundColor = statuses[status].color;
  popupStatus.dataset.status = statuses[status].label;

  fetch('/api/update-problem-status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
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
    cell.dataset.score = finalScore;
    popupScore.textContent = finalScore;

    fetch('/api/update-problem-score', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(
          {problem_name: name, source: source, year: year, score: finalScore})
    });
  }
}
