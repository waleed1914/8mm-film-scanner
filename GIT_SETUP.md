# CARRERO-8 Git Setup

This project is ready to use with Git.

## 1. Install Git on your Windows PC

Use one of these:

- Download Git for Windows: https://git-scm.com/download/win
- Or install with `winget`:

```powershell
winget install --id Git.Git -e --source winget
```

After install, close and reopen VS Code or PowerShell.

Check:

```powershell
git --version
```

## 2. Create the local repo

Open PowerShell in this project folder:

```powershell
cd C:\Users\pc\Desktop\flim_digital
git init
git add .
git commit -m "Initial CARRERO-8 project"
```

## 3. Push to GitHub

Create an empty GitHub repo first, then run:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR-USER/YOUR-REPO.git
git push -u origin main
```

If GitHub asks for login, use your browser or a personal access token.

## 4. Raspberry Pi first-time setup

On the Raspberry Pi:

```bash
sudo apt update
sudo apt install -y git python3-pip ffmpeg
git clone https://github.com/YOUR-USER/YOUR-REPO.git
cd YOUR-REPO
pip3 install -r requirements.txt
python3 main.py
```

## 5. Update code on Raspberry Pi later

When you change code on Windows:

```powershell
cd C:\Users\pc\Desktop\flim_digital
git add .
git commit -m "Describe the change"
git push
```

Then on Raspberry Pi:

```bash
cd YOUR-REPO
git pull
pip3 install -r requirements.txt
python3 main.py
```

## 6. Quick recovery if the Pi has local changes

If you changed files directly on the Pi and `git pull` fails:

```bash
cd YOUR-REPO
git status
```

Either commit the Pi changes or discard only if you really want to remove them:

```bash
git add .
git commit -m "Pi local changes"
git pull --rebase
```

## 7. Best workflow for your project

- Do code changes on Windows.
- Push to GitHub.
- On Raspberry Pi, only do `git pull`.
- Avoid editing the same files on both machines.

That will keep updates simple once the 3.5 inch LCD is active.
