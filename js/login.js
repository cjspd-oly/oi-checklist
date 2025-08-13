document.getElementById('login-form')
    .addEventListener('submit', async (event) => {
      event.preventDefault();

      const username = document.getElementById('username').value;
      const password = document.getElementById('password').value;

      const errorBox = document.getElementById('error-message');

      try {
        const response = await fetch(`${apiUrl}/api/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok && data.success) {
          if (data.local_storage) {
            try {
              const savedData = JSON.parse(data.local_storage);
              if (savedData && typeof savedData === 'object') {
                for (const key in savedData) {
                  localStorage.setItem(key, savedData[key]);
                }
              }
            } catch (e) {
              console.warn('Failed to parse saved localStorage from server:', e);
            }
          }
          localStorage.setItem('sessionToken', data.token);
          window.location.href = '/';
        } else {
          errorBox.style.display = 'block';
          errorBox.innerText = data.error || 'Login failed';
        }
      } catch (error) {
        errorBox.style.display = 'block';
        console.error('Error during login:', error);
        errorBox.innerText = 'An error occurred. Please try again later.';
      }
    });

document.getElementById('github-continue').addEventListener('click', () => {
  window.location.href = `${apiUrl}/auth/github/start`;
});

document.getElementById('discord-continue').addEventListener('click', () => {
  window.location.href = `${apiUrl}/auth/discord/start`;
});

document.getElementById('google-continue').addEventListener('click', () => {
  window.location.href = `${apiUrl}/auth/google/start`;
});