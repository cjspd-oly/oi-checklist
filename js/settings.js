// show welcome message
document.addEventListener("DOMContentLoaded", async () => {
  const session_token = localStorage.getItem('sessionToken');
  let whoamires = await fetch(`${apiUrl}/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Authorization': `Bearer ${session_token}` }
  });
  if (!whoamires.ok) return window.location.href = 'home';
  const { username } = await whoamires.json();
  document.getElementById('welcome-message').textContent = `Welcome, ${username}`;

  // also update that checklist visibility message
  document.getElementById('checklist-visibility-description').innerHTML = `Click to toggle your checklist's visibility at <a href='/profile/${username}' target='_blank' class='profile-link'>/profile/${username}</a>.`;

  // Fetch initial visibility state and set UI dynamically
  const checklistVisibilityItem = document.getElementById('checklist-visibility-item');
  const visibilityBadge = document.getElementById('visibility-badge');

  if (checklistVisibilityItem) {
    try {
      const response = await fetch(`${apiUrl}/api/settings`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Authorization': `Bearer ${session_token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const isPublic = data.checklist_public;
        updateVisibilityUI(checklistVisibilityItem, visibilityBadge, isPublic);
      }
    } catch (err) {
      console.error('Error fetching initial visibility state:', err);
    }
  }

  // Handle visibility toggle functionality
  const handleVisibilityToggle = async () => {
    const currentState = checklistVisibilityItem.getAttribute('data-state');
    const newStateIsPublic = currentState === 'private';

    updateVisibilityUI(checklistVisibilityItem, visibilityBadge, newStateIsPublic);

    try {
      const sessionToken = localStorage.getItem('sessionToken');
      const response = await fetch(`${apiUrl}/api/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ checklist_public: newStateIsPublic })
      });

      if (!response.ok) {
        console.error('Error updating settings:', response.status, response.statusText);
        // Revert UI on error
        updateVisibilityUI(checklistVisibilityItem, visibilityBadge, !newStateIsPublic);
        return;
      }

      console.log('Settings updated successfully:', newStateIsPublic ? 'Public' : 'Private');
    } catch (err) {
      console.error('Error updating settings:', err);
      // Revert UI on error
      updateVisibilityUI(checklistVisibilityItem, visibilityBadge, !newStateIsPublic);
    }
  };

  // Add event listeners - now just click the badge or the whole item
  if (checklistVisibilityItem && visibilityBadge) {
    checklistVisibilityItem.addEventListener('click', function(e) {
      // Prevent toggle if clicking the profile link
      if (e.target.classList.contains('profile-link')) return;
      handleVisibilityToggle();
    });
    visibilityBadge.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent double-firing
      handleVisibilityToggle();
    });
  }
});

function updateVisibilityUI(itemElement, badgeElement, isPublic) {
  // Update badge
  if (badgeElement) {
    badgeElement.textContent = isPublic ? 'Public' : 'Private';
    badgeElement.className = `status-badge-new ${isPublic ? 'public' : 'private'}`;
  }

  // Update data state
  if (itemElement) {
    itemElement.setAttribute('data-state', isPublic ? 'public' : 'private');
  }
}