const apiUrl = 'https://avighna.pythonanywhere.com';
// const apiUrl = 'http://127.0.0.1:5000';

document.getElementById('register-form')
    .addEventListener('submit', async (e) => {
      e.preventDefault();

      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;
      const errorBox = document.getElementById('error-message');

      try {
        const res = await fetch(apiUrl + '/api/register', {
          method: 'POST',
          credentials: 'include',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({username, password})
        });

        const result = await res.json();

        if (res.ok) {
          window.location.href = '/login.html';
        } else {
          errorBox.style.display = 'block';
          errorBox.innerText = result.error || 'Registration failed';
        }
      } catch (error) {
        errorBox.style.display = 'block';
        errorBox.innerText = 'An unexpected error occurred';
      }
    });
