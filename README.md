# dual-cam-osc-tracker

A dual-camera body tracking system for VRChat using MediaPipe pose estimation and OSC. Uses a **front camera** and a **side camera** together to get accurate 3D depth positioning — no depth sensor required.

---

## How It Works

Single cameras can't accurately estimate depth (Z axis). This tracker solves that:

| Camera | What it contributes |
|--------|---------------------|
| **Front** | X (left/right), Y (up/down) |
| **Side** | Z (depth/distance from front cam) |

The side camera's horizontal axis directly maps to real-world depth. By combining both, the tracker produces accurate 3D positions for all body joints.

---

## Requirements

- Python 3.10+
- A webcam (USB, device index)
- A phone running an IP camera app on the same Wi-Fi network
  - Android: [IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam)
  - iOS: [EpocCam](https://apps.apple.com/app/epoccam/id435355256) or similar
- VRChat with OSC enabled (`Settings → OSC → Enable`)

### Install dependencies (Arch Linux)

```bash
# System deps
sudo pacman -S python python-pip opencv tk

# Python deps
pip install -r requirements.txt --break-system-packages
```

---

## Setup

### 1. Configure cameras

Edit `config/user_config.json`:

```json
"cameras": {
  "front": {
    "source": 0,          // USB webcam device index
    "role": "front"
  },
  "side": {
    "source": "http://192.168.1.X:8080/video",  // Phone camera URL
    "role": "side",
    "side": "left"        // "left" or "right" — which side of you the camera is on
  }
}
```

> **Finding your phone's IP:** In IP Webcam app, start server and note the URL it shows (e.g. `http://192.168.1.42:8080`). Use `/video` as the path.

> **Finding USB webcam index:** If index 0 doesn't work, try 1, 2, etc.

### 2. Set your real-world measurements

```json
"calibration": {
  "camera_distance_meters": 2.0,    // Distance between front and side camera (meters)
  "user_height_meters": 1.75        // Your real height in meters
}
```

These values scale the depth estimation. Measure them as accurately as possible for best results.

### 3. Enable/disable individual trackers

```json
"trackers": {
  "hips": true,
  "left_foot": true,
  "right_foot": true,
  "left_knee": true,
  "right_knee": true,   // Set to false to disable right knee tracker
  "left_elbow": true,
  "right_elbow": true,
  "left_wrist": true,
  "right_wrist": true,
  "left_shoulder": true,
  "right_shoulder": true,
  "chest": true,
  "head": false         // Off by default — headset provides head tracking
}
```

Set any tracker to `false` to completely disable it (no OSC messages sent for it).

### 4. Tune smoothing

```json
"smoothing": {
  "enabled": true,
  "factor": 0.5    // 0.0 = raw/jittery, 1.0 = very smooth but laggy
}
```

Start at `0.5`. If tracking feels laggy, lower it. If it's too jittery, raise it.

---

## Running

### Normal mode
```bash
python main.py
```

### With custom config path
```bash
python main.py --config /path/to/my_config.json
```

### Without camera preview windows (better performance)
```bash
python main.py --no-display
```

### Calibration helper
```bash
python main.py --calibrate
```
Stand in T-pose in front of both cameras and press SPACE. Helps verify detection is working.

Press **Q** in any camera window (or Ctrl+C in terminal) to stop.

---

## Camera Placement Guide

```
         [FRONT CAMERA]
               |
               |  ~2m
               |
          [YOU HERE]  ←——— [SIDE CAMERA] (left or right, ~1-2m away)
```

- Both cameras should see your **full body** (head to feet)
- Side camera should be roughly **perpendicular** to the front camera (90 degrees)
- Try to have both cameras at roughly **hip height** or slightly below
- Avoid backlighting — make sure you're well-lit from the front

---

## VRChat OSC Setup

1. In VRChat, go to **Settings → OSC**
2. Enable OSC
3. Make sure port matches config (default: `9000`)
4. In-game, go to **Action Menu → Calibrate FBT** and follow the T-pose calibration

### Tracker index assignments (VRChat)

| Index | Tracker |
|-------|---------|
| 1 | Hips |
| 2 | Left Foot |
| 3 | Right Foot |
| 4 | Left Knee |
| 5 | Right Knee |
| 6 | Chest |
| 7 | Left Elbow |
| 8 | Right Elbow |
| 9 | Left Wrist |
| 10 | Right Wrist |
| 11 | Left Shoulder |
| 12 | Right Shoulder |

---

## Config File Reference

The config file at `config/user_config.json` is the single source of truth. You can edit it while the tracker is stopped to adjust any setting. A `.json.bak` backup is created every time the config is saved programmatically.

All fields with a `"notes"` key are documentation — they are safely ignored by the program.

---

## Troubleshooting

**Tracking is way off / floaty**
- Check `camera_distance_meters` — this is the most impactful calibration value
- Make sure `side` is set to `"left"` or `"right"` correctly

**One camera not detected**
- For USB: try incrementing the device index (0 → 1 → 2)
- For phone: make sure phone and PC are on the same Wi-Fi network, and the IP Webcam app server is running

**Pose not detected**
- Ensure your full body is visible in both cameras
- Improve lighting — MediaPipe struggles in dark or backlit conditions

**High latency / lag**
- Lower `smoothing.factor` (e.g. 0.3)
- Run with `--no-display` to skip rendering camera windows
- Make sure nothing else is using heavy CPU/GPU

**VRChat not receiving data**
- Confirm OSC is enabled in VRChat settings
- Confirm port in config matches VRChat's OSC port (default 9000)
- Check firewall isn't blocking localhost UDP

---

## Project Structure

```
dual-cam-osc-tracker/
├── main.py                  # Entry point
├── requirements.txt
├── config/
│   └── user_config.json     # All user settings (edit this)
└── src/
    ├── config_loader.py     # JSON config read/write
    ├── camera_capture.py    # Threaded camera input (webcam + IP cam)
    ├── pose_estimator.py    # MediaPipe pose estimation per camera
    ├── fusion.py            # Dual-camera 3D position fusion
    └── osc_sender.py        # VRChat OSC protocol output
```

---

## GUI

The main interface is a dark-theme Tkinter GUI with:

- **Live camera feeds** — front and side, with color-coded tracker dots overlaid on each joint
- **Front camera** — webcam dropdown (auto-detected) or IP/URL text input for phone
- **Side camera** — dropdown: `None` (disables side processing), webcam index, or `IP / Phone`
- **Left/Right toggle** — which side the side camera is on
- **OSC destination** — set to `127.0.0.1` for same machine, or your Quest/headset's LAN IP for standalone
- **Smoothing slider** — real-time
- **Per-tracker toggles** — color-coded checkboxes, one per joint + master "ALL" toggle
- **Save Config** — writes back to `user_config.json` (backs up `.json.bak` first)
- **Web UI URL** — shown at the bottom of the controls panel once running

---

## Web UI (LAN Remote Config)

A lightweight web interface is served on port `8765` when the tracker starts. Access it from any device on the same network:

```
http://<your-machine-ip>:8765
```

The URL is printed on startup and shown in the GUI. Useful for:
- Configuring from your phone while wearing a headset
- Setting the OSC destination IP for standalone Quest use
- Toggling trackers without alt-tabbing

To disable the web UI:
```bash
python main.py --no-web
```

### Standalone Quest / Remote Processing Setup

If you're processing on a laptop and playing VRChat on a standalone Quest:

1. Make sure both devices are on the same Wi-Fi network
2. Find your Quest's local IP: `Settings → Wi-Fi → (your network) → IP address`
3. Set `osc.ip` in config (or via GUI/web UI) to that IP
4. Make sure VRChat on Quest has OSC enabled

---

## Running Modes

| Mode | Command |
|------|---------|
| GUI + Web UI (default) | `python main.py` |
| Headless + Web UI | `python main.py --headless` |
| GUI only (no web) | `python main.py --no-web` |
| Headless, no web | `python main.py --headless --no-web` |
| Custom config | `python main.py --config /path/to/config.json` |

---

## Project Structure

```
dual-cam-osc-tracker/
├── main.py                  # Entry point + TrackerEngine
├── requirements.txt
├── config/
│   └── user_config.json     # All user settings
└── src/
    ├── config_loader.py     # JSON config read/write
    ├── camera_capture.py    # Threaded camera (webcam + IP)
    ├── pose_estimator.py    # MediaPipe per camera
    ├── fusion.py            # Dual-camera 3D fusion
    ├── osc_sender.py        # VRChat OSC output
    ├── gui.py               # Dark theme Tkinter GUI
    └── web_ui.py            # Flask LAN web interface
```
