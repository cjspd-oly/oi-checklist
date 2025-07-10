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
          body: JSON.stringify({username, password})
        });

        const data = await response.json();

        if (response.ok && data.success) {
          const sessionToken = data.token;
          console.log('JWT Token: ' + sessionToken);
          localStorage.setItem('sessionToken', sessionToken);

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
