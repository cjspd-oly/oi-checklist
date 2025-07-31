# oi-checklist

A modern, full-featured checklist for tracking progress across major Olympiads in Informatics.

<p align="center">
  <img src="https://github.com/user-attachments/assets/4dd874d2-b6c8-4188-b01b-65e1070fc668" alt="Landing Page (Dark Mode)" width="80%">
</p>

<p align="center"><i>Dark mode landing page – clean, responsive</i></p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/f2ad6ffc-0ab8-44dd-a30e-beee810cda7a" alt="Dashboard View (Logged In)" width="80%">
</p>

<p align="center"><i>Dashboard after logging in – track scores, status, and more</i></p>

---

## Supported Olympiads

OI Checklist includes problems from a wide range of Olympiads. If you’d like to see another one added, feel free to open an issue or a pull request.

### Core Olympiads

- Singapore National Olympiad in Informatics (NOI)
- Asia-Pacific Informatics Olympiad (APIO)
- Central European Olympiad in Informatics (CEOI)
- International Olympiad in Informatics (IOI)
- Indian National Olympiad in Informatics (INOI)
- Indian Zonal Computing Olympiad (ZCO)
- USA Computing Olympiad (USACO):
  - Bronze
  - Silver
  - Gold
  - Platinum
- Croatian Olympiad in Informatics (COI)
- Indian IOI Training Camp (IOITC)
- Japanese Olympiad in Informatics:
  - Spring Camp
  - Final Round
- European Girls' Olympiad in Informatics (EGOI)
- Polish Olympiad in Informatics (POI)
- Baltic Olympiad in Informatics (BOI)

### Miscellaneous

- Google Kick Start

---

## Local Development Instructions

> Requires Python 3 and Node.js installed locally.

1. Install all Python dependencies from:
   ```
   backend/requirements.txt
   ```

2. Initialize the database:
   ```bash
   python backend/init_db.py
   ```

3. Populate problems:
   ```bash
   python populate_problems.py
   ```

4. Start the Flask backend:
   ```bash
   python backend/app.py
   ```

5. Use a tool like Live Server to launch the frontend from the root directory (where `index.html` lives).

> 💡 Make sure to update the `apiUrl` in `config.js` to match your Flask server’s URL.

Once setup is complete, you can use the `checklist.sh` script to start both frontend and backend together. Modify directory paths inside it as needed.

---

## Public Deployment

You can try the live version [here](https://checklist.spoi.org.in/)!

---

## Contributing

Bug reports, feature requests, and PRs are welcome. Feel free to file an issue or submit a fix.

---

## License

This project is released under the MIT License.
