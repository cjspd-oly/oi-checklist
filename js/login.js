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

        const errorBox = document.getElementById('error-message');

        if (response.ok && data.success) {
          window.location.href = 'index.html';
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
