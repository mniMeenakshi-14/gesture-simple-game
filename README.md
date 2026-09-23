# Slice Ninja (Python / OpenCV / MediaPipe / Pygame)

A desktop gesture-controlled shape-slicing game — slice circles, squares,
triangles, stars, pentagons and hexagons with your index finger, dodge the
bombs. Runs on your webcam using OpenCV + MediaPipe for hand tracking,
rendered with Pygame.

## 1. Set up and run

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
python game.py
```

Press **S** to start, **Q** or **Esc** to quit. Make sure no other app
(Zoom, Teams, another browser tab) is already using your webcam.

## 2. How to share this with your friends

This is a **desktop Python app** — it opens its own window and needs a
webcam attached to whatever machine runs it, so a link alone won't work
the way a website does. Here are your real options, easiest first:

### Option A — Send the folder, they run it with Python (simplest)
1. Zip the folder (`game.py` + `requirements.txt` + this `README.md`) or push it to GitHub.
2. Your friend needs Python 3.9–3.11 installed, then:
   ```bash
   pip install -r requirements.txt
   python game.py
   ```
   Works on Windows, Mac, and Linux, as long as they have a webcam.

### Option B — Package it as a standalone .exe (Windows friends, no Python needed)
```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name SliceNinja game.py
```
This creates `dist/SliceNinja/` — zip that whole folder and send it. Your
friend just double-clicks `SliceNinja.exe` inside it, no Python install
required. Use `--onedir` (not `--onefile`) — MediaPipe's model files bundle
more reliably that way. Note this only makes a Windows build if you run
PyInstaller on Windows (build on Mac for a Mac app, etc. — it doesn't
cross-compile).

### Option C — Rebuild the browser version instead (best for sharing widely)
If most of your friends are on phones or you want them to just tap a link
with nothing to install, the browser/HTML version I built earlier
(hosted via GitHub Pages) is the better fit — anyone opens the link in
Chrome/Safari, allows the camera, and plays immediately on PC or mobile.
Happy to hand that back over if you want to go that route for sharing,
and keep this Python version for local play / recording your screen for
LinkedIn.

## 3. Recording it for LinkedIn

Use OBS Studio or your OS's built-in recorder (Win+Alt+R on Windows,
Cmd+Shift+5 on Mac) while `game.py` is running, same as any other app.