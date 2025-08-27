import pytz
import json
from flask import request, jsonify
from datetime import timedelta, datetime
from database.db import get_db
from scrape.ojuz import sync_ojuz_submissions
from scrape.qoj import sync_qoj_submissions
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_virtual_contests():
    user_id = request.user_id
    db = get_db()
    
    # Check if user has an active virtual contest
    active_contest = db.execute('''
        SELECT 
            avc.contest_name,
            avc.contest_stage,
            avc.start_time,
            avc.end_time,
            avc.autosynced,
            c.duration_minutes,
            c.location,
            c.website,
            c.link
        FROM active_virtual_contests avc
        JOIN contests c ON avc.contest_name = c.name AND (avc.contest_stage = c.stage OR (avc.contest_stage IS NULL AND c.stage IS NULL))
        WHERE avc.user_id = ?
    ''', (user_id,)).fetchone()
    
    # Get all contests with their problems
    contests = db.execute('''
        SELECT 
            name, stage, source, year, duration_minutes,
            COALESCE(location, '') as location,
            COALESCE(website, '') as website,
            COALESCE(link, '') as link,
            COALESCE(date, '') as date,
            COALESCE(notes, '') as notes
        FROM contests 
        ORDER BY year DESC, source, stage
    ''').fetchall()
    
    # Get contest problems for all contests
    contest_problems = db.execute('''
        SELECT 
            cp.contest_name,
            cp.contest_stage,
            cp.problem_source,
            cp.problem_year,
            cp.problem_number,
            cp.problem_extra,
            cp.problem_index
        FROM contest_problems cp
        ORDER BY cp.contest_name, cp.contest_stage, cp.problem_index
    ''').fetchall()
    
    # Get last 3 virtual contests for this user
    recent_virtuals = db.execute('''
        SELECT 
            v.contest_name, v.contest_stage,
            c.source as contest_source, c.year as contest_year,
            v.started_at,
            v.score as total_score,
            v.per_problem_scores,
            CASE 
                WHEN c.link LIKE '%oj.uz%' THEN 'oj.uz'
                ELSE 'manual'
            END as platform
        FROM user_virtual_contests v
        JOIN contests c ON v.contest_name = c.name AND (v.contest_stage = c.stage OR (v.contest_stage IS NULL AND c.stage IS NULL))
        WHERE v.user_id = ?
        ORDER BY v.started_at DESC
        LIMIT 3
    ''', (user_id,)).fetchall()

    # Get all completed contests for this user
    completed_contests = db.execute('''
        SELECT DISTINCT contest_name || '|' || COALESCE(contest_stage, '') as contest_key
        FROM user_virtual_contests
        WHERE user_id = ?
    ''', (user_id,)).fetchall()

    # Convert to dictionary format
    contests_dict = {}
    for c in contests:
        source = c['source']
        year = c['year']
        if source not in contests_dict:
            contests_dict[source] = {}
        if year not in contests_dict[source]:
            contests_dict[source][year] = []
        
        contest_dict = dict(c)
        # Add problems for this contest
        contest_dict['problems'] = []
        for cp in contest_problems:
            if cp['contest_name'] == c['name'] and (cp['contest_stage'] == c['stage'] or (cp['contest_stage'] is None and c['stage'] is None)):
                p = {
                    'source': cp['problem_source'],
                    'year': cp['problem_year'],
                    'number': cp['problem_number'],
                    'index': cp['problem_index']
                }
                if cp['problem_extra'] is not None and cp['problem_extra'] != '':
                    p['extra'] = cp['problem_extra']
                contest_dict['problems'].append(p)
        
        contests_dict[source][year].append(contest_dict)

    recent_list = [dict(v) for v in recent_virtuals]
    completed_list = [row['contest_key'] for row in completed_contests]

    result = {
        'contests': contests_dict,
        'recent': recent_list,
        'completed_contests': completed_list
    }
    
    # Add active contest info if exists
    if active_contest:
        result['active_contest'] = dict(active_contest)
    
    return jsonify(result)

