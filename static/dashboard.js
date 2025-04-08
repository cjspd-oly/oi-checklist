const statuses = [
  {color: '', value: 0}, {color: '#ffd966', value: 1},  // In progress
  {color: '#7dbf7d', value: 2},                         // Solved
  {color: '#f47174', value: 3}                          // Failed
];

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.problem-cell').forEach(cell => {
    const link = cell.querySelector('a');
    const problemId = link?.textContent?.trim();

    currentStatus = parseInt(cell.dataset.status || '0');
    cell.style.backgroundColor = statuses[currentStatus].color;

    cell.addEventListener('click', e => {
      if (e.target.tagName.toLowerCase() === 'a') return;

      currentStatus = parseInt(cell.dataset.status || '0');
      const nextStatus = (currentStatus + 1) % statuses.length;
      cell.dataset.status = nextStatus;
      cell.style.backgroundColor = statuses[nextStatus].color;

      fetch('/api/update-problem-status', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({problem_name: problemId, status: nextStatus})
      });
    });
  });
});
