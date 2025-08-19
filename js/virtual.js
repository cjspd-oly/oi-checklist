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

  // Show loading skeleton initially
  document.getElementById('past-vc-loading').style.display = 'block';
  pastVcList.style.display = 'none';
  document.querySelector('.view-all-link').style.display = 'none';

  // Check if we expect an active contest from localStorage
  const contestOngoing = localStorage.getItem('contest_ongoing') === 'true';

  // Show appropriate skeleton based on expected state
  if (contestOngoing) {
    // Show active contest skeleton
    document.getElementById('vc-main-loading').style.display = 'block';
    document.getElementById('vc-main-loading').className = 'vc-main-loading active-contest-skeleton';
  } else {
    // Show form skeleton
    document.getElementById('vc-main-loading').style.display = 'block';
    document.getElementById('vc-main-loading').className = 'vc-main-loading form-skeleton';
  }

  vcForm.style.display = 'none';
  activeContest.style.display = 'none';
  scoreEntry.style.display = 'none';

  // If we're not logged in, redirect to the home page
  const whooamires = await fetch(`${apiUrl}/api/whoami`, {
    method: 'GET',
    credentials: 'include',
    headers: { 'Authorization': `Bearer ${sessionToken}` }
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
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });

  if (!response.ok) {
    console.error('Failed to fetch virtual contests data');
    // Hide skeleton on error
    document.getElementById('past-vc-loading').style.display = 'none';
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

    // Trigger animation after a brief delay to ensure display is set
    setTimeout(() => {
      messageContainer.classList.add('show');
    }, 10);
  }

  function hideMessage() {
    const messageContainer = document.getElementById('message-container');
    messageContainer.classList.remove('show');

    // Hide the element after animation completes
    setTimeout(() => {
      messageContainer.style.display = 'none';
    }, 300);
  }

  // Handle message close button
  document.getElementById('message-close').addEventListener('click', hideMessage);

  // Close message when clicking outside
  document.getElementById('message-container').addEventListener('click', (e) => {
    if (e.target.id === 'message-container') {
      hideMessage();
    }
  });

  function showScoreEntry(isReadOnly = false) {
    if (!currentActiveContest) {
      showMessage('No active contest data available.');
      return;
    }

    // Get contest info from the active contest data
    const contestTitle = currentActiveContest.contest_stage ?
      `${currentActiveContest.contest_name} ${currentActiveContest.contest_stage}` :
      currentActiveContest.contest_name;

    document.getElementById('score-contest-title').textContent = contestTitle;

    // Calculate time used based on stored start and end times, capped at contest duration
    const startTime = new Date(currentActiveContest.start_time);
    let endTime;

    if (currentActiveContest.end_time) {
      // Use the stored end time from the API
      endTime = new Date(currentActiveContest.end_time);
    } else {
      // Fallback to current time if no end_time (shouldn't happen in score entry)
      endTime = new Date();
    }

    // Cap the end time at contest duration
    const contestDurationMs = currentActiveContest.duration_minutes * 60 * 1000;
    const maxEndTime = new Date(startTime.getTime() + contestDurationMs);
    const cappedEndTime = new Date(Math.min(endTime.getTime(), maxEndTime.getTime()));

    const elapsedMilliseconds = cappedEndTime - startTime;
    const elapsedMinutes = Math.floor(elapsedMilliseconds / (1000 * 60));
    const elapsedHours = Math.floor(elapsedMinutes / 60);
    const remainingMinutes = elapsedMinutes % 60;

    const timeUsed = elapsedHours > 0 ? `${elapsedHours}h ${remainingMinutes}m` : `${remainingMinutes}m`;
    document.getElementById('completion-time').textContent = timeUsed;

    // Update header and description based on mode
    const scoreSection = document.querySelector('.score-section');
    const scoreSectionH3 = scoreSection.querySelector('h3');
    const scoreSubtitle = document.querySelector('.score-subtitle');

    if (isReadOnly) {
      scoreSectionH3.textContent = 'View Your Scores';
      scoreSubtitle.textContent = 'Click on each problem to view detailed scoring information.';
    } else {
      scoreSectionH3.textContent = 'Enter Your Scores';
      scoreSubtitle.textContent = 'Click on each problem to set your score.';
    }

    // Calculate total score for oj.uz mode and update completion stats
    if (isReadOnly && currentActiveContest.ojuz_data) {
      const totalScore = currentActiveContest.ojuz_data.reduce((sum, submission) => sum + submission.score, 0);

      // Add total score stat item
      const completionStats = document.querySelector('.completion-stats');

      // Check if total score stat already exists
      let totalScoreStat = document.getElementById('total-score-stat');
      if (!totalScoreStat) {
        totalScoreStat = document.createElement('div');
        totalScoreStat.id = 'total-score-stat';
        totalScoreStat.className = 'stat-item';
        totalScoreStat.innerHTML = `
          <span class="stat-label">Total Score:</span>
          <span class="stat-value" id="total-score-value">${totalScore}/300</span>
        `;
        completionStats.appendChild(totalScoreStat);
      } else {
        // Update existing stat
        document.getElementById('total-score-value').textContent = `${totalScore}/300`;
      }
    }

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
        const contest = contests.find(c => c.name === contestName &&
          (contestStage ? c.stage === contestStage : c.stage == null));
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
              status: 0,
              index: prob.index
            });
          } else {
            problemData.push({
              name: `Problem ${index + 1}`,
              link: '#',
              source: prob.source,
              year: prob.year,
              score: 0,
              status: 0,
              index: prob.index
            });
          }
        } else {
          problemData.push({
            name: `Problem ${index + 1}`,
            link: '#',
            source: prob.source,
            year: prob.year,
            score: 0,
            status: 0,
            index: prob.index
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
          status: 0,
          index: i
        });
      }
    }

    // If we have oj.uz data, populate scores
    if (isReadOnly && currentActiveContest.ojuz_data) {
      const ojuzData = currentActiveContest.ojuz_data;
      ojuzData.forEach(submission => {
        const problemIndex = problemData.findIndex(p => p.index === submission.problem_index);
        if (problemIndex !== -1) {
          problemData[problemIndex].score = submission.score;
          problemData[problemIndex].subtask_scores = submission.subtask_scores;
          problemData[problemIndex].submission_time = submission.submission_time;
          // Set status based on score
          if (submission.score === 100) {
            problemData[problemIndex].status = 2; // solved
          } else if (submission.score > 0) {
            problemData[problemIndex].status = 1; // partial
          } else {
            problemData[problemIndex].status = 0; // failed
          }
        }
      });
    }

    // Create table row with problem cells (same as main page)
    const row = document.createElement('tr');

    problemData.forEach((problem, index) => {
      const cell = document.createElement('td');
      cell.className = `problem-cell ${getStatusColor(problem.status)}`;
      cell.dataset.status = problem.status.toString();
      cell.dataset.problemId = problem.name;
      cell.dataset.source = problem.source;
      cell.dataset.year = problem.year;
      cell.dataset.score = problem.score.toString();
      cell.dataset.readOnly = isReadOnly.toString();

      // Store additional data for read-only mode
      if (isReadOnly) {
        cell.dataset.subtaskScores = JSON.stringify(problem.subtask_scores || []);
        cell.dataset.submissionTime = problem.submission_time || '';
      }

      const cellContent = document.createElement('div');
      cellContent.className = 'problem-cell-content';

      const link = document.createElement('a');
      link.href = problem.link;
      link.target = '_blank';
      link.textContent = problem.name;
      cellContent.appendChild(link);

      cell.appendChild(cellContent);

      // Add click handler using the appropriate system
      if (isReadOnly) {
        cell.addEventListener('click', (e) => handleReadOnlyCellClick(cell, problem, e));
      } else {
        cell.addEventListener('click', (e) => handleCellClick(cell, problem.name, problem.source, problem.year, e));
      }

      row.appendChild(cell);
    });

    scoreTbody.appendChild(row);

    // Hide active contest UI elements
    activeContest.style.display = 'none';
    scoreEntry.style.display = 'block';
  }

  function showForm() {
    // Clear contest ongoing flag
    localStorage.setItem('contest_ongoing', 'false');

    // Hide skeleton and show form
    document.getElementById('vc-main-loading').style.display = 'none';

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
    headers: { 'Authorization': `Bearer ${sessionToken}` }
  });

  if (problemsResponse.ok) {
    problemsData = await problemsResponse.json();
  }

  // Check if user has an active contest
  if (data.active_contest) {
    // User has an ongoing contest
    currentActiveContest = data.active_contest;

    // Set localStorage flag for future loads
    localStorage.setItem('contest_ongoing', 'true');

    // Hide main skeleton
    document.getElementById('vc-main-loading').style.display = 'none';

    // Check if contest is ended (has end_time)
    if (currentActiveContest.end_time) {
      // Contest is finished, show score entry screen
      localStorage.setItem('contest_ongoing', 'false');
      vcForm.style.display = 'none';
      document.getElementById('active-contest').style.display = 'none';

      // Check if we have oj.uz data OR if this was previously synced
      const wasSynced = localStorage.getItem('is_synced') === 'true';
      const hasOjuzData = currentActiveContest.ojuz_data && currentActiveContest.ojuz_data.length > 0;

      // If we were synced but don't have ojuz_data, restore from localStorage
      if (wasSynced && !hasOjuzData) {
        const storedOjuzData = localStorage.getItem('ojuz_data');
        if (storedOjuzData) {
          try {
            currentActiveContest.ojuz_data = JSON.parse(storedOjuzData);
          } catch (e) {
            console.error('Failed to parse stored oj.uz data:', e);
          }
        }
      }

      showScoreEntry(hasOjuzData || wasSynced);
    } else {
      // Contest is still running, show timer
      vcForm.style.display = 'none';
      document.getElementById('active-contest').style.display = 'block';

      // Set contest title and metadata
      const titleText = currentActiveContest.contest_stage ?
        `${currentActiveContest.contest_name} <svg width="12" height="3" viewBox="0 0 12 3" style="vertical-align: middle; margin: 0 4px;"><rect width="12" height="2" fill="currentColor"/></svg> ${currentActiveContest.contest_stage}` :
        currentActiveContest.contest_name;
      document.getElementById('active-contest-title').innerHTML = titleText;

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

      // Calculate remaining time, capped at contest duration
      const startTime = new Date(currentActiveContest.start_time);
      const now = new Date();
      const elapsedMilliseconds = now - startTime;
      const elapsedSeconds = Math.floor(elapsedMilliseconds / 1000);
      const elapsedMinutes = Math.floor(elapsedSeconds / 60);

      // Cap elapsed time at contest duration
      const maxElapsedSeconds = currentActiveContest.duration_minutes * 60;
      const cappedElapsedSeconds = Math.min(elapsedSeconds, maxElapsedSeconds);

      const remainingSeconds = Math.max(0, maxElapsedSeconds - cappedElapsedSeconds);
      const remainingMinutes = Math.floor(remainingSeconds / 60);

      console.log('Start time:', startTime);
      console.log('Current time:', now);
      console.log('Elapsed seconds:', elapsedSeconds);
      console.log('Capped elapsed seconds:', cappedElapsedSeconds);
      console.log('Elapsed minutes:', elapsedMinutes);
      console.log('Remaining seconds:', remainingSeconds);
      console.log('Remaining minutes:', remainingMinutes);

      // Start timer with remaining time and capped elapsed time (in seconds precision)
      startTimerWithSeconds(remainingSeconds, cappedElapsedSeconds);
    }

    // Don't return here - we still need to set up event listeners
  }

  // Populate olympiad select (only if not in active contest)
  if (!currentActiveContest) {
    // No active contest, clear localStorage flag
    localStorage.setItem('contest_ongoing', 'false');

    // Hide main skeleton and show form
    document.getElementById('vc-main-loading').style.display = 'none';
    vcForm.style.display = 'block';

    olympiadSelect.innerHTML = '<option value="">Select Olympiad</option>';
    Object.keys(contestData).forEach(source => {
      const option = document.createElement('option');
      option.value = source;
      option.textContent = getFullOlympiadName(source);
      olympiadSelect.appendChild(option);
    });
  }

  // Update recent virtual contests
  // Hide skeleton and show actual content
  document.getElementById('past-vc-loading').style.display = 'none';
  pastVcList.style.display = 'block';
  document.querySelector('.view-all-link').style.display = 'block';

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
              <div class="past-vc-title">${contest.contest_source} ${contest.contest_year}${contest.contest_stage ? ` ${contest.contest_stage}` : ''}</div>
              <div class="past-vc-score">${contest.total_score || 0}/300</div>
              <div class="past-vc-date">${formattedDate}</div>
          `;
      item.addEventListener('click', (e) => {
        if (e.target.tagName === 'A' || e.target.closest('a')) {
          return;
        }
        const slug = (contest.contest_name + (contest.contest_stage || '')).toLowerCase().replace(/\s+/g, '');
        window.location.href = `virtual-contest-detail?contest=${slug}`;
      });
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

    // Hide completion warning when olympiad changes
    const completionWarning = document.getElementById('completion-warning');
    completionWarning.style.display = 'none';

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

    // Hide completion warning when contest changes
    const completionWarning = document.getElementById('completion-warning');
    completionWarning.style.display = 'none';

    // Hide day row initially
    dayRow.style.display = 'none';

    if (selectedContest && contestData[selectedOlympiad]) {
      const [contestName, year] = selectedContest.split('|');
      const contests = contestData[selectedOlympiad][year] || [];
      const matchingContests = contests.filter(c => c.name === contestName);

      // Get unique stages and filter out null/undefined stages
      const stages = [...new Set(matchingContests.map(c => c.stage).filter(stage => stage != null))].sort();

      // Check if there's only one contest and it has no stage
      if (matchingContests.length === 1 && (matchingContests[0].stage == null || matchingContests[0].stage === '')) {
        // Skip stage selection entirely - directly show contest details
        const contest = matchingContests[0];

        // Check if this contest has been completed
        const contestKey = `${contestName}|${contest.stage || ''}`;
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

        const hasOjuz = platforms && platforms.length > 0 && platforms.every(p => p === 'oj.uz');
        if (hasOjuz) {
          ojuzSection.style.display = 'block';
        } else {
          ojuzSection.style.display = 'none';
        }

        // Don't show the day row at all
        dayRow.style.display = 'none';
      } else if (stages.length > 0) {
        // Normal behavior - show stage selection
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

      const hasOjuz = platforms && platforms.length > 0 && platforms.every(p => p === 'oj.uz');
      if (hasOjuz) {
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

    // Handle both cases: with stage selection and without
    let contest;
    let finalStage;

    if (daySelect.style.display === 'none' || !selectedStage) {
      // No stage selection was shown - find the single contest
      const matchingContests = contests.filter(c => c.name === contestName);
      if (matchingContests.length === 1) {
        contest = matchingContests[0];
        finalStage = contest.stage || null; // Use the contest's stage (which might be null)
      } else {
        showMessage('Error: Multiple contests found but no stage selected.', 'error');
        return;
      }
    } else {
      // Normal stage selection
      contest = contests.find(c => c.name === contestName && c.stage === selectedStage);
      finalStage = selectedStage;
    }

    if (!contest) {
      showMessage('Error: Contest not found.', 'error');
      return;
    }

    // Get the oj.uz username if provided
    const ojuzUsername = document.getElementById('ojuz-username')?.value?.trim() || null;

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
          contest_stage: finalStage
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

      // Set localStorage flag for active contest
      localStorage.setItem('contest_ongoing', 'true');
      localStorage.removeItem('is_synced'); // Clear any previous sync flag

      // Store oj.uz username if provided
      if (ojuzUsername) {
        localStorage.setItem('ojuz_username', ojuzUsername);
      } else {
        localStorage.removeItem('ojuz_username');
      }
    } catch (error) {
      showMessage('Failed to start contest: ' + error.message);
      return;
    }

    // Update currentActiveContest with the contest data we just started FIRST
    currentActiveContest = {
      contest_name: contestName,
      contest_stage: finalStage,
      start_time: new Date().toISOString(),
      duration_minutes: contest.duration_minutes,
      location: contest.location || '',
      website: contest.website || '',
      link: contest.link || '',
      ojuz_username: ojuzUsername // Store the oj.uz username
    };

    // Hide form and show active contest
    vcForm.style.display = 'none';
    activeContest.style.display = 'block';

    // Set contest title and metadata
    const titleText = finalStage ? `${contestName} <svg width="12" height="3" viewBox="0 0 12 3" style="vertical-align: middle; margin: 0 4px;"><rect width="12" height="2" fill="currentColor"/></svg> ${finalStage}` : contestName;
    document.getElementById('active-contest-title').innerHTML = titleText;

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

    // Start timer with actual contest duration (after currentActiveContest is set)
    startTimer(contest.duration_minutes);
  });

  // Handle end contest button
  document.getElementById('end-contest-btn').addEventListener('click', async () => {
    // Get oj.uz username from localStorage (stored when contest started) or from currentActiveContest
    const ojuzUsername = localStorage.getItem('ojuz_username') || currentActiveContest?.ojuz_username || null;

    try {
      // Hide entire UI and show loading spinner if oj.uz username is provided
      if (ojuzUsername) {
        activeContest.style.display = 'none';
        document.getElementById('ojuz-sync-loading').style.display = 'flex';
      }

      const response = await fetch(`${apiUrl}/api/virtual-contests/end`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ojuz_username: ojuzUsername
        })
      });

      // Hide loading spinner and restore UI
      if (ojuzUsername) {
        document.getElementById('ojuz-sync-loading').style.display = 'none';
      }

      if (response.ok) {
        const result = await response.json();

        console.log(ojuzUsername);
        console.log(result);
        console.log(result.submissions);
        if (ojuzUsername && result.submissions) {
          // Show score entry with oj.uz data in read-only mode
          localStorage.setItem('contest_ongoing', 'false');
          localStorage.setItem('is_synced', 'true');

          // Store oj.uz data in localStorage for persistence across refreshes
          localStorage.setItem('ojuz_data', JSON.stringify(result.submissions));

          // Update currentActiveContest to mark it as ended with capped end time
          const contestDurationMs = currentActiveContest.duration_minutes * 60 * 1000;
          const startTime = new Date(currentActiveContest.start_time);
          const maxEndTime = new Date(startTime.getTime() + contestDurationMs);
          const actualEndTime = new Date();
          const cappedEndTime = new Date(Math.min(actualEndTime.getTime(), maxEndTime.getTime()));

          currentActiveContest.end_time = cappedEndTime.toISOString();
          currentActiveContest.ojuz_data = result.submissions; // Store detailed submission data

          showScoreEntry(true); // Pass true to indicate read-only mode with oj.uz data
        } else {
          // Hide active contest and show manual score entry
          localStorage.setItem('contest_ongoing', 'false');
          localStorage.removeItem('is_synced');
          localStorage.removeItem('ojuz_username'); // Clear stored username

          // Update currentActiveContest to mark it as ended with capped end time
          const contestDurationMs = currentActiveContest.duration_minutes * 60 * 1000;
          const startTime = new Date(currentActiveContest.start_time);
          const maxEndTime = new Date(startTime.getTime() + contestDurationMs);
          const actualEndTime = new Date();
          const cappedEndTime = new Date(Math.min(actualEndTime.getTime(), maxEndTime.getTime()));

          currentActiveContest.end_time = cappedEndTime.toISOString();

          showScoreEntry(false); // Pass false for manual entry mode
        }
      } else {
        throw new Error('Failed to end contest');
      }
    } catch (error) {
      // Hide loading spinner and restore UI on error
      if (ojuzUsername) {
        document.getElementById('ojuz-sync-loading').style.display = 'none';
        activeContest.style.display = 'block';
      }
      console.error('Error ending contest:', error);
      showMessage('Failed to end contest. Please try again.', 'error');
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

    // Handle both cases: with stage selection and without
    let contest;
    let selectedStage;

    if (daySelect.style.display === 'none') {
      // No stage selection was shown - find the single contest
      const matchingContests = contests.filter(c => c.name === contestName);
      if (matchingContests.length === 1) {
        contest = matchingContests[0];
        selectedStage = contest.stage;
      }
    } else {
      // Normal stage selection
      selectedStage = daySelect.value;
      contest = contests.find(c => c.name === contestName && c.stage === selectedStage);
    }

    console.log('Found contest:', contest);

    if (contest && contest.link) {
      window.open(contest.link, '_blank');
    } else {
      showMessage('No contest link available for this contest.', 'warning');
    }
  });

  // Helper function to get status color
  function getStatusColor(status) {
    switch (status) {
      case 2: return 'green';
      case 1: return 'yellow';
      case 0: return 'red';
      default: return 'white';
    }
  }

  // Handle read-only cell clicks for oj.uz mode
  function handleReadOnlyCellClick(cell, problem, event) {
    event.preventDefault();

    const subtaskScores = JSON.parse(cell.dataset.subtaskScores || '[]');
    const totalScore = parseFloat(cell.dataset.score) || 0;

    showReadOnlyPopup(cell, {
      problemName: problem.name,
      totalScore: totalScore,
      subtaskScores: subtaskScores
    }, event);
  }

  // Show read-only popup for oj.uz scores
  function showReadOnlyPopup(cell, data, event) {
    let readonlyPopup = document.getElementById('readonly-popup');
    if (!readonlyPopup) {
      // Create the popup if it doesn't exist
      const popupDiv = document.createElement('div');
      popupDiv.id = 'readonly-popup';
      popupDiv.className = 'readonly-popup hidden';
      popupDiv.innerHTML = `
        <div class="readonly-popup-content">
          <div class="readonly-popup-header">
            <div id="readonly-popup-problem"></div>
            <div id="readonly-popup-total-score"></div>
          </div>
          <div class="readonly-popup-subtasks" id="readonly-popup-subtasks"></div>
        </div>
      `;
      document.body.appendChild(popupDiv);

      // Close popup when clicking outside
      popupDiv.addEventListener('click', (e) => {
        if (e.target === popupDiv) {
          hideReadOnlyPopup();
        }
      });

      // Close popup on escape key
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          hideReadOnlyPopup();
        }
      });

      readonlyPopup = popupDiv;
    }

    // Populate popup content
    document.getElementById('readonly-popup-problem').textContent = data.problemName;
    document.getElementById('readonly-popup-total-score').textContent = `Total Score: ${data.totalScore}/100`;

    // Create subtasks list
    const subtasksDiv = document.getElementById('readonly-popup-subtasks');
    if (data.subtaskScores && data.subtaskScores.length > 0) {
      subtasksDiv.innerHTML = '<div class="subtasks-header">Subtask Scores:</div>';
      const subtasksList = document.createElement('div');
      subtasksList.className = 'subtasks-list';

      data.subtaskScores.forEach((score, index) => {
        const subtaskDiv = document.createElement('div');
        subtaskDiv.className = 'subtask-item';
        subtaskDiv.innerHTML = `
          <span class="subtask-label">Subtask ${index + 1}:</span>
          <span class="subtask-score">${score}</span>
        `;
        subtasksList.appendChild(subtaskDiv);
      });

      subtasksDiv.appendChild(subtasksList);
    } else {
      subtasksDiv.innerHTML = '<div class="no-subtasks">No subtask information available</div>';
    }

    // Show popup
    readonlyPopup.style.display = 'flex';
    readonlyPopup.classList.remove('hidden');

    // Trigger animation after a brief delay to ensure display is set
    setTimeout(() => {
      readonlyPopup.classList.add('show');
    }, 10);
  }

  function hideReadOnlyPopup() {
    const popup = document.getElementById('readonly-popup');
    if (popup) {
      popup.classList.remove('show');
      popup.classList.add('hidden');

      // Hide the element after animation completes
      setTimeout(() => {
        popup.style.display = 'none';
      }, 300);
    }
  }
  document.getElementById('submit-scores-btn').addEventListener('click', async () => {
    if (!currentActiveContest) {
      showMessage('No active contest data available.');
      return;
    }

    // Check if we're in read-only mode (with oj.uz data)
    const isReadOnly = currentActiveContest.ojuz_data;

    if (isReadOnly) {
      // oj.uz mode - just confirm the contest completion
      try {
        const confirmResponse = await fetch(`${apiUrl}/api/virtual-contests/confirm`, {
          method: 'POST',
          credentials: 'include',
          headers: {
            'Authorization': `Bearer ${sessionToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (!confirmResponse.ok) {
          const error = await confirmResponse.json();
          showMessage('Failed to confirm virtual contest: ' + error.error);
          return;
        }

        // Redirect to virtual history page
        window.location.href = '/virtual-history';

        // Clear stored data since contest is now completed
        localStorage.removeItem('is_synced');
        localStorage.removeItem('ojuz_data');
        localStorage.removeItem('ojuz_username');

      } catch (error) {
        showMessage('Failed to confirm contest: ' + error.message);
      }

      return; // Exit early for oj.uz mode
    }

    // Manual entry mode - collect and validate scores
    let scores = [];
    let totalScore = 0;

    const problemCells = document.querySelectorAll('#score-problems-tbody .problem-cell');

    // Validate scores first
    for (let i = 0; i < problemCells.length; i++) {
      const score = parseFloat(problemCells[i].dataset.score) || 0;
      if (score < 0 || score > 100) {
        showMessage(`${problemCells[i].dataset.problemId} score must be between 0 and 100.`, 'warning');
        return;
      }
      scores.push(score);
      totalScore += score;
    }

    console.log('Using manual scores:', scores, 'Total:', totalScore);

    try {
      // Update individual problem statuses and scores
      for (let i = 0; i < problemCells.length; i++) {
        const cell = problemCells[i];
        const problemName = cell.dataset.problemId;
        const source = cell.dataset.source;
        const year = parseInt(cell.dataset.year);
        const score = parseFloat(cell.dataset.score) || 0;
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

      // Submit the virtual contest scores
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

      // Clear stored data since contest is now completed
      localStorage.removeItem('is_synced');
      localStorage.removeItem('ojuz_data');
      localStorage.removeItem('ojuz_username');

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

      timer.textContent = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

      // Only update progress if we have contest data
      if (currentActiveContest && currentActiveContest.duration_minutes) {
        // Total elapsed time = already elapsed + timer elapsed
        const totalElapsedSeconds = alreadyElapsedSeconds + timerElapsedSeconds;
        const totalContestSeconds = currentActiveContest.duration_minutes * 60;

        // Cap elapsed time at contest duration
        const cappedElapsedSeconds = Math.min(totalElapsedSeconds, totalContestSeconds);

        const progressPercent = (cappedElapsedSeconds / totalContestSeconds) * 100;
        progressFill.style.width = `${Math.min(100, progressPercent)}%`;

        const elapsedHours = Math.floor(cappedElapsedSeconds / 3600);
        const elapsedMins = Math.floor((cappedElapsedSeconds % 3600) / 60);
        progressText.textContent = `${elapsedHours}h ${elapsedMins}m elapsed`;
      }
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

        // Only show message if page is visible to avoid popup-like behavior
        if (!document.hidden) {
          // Small delay to ensure consistent behavior
          setTimeout(() => {
            showMessage('Time is up! Please end your contest and submit your scores.', 'warning');
          }, 100);
        }
      }
    }, 1000);
  }

  function startTimer(remainingMinutes, alreadyElapsedMinutes = 0) {
    // Convert to seconds and use the seconds-based function
    startTimerWithSeconds(remainingMinutes * 60, alreadyElapsedMinutes * 60);
  }
});