// Virtual Contest Detail JavaScript
document.addEventListener('DOMContentLoaded', async () => {
  const sessionToken = localStorage.getItem('sessionToken');
  
  // Get contest slug from URL query parameters
  const urlParams = new URLSearchParams(window.location.search);
  const slug = urlParams.get('contest');
  
  if (!slug) {
    showError();
    return;
  }

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
  
  // Show the welcome message
  document.getElementById('welcome-message').innerHTML = `Welcome, ${username}`;

  // Load contest details
  await loadContestDetails(slug);

  // Handle logout
  document.getElementById('logout-button').addEventListener('click', async (event) => {
    event.preventDefault();
    
    const res = await fetch(`${apiUrl}/api/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {'Authorization': `Bearer ${sessionToken}`}
    });

    if (res.status === 200) {
      window.location.href = 'home';
    } else {
      console.error('Logout failed');
    }
  });
});

async function loadContestDetails(slug) {
  const sessionToken = localStorage.getItem('sessionToken');
  
  try {
    // Fetch contest details using slug
    const response = await fetch(`${apiUrl}/api/virtual-contests/detail/${slug}`, {
      method: 'GET',
      credentials: 'include',
      headers: {'Authorization': `Bearer ${sessionToken}`}
    });

    if (!response.ok) {
      showError();
      return;
    }

    const contestData = await response.json();
    
    // Fetch additional data for proper display
    await fetchAdditionalData(contestData);
    
  } catch (error) {
    console.error('Error loading contest details:', error);
    showError();
  }
}

async function fetchAdditionalData(contest) {
  const sessionToken = localStorage.getItem('sessionToken');
  
  try {
    // Fetch contest metadata and problems data
    const vcResponse = await fetch(`${apiUrl}/api/virtual-contests`, {
      method: 'GET',
      credentials: 'include',
      headers: {'Authorization': `Bearer ${sessionToken}`}
    });
    
    let contestMetadata = {};
    let problemsData = {};
    
    if (vcResponse.ok) {
      const vcData = await vcResponse.json();
      const contestDataAll = vcData.contests;
      
      // Fetch problems data
      const contestSources = Object.keys(contestDataAll);
      const problemsResponse = await fetch(`${apiUrl}/api/problems?names=${contestSources.join(',')}`, {
        method: 'GET',
        credentials: 'include',
        headers: {'Authorization': `Bearer ${sessionToken}`}
      });
      
      if (problemsResponse.ok) {
        problemsData = await problemsResponse.json();
      }
      
      // Find contest metadata
      for (const [olympiad, years] of Object.entries(contestDataAll)) {
        for (const [year, contests] of Object.entries(years)) {
          const contestInfo = contests.find(c => c.name === contest.contest_name && c.stage === contest.contest_stage);
          if (contestInfo) {
            contestMetadata = contestInfo;
            break;
          }
        }
        if (contestMetadata.name) break;
      }
    }
    
    // Fetch contest scores for medal/rank data
    const contestKey = `${contest.contest_name}|${contest.contest_stage}`;
    const scoresResponse = await fetch(`${apiUrl}/api/contest-scores?contests=${contestKey}`, {
      method: 'GET',
      credentials: 'include',
      headers: {'Authorization': `Bearer ${sessionToken}`}
    });
    
    let contestScores = {};
    if (scoresResponse.ok) {
      contestScores = await scoresResponse.json();
    }
    
    displayContestDetails(contest, contestMetadata, problemsData, contestScores[contestKey]);
    
  } catch (error) {
    console.error('Error fetching additional data:', error);
    displayContestDetails(contest, {}, {}, {});
  }
}

function displayContestDetails(contest, contestMetadata, problemsData, scoreData) {
  document.getElementById('vc-detail-loading').style.display = 'none';
  document.getElementById('vc-detail-content').style.display = 'block';
  
  // Parse problem scores
  const problemScores = JSON.parse(contest.per_problem_scores || '[]');
  const problemCount = problemScores.length || 3;
  const maxScore = problemCount * 100;
  const totalScore = contest.total_score || 0;
  
  // Calculate medal and rank
  let medalClass = '';
  let rank = 'N/A';
  let totalParticipants = 'N/A';
  
  if (scoreData && scoreData.medal_cutoffs && scoreData.medal_cutoffs.length >= 3) {
    const [goldCutoff, silverCutoff, bronzeCutoff] = scoreData.medal_cutoffs;
    
    if (totalScore >= goldCutoff) {
      medalClass = 'medal-gold';
    } else if (totalScore >= silverCutoff) {
      medalClass = 'medal-silver';
    } else if (totalScore >= bronzeCutoff) {
      medalClass = 'medal-bronze';
    }
    
    // Calculate rank based on total score and problem scores distribution
    if (scoreData.problem_scores && scoreData.problem_scores.length > 0) {
      // Sum up individual problem scores to get total scores for all participants
      const allTotalScores = [];
      const numParticipants = scoreData.problem_scores[0].length;
      
      for (let i = 0; i < numParticipants; i++) {
        let participantTotal = 0;
        for (let j = 0; j < scoreData.problem_scores.length; j++) {
          participantTotal += scoreData.problem_scores[j][i] || 0;
        }
        allTotalScores.push(participantTotal);
      }
      
      // Sort descending
      allTotalScores.sort((a, b) => b - a);
      
      // Find rank (handle ties by using the highest possible rank)
      let currentRank = 1;
      for (let i = 0; i < allTotalScores.length; i++) {
        if (allTotalScores[i] > totalScore) {
          currentRank = i + 1;
        } else {
          break;
        }
      }
      rank = currentRank;
      totalParticipants = allTotalScores.length;
    }
  }
  
  // Calculate time used
  const startTime = new Date(contest.started_at);
  const endTime = new Date(contest.ended_at);
  const durationMs = endTime - startTime;
  const durationMinutes = Math.floor(durationMs / (1000 * 60));
  const hours = Math.floor(durationMinutes / 60);
  const minutes = durationMinutes % 60;
  const timeUsed = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
  
  // Format date
  const date = new Date(contest.started_at);
  const formattedDate = date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
  
  // Calculate stats
  const scoreRate = Math.round((totalScore / maxScore) * 100);
  const variance = calculateVariance(problemScores);
  const bestScore = problemScores.length > 0 ? Math.max(...problemScores) : 0;
  const fullScores = problemScores.filter(score => score === 100).length;
  
  // Calculate advanced statistics
  let avgProblemScore = 0;
  let medianScore = 0;
  let participantPercentile = 0;
  let solvedCount = problemScores.filter(score => score > 0).length;
  let perfectProblems = [];
  let hardestProblem = '';
  let easiestProblem = '';
  let contestMean = 0;
  let aboveAverage = 0;
  let consistency = '';
  let performancePattern = '';
  
  console.log('Debug: problemCount =', problemCount, 'solvedCount =', solvedCount, 'fullScores =', fullScores);
  
  if (problemScores.length > 0) {
    avgProblemScore = Math.round(problemScores.reduce((a, b) => a + b, 0) / problemScores.length);
    
    const sortedMyScores = [...problemScores].sort((a, b) => b - a);
    medianScore = problemScores.length % 2 === 0 
      ? (sortedMyScores[Math.floor(problemScores.length / 2) - 1] + sortedMyScores[Math.floor(problemScores.length / 2)]) / 2
      : sortedMyScores[Math.floor(problemScores.length / 2)];
    medianScore = Math.round(medianScore);
    
    // Find perfect problems
    perfectProblems = problemScores.map((score, idx) => ({ score, idx }))
      .filter(p => p.score === 100)
      .map(p => p.idx);
  }
  
  // Calculate contest-wide statistics
  if (scoreData && scoreData.problem_scores) {
    // Calculate percentile
    const allTotalScores = [];
    const numParticipants = scoreData.problem_scores[0].length;
    
    for (let i = 0; i < numParticipants; i++) {
      let participantTotal = 0;
      for (let j = 0; j < scoreData.problem_scores.length; j++) {
        participantTotal += scoreData.problem_scores[j][i] || 0;
      }
      allTotalScores.push(participantTotal);
    }
    
    const betterThanCount = allTotalScores.filter(score => score < totalScore).length;
    participantPercentile = Math.round((betterThanCount / allTotalScores.length) * 100);
    
    // Calculate contest mean
    contestMean = Math.round(allTotalScores.reduce((a, b) => a + b, 0) / allTotalScores.length);
    aboveAverage = totalScore - contestMean;
    
    // Find hardest and easiest problems based on average scores
    if (scoreData.problem_scores.length > 0) {
      const problemAverages = scoreData.problem_scores.map((problemScores, idx) => {
        const avg = problemScores.reduce((a, b) => a + b, 0) / problemScores.length;
        return { avg, idx };
      });
      
      problemAverages.sort((a, b) => a.avg - b.avg);
      const hardestIdx = problemAverages[0].idx;
      const easiestIdx = problemAverages[problemAverages.length - 1].idx;
      
      // Get problem names
      try {
        if (contestMetadata && contestMetadata.problems) {
          if (contestMetadata.problems[hardestIdx]) {
            const prob = contestMetadata.problems[hardestIdx];
            const olympiadProblems = problemsData[prob.source];
            if (olympiadProblems && olympiadProblems[prob.year]) {
              const problem = olympiadProblems[prob.year].find(p => 
                p.source === prob.source && p.year === prob.year && p.number === prob.number
              );
              hardestProblem = problem ? problem.name : `Problem ${hardestIdx + 1}`;
            }
          }
          
          if (contestMetadata.problems[easiestIdx]) {
            const prob = contestMetadata.problems[easiestIdx];
            const olympiadProblems = problemsData[prob.source];
            if (olympiadProblems && olympiadProblems[prob.year]) {
              const problem = olympiadProblems[prob.year].find(p => 
                p.source === prob.source && p.year === prob.year && p.number === prob.number
              );
              easiestProblem = problem ? problem.name : `Problem ${easiestIdx + 1}`;
            }
          }
        }
      } catch (error) {
        hardestProblem = `Problem ${hardestIdx + 1}`;
        easiestProblem = `Problem ${easiestIdx + 1}`;
      }
    }
  }
  
  // Build the detail page content with proper styling
  const content = `
    <div class="vc-detail-main ${medalClass}">
      <div class="vc-detail-header-section">
        <div>
          <div class="vc-detail-title">${contest.contest_source} ${contest.contest_year} ${contest.contest_stage}</div>
          <div class="vc-detail-subtitle">${problemCount} Problems</div>
          ${contestMetadata.location || contestMetadata.website ? `<div class="vc-detail-location">${contestMetadata.location || ''}${contestMetadata.location && contestMetadata.website ? ' | ' : ''}${contestMetadata.website ? `<a href="${contestMetadata.website}" target="_blank">${contestMetadata.website}</a>` : ''}</div>` : ''}
        </div>
        ${medalClass ? `<div class="vc-detail-medal-ribbon ${medalClass}"></div>` : ''}
      </div>
      
      <div class="vc-detail-summary">
        <div class="vc-detail-score-display">
          <div class="vc-detail-total-score">${totalScore}/${maxScore}</div>
          <div class="vc-detail-score-rate-container">
            <div class="score-progress-bar">
              <div class="score-progress-fill" style="width: ${scoreRate}%"></div>
            </div>
            <span class="score-percentage">${scoreRate}% score rate</span>
          </div>
        </div>
        <div class="vc-detail-rank">
          <div class="rank-number">#${rank}</div>
          <div class="rank-text">out of ${totalParticipants}</div>
        </div>
      </div>
      
      <div class="vc-detail-metadata">
        <div class="vc-detail-meta-item">
          <div class="vc-detail-meta-label">Date</div>
          <div class="vc-detail-meta-value">${formattedDate}</div>
        </div>
        <div class="vc-detail-meta-item">
          <div class="vc-detail-meta-label">Time Used</div>
          <div class="vc-detail-meta-value">${timeUsed}</div>
        </div>
        <div class="vc-detail-meta-item">
          <div class="vc-detail-meta-label">Medal</div>
          <div class="vc-detail-meta-value">${medalClass ? (medalClass === 'medal-gold' ? 'Gold' : medalClass === 'medal-silver' ? 'Silver' : 'Bronze') : 'No Medal'}</div>
        </div>
        <div class="vc-detail-meta-item">
          <div class="vc-detail-meta-label">Percentile</div>
          <div class="vc-detail-meta-value">${participantPercentile}th</div>
        </div>
      </div>
      
      <div class="vc-detail-problems-section">
        <h3>Problem Performance</h3>
        <div class="vc-detail-problems">
          ${generateProblemsHTML(problemScores, contest, contestMetadata, problemsData, scoreData)}
        </div>
      </div>
      
      <div class="vc-detail-stats-section">
        <h3>Performance Analysis</h3>
        
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-number ${fullScores >= problemCount / 2 ? 'positive' : ''}">${fullScores}</div>
            <div class="stat-label">Perfect scores</div>
          </div>
          <div class="stat-item">
            <div class="stat-number ${solvedCount === problemCount ? 'positive' : (solvedCount < problemCount / 2 ? 'negative' : 'warning')}">${solvedCount}</div>
            <div class="stat-label">Attempted</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">${avgProblemScore}</div>
            <div class="stat-label">Average</div>
          </div>
          <div class="stat-item">
            <div class="stat-number">${Math.min(...problemScores)}-${Math.max(...problemScores)}</div>
            <div class="stat-label">Range</div>
          </div>
        </div>
        
        <div class="contest-comparison">
          <div class="comparison-header">
            <span class="comparison-title">Contest Performance</span>
          </div>
          <div class="comparison-bars">
            <div class="score-bar">
              <div class="score-bar-container">
                ${contestMean <= totalScore ? `
                  <div class="score-bar-fill yours" style="width: ${(totalScore / maxScore) * 100}%"></div>
                  <div class="score-bar-fill average" style="width: ${(contestMean / maxScore) * 100}%"></div>
                ` : `
                  <div class="score-bar-fill average" style="width: ${(contestMean / maxScore) * 100}%"></div>
                  <div class="score-bar-fill yours" style="width: ${(totalScore / maxScore) * 100}%"></div>
                `}
                <span class="score-bar-value">${contestMean}/${totalScore}</span>
              </div>
            </div>
          </div>
          <div class="comparison-summary">
            <span class="comparison-delta ${aboveAverage >= 0 ? 'positive' : 'negative'}">
              ${aboveAverage >= 0 ? '+' : ''}${aboveAverage} vs average
            </span>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.getElementById('vc-detail-content').innerHTML = content;
}

function generateProblemsHTML(problemScores, contest, contestMetadata, problemsData, scoreData) {
  if (problemScores.length === 0) {
    return '<div class="vc-detail-problem-empty">No problem data available</div>';
  }
  
  return problemScores.map((score, index) => {
    // Try to get actual problem name
    let problemName = `Problem ${index + 1}`;
    try {
      if (contestMetadata && contestMetadata.problems && contestMetadata.problems[index]) {
        const prob = contestMetadata.problems[index];
        // Find the problem in problemsData
        const olympiadProblems = problemsData[prob.source];
        if (olympiadProblems && olympiadProblems[prob.year]) {
          const problem = olympiadProblems[prob.year].find(p => 
            p.source === prob.source && 
            p.year === prob.year && 
            p.number === prob.number
          );
          if (problem) {
            problemName = problem.name;
          }
        }
      }
    } catch (error) {
      console.error('Error getting problem name:', error);
    }
    
    // Calculate rank for this problem
    let problemRank = 'N/A';
    let problemTotal = 'N/A';
    if (scoreData && scoreData.problem_scores && scoreData.problem_scores.length > index) {
      const problemScoresList = scoreData.problem_scores[index] || [];
      if (problemScoresList.length > 0) {
        const sortedScores = [...problemScoresList].sort((a, b) => b - a);
        
        // Find rank (handle ties by using the highest possible rank)
        let currentRank = 1;
        for (let i = 0; i < sortedScores.length; i++) {
          if (sortedScores[i] > score) {
            currentRank = i + 1;
          } else {
            break;
          }
        }
        problemRank = currentRank;
        problemTotal = sortedScores.length;
      }
    }
    
    // Determine score color class
    let scoreClass = '';
    if (score === 100) {
      scoreClass = 'score-perfect'; // Green
    } else if (score > 0) {
      scoreClass = 'score-partial'; // Yellow
    } else {
      scoreClass = 'score-zero'; // Red
    }
    
    return `
      <div class="vc-detail-problem">
        <div class="vc-detail-problem-header">
          <div class="vc-detail-problem-info">
            <div class="vc-detail-problem-name">${problemName}</div>
            <div class="vc-detail-problem-rank">#${problemRank} of ${problemTotal}</div>
          </div>
          <div class="vc-detail-problem-score ${scoreClass}">${score}/100</div>
        </div>
      </div>
    `;
  }).join('');
}

function calculateVariance(scores) {
  if (scores.length === 0) return 0;
  
  const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
  const squaredDiffs = scores.map(score => Math.pow(score - mean, 2));
  return Math.round(Math.sqrt(squaredDiffs.reduce((a, b) => a + b, 0) / scores.length));
}

function showError() {
  document.getElementById('vc-detail-loading').style.display = 'none';
  document.getElementById('vc-detail-error').style.display = 'block';
}