// Virtual Contest JavaScript
document.addEventListener('DOMContentLoaded', async () => {
  // Set virtual contest mode flag
  window.isVirtualContestMode = true;
  
  const olympiadSelect = document.getElementById('olympiad-select');
  const contestSelect = document.getElementById('contest-select');
  const daySelect = document.getElementById('day-select');
  const contestDetails = document.getElementById('contest-details');
  const ojuzSection = document.getElementById('ojuz-section');
  const startBtn = document.getElementById('start-contest-btn');
  const vcForm = document.querySelector('.vc-form');
  const activeContest = document.getElementById('active-contest');
  const scoreEntry = document.getElementById('score-entry');
  const pastVcList = document.querySelector('.past-vc-list');
  const sessionToken = localStorage.getItem('sessionToken');

  // If we're not logged in, redirect to the home page
  const whooamires = await fetch(`${apiUrl}/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: {'Authorization': `Bearer ${sessionToken}`}
  });
  if (!whooamires.ok) {
    return window.location.href = 'home';
  }
  const { username } = await whooamires.json();
  // Also show the welcome message
  document.getElementById('welcome-message').innerHTML = `Welcome, ${username}`;

  // Fetch contest data from API
  const response = await fetch(`${apiUrl}/api/virtual-contests`, {
    method: 'GET',
    credentials: 'include',
    headers: {'Authorization': `Bearer ${sessionToken}`}
  });

  if (!response.ok) {
    console.error('Failed to fetch virtual contests data');
    return;
  }

  const data = await response.json();
  const contestData = data.contests;
  let currentActiveContest = null; // Store active contest data

  // Define functions first so they're available when needed
  function showMessage(text, type = 'error') {
    const messageContainer = document.getElementById('message-container');
    const messageContent = document.getElementById('message-content');
    const messageText = document.getElementById('message-text');
    
    messageText.textContent = text;
    messageContent.className = `message-content ${type}`;
    messageContainer.style.display = 'flex';
  }

  function hideMessage() {
    document.getElementById('message-container').style.display = 'none';
  }

  // Handle message close button
  document.getElementById('message-close').addEventListener('click', hideMessage);
  
  // Close message when clicking outside
  document.getElementById('message-container').addEventListener('click', (e) => {
    if (e.target.id === 'message-container') {
      hideMessage();
    }
  });

  function showScoreEntry() {
    if (!currentActiveContest) {
      showMessage('No active contest data available.');
      return;
    }

    // Get contest info from the active contest data
    const contestTitle = `${currentActiveContest.contest_name} ${currentActiveContest.contest_stage}`;
    
    document.getElementById('score-contest-title').textContent = contestTitle;

    // Calculate time used based on stored start and end times
    const startTime = new Date(currentActiveContest.start_time);
    let endTime;
    
    if (currentActiveContest.end_time) {
      // Use the stored end time from the API
      endTime = new Date(currentActiveContest.end_time);
    } else {
      // Fallback to current time if no end_time (shouldn't happen in score entry)
      endTime = new Date();
    }
    
    const elapsedMilliseconds = endTime - startTime;
    const elapsedMinutes = Math.floor(elapsedMilliseconds / (1000 * 60));
    const elapsedHours = Math.floor(elapsedMinutes / 60);
    const remainingMinutes = elapsedMinutes % 60;
    
    const timeUsed = elapsedHours > 0 ? `${elapsedHours}h ${remainingMinutes}m` : `${remainingMinutes}m`;
    document.getElementById('completion-time').textContent = timeUsed;

    // Generate score table with actual problem names using main page cell system
    const scoreTbody = document.getElementById('score-problems-tbody');
    scoreTbody.innerHTML = '';

    // Get the contest data to find problems
    const contestName = currentActiveContest.contest_name;
    const contestStage = currentActiveContest.contest_stage;
    
    // Find the contest in contestData to get problems
    let contestProblems = [];
    let problemCount = 3; // fallback
    
    // Search through all olympiads and years to find this contest
    for (const [olympiad, years] of Object.entries(contestData)) {
      for (const [year, contests] of Object.entries(years)) {
        const contest = contests.find(c => c.name === contestName && c.stage === contestStage);
        if (contest && contest.problems) {
          contestProblems = contest.problems;
          problemCount = contest.problems.length;
          break;
        }
      }
      if (contestProblems.length > 0) break;
    }
    
    // Get actual problem names and links
    const problemData = [];
    if (contestProblems.length > 0 && problemsData) {
      contestProblems.forEach((prob, index) => {
        // Find the problem in problemsData
        const olympiadProblems = problemsData[prob.source];
        if (olympiadProblems && olympiadProblems[prob.year]) {
          const problem = olympiadProblems[prob.year].find(p => 
            p.source === prob.source && 
            p.year === prob.year && 
            p.number === prob.number
          );
          if (problem) {
            problemData.push({
              name: problem.name,
              link: problem.link,
              source: prob.source,
              year: prob.year,
              score: 0,
              status: 0
            });
          } else {
            problemData.push({
              name: `Problem ${index + 1}`,
              link: '#',
              source: prob.source,
              year: prob.year,
              score: 0,
              status: 0
            });
          }
        } else {
          problemData.push({
            name: `Problem ${index + 1}`,
            link: '#',
            source: 'Unknown',
            year: new Date().getFullYear(),
            score: 0,
            status: 0
          });
        }
      });
    } else {
      // Fallback to generic names
      for (let i = 1; i <= problemCount; i++) {
        problemData.push({
          name: `Problem ${i}`,
          link: '#',
          source: 'Unknown',
          year: new Date().getFullYear(),
          score: 0,
          status: 0
        });
      }
    }
    
    // Create table row with problem cells (same as main page)
    const row = document.createElement('tr');
    
    problemData.forEach((problem, index) => {
      const cell = document.createElement('td');
      cell.className = 'problem-cell white';
      cell.dataset.status = '0';
      cell.dataset.problemId = problem.name;
      cell.dataset.source = problem.source;
      cell.dataset.year = problem.year;
      cell.dataset.score = '0';
      
      const link = document.createElement('a');
      link.href = problem.link;
      link.target = '_blank';
      link.textContent = problem.name;
      cell.appendChild(link);
      
      // Add click handler using the same system as main page
      cell.addEventListener('click', (e) => handleCellClick(cell, problem.name, problem.source, problem.year, e));
      
      row.appendChild(cell);
    });
    
    scoreTbody.appendChild(row);

    scoreEntry.style.display = 'block';
  }

  function showForm() {
    // Reset form
    olympiadSelect.value = '';
    contestSelect.innerHTML = '<option value="">Select Contest</option>';
    daySelect.innerHTML = '<option value="">Select Day</option>';
    contestSelect.disabled = true;
    daySelect.disabled = true;
    contestDetails.style.display = 'none';
    ojuzSection.style.display = 'none';
    startBtn.disabled = true;

    // Show form, hide others
    vcForm.style.display = 'block';
    activeContest.style.display = 'none';
    scoreEntry.style.display = 'none';
  }

  // Fetch problems data for all contest sources to avoid lag
  const contestSources = Object.keys(contestData);
  let problemsData = {};
  
  // Always fetch problems data (we need it for contest problem names)
  const problemsResponse = await fetch(`${apiUrl}/api/problems?names=${contestSources.join(',')}`, {
    method: 'GET',
    credentials: 'include',
    headers: {'Authorization': `Bearer ${sessionToken}`}
  });

  if (problemsResponse.ok) {
    problemsData = await problemsResponse.json();
  }

  // Check if user has an active contest
  if (data.active_contest) {
    // User has an ongoing contest
    currentActiveContest = data.active_contest;
    
    // Check if contest is ended (has end_time)
    if (currentActiveContest.end_time) {
      // Contest is finished, show score entry screen
      vcForm.style.display = 'none';
      document.getElementById('active-contest').style.display = 'none';
      showScoreEntry();
    } else {
      // Contest is still running, show timer
      vcForm.style.display = 'none';
      document.getElementById('active-contest').style.display = 'block';
      
      // Set contest title and metadata
      document.getElementById('active-contest-title').innerHTML = `${currentActiveContest.contest_name} <svg width="12" height="3" viewBox="0 0 12 3" style="vertical-align: middle; margin: 0 4px;"><rect width="12" height="2" fill="currentColor"/></svg> ${currentActiveContest.contest_stage}`;
      
      // Set location and website in one line
      const locationElement = document.getElementById('active-contest-location');
      const websiteElement = document.getElementById('active-contest-website');
      
      if (currentActiveContest.location || currentActiveContest.website) {
        let metadataHTML = '';
        if (currentActiveContest.location) {
          metadataHTML += currentActiveContest.location;
        }
        if (currentActiveContest.website) {
          if (metadataHTML) metadataHTML += ' | ';
          metadataHTML += `<a href="${currentActiveContest.website}" target="_blank">${currentActiveContest.website}</a>`;
        }
        locationElement.innerHTML = metadataHTML;
        locationElement.style.display = 'block';
        websiteElement.style.display = 'none';
      } else {
        locationElement.style.display = 'none';
        websiteElement.style.display = 'none';
      }

      // Calculate remaining time
      const startTime = new Date(currentActiveContest.start_time);
      const now = new Date();
      const elapsedMilliseconds = now - startTime;
      const elapsedSeconds = Math.floor(elapsedMilliseconds / 1000);
      const elapsedMinutes = Math.floor(elapsedSeconds / 60);
      const remainingSeconds = Math.max(0, (currentActiveContest.duration_minutes * 60) - elapsedSeconds);
      const remainingMinutes = Math.floor(remainingSeconds / 60);
      
      console.log('Start time:', startTime);
      console.log('Current time:', now);
      console.log('Elapsed seconds:', elapsedSeconds);
      console.log('Elapsed minutes:', elapsedMinutes);
      console.log('Remaining seconds:', remainingSeconds);
      console.log('Remaining minutes:', remainingMinutes);
      
      // Start timer with remaining time and elapsed time (in seconds precision)
      startTimerWithSeconds(remainingSeconds, elapsedSeconds);
    }
    
    // Don't return here - we still need to set up event listeners
  }

  // Populate olympiad select (only if not in active contest)
  if (!currentActiveContest) {
    olympiadSelect.innerHTML = '<option value="">Select Olympiad</option>';
    Object.keys(contestData).forEach(source => {
      const option = document.createElement('option');
      option.value = source;
      option.textContent = getFullOlympiadName(source);
      olympiadSelect.appendChild(option);
    });
  }

    // Update recent virtual contests
  pastVcList.innerHTML = '';
  const viewAllLink = document.querySelector('.view-all-link');
  
  if (data.recent.length === 0) {
    const emptyMessage = document.createElement('div');
    emptyMessage.className = 'past-vc-empty';
    emptyMessage.innerHTML = `
      <div class="empty-text">No virtual contests yet.</div>
      <div class="empty-subtext">Start your first one here.</div>
    `;
    pastVcList.appendChild(emptyMessage);
    viewAllLink.style.display = 'none';
  } else {
    data.recent.forEach(contest => {
      const item = document.createElement('div');
      item.className = 'past-vc-item';
      const date = new Date(contest.started_at);
      const formattedDate = date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
      item.innerHTML = `
              <div class="past-vc-title">${contest.contest_source} ${
          contest.contest_year} ${contest.contest_stage}</div>
              <div class="past-vc-score">${contest.total_score || 0}/300</div>
              <div class="past-vc-date">${formattedDate}</div>
          `;
      pastVcList.appendChild(item);
    });
    viewAllLink.style.display = 'block';
  }

  // Handle olympiad selection
  olympiadSelect.addEventListener('change', (e) => {
    const selectedOlympiad = e.target.value;
    const contestRow = document.getElementById('contest-row');
    const dayRow = document.getElementById('day-row');
    
    contestSelect.innerHTML = '<option value="">Select Contest</option>';
    daySelect.innerHTML = '<option value="">Select Day</option>';
    contestSelect.disabled = !selectedOlympiad;
    daySelect.disabled = true;
    contestDetails.style.display = 'none';
    ojuzSection.style.display = 'none';
    startBtn.disabled = true;
    
    // Show/hide entire form rows
    contestRow.style.display = selectedOlympiad ? 'block' : 'none';
    dayRow.style.display = 'none';

    if (selectedOlympiad && contestData[selectedOlympiad]) {
      Object.keys(contestData[selectedOlympiad]).forEach(year => {
        const contests = contestData[selectedOlympiad][year];
        // Group contests by name and show location
        const contestMap = {};
        contests.forEach(contest => {
          if (!contestMap[contest.name]) {
            contestMap[contest.name] = contest;
          }
        });
        
        Object.values(contestMap).forEach(contest => {
          const option = document.createElement('option');
          option.value = `${contest.name}|${year}`;
          option.textContent = contest.name;
          contestSelect.appendChild(option);
        });
      });
      contestSelect.disabled = false;
    }
  });

  // Handle contest selection
  contestSelect.addEventListener('change', (e) => {
    const selectedContest = e.target.value;
    const selectedOlympiad = olympiadSelect.value;
    const dayRow = document.getElementById('day-row');
    const dayLabel = dayRow.querySelector('label');
    
    daySelect.innerHTML = '<option value="">Select Stage</option>';
    daySelect.disabled = true;
    contestDetails.style.display = 'none';
    ojuzSection.style.display = 'none';
    startBtn.disabled = true;
    
    // Hide day row initially
    dayRow.style.display = 'none';

    if (selectedContest && contestData[selectedOlympiad]) {
      const [contestName, year] = selectedContest.split('|');
      const contests = contestData[selectedOlympiad][year] || [];
      const matchingContests = contests.filter(c => c.name === contestName);
      
      // Get unique stages and sort them
      const stages = [...new Set(matchingContests.map(c => c.stage))].sort();

      if (stages.length > 0) {
        // Check if all stages follow "Day X" pattern
        const allDayPattern = stages.every(stage => /^Day \d+$/.test(stage));
        
        if (allDayPattern) {
          dayLabel.textContent = 'Day';
          daySelect.innerHTML = '<option value="">Select Day</option>';
        } else {
          dayLabel.textContent = 'Stage';
          daySelect.innerHTML = '<option value="">Select Stage</option>';
        }
        
        stages.forEach(stage => {
          const option = document.createElement('option');
          option.value = stage;
          option.textContent = stage;
          daySelect.appendChild(option);
        });
        daySelect.disabled = false;
        dayRow.style.display = 'block';
      }
    }
  });

  // Handle day selection
  daySelect.addEventListener('change', (e) => {
    const selectedStage = e.target.value;
    const selectedOlympiad = olympiadSelect.value;
    const selectedContest = contestSelect.value;

    if (selectedStage && selectedContest && contestData[selectedOlympiad]) {
      const [contestName, year] = selectedContest.split('|');
      const contests = contestData[selectedOlympiad][year] || [];
      const contest = contests.find(c => c.name === contestName && c.stage === selectedStage);
      
      if (!contest) return;

      // Check if this contest has been completed
      const contestKey = `${contestName}|${selectedStage}`;
      const isCompleted = data.completed_contests && data.completed_contests.includes(contestKey);

      // Calculate problem count from contest.problems array
      const problemCount = contest.problems ? contest.problems.length : 3;
      
      // Get platforms from the problems data we already fetched
      let platforms = ['Unknown'];
      if (contest.problems && problemsData[selectedOlympiad]) {
        const platformSet = new Set();
        contest.problems.forEach(prob => {
          const yearProblems = problemsData[selectedOlympiad][prob.year] || [];
          const problem = yearProblems.find(p => p.source === prob.source && p.year === prob.year && p.number === prob.number);
          if (problem && problem.link) {
            platformSet.add(getPlatformFromLink(problem.link));
          }
        });
        platforms = Array.from(platformSet).filter(p => p !== 'Unknown');
        if (platforms.length === 0) platforms = ['Unknown'];
      }

      // Show contest details with accurate info
      document.getElementById('contest-duration').textContent = formatDuration(contest.duration_minutes);
      document.getElementById('contest-problems').textContent = problemCount;
      document.getElementById('contest-platform').textContent = platforms.join(', ');
      
      contestDetails.style.display = 'block';

      // Show/hide completion warning
      const completionWarning = document.getElementById('completion-warning');
      if (isCompleted) {
        completionWarning.style.display = 'block';
        startBtn.disabled = true;
      } else {
        completionWarning.style.display = 'none';
        startBtn.disabled = false;
      }

      // Show oj.uz section if needed (check if any platform is oj.uz)
      const hasOjuz = contest.link?.includes('oj.uz') || (platforms && platforms.some(p => p === 'oj.uz'));
      if (hasOjuz && false)  { // temporarily disabling this feature until I finish coding it lol
        ojuzSection.style.display = 'block';
      } else {
        ojuzSection.style.display = 'none';
      }
    }
  });

  // Handle start contest button
  startBtn.addEventListener('click', async () => {
    // Double-check if button should be disabled
    if (startBtn.disabled) {
      return;
    }

    const selectedOlympiad = olympiadSelect.value;
    const selectedContest = contestSelect.value;
    const selectedStage = daySelect.value;
    
    const [contestName, year] = selectedContest.split('|');
    const contests = contestData[selectedOlympiad][year] || [];
    const contest = contests.find(c => c.name === contestName && c.stage === selectedStage);

    // Start the virtual contest in the database
    try {
      const startResponse = await fetch(`${apiUrl}/api/virtual-contests/start`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          contest_name: contestName,
          contest_stage: selectedStage
        })
      });

      if (!startResponse.ok) {
        const error = await startResponse.json();
        if (error.error === 'Contest already completed') {
          showMessage('You have already completed this virtual contest.', 'warning');
        } else {
          showMessage('Failed to start contest: ' + error.error);
        }
        return;
      }
    } catch (error) {
      showMessage('Failed to start contest: ' + error.message);
      return;
    }

    // Hide form and show active contest
    vcForm.style.display = 'none';
    activeContest.style.display = 'block';

    // Set contest title and metadata
    document.getElementById('active-contest-title').innerHTML = `${contestName} <svg width="12" height="3" viewBox="0 0 12 3" style="vertical-align: middle; margin: 0 4px;"><rect width="12" height="2" fill="currentColor"/></svg> ${selectedStage}`;
    
    // Set location and website in one line
    const locationElement = document.getElementById('active-contest-location');
    const websiteElement = document.getElementById('active-contest-website');
    
    if (contest.location || contest.website) {
      let metadataHTML = '';
      if (contest.location) {
        metadataHTML += contest.location;
      }
      if (contest.website) {
        if (metadataHTML) metadataHTML += ' | ';
        metadataHTML += `<a href="${contest.website}" target="_blank">${contest.website}</a>`;
      }
      locationElement.innerHTML = metadataHTML;
      locationElement.style.display = 'block';
      websiteElement.style.display = 'none';
    } else {
      locationElement.style.display = 'none';
      websiteElement.style.display = 'none';
    }

    // Start timer with actual contest duration
    startTimer(contest.duration_minutes);
    
    // Update currentActiveContest with the contest data we just started
    currentActiveContest = {
      contest_name: contestName,
      contest_stage: selectedStage,
      start_time: new Date().toISOString(),
      duration_minutes: contest.duration_minutes,
      location: contest.location || '',
      website: contest.website || '',
      link: contest.link || ''
    };
  });

  // Handle end contest button
  document.getElementById('end-contest-btn').addEventListener('click', async () => {
    console.log('End contest clicked, currentActiveContest:', currentActiveContest);
    
    // Check if oj.uz username is provided
    const ojuzUsername = document.getElementById('ojuz-username').value.trim();
    
    try {
      const endResponse = await fetch(`${apiUrl}/api/virtual-contests/end`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ojuz_username: ojuzUsername || undefined
        })
      });

      if (!endResponse.ok) {
        const error = await endResponse.json();
        showMessage('Failed to end contest: ' + error.error);
        return;
      }

      // Contest ended successfully
      if (ojuzUsername) {
        showMessage('Contest ended! Scores will be synced automatically from oj.uz.', 'success');
        // TODO: Handle oj.uz sync success case when implemented
        activeContest.style.display = 'none';
        showForm();
        currentActiveContest = null;
      } else {
        // Hide active contest and show manual score entry
        activeContest.style.display = 'none';
        
        // Update currentActiveContest to mark it as ended
        currentActiveContest.end_time = new Date().toISOString();
        
        showScoreEntry();
      }
      
    } catch (error) {
      showMessage('Failed to end contest: ' + error.message);
    }
  });

  // Handle open contest button
  document.getElementById('open-contest-btn').addEventListener('click', () => {
    console.log('Open contest button clicked!');
    console.log('currentActiveContest:', currentActiveContest);
    
    // For active contests, use the stored active contest data
    const activeContestElement = document.getElementById('active-contest');
    console.log('activeContestElement style.display:', activeContestElement.style.display);
    
    if (activeContestElement.style.display !== 'none' && currentActiveContest) {
      console.log('Using active contest link:', currentActiveContest.link);
      // We're in an active contest, use the contest link
      if (currentActiveContest.link) {
        window.open(currentActiveContest.link, '_blank');
      } else {
        showMessage('No contest link available for this contest.', 'warning');
      }
      return;
    }
    
    // For contest selection (not active), use the old logic
    const selectedOlympiad = olympiadSelect.value;
    const selectedContest = contestSelect.value;
    console.log('Using form selection:', selectedOlympiad, selectedContest);
    
    if (!selectedOlympiad || !selectedContest || !contestData[selectedOlympiad]) {
      showMessage('No contest selected.', 'warning');
      return;
    }
    
    const [contestName, year] = selectedContest.split('|');
    const contests = contestData[selectedOlympiad][year] || [];
    const selectedStage = daySelect.value;
    const contest = contests.find(c => c.name === contestName && c.stage === selectedStage);
    
    console.log('Found contest:', contest);
    
    if (contest && contest.link) {
      window.open(contest.link, '_blank');
    } else {
      showMessage('No contest link available for this contest.', 'warning');
    }
  });

  // Handle score submission
  document.getElementById('submit-scores-btn').addEventListener('click', async () => {
    if (!currentActiveContest) {
      showMessage('No active contest data available.');
      return;
    }

    // Collect scores from problem cells (same as main page)
    const scores = [];
    const problemCells = document.querySelectorAll('#score-problems-tbody .problem-cell');
    let totalScore = 0;
    
    // Validate scores first
    for (let i = 0; i < problemCells.length; i++) {
      const score = parseInt(problemCells[i].dataset.score) || 0;
      if (score < 0 || score > 100) {
        showMessage(`${problemCells[i].dataset.problemId} score must be between 0 and 100.`, 'warning');
        return;
      }
      scores.push(score);
      totalScore += score;
    }

    try {
      // First, update individual problem statuses and scores
      for (let i = 0; i < problemCells.length; i++) {
        const cell = problemCells[i];
        const problemName = cell.dataset.problemId;
        const source = cell.dataset.source;
        const year = parseInt(cell.dataset.year);
        const score = parseInt(cell.dataset.score) || 0;
        const status = parseInt(cell.dataset.status) || 0;

        // Update problem status
        const statusResponse = await fetch(`${apiUrl}/api/update-problem-status`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            problem_name: problemName,
            source: source,
            year: year,
            status: status
          })
        });

        if (!statusResponse.ok) {
          const error = await statusResponse.json();
          showMessage(`Failed to update status for ${problemName}: ${error.error}`);
          return;
        }

        // Update problem score
        const scoreResponse = await fetch(`${apiUrl}/api/update-problem-score`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            problem_name: problemName,
            source: source,
            year: year,
            score: score
          })
        });

        if (!scoreResponse.ok) {
          const error = await scoreResponse.json();
          showMessage(`Failed to update score for ${problemName}: ${error.error}`);
          return;
        }
      }

      // Then submit the virtual contest scores
      const submitResponse = await fetch(`${apiUrl}/api/virtual-contests/submit`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          scores: scores,
          total_score: totalScore
        })
      });

      if (!submitResponse.ok) {
        const error = await submitResponse.json();
        showMessage('Failed to submit virtual contest: ' + error.error);
        return;
      }

      // Redirect to virtual history page
      window.location.href = '/virtual-history';
      
    } catch (error) {
      showMessage('Failed to submit scores: ' + error.message);
    }
  });

  function startTimerWithSeconds(remainingSeconds, alreadyElapsedSeconds = 0) {
    // Use remaining seconds directly
    let timeRemaining = remainingSeconds;
    const timer = document.getElementById('contest-timer');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    // Track how much time has passed since the timer started
    let timerElapsedSeconds = 0;

    // Update display function
    const updateDisplay = () => {
      const hours = Math.floor(timeRemaining / 3600);
      const minutes = Math.floor((timeRemaining % 3600) / 60);
      const seconds = timeRemaining % 60;

      timer.textContent = `${hours}:${minutes.toString().padStart(2, '0')}:${
          seconds.toString().padStart(2, '0')}`;

      // Total elapsed time = already elapsed + timer elapsed
      const totalElapsedSeconds = alreadyElapsedSeconds + timerElapsedSeconds;
      const totalContestSeconds = alreadyElapsedSeconds + remainingSeconds;
      
      const progressPercent = (totalElapsedSeconds / totalContestSeconds) * 100;
      progressFill.style.width = `${Math.min(100, progressPercent)}%`;

      const elapsedHours = Math.floor(totalElapsedSeconds / 3600);
      const elapsedMins = Math.floor((totalElapsedSeconds % 3600) / 60);
      progressText.textContent = `${elapsedHours}h ${elapsedMins}m elapsed`;
    };

    // Set initial display
    updateDisplay();

    const interval = setInterval(() => {
      timeRemaining--;
      timerElapsedSeconds++;
      updateDisplay();

      if (timeRemaining <= 0) {
        clearInterval(interval);
        timer.textContent = '0:00:00';
        progressFill.style.width = '100%';
        showMessage('Time is up! Please end your contest and submit your scores.', 'warning');
      }
    }, 1000);
  }

  function startTimer(remainingMinutes, alreadyElapsedMinutes = 0) {
    // Convert to seconds and use the seconds-based function
    startTimerWithSeconds(remainingMinutes * 60, alreadyElapsedMinutes * 60);
  }
});