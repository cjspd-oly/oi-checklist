
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

document.addEventListener('DOMContentLoaded', function() {
  const connectButtons = document.querySelectorAll('.connect-button');
  connectButtons.forEach(button => {
    const card = button.closest('.connection-card');
    const providerName = card?.querySelector('.connection-name')
                             ?.textContent?.trim()
                             ?.toLowerCase();

    if (providerName === 'github') {
      button.addEventListener('click', () => handleGithubClick());
    } else if (providerName === 'oj.uz') {
      button.addEventListener('click', () => showOjuzPopup());
    } else if (providerName === 'discord') {
      button.addEventListener('click', () => handleDiscordClick());
    }
  });

  document.getElementById('submit-cookie-button')
      ?.addEventListener('click', onSubmitOjuzCookie);
});

function closeProviderPopup() {
  const popup = document.getElementById('provider-popup');
  popup.classList.remove('active');
  popup.addEventListener('transitionend', function() {
    if (!popup.classList.contains('active')) {
      popup.style.display = 'none';
    }
  }, {once: true});
}

function showProviderPopup(title, contentHTML) {
  const popup = document.getElementById('provider-popup');
  const body = document.getElementById('provider-popup-body');
  const titleElem = document.getElementById('popup-title');

  titleElem.textContent = title;
  body.innerHTML = contentHTML;

  popup.style.display = 'flex';
  setTimeout(() => popup.classList.add('active'), 10);
}

function showOjuzPopup() {
  showProviderPopup('Connect to oj.uz', `
      <p>
        Connect your <strong>oj.uz</strong> account to automatically update your OI checklist.
      </p>
      <p>
        This performs a <strong>one-time fetch</strong> of your solved problems to sync them with your checklist.
      </p>
      <p>
        Please log in to oj.uz in your browser, and paste the following cookie value here:
      </p>
      <div class="cookie-instruction">
        <code>Type: COOKIE &nbsp;&nbsp; Domain: oj.uz &nbsp;&nbsp; Name: oidc-auth</code>
      </div>
      <input type="text" class="cookie-input" id="oidc-input"
        placeholder="Paste your 'oidc-auth' cookie value here" required>
      <div id="popup-message"></div>
      <button class="primary-button" id="submit-cookie-button">Submit</button>
    `);

  document.getElementById('submit-cookie-button')
      .addEventListener('click', onSubmitOjuzCookie);
}

async function handleGithubClick() {
  const token = localStorage.getItem('sessionToken');
  if (!token) {
    showGithubError('You are not logged in.');
    return;
  }

  // Immediately show popup with loading spinner
  showProviderPopup(
    'GitHub Connection',
    `
    <p>
      GitHub is currently linked to
      <strong>
        <a id="github-link" href="https://github.com/" target="_blank" rel="noopener noreferrer">
          <span id="github-placeholder">@<span class="spinner"></span></span>
        </a>
      </strong>.
    </p>
    <div id="popup-message"></div>
    <button class="primary-button" id="unlink-github-button">Unlink</button>
  `
  );

  try {
    const res = await fetch(`${apiUrl}/api/github/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (res.status === 200) {
      const { github_username } = await res.json();
      const linkEl = document.getElementById('github-link');
      const placeholderEl = document.getElementById('github-placeholder');
      if (linkEl && placeholderEl) {
        linkEl.href = `https://github.com/${github_username}`;
        placeholderEl.textContent = `@${github_username}`;
      }

      document.getElementById('unlink-github-button').onclick = async () => {
        const messageBox = document.getElementById('popup-message');
        messageBox.style.display = 'block';
        try {
          const unlinkRes = await fetch(`${apiUrl}/api/github/unlink`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          });

          const resBody = await unlinkRes.json();

          if (unlinkRes.ok) {
            messageBox.textContent =
              resBody.message || 'GitHub unlinked successfully.';
            messageBox.style.color = 'green';
            setTimeout(closeProviderPopup, 1000);
          } else {
            messageBox.textContent =
              resBody.error || 'Failed to unlink GitHub.';
            messageBox.style.color = 'red';
          }
        } catch (err) {
          console.error(err);
          messageBox.textContent = 'Unexpected error occurred.';
          messageBox.style.color = 'red';
        }
      };
    } else {
      showProviderPopup(
        'Link GitHub',
        `
        <p>You have not linked your GitHub account yet.</p>
        <div id="popup-message"></div>
        <button class="primary-button" id="link-github-button">Link GitHub</button>
      `
      );

      document.getElementById('link-github-button').onclick = () => {
        const state = crypto.randomUUID();
        localStorage.setItem('oauth_github_state', state);
        const sessionToken = localStorage.getItem('sessionToken');
        const currentPage = encodeURIComponent(window.location.pathname);
        window.location.href = `${apiUrl}/auth/github/link?state=${state}&session_id=${sessionToken}&redirect_to=${currentPage}`;
      };
    }
  } catch (err) {
    console.error('Error checking GitHub status:', err);
    showGithubError('Error checking GitHub status.');
  }
}