def get_virtual_contest_history():
    user_id = request.user_id
    db = get_db()
    
    # Get all virtual contests for this user
    contests = db.execute('''
        SELECT 
            v.contest_name,
            v.contest_stage,
            c.source as contest_source,
            c.year as contest_year,
            v.started_at,
            v.ended_at,
            v.score as total_score,
            v.per_problem_scores,
            CASE 
                WHEN c.link LIKE '%oj.uz%' THEN 'oj.uz'
                ELSE 'manual'
            END as platform
        FROM user_virtual_contests v
        JOIN contests c ON v.contest_name = c.name AND (v.contest_stage = c.stage OR (v.contest_stage IS NULL AND c.stage IS NULL))
        WHERE v.user_id = ?
        ORDER BY v.started_at DESC
    ''', (user_id,)).fetchall()
    
    # Convert to list of dictionaries
    contests_list = [dict(contest) for contest in contests]
    
    return jsonify({
        'contests': contests_list
    })

def start_virtual_contest():
    user_id = request.user_id
    data = request.get_json()
    autosynced_flag = 1 if bool(data.get('autosynced')) else 0
    
    contest_name = data.get('contest_name')
    contest_stage = data.get('contest_stage')  # This can be None/null now
    
    if not contest_name:
        return jsonify({'error': 'Missing contest_name'}), 400
    
    db = get_db()
    
    # Check if user already has an active contest
    existing = db.execute(
        'SELECT 1 FROM active_virtual_contests WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if existing:
        return jsonify({'error': 'User already has an active contest'}), 400
    
    # Check if user has already completed this contest
    # Handle both NULL and non-NULL contest_stage cases
    if contest_stage is not None:
        completed = db.execute(
            'SELECT 1 FROM user_virtual_contests WHERE user_id = ? AND contest_name = ? AND contest_stage = ?',
            (user_id, contest_name, contest_stage)
        ).fetchone()
    else:
        completed = db.execute(
            'SELECT 1 FROM user_virtual_contests WHERE user_id = ? AND contest_name = ? AND contest_stage IS NULL',
            (user_id, contest_name)
        ).fetchone()
    
    if completed:
        return jsonify({'error': 'Contest already completed'}), 400
    
    # Verify contest exists
    # Handle both NULL and non-NULL contest_stage cases
    if contest_stage is not None:
        contest_exists = db.execute(
            'SELECT 1 FROM contests WHERE name = ? AND stage = ?',
            (contest_name, contest_stage)
        ).fetchone()
    else:
        contest_exists = db.execute(
            'SELECT 1 FROM contests WHERE name = ? AND stage IS NULL',
            (contest_name,)
        ).fetchone()
    
    if not contest_exists:
        return jsonify({'error': 'Contest not found'}), 404
    
    # Start the virtual contest with UTC timestamp
    utc_now = datetime.now(pytz.UTC).isoformat()
    db.execute('''
        INSERT INTO active_virtual_contests 
        (user_id, contest_name, contest_stage, start_time, autosynced)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, contest_name, contest_stage, utc_now, autosynced_flag))
    
    db.commit()
    return jsonify({'success': True})

def end_virtual_contest():
    user_id = request.user_id
    data = request.get_json(silent=True) or {}
    
    # Determine oj.uz username from database settings instead of request
    ojuz_username = None
    try:
        db_for_username = get_db()
        row = db_for_username.execute(
            "SELECT platform_usernames FROM user_settings WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row and row['platform_usernames']:
            try:
                usernames = json.loads(row['platform_usernames'])
                if isinstance(usernames, dict):
                    ojuz_username = usernames.get('oj.uz') or usernames.get('ojuz') or None
            except Exception:
                pass
    except Exception:
        # If any issue occurs, fall back to no username (no sync)
        ojuz_username = None
    
    db = get_db()
    
    # Get the active contest with duration info
    active_contest = db.execute('''
        SELECT 
            avc.contest_name, 
            avc.contest_stage, 
            avc.start_time,
            avc.autosynced,
            c.duration_minutes
        FROM active_virtual_contests avc
        JOIN contests c ON avc.contest_name = c.name AND (avc.contest_stage = c.stage OR (avc.contest_stage IS NULL AND c.stage IS NULL))
        WHERE avc.user_id = ?
    ''', (user_id,)).fetchone()

    if active_contest:
        active_contest = dict(active_contest)
    
    if not active_contest:
        return jsonify({'error': 'No active contest found'}), 404
    
    # Calculate the end time, capped at contest duration
    start_time = datetime.fromisoformat(active_contest['start_time'].replace('Z', '+00:00'))
    duration_minutes = active_contest['duration_minutes']
    utc_now = datetime.now(pytz.UTC)
    
    # Calculate maximum allowed end time based on contest duration
    max_end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Cap the end time at the maximum allowed time
    capped_end_time = min(utc_now, max_end_time)
    capped_end_time_iso = capped_end_time.isoformat()
    
    # Update the active contest with capped end_time
    db.execute('''
        UPDATE active_virtual_contests 
        SET end_time = ?
        WHERE user_id = ?
    ''', (capped_end_time_iso, user_id))
    db.commit()
    
    # Create updated active_contest object with capped end_time for sync function
    active_contest_with_end = {
        'user_id': user_id,
        'contest_name': active_contest['contest_name'],
        'contest_stage': active_contest['contest_stage'],
        'start_time': active_contest['start_time'],
        'end_time': capped_end_time_iso
    }
    
    # Handle autosync across multiple platforms (oj.uz, qoj.ac) if autosynced is true
    submissions = []
    final_scores = []

    if active_contest.get('autosynced', False):
        # Resolve usernames from user_settings
        platform_usernames = {}
        try:
            db_for_username = get_db()
            row = db_for_username.execute(
                "SELECT platform_usernames FROM user_settings WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            if row and row['platform_usernames']:
                try:
                    platform_usernames = json.loads(row['platform_usernames'])
                    if not isinstance(platform_usernames, dict):
                        platform_usernames = {}
                except Exception:
                    platform_usernames = {}
        except Exception:
            platform_usernames = {}

        # Map of supported platforms to their sync functions
        sync_funcs = {
            'oj.uz': (sync_ojuz_submissions, platform_usernames.get('oj.uz')),
            'qoj.ac': (sync_qoj_submissions, platform_usernames.get('qoj.ac')),
        }

        # Kick off parallel syncs for platforms that have a username configured
        futures = []
        with ThreadPoolExecutor(max_workers=len(sync_funcs)) as executor:
            for plat, (fn, uname) in sync_funcs.items():
                if uname:
                    futures.append(executor.submit(fn, active_contest_with_end, uname))

            # Collect results as they complete
            for fut in as_completed(futures):
                try:
                    res = fut.result() or []
                    if isinstance(res, list):
                        submissions.extend(res)
                except Exception as e:
                    print(f"Error syncing submissions: {e}")

        # Compute per-problem final scores by maxing **per-subtask** across all platforms
        try:
            # Get declared problems for this contest to shape the score array deterministically
            contest_problems = db.execute('''
                SELECT cp.problem_index
                FROM contest_problems cp
                WHERE cp.contest_name = ? AND (cp.contest_stage = ? OR (cp.contest_stage IS NULL AND ? IS NULL))
                ORDER BY cp.problem_index
            ''', (active_contest['contest_name'], active_contest['contest_stage'], active_contest['contest_stage'])).fetchall()
            indices = [row['problem_index'] for row in contest_problems]
        except Exception:
            indices = []

        if submissions and indices:
            # For each problem index, keep the **element-wise max** of subtask scores
            # If a submission has no subtask breakdown, treat it as a single subtask with the total score
            from math import isfinite

            def _normalize_scores(x):
                # Return a list of floats for subtask scores
                if isinstance(x, (list, tuple)):
                    out = []
                    for v in x:
                        try:
                            fv = float(v)
                        except Exception:
                            fv = 0.0
                        out.append(fv if isfinite(fv) else 0.0)
                    return out
                # Fallback: single total score as one subtask
                try:
                    s = float(x)
                except Exception:
                    s = 0.0
                return [s if isfinite(s) else 0.0]

            best_subtasks = {idx: [] for idx in indices}

            for sub in submissions:
                try:
                    idx = int(sub.get('problem_index'))
                except Exception:
                    continue
                if idx not in best_subtasks:
                    # Ignore submissions for indices not declared in this contest
                    continue

                # Prefer explicit subtask_scores; fallback to the total score
                sts = sub.get('subtask_scores')
                if sts is None:
                    sts = sub.get('score', 0)
                cur = _normalize_scores(sts)

                # Element-wise max into accumulator (pad with zeros as needed)
                acc = best_subtasks[idx]
                if len(cur) > len(acc):
                    acc.extend([0.0] * (len(cur) - len(acc)))
                for i in range(len(cur)):
                    acc[i] = max(acc[i] if i < len(acc) else 0.0, cur[i])
                best_subtasks[idx] = acc

            # Final scores are the sum of best subtasks per problem, ordered by official indices
            final_scores = [float(sum(best_subtasks[idx])) for idx in indices]
            total_score = float(sum(final_scores))

            # Persist aggregated scores on the active contest
            db.execute('''
                UPDATE active_virtual_contests 
                SET score = ?, per_problem_scores = ?
                WHERE user_id = ?
            ''', (total_score, json.dumps(final_scores), user_id))
            db.commit()

    response_data = {'success': True}
    if active_contest.get('autosynced', False) and submissions:
        response_data['submissions'] = submissions
        response_data['final_scores'] = final_scores

    return jsonify(response_data)

def confirm_virtual_contest():
    """
    Confirm and finalize an oj.uz synced virtual contest.
    This moves the contest from active_virtual_contests to user_virtual_contests
    and updates the user's problem scores in the database.
    """
    user_id = request.user_id
    db = get_db()
    
    # Get the ended active contest with oj.uz sync
    active_contest = db.execute('''
        SELECT contest_name, contest_stage, start_time, end_time, score, per_problem_scores, autosynced
        FROM active_virtual_contests 
        WHERE user_id = ? AND end_time IS NOT NULL AND autosynced = 1
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No oj.uz synced contest found to confirm'}), 404
    
    contest_name = active_contest['contest_name']
    contest_stage = active_contest['contest_stage']
    start_time = active_contest['start_time']
    end_time = active_contest['end_time']
    total_score = active_contest['score']
    per_problem_scores = active_contest['per_problem_scores']
    
    # Get contest problems to update user's problem scores
    contest_problems = db.execute('''
        SELECT 
            cp.problem_index,
            p.name as problem_name,
            p.source,
            p.year
        FROM contest_problems cp
        JOIN problems p ON cp.problem_source = p.source 
                        AND cp.problem_year = p.year 
                        AND cp.problem_number = p.number
        WHERE cp.contest_name = ? AND (cp.contest_stage = ? OR (cp.contest_stage IS NULL AND ? IS NULL))
        ORDER BY cp.problem_index
    ''', (contest_name, contest_stage, contest_stage)).fetchall()
    
    # Parse the per-problem scores from JSON
    try:
        scores_list = json.loads(per_problem_scores) if per_problem_scores else []
    except:
        scores_list = []
    
    # Update user's problem scores in the database
    for i, problem in enumerate(contest_problems):
        if i < len(scores_list):
            score = scores_list[i]
            
            # Determine status based on score
            if score == 100:
                status = 2  # solved
            elif score > 0:
                status = 1  # partial
            else:
                status = 0  # failed
            
            # Update or insert the problem status and score
            db.execute('''
                INSERT INTO problem_statuses (user_id, problem_name, source, year, status, score)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, problem_name, source, year)
                DO UPDATE SET 
                    status = CASE WHEN excluded.score > problem_statuses.score THEN excluded.status ELSE problem_statuses.status END,
                    score = MAX(excluded.score, problem_statuses.score)
            ''', (user_id, problem['problem_name'], problem['source'], problem['year'], status, score))
    
    # Move the contest to completed virtual contests
    db.execute('''
        INSERT OR REPLACE INTO user_virtual_contests 
        (user_id, contest_name, contest_stage, started_at, ended_at, score, per_problem_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, contest_name, contest_stage, start_time, end_time, total_score, per_problem_scores))
    
    # Remove from active contests
    db.execute('DELETE FROM active_virtual_contests WHERE user_id = ?', (user_id,))
    
    db.commit()
    return jsonify({'success': True})

def submit_virtual_contest():
    user_id = request.user_id
    data = request.get_json()
    
    # Get scores data
    scores = data.get('scores', [])
    total_score = data.get('total_score', 0)
    
    if not scores:
        return jsonify({'error': 'No scores provided'}), 400
    
    db = get_db()
    
    # Get the ended active contest
    active_contest = db.execute('''
        SELECT contest_name, contest_stage, start_time, end_time, autosynced
        FROM active_virtual_contests 
        WHERE user_id = ? AND end_time IS NOT NULL
    ''', (user_id,)).fetchone()
    
    if not active_contest:
        return jsonify({'error': 'No ended contest found'}), 404
    
    # Security check: Prevent manual score submission for synced contests
    if active_contest['autosynced']:
        return jsonify({'error': 'Cannot manually modify scores for autosynced contests!'}), 403
    
    contest_name = active_contest['contest_name']
    contest_stage = active_contest['contest_stage']
    start_time = active_contest['start_time']
    end_time = active_contest['end_time']
    
    # Save the virtual contest result to main table
    db.execute('''
        INSERT OR REPLACE INTO user_virtual_contests 
        (user_id, contest_name, contest_stage, started_at, ended_at, score, per_problem_scores)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, contest_name, contest_stage, start_time, end_time, total_score, json.dumps(scores)))
    
    # Remove from active contests
    db.execute('DELETE FROM active_virtual_contests WHERE user_id = ?', (user_id,))
    
    db.commit()
    return jsonify({'success': True})

def get_contest_scores():
    contest_names = request.args.get('contests')
    if not contest_names:
        return jsonify({"error": "Missing 'contests' query parameter"}), 400

    contest_list = []
    for contest in contest_names.split(','):
        if '|' in contest:
            name, stage = contest.strip().split('|', 1)
            # Handle empty stage (convert to None for NULL matching)
            stage = stage.strip() if stage.strip() else None
            contest_list.append((name.strip(), stage))
        else:
            # No stage separator, assume no stage (NULL)
            contest_list.append((contest.strip(), None))

    if not contest_list:
        return jsonify({"error": "No valid contests provided"}), 400

    db = get_db()
    
    # Build dynamic query to handle NULL stages properly
    where_conditions = []
    params = []
    
    for name, stage in contest_list:
        if stage is None:
            where_conditions.append("(contest_name = ? AND contest_stage IS NULL)")
            params.append(name)
        else:
            where_conditions.append("(contest_name = ? AND contest_stage = ?)")
            params.extend([name, stage])
    
    where_clause = " OR ".join(where_conditions)
    
    contest_scores = db.execute(f'''
        SELECT contest_name, contest_stage, medal_names, medal_cutoffs, problem_scores
        FROM contest_scores 
        WHERE {where_clause}
    ''', params).fetchall()
    
    # Convert to dictionary format
    scores_dict = {}
    for row in contest_scores:
        key = f"{row['contest_name']}|{row['contest_stage'] or ''}"
        scores_dict[key] = {
            'medal_names': json.loads(row['medal_names']) if row['medal_names'] else [],
            'medal_cutoffs': json.loads(row['medal_cutoffs']) if row['medal_cutoffs'] else [],
            'problem_scores': json.loads(row['problem_scores']) if row['problem_scores'] else []
        }
    
    return jsonify(scores_dict)

def get_virtual_contest_detail(slug):
    user_id = request.user_id
    db = get_db()

    # Get all virtual contests for this user to find matching slug
    contests = db.execute('''
        SELECT 
            v.contest_name,
            v.contest_stage,
            c.source AS contest_source,
            c.year AS contest_year,
            c.location,
            c.website,
            v.started_at,
            v.ended_at,
            v.score AS total_score,
            v.per_problem_scores,
            CASE 
                WHEN c.link LIKE '%oj.uz%' THEN 'oj.uz'
                ELSE 'manual'
            END AS platform
        FROM user_virtual_contests v
        JOIN contests c 
          ON v.contest_name = c.name 
         AND (v.contest_stage = c.stage OR (v.contest_stage IS NULL AND c.stage IS NULL))
        WHERE v.user_id = ?
    ''', (user_id,)).fetchall()

    for contest in contests:
        contest_slug = (contest['contest_name'] + (contest['contest_stage'] or '')).lower().replace(' ', '')
        if contest_slug == slug:
            result = dict(contest)

            # Fetch only the relevant submission fields
            submissions = db.execute('''
                SELECT 
                    submission_time,
                    problem_index,
                    score,
                    subtask_scores
                FROM user_virtual_submissions
                WHERE user_id = ?
                  AND contest_name = ?
                  AND (
                        (contest_stage = ?)
                        OR (contest_stage IS NULL AND ? IS NULL)
                      )
                  AND submission_time >= ?
                  AND submission_time <= ?
                ORDER BY submission_time ASC
            ''', (
                user_id,
                contest['contest_name'],
                contest['contest_stage'], contest['contest_stage'],
                contest['started_at'],
                contest['ended_at'],
            )).fetchall()

            out_subs = []
            for row in submissions:
                d = dict(row)
                try:
                    import json
                    d['subtask_scores'] = json.loads(d.get('subtask_scores') or 'null')
                except Exception:
                    pass
                out_subs.append(d)

            result['submissions'] = out_subs
            return jsonify(result)

    return jsonify({'error': 'Contest not found'}), 404