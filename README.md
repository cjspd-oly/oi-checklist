# oi-checklist
A complete checklist for OI problems.

# Is it actually complete?

Here are the olympiads the OI checklist has right now. Open an issue if you want me to add some other OI (or feel free to PR):

## Olympiads

- Singapore National Olympiad in Informatics
- Asia-Pacific Informatics Olympiad
- Central European Olympiad in Informatics
- International Olympiad in Informatics
- Indian National Olympiad in Informatics
- Indian Zonal Computing Olympiad
- USA Computing Olympiad:
  - Bronze
  - Silver
  - Gold
  - Platinum
- Croatian Olympiad in Informatics
- Indian International Olympiad in Informatics: Training Camp
- Japanese Olympiad in Informatics: Spring Camp
- Japanese Olympiad in Informatics: Final Round
- European Girls' Olympiad in Informatics
- Polish Olympiad in Informatics
- Baltic Olympiad in Informatics

## Miscellaneous Competitions

- Google Kick Start

# Local Running Instructions

Install all requirements from `backend/requirements.txt`.

1. Run init_db.py (in the backend directory) to initialize the SQL database.
2. Run populate_problems.py to add the OI problems to the database. You will only need to run steps 1 and 2 once.
3. To run the back-end server, run app.py. 
4. Then use something like live server to run the front-end. You'll need to run it in root directory of this repo (so the directory with index.html).

**Note**: You'll also need to change the `apiUrl` variable in the `config.js` file to whatever URL the flask server ends up running on.

Once you've done all of this once, you can use `checklist.sh` to run the front-end and back-end servers automatically and seamlessly. You'll obviously have to modify the relative directories here too.

# Public

Visit [this website](https://checklist.spoi.org.in/) to use the OI checklist!
