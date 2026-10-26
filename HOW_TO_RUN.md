# How to Run This App (Docker)

This is the simplest way to run the whole app — no Python, no Node.js,
nothing to install except Docker itself.

## 1. Install Docker Desktop

Download and install it from https://www.docker.com/products/docker-desktop/
(Windows, Mac, or Linux). Open it once after installing so it's running in
the background.

## 2. Get your API keys

Before running the app you need a handful of free API keys (for AI chat,
voice, etc.). See **GETTING_API_KEYS.md** for exact step-by-step
instructions on where to get each one.

## 3. Set up your `.env` file

Inside the `backend` folder, copy `.env.example` to a new file named `.env`:

```bash
cd backend
copy .env.example .env      # Windows
cp .env.example .env        # Mac/Linux
```

Open `backend/.env` in any text editor and paste in the keys you got in
step 2. Save the file.

## 4. Start everything

From the project's root folder (the one with `docker-compose.yml` in it),
run:

```bash
docker compose up --build
```

The first run takes a few minutes (it's downloading and building
everything). After that, starting it again is much faster.

Leave this terminal window open — it's running the app. To stop everything,
press `Ctrl+C`, or close the terminal.

## 5. Open the app

Once it says everything has started, open your browser to:

**http://localhost:5173**

You'll land on a sign-in screen. The very first account you create needs to
be approved before it can log in — see the admin login below.

## 6. Logging in as admin

The app creates one admin account automatically, using the email and
password you set in `backend/.env` under `ADMIN_EMAIL` and
`ADMIN_PASSWORD`. Log in with those to approve new users and manage the
app from `/admin`.

## Everyday use after the first run

You don't need to repeat steps 1–3 again. Just run, from the project
folder:

```bash
docker compose up
```

(No `--build` needed unless the code itself has changed.)

To stop everything cleanly:

```bash
docker compose down
```

## If something goes wrong

- **A port is already in use** — something else on your computer is using
  port 5173, 8001, 5432, 9000, or 9001. Close whatever that is, or edit
  the port numbers on the left side of the `"host:container"` pairs in
  `docker-compose.yml`.
- **"docker compose" command not found** — make sure Docker Desktop is
  open and running first.
- **Blank page / can't reach the app** — give it 30–60 seconds after
  startup for the backend and database to finish initializing, then
  refresh.
