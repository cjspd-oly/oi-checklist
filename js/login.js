// const apiUrl = 'https://avighna.pythonanywhere.com';
const apiUrl = 'http://127.0.0.1:5000';

document.getElementById('login-form')
    .addEventListener('submit', async (event) => {
      event.preventDefault();

      const username = document.getElementById('username').value;
      const password = document.getElementById('password').value;

      try {
        const response = await fetch(`${apiUrl}/api/login`, {
          method: 'POST',
          credentials: 'include',  // Allows cookies/session to persist
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({username, password})
        });

        const data = await response.json();

        if (response.ok && data.success) {
          window.location.href = '/';
        } else {
          document.getElementById('error-message').innerText =
              data.error || 'Login failed';
        }
      } catch (error) {
        console.error('Error during login:', error);
        document.getElementById('error-message').innerText =
            'An error occurred. Please try again later.';
      }
    });
