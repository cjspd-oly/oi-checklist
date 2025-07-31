window.onload = async () => {
  const sessionToken = localStorage.getItem('sessionToken');

  // Verify login
  const res = await fetch(`${apiUrl}/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });

  if (!res.ok) return window.location.href = 'home';

  const { username } = await res.json();
  document.getElementById('welcome-message').textContent = `Welcome, ${username}`;

  // Load user's olympiad order
  const orderRes = await fetch(`${apiUrl}/api/get-olympiad-order?username=${username}`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });

  if (orderRes.ok) {
    const data = await orderRes.json();
    if (data.olympiad_order && Array.isArray(data.olympiad_order)) {
      applyOlympiadOrder(data.olympiad_order);
    }
  }

  // Unhide all H3s after DOM has been updated
  document.querySelectorAll('#olympiad-reorder-list h3').forEach(h3 => {
    h3.style.visibility = 'visible';
  });

  // Init Sortable
  new Sortable(document.getElementById('olympiad-reorder-list'), {
    animation: 150,
    ghostClass: 'dragging'
  });
};

// Reorders DOM based on saved order
function applyOlympiadOrder(order) {
  const container = document.getElementById('olympiad-reorder-list');
  const cards = Array.from(container.children);
  const cardMap = new Map(cards.map(card => [card.dataset.id, card]));

  container.innerHTML = '';

  const seen = new Set();
  for (const id of order) {
    const card = cardMap.get(id.toLowerCase());
    if (card) {
      container.appendChild(card);
      seen.add(id.toLowerCase());
    }
  }

  // Append any leftover cards not in order
  for (const [id, card] of cardMap.entries()) {
    if (!seen.has(id.toLowerCase())) {
      container.appendChild(card);
    }
  }
}

function saveOlympiadOrder() {
  const order = Array.from(document.querySelectorAll('#olympiad-reorder-list .connection-card'))
    .map(card => card.dataset.id);

  const sessionToken = localStorage.getItem('sessionToken');
  const messageBox = document.getElementById('popup-message-oly-save');
  messageBox.style.display = 'block';
  let currentTheme = localStorage.getItem('theme') || 'light-mode';
  messageBox.color = currentTheme == 'light-mode' ? 'black' : 'white';

  fetch(apiUrl + '/api/update-olympiad-order', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${sessionToken}`
    },
    body: JSON.stringify({
      olympiad_order: order
    })
  })
  .then(response => response.json())
  .then(result => {
    if (result.success) {
      messageBox.textContent = 'Olympiad order saved!';
      messageBox.style.color = 'green';
    } else {
      messageBox.textContent = `Error saving order: ${result.error || 'unknown error'}`;
      messageBox.style.color = 'red';
    }
  })
  .catch(err => {
    console.error('Save failed:', err);
    messageBox.textContent = `Error saving order: ${result.error || 'unknown error'}`;
    messageBox.style.color = 'red';
  });
}
