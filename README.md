# oi-checklist

A modern, full-featured checklist for tracking progress across major Olympiads in Informatics.

<p align="center">
  <img src="https://github.com/user-attachments/assets/f2ad6ffc-0ab8-44dd-a30e-beee810cda7a" alt="Dashboard view (logged in, dark mode)" width="80%">
</p>

<p align="center"><i>Dashboard after logging in – track scores, status, and more</i></p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/4dd874d2-b6c8-4188-b01b-65e1070fc668" alt="Landing page (dark mode)" width="80%">
</p>

<p align="center"><i>Dark mode landing page – clean, responsive</i></p>

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

### 0. Create a `.env` file

In the `backend/` directory, create a `.env` file with the following values:

| Variable              | Description |
|-----------------------|-------------|
| `FLASK_ENV`           | Set to `local` for local development |
| `DATABASE_PATH`       | Path to your SQLite database (e.g., `database.db`) |
| `BACKEND_DIR`         | Absolute path to the `backend/` folder |
| `FRONTEND_URL`        | URL where the frontend runs (e.g., `http://localhost:5501`) |
| `BACKEND_URL`         | URL where the Flask backend runs (e.g., `http://localhost:5001`) |
| `GITHUB_CLIENT_ID`    | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET`| GitHub OAuth client secret |

> ⚠️ Mostly just don't mess with the GitHub login stuff unless you know what you're doing — it's primarily meant for production and you'd end up creating a duplicate OAuth app on GitHub that doesn’t really do anything.  
>  
> But *if* you really want to test GitHub login locally:
> - Go to [https://github.com/settings/developers](https://github.com/settings/developers)  
> - Register a new OAuth App with the following:
>   - **Authorization callback URL**: `your_backend_url_here/auth/github/callback`
>   - **Homepage URL**: `your_frontend_url_here`
> - Copy the **Client ID** and **Client Secret** into your `.env` file as `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`.

---

### 1. Install Python dependencies

```bash
pip install -r backend/requirements.txt
````

### 2. Initialize the database

```bash
python3 backend/init_db.py
```

### 3. Populate Olympiad problems

```bash
python3 backend/populate_problems.py
```

### 4. Start the Flask backend

```bash
python3 backend/app.py
```

### 5. Launch the frontend

Use Live Server (or a simple HTTP server) from the root directory (where `index.html` is located).

> 💡 Make sure to update the `apiUrl` in `frontend/js/config.js` to match your Flask server’s URL if it differs.

---

Once everything is working, you can use the `checklist.sh` script to start both the frontend and backend together. Modify the paths in it as needed.

---

## Public Deployment

You can try the live version [here](https://checklist.spoi.org.in/)!

---

## Contributing

Bug reports, feature requests, and PRs are welcome. Feel free to file an issue or submit a fix.

---

## License

This project is released under the MIT License.
