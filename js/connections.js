window.onload = async () => {
  const sessionToken = localStorage.getItem('sessionToken');
  let res = await fetch(`${apiUrl}/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: {'Authorization': `Bearer ${sessionToken}`}
  });

  if (!res.ok) return window.location.href = 'home';

  const {username} = await res.json();
  document.getElementById('welcome-message').textContent =
      `Welcome, ${username}`;
};

// Dark mode
document.addEventListener('DOMContentLoaded', function() {
  const toggleSwitch = document.getElementById('dark-mode-switch');
  if (!toggleSwitch) {
    console.error('Dark mode toggle switch not found.');
    return;
  }

  let currentTheme = localStorage.getItem('theme') || 'light-mode';
  if (currentTheme === 'dark-mode') {
    document.body.classList.add('dark-mode');
    toggleSwitch.checked = true;
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

  const connectButtons = document.querySelectorAll('.connect-button');
  connectButtons.forEach(button => {
    button.addEventListener('click', openPopup);
  });
});

// Showing/closing the popup
function openPopup() {
  const popupOverlay = document.getElementById('connect-popup');
  // Set display to flex first so transitions can apply
  popupOverlay.style.display = 'flex';
  // Use a small timeout to allow the display change to register before adding
  // the active class This is sometimes necessary in browsers for the transition
  // to trigger correctly.
  setTimeout(() => {
    popupOverlay.classList.add('active');
  }, 10);  // A small delay like 10ms is usually sufficient
}

function closePopup() {
  const popupOverlay = document.getElementById('connect-popup');
  popupOverlay.classList.remove('active');

  // Wait for the transition to finish before setting display back to none
  popupOverlay.addEventListener('transitionend', function() {
    // Check if the popup still doesn't have the active class (handles rapid
    // closing)
    if (!popupOverlay.classList.contains('active')) {
      popupOverlay.style.display = 'none';
    }
  }, {
    once: true
  });  // Use { once: true } to automatically remove the event listener after it
       // fires
}

// logout
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

// submit cookie and update problems
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('submit-cookie-button')
      .addEventListener('click', onSubmitCookie);
});

async function onSubmitCookie(e) {
  e.preventDefault();

  const oidcAuth = document.getElementById('oidc-input').value.trim();
  const messageBox = document.getElementById(
      'popup-message');  // Assuming there's an element to show messages
  messageBox.style.display =
      'block';  // Make sure the message box is visible during the process
  messageBox.textContent = 'Validating cookie...';
  let currentTheme = localStorage.getItem('theme') || 'light-mode';
  messageBox.color = currentTheme == 'light-mode' ? 'black' : 'white';

  if (!oidcAuth) {
    messageBox.textContent = 'Please paste your oidc-auth cookie value.';
    messageBox.style.color = 'red';
    return;
  }

  const sessionToken = localStorage.getItem('sessionToken');
  if (!sessionToken) {
    messageBox.textContent = 'You are not logged in.';
    messageBox.style.color = 'red';
    return;
  }

  try {
    // First, verify the cookie by calling /api/verify-ojuz
    const verifyRes = await fetch(`${apiUrl}/api/verify-ojuz`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`
      },
      body: JSON.stringify({cookie: oidcAuth})
    });

    if (!verifyRes.ok) {
      const text = await verifyRes.text();
      messageBox.textContent = `Cookie validation failed: ${text}`;
      messageBox.style.color = 'red';
      return;
    }

    const verifyResult = await verifyRes.json();
    if (verifyResult.valid) {
      // If the cookie is valid
      messageBox.textContent = `Cookie is valid. Username: ${
          verifyResult.username}. Your problems will be updated shortly.`;
      messageBox.style.color = 'green';

      // Proceed to update problems in the background without waiting for a
      // response
      fetch(`${apiUrl}/api/update-ojuz`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({cookie: oidcAuth})
      })
          .then(res => res.json())
          .then(result => {
            console.log('Problems updated in the background.');
          })
          .catch(err => {
            console.error('Error updating problems in the background:', err);
          });
    } else {
      // If the cookie is invalid
      messageBox.textContent = `Invalid cookie. Please check and try again.`;
      messageBox.style.color = 'red';
    }
  } catch (err) {
    console.error(err);
    messageBox.textContent =
        'Something went wrong while validating the cookie.';
    messageBox.style.color = 'red';
  }
}