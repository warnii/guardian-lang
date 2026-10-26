# Guardian — Laptop Setup

## 1. Requirements
- Python 3.9 or newer  (check:  `python --version`)
- Nothing else. No pip packages.

## 2. Install

**Windows**
1. Unzip `guardian-v1.1.zip`
2. Double-click `install.bat`  (or run it in a terminal)
3. Close the terminal, open a NEW one

**Linux / macOS**
```
unzip guardian-v1.1.zip && cd guardian
sh install.sh
```
Then open a new terminal.

## 3. Check it works
```
guardian version
guardian run   ~/guardian/demo.grd
guardian check ~/guardian/examples/unsafe.grd     # should refuse with G101/G103/G401
python ~/guardian/run_tests.py                    # expect 150/150
```
(Windows: use `%USERPROFILE%\guardian\...` in place of `~/guardian/...`.)

## 4. Daily use
```
guardian new myapp          # scaffold a project
cd myapp
guardian run main.grd
guardian check main.grd     # security scan only
guardian repl               # interactive shell
```
Name your files `*.grd`. Open the folder in VS Code; set the language mode to
Python or Plain Text for now (a .grd highlighter is not built yet).

## 5. Put it on GitHub (portfolio)
```
cd ~/guardian
git init
git add .
git commit -m "Guardian language v1.1"
git branch -M main
git remote add origin https://github.com/<you>/guardian-lang.git
git push -u origin main
```

## Troubleshooting
- `guardian` not found → you didn't open a NEW terminal after installing.
- Windows "python not found" → reinstall Python, tick **Add python.exe to PATH**.
- Without installing, always works:  `python guardian.py run demo.grd`
