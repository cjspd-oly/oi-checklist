from datetime import timedelta, datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import requests
import re
import time
import json
from database.db import get_db

def sync_ojuz_submissions(active_contest, ojuz_username):
    """
    Utility function to sync oj.uz submissions for a virtual contest.
    
    Args:
        active_contest: The active contest object with user_id, contest_name, contest_stage, start_time, end_time
        ojuz_username: The user's oj.uz username
        
    Returns:
        List of submission data dictionaries
    """
    db = get_db()
    
    user_id = active_contest['user_id']
    contest_name = active_contest['contest_name']
    contest_stage = active_contest['contest_stage']
    contest_start_time = active_contest['start_time']
    contest_end_time = active_contest['end_time']
    
    # Convert times to datetime objects for comparison
    start_dt = datetime.fromisoformat(contest_start_time.replace('Z', '+00:00'))
    end_dt = datetime.fromisoformat(contest_end_time.replace('Z', '+00:00'))
    
    # Get contest problems and their oj.uz links
    if contest_stage is not None:
        contest_problems = db.execute('''
            SELECT 
                cp.problem_index,
                p.name as problem_name,
                p.link as problem_link
            FROM contest_problems cp
            JOIN problems p ON cp.problem_source = p.source 
                            AND cp.problem_year = p.year 
                            AND cp.problem_number = p.number
            WHERE cp.contest_name = ? AND cp.contest_stage = ?
            AND p.link LIKE 'https://oj.uz/%'
            ORDER BY cp.problem_index
        ''', (contest_name, contest_stage)).fetchall()
    else:
        contest_problems = db.execute('''
            SELECT 
                cp.problem_index,
                p.name as problem_name,
                p.link as problem_link
            FROM contest_problems cp
            JOIN problems p ON cp.problem_source = p.source 
                            AND cp.problem_year = p.year 
                            AND cp.problem_number = p.number
            WHERE cp.contest_name = ? AND cp.contest_stage IS NULL
            AND p.link LIKE 'https://oj.uz/%'
            ORDER BY cp.problem_index
        ''', (contest_name,)).fetchall()
    
    print(f"Found {len(contest_problems)} oj.uz problems for contest {contest_name}, stage: {contest_stage}")
    for row in contest_problems:
        print(dict(row))
    
    if not contest_problems:
        return []
    
    # Create mapping of problem links to problem info
    problem_link_map = {
        problem['problem_link']: {
            'index': problem['problem_index'],
            'name': problem['problem_name']
        }
        for problem in contest_problems
    }
    
    # Headers for requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"Starting oj.uz sync for user {ojuz_username}, contest {contest_name} {contest_stage}")
    print(f"Contest time range: {contest_start_time} to {contest_end_time}")
    
    # Step 1: Get all relevant submissions from the submissions page(s)
    relevant_submissions = []
    submissions_url = f"https://oj.uz/submissions?handle={ojuz_username}"
    
    while submissions_url:
        print(f"Fetching submissions page: {submissions_url}")
        
        try:
            response = requests.get(submissions_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch submissions page: {response.status_code}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all submission rows in the table
            submission_rows = soup.select('table.table tbody tr')
            if not submission_rows:
                print("No submission rows found, breaking")
                break
            
            last_submission_id = None
            found_relevant = False
            
            for row in submission_rows:
                try:
                    # Extract submission time
                    time_span = row.find('span', {'data-timestamp-iso': True})
                    if not time_span:
                        continue
                    
                    submission_time_str = time_span['data-timestamp-iso']
                    submission_dt = datetime.fromisoformat(submission_time_str.replace('Z', '+00:00'))
                    
                    # Check if submission is within contest time range
                    if submission_dt < start_dt:
                        # We've gone past the contest start time, stop pagination
                        print(f"Reached submission before contest start time: {submission_time_str}")
                        submissions_url = None
                        break
                    
                    if submission_dt > end_dt:
                        # Submission is after contest end, skip
                        continue
                    
                    # Extract submission ID
                    submission_link = row.find('a', href=re.compile(r'/submission/\d+'))
                    if not submission_link:
                        continue
                    
                    submission_id = submission_link['href'].split('/')[-1]
                    last_submission_id = submission_id
                    
                    # Extract problem link
                    problem_link_elem = row.find('a', href=re.compile(r'/problem/view/'))
                    if not problem_link_elem:
                        continue
                    
                    problem_link = 'https://oj.uz' + problem_link_elem['href']
                    
                    # Check if this problem is part of our contest
                    if problem_link in problem_link_map:
                        print(f"Found relevant submission {submission_id} for {problem_link} at {submission_time_str}")
                        relevant_submissions.append({
                            'submission_id': submission_id,
                            'submission_time': submission_time_str,
                            'problem_link': problem_link,
                            'problem_index': problem_link_map[problem_link]['index'],
                            'problem_name': problem_link_map[problem_link]['name']
                        })
                        found_relevant = True
                
                except Exception as e:
                    print(f"Error processing submission row: {e}")
                    continue
            
            # Prepare next page URL if we need to continue
            if submissions_url and last_submission_id and not found_relevant:
                # If we didn't find any relevant submissions on this page, continue to next
                submissions_url = f"https://oj.uz/submissions?handle={ojuz_username}&direction=down&id={last_submission_id}"
            elif submissions_url and last_submission_id and found_relevant:
                # We found some, but might need more from earlier pages
                submissions_url = f"https://oj.uz/submissions?handle={ojuz_username}&direction=down&id={last_submission_id}"
            else:
                submissions_url = None
                
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"Error fetching submissions page: {e}")
            break
    
    print(f"Found {len(relevant_submissions)} relevant submissions")
    
    # Step 2: Fetch detailed scores for each submission (only if submissions exist)
    detailed_submissions = []
    if relevant_submissions:
        def fetch_submission_details(submission_info):
            try:
                submission_url = f"https://oj.uz/submission/{submission_info['submission_id']}"
                print(f"Fetching submission details: {submission_url}")
                
                response = requests.get(submission_url, headers=headers, timeout=10)
                if response.status_code != 200:
                    print(f"Failed to fetch submission {submission_info['submission_id']}")
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract subtask scores
                subtask_scores = []
                total_score = 0
                
                # Find all subtask panels
                subtask_divs = soup.find_all('div', id=re.compile(r'subtask_results_div_\d+'))
                
                for subtask_div in subtask_divs:
                    try:
                        # Find the subtask score span
                        score_span = subtask_div.find('span', class_=re.compile(r'subtask-score'))
                        if score_span:
                            # Extract score text like "17 / 17" or "0 / 6" or "39.61 / 100"
                            score_text = score_span.get_text().strip()
                            score_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)', score_text)
                            if score_match:
                                earned = float(score_match.group(1))
                                max_points = float(score_match.group(2))
                                # Round to 2 decimal places and convert to int if it's a whole number
                                earned_rounded = round(earned, 2)
                                if earned_rounded == int(earned_rounded):
                                    earned_rounded = int(earned_rounded)
                                total_score += earned_rounded
                                subtask_scores.append(earned_rounded)
                            else:
                                subtask_scores.append(0)
                        else:
                            subtask_scores.append(0)
                    except Exception as e:
                        print(f"Error parsing subtask in submission {submission_info['submission_id']}: {e}")
                        subtask_scores.append(0)
                
                return {
                    'submission_id': submission_info['submission_id'],
                    'submission_time': submission_info['submission_time'],
                    'problem_index': submission_info['problem_index'],
                    'problem_name': submission_info['problem_name'],
                    'problem_link': submission_info['problem_link'],
                    'total_score': total_score,
                    'subtask_scores': subtask_scores
                }
                
            except Exception as e:
                print(f"Error fetching submission {submission_info['submission_id']}: {e}")
                return None
        
        # Fetch all submission details in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(fetch_submission_details, relevant_submissions)
            for result in results:
                if result:
                    detailed_submissions.append(result)
                time.sleep(0.2)  # Rate limiting between requests
    
    print(f"Successfully fetched details for {len(detailed_submissions)} submissions")
    
    # Step 3: Calculate best scores per problem and save to database
    problem_best_scores = {}  # problem_index -> {'total_score': X, 'subtask_scores': [], 'earliest_improvement_time': str}
    
    for submission in detailed_submissions:
        problem_idx = submission['problem_index']
        
        if problem_idx not in problem_best_scores:
            problem_best_scores[problem_idx] = {
                'total_score': submission['total_score'],
                'subtask_scores': submission['subtask_scores'][:],
                'earliest_improvement_time': submission['submission_time']
            }
        else:
            # Update with maximum scores per subtask
            current_best = problem_best_scores[problem_idx]
            new_subtask_scores = []
            improved = False
            
            max_len = max(len(current_best['subtask_scores']), len(submission['subtask_scores']))
            for i in range(max_len):
                current_score = current_best['subtask_scores'][i] if i < len(current_best['subtask_scores']) else 0
                new_score = submission['subtask_scores'][i] if i < len(submission['subtask_scores']) else 0
                max_score = max(current_score, new_score)
                new_subtask_scores.append(max_score)
                
                # Check if this submission improved any subtask
                if new_score > current_score:
                    improved = True
            
            new_total_score = sum(new_subtask_scores)
            
            # If this submission improved the total score, update the earliest improvement time
            if new_total_score > current_best['total_score']:
                # Parse submission times to compare which is earlier
                current_time = datetime.fromisoformat(current_best['earliest_improvement_time'].replace('Z', '+00:00'))
                submission_time = datetime.fromisoformat(submission['submission_time'].replace('Z', '+00:00'))
                earliest_time = min(current_time, submission_time).isoformat().replace('+00:00', 'Z')
                
                problem_best_scores[problem_idx] = {
                    'total_score': new_total_score,
                    'subtask_scores': new_subtask_scores,
                    'earliest_improvement_time': earliest_time
                }
            elif improved:
                # Even if total didn't improve, if any subtask improved, consider updating time if this is earlier
                submission_time = datetime.fromisoformat(submission['submission_time'].replace('Z', '+00:00'))
                current_time = datetime.fromisoformat(current_best['earliest_improvement_time'].replace('Z', '+00:00'))
                
                if submission_time < current_time:
                    problem_best_scores[problem_idx]['earliest_improvement_time'] = submission['submission_time']
                
                # Update subtask scores even if total didn't improve
                problem_best_scores[problem_idx]['subtask_scores'] = new_subtask_scores
        
        # Save individual submission to database
        db.execute('''
            INSERT OR REPLACE INTO user_virtual_submissions 
            (user_id, contest_name, contest_stage, submission_time, problem_index, score, subtask_scores)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, contest_name, contest_stage,
            submission['submission_time'],
            submission['problem_index'],
            submission['total_score'],
            json.dumps(submission['subtask_scores'])
        ))
    
    db.commit()
    
    # Prepare return data with final scores
    submissions_summary = []
    
    # Ensure all contest problems are represented, even if not attempted
    for problem in contest_problems:
        problem_idx = problem['problem_index']
        
        if problem_idx in problem_best_scores:
            # Problem was attempted
            best_scores = problem_best_scores[problem_idx]
            submissions_summary.append({
                'problem_index': problem_idx,
                'problem_name': problem['problem_name'],
                'problem_link': problem['problem_link'],
                'score': best_scores['total_score'],
                'subtask_scores': best_scores['subtask_scores'],
                'submission_time': best_scores['earliest_improvement_time']
            })
        else:
            # Problem was not attempted - default to 0 score
            submissions_summary.append({
                'problem_index': problem_idx,
                'problem_name': problem['problem_name'],
                'problem_link': problem['problem_link'],
                'score': 0,
                'subtask_scores': [],
                'submission_time': None
            })
    
    # Sort by problem index to ensure correct order
    submissions_summary.sort(key=lambda x: x['problem_index'])
    
    print(f"Final scores calculated for {len(submissions_summary)} problems")
    
    return submissions_summary