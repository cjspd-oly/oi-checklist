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