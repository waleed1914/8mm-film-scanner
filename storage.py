import os
import getpass
import glob
import shutil
import subprocess
import uuid
from datetime import datetime

from config import BASE_DIR, FRAMES_DIR, RECORDINGS_DIR


def find_usb_base():
    user = getpass.getuser()

    possible_roots = [
        f"/media/{user}",
        "/media/pi",
        "/mnt",
    ]

    for root in possible_roots:
        if os.path.exists(root):
            try:
                items = os.listdir(root)
                for item in items:
                    path = os.path.join(root, item)
                    if os.path.ismount(path) or os.path.isdir(path):
                        return path
            except Exception:
                pass

    return None


def get_output_base(settings):
    if settings.save_location == "USB":
        usb = find_usb_base()
        if usb:
            return usb

        print("USB not found. Falling back to internal storage.")

    return BASE_DIR


def get_frames_dir(settings):
    base = get_output_base(settings)
    path = os.path.join(base, "frames") if base != BASE_DIR else FRAMES_DIR
    os.makedirs(path, exist_ok=True)
    return path


def get_videos_dir(settings):
    base = get_output_base(settings)
    path = os.path.join(base, "recordings") if base != BASE_DIR else RECORDINGS_DIR
    os.makedirs(path, exist_ok=True)
    return path


def find_ffmpeg():
    configured = os.environ.get("FFMPEG_BINARY")
    if configured and os.path.isfile(configured):
        return configured

    executable = shutil.which("ffmpeg")
    if executable:
        return executable

    if os.name == "nt":
        package_root = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Microsoft", "WinGet", "Packages",
        )
        matches = glob.glob(
            os.path.join(package_root, "Gyan.FFmpeg_*", "**", "ffmpeg.exe"),
            recursive=True,
        )
        if matches:
            return matches[0]

    return None


def make_session_name(prefix):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefix}_{timestamp}_{uuid.uuid4().hex[:8]}"


def cleanup_session_frames(session):
    frames_dir = session.get("frames_dir")
    if frames_dir and os.path.isdir(frames_dir):
        shutil.rmtree(frames_dir, ignore_errors=True)


def copy_recording_to_usb(path):
    usb = find_usb_base()
    if not usb:
        return None

    target_dir = os.path.join(usb, "recordings")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, os.path.basename(path))
    shutil.copy2(path, target_path)
    return target_path


def copy_frame_session_to_usb(path):
    usb = find_usb_base()
    if not usb:
        return None

    target_dir = os.path.join(usb, "frames", os.path.basename(path))
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    shutil.copytree(path, target_dir)
    return target_dir


def delete_recording(path):
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def delete_frame_session(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        return True
    return False


def list_recordings(settings):
    recordings_dir = get_videos_dir(settings)
    files = glob.glob(os.path.join(recordings_dir, "*.mp4"))
    return sorted(files, key=os.path.getmtime, reverse=True)


def list_frame_sessions(settings):
    frames_dir = get_frames_dir(settings)
    sessions = [
        path for path in glob.glob(os.path.join(frames_dir, "*"))
        if os.path.isdir(path)
    ]
    return sorted(sessions, key=os.path.getmtime, reverse=True)


def list_saved_items(settings):
    items = []

    for path in list_recordings(settings):
        items.append({
            "type": "MP4",
            "path": path,
            "name": os.path.basename(path),
            "mtime": os.path.getmtime(path),
            "size_bytes": os.path.getsize(path),
        })

    for path in list_frame_sessions(settings):
        frame_files = sorted(glob.glob(os.path.join(path, "frame_*.jpg")))
        items.append({
            "type": "FRAMES",
            "path": path,
            "name": os.path.basename(path),
            "mtime": os.path.getmtime(path),
            "frame_count": len(frame_files),
        })

    return sorted(items, key=lambda item: item["mtime"], reverse=True)


def start_session(settings, prefix="session"):
    session_name = make_session_name(prefix)

    frames_base = get_frames_dir(settings)
    videos_base = get_videos_dir(settings)

    session_frames_dir = os.path.join(frames_base, session_name)
    os.makedirs(session_frames_dir, exist_ok=True)

    return {
        "name": session_name,
        "frames_dir": session_frames_dir,
        "videos_dir": videos_base,
        "frame_count": 0,
    }


def save_frame_to_session(img, session):
    frame_count = session["frame_count"]
    filename = f"frame_{frame_count:06d}.jpg"
    path = os.path.join(session["frames_dir"], filename)

    img.save(path, quality=95)

    session["frame_count"] += 1

    print("Saved frame:", path)
    return path


def save_single_frame(img, settings, prefix="frame", progress_callback=None):
    session = start_session(settings, prefix=prefix)
    if progress_callback:
        progress_callback(20)
    return save_frame_to_session(img, session)


def make_mp4_from_session(session, fps, progress_callback=None):
    if session["frame_count"] <= 0:
        print("No frames captured. MP4 not created.")
        return None

    output_path = os.path.join(session["videos_dir"], session["name"] + ".mp4")
    input_pattern = os.path.join(session["frames_dir"], "frame_%06d.jpg")

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("MP4 creation failed: FFmpeg was not found.")
        return None

    cmd = [
        ffmpeg,
        "-y",
        "-framerate", str(fps),
        "-i", input_pattern,
        "-progress", "pipe:1",
        "-nostats",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    print("Creating MP4...")
    print(" ".join(cmd))

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        duration_seconds = max(session["frame_count"] / max(fps, 1), 0.001)

        if progress_callback:
            progress_callback(0)

        for line in process.stdout:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == "out_time_ms":
                try:
                    elapsed = int(value) / 1_000_000
                    percent = min(99, max(0, int((elapsed / duration_seconds) * 100)))
                    if progress_callback:
                        progress_callback(percent)
                except ValueError:
                    pass

        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(
                return_code, cmd, output="", stderr=""
            )

        print("MP4 saved:", output_path)
        cleanup_session_frames(session)
        if progress_callback:
            progress_callback(100)
        return output_path
    except subprocess.CalledProcessError as e:
        details = (e.stderr or e.stdout or str(e)).strip()
        print("MP4 creation failed:", details)
        return None
    except OSError as e:
        print("MP4 creation failed:", e)
        return None
    finally:
        if "process" in locals() and process.stdout is not None:
            try:
                process.stdout.close()
            except OSError:
                pass
