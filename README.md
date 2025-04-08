# oi-checklist
A complete checklist for OI problems.

# Is it actually complete?

Here are the olympiads the OI checklist has right now. Open an issue if you want me to add some other OI (or feel free to PR):

- Singapore National Olympiad in Informatics
- Asia-Pacific Informatics Olympiad
- Indian National Olympiad in Informatics
- Indian Zonal Computing Olympiad
- Japanese Olympiad in Informatics: Spring Camp

# Instructions

First of all, I'm surprised someone who's not me is using this, but okay I guess.

Install all requirements from `requirements.txt`.

1. Run init_db.py to initialize the SQL database.
2. Run populate_problems.py to add the OI problems to the database. You will only need to run steps 1 and 2 once.
3. To run the server, run app.py.