async function handleDiscordClick() {
  const token = localStorage.getItem('sessionToken');
  if (!token) {
    showDiscordError('You are not logged in.');
    return;
  }

  // Immediately show popup with loading spinner
  showProviderPopup(
    'Discord Connection',
    `
    <p>
      Discord is currently linked to
      <strong>
        <a id="discord-link" href="https://discord.com/" target="_blank" rel="noopener noreferrer">
          <span id="discord-placeholder">@<span class="spinner"></span></span>
        </a>
      </strong>.
    </p>
    <div id="popup-message"></div>
    <button class="primary-button" id="unlink-discord-button">Unlink</button>
  `
  );

  try {
    const res = await fetch(`${apiUrl}/api/discord/status`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (res.status === 200) {
      const { discord_username, provider_user_id } = await res.json();
      const linkEl = document.getElementById('discord-link');
      const placeholderEl = document.getElementById('discord-placeholder');
      if (linkEl && placeholderEl) {
        linkEl.href = `https://discord.com/users/${provider_user_id}`;
        placeholderEl.textContent = `@${discord_username}`;
      }

      document.getElementById('unlink-discord-button').onclick = async () => {
        const messageBox = document.getElementById('popup-message');
        messageBox.style.display = 'block';
        try {
          const unlinkRes = await fetch(`${apiUrl}/api/discord/unlink`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
          });

          const resBody = await unlinkRes.json();

          if (unlinkRes.ok) {
            messageBox.textContent =
              resBody.message || 'Discord unlinked successfully.';
            messageBox.style.color = 'green';
            setTimeout(closeProviderPopup, 1000);
          } else {
            messageBox.textContent =
              resBody.error || 'Failed to unlink Discord.';
            messageBox.style.color = 'red';
          }
        } catch (err) {
          console.error(err);
          messageBox.textContent = 'Unexpected error occurred.';
          messageBox.style.color = 'red';
        }
      };
    } else {
      showProviderPopup(
        'Link Discord',
        `
        <p>You have not linked your Discord account yet.</p>
        <div id="popup-message"></div>
        <button class="primary-button" id="link-discord-button">Link Discord</button>
      `
      );

      document.getElementById('link-discord-button').onclick = () => {
        const state = crypto.randomUUID();
        localStorage.setItem('oauth_discord_state', state);
        const sessionToken = localStorage.getItem('sessionToken');
        const currentPage = encodeURIComponent(window.location.pathname);
        window.location.href = `${apiUrl}/auth/discord/link?state=${state}&session_id=${sessionToken}&redirect_to=${currentPage}`;
      };
    }
  } catch (err) {
    console.error('Error checking Discord status:', err);
    showDiscordError('Error checking Discord status.');
  }
}

function showGithubError(message) {
  const messageBox = document.getElementById('popup-message');
  if (!messageBox) return;
  messageBox.style.display = 'block';
  messageBox.textContent = message;
  messageBox.style.color =
      (localStorage.getItem('theme') || 'light-mode') === 'light-mode' ?
      'black' :
      'white';
}

function showDiscordError(message) {
  const messageBox = document.getElementById('popup-message');
  if (!messageBox) return;
  messageBox.style.display = 'block';
  messageBox.textContent = message;
  messageBox.style.color =
      (localStorage.getItem('theme') || 'light-mode') === 'light-mode' ?
      'black' :
      'white';
}

async function onSubmitOjuzCookie(e) {
  e.preventDefault();

  const oidcAuth = document.getElementById('oidc-input').value.trim();
  const messageBox = document.getElementById('popup-message');
  messageBox.style.display = 'block';
  messageBox.textContent = 'Validating cookie...';
  messageBox.style.color =
      (localStorage.getItem('theme') || 'light-mode') === 'light-mode' ?
      'black' :
      'white';

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
      messageBox.textContent = `Cookie is valid. Username: ${
          verifyResult.username}. Your problems will be updated shortly.`;
      messageBox.style.color = 'green';

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
