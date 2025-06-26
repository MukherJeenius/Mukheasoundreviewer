import sounddevice as sd #Realtime Audio Flexxx
import numpy as np # Onkoooo
import soundfile as sf #Save soundzzz
import threading
import time
import queue # LINE UP FOR THE AUDIOZZZ
import customtkinter as ctk #CUZ WE DONT LIKE BASIC TKINTER
from tkinter import simpledialog, filedialog, messagebox


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Constants
SAMPLE_RATE = 44100
CHANNELS = 1
BLOCK_SIZE = 1024

# State
start_time = None
recording = False
paused = False
frames = []
notes = []
q = queue.Queue()
is_playing = False
playback_start_time = None

# Root Window
root = ctk.CTk()
root.title("🎙️ Mukhea Audio Notes")
root.geometry("700x750")

# Timer label
timer_label = ctk.CTkLabel(root, text="Time: 0.00s", font=ctk.CTkFont(size=16, weight="bold"))
timer_label.pack(pady=10)

# Progress bar canvas
canvas_frame = ctk.CTkFrame(root)
canvas_frame.pack(pady=5)
progress_canvas = ctk.CTkCanvas(canvas_frame, width=500, height=20, bg="#ccc", bd=0, highlightthickness=0)
progress_canvas.pack()
progress_fill = progress_canvas.create_rectangle(0, 0, 0, 20, fill="#4caf50", width=0)
progress_tags = []

# Log display
note_display = ctk.CTkTextbox(root, width=650, height=250, font=("Consolas", 12))
note_display.pack(pady=10)
note_display.configure(state="disabled")

def log(msg):
    note_display.configure(state="normal")
    note_display.insert("end", msg + "\n")
    note_display.see("end")
    note_display.configure(state="disabled")

def audio_callback(indata, frames_count, time_info, status):
    if status:
        log("⚠️ " + str(status))
    if not paused:
        q.put(indata.copy())
        frames.append(indata.copy())

def update_timer():
    global is_playing
    if recording and not paused:
        current = time.time() - start_time
        timer_label.configure(text=f"Time: {current:.2f}s")
        progress_ratio = min(current / 300, 1.0)
        progress_canvas.coords(progress_fill, 0, 0, 500 * progress_ratio, 20)
    elif is_playing:
        current = time.time() - playback_start_time
        timer_label.configure(text=f"Time: {current:.2f}s")
        progress_ratio = min(current / 300, 1.0)
        progress_canvas.coords(progress_fill, 0, 0, 500 * progress_ratio, 20)
    if recording or is_playing:
        root.after(100, update_timer)

def draw_tag_marker(timestamp, color):
    x = (timestamp / 300) * 500
    marker = progress_canvas.create_line(x, 0, x, 20, fill=color, width=2)
    progress_tags.append(marker)

def start_recording():
    global start_time, recording, paused, notes, frames
    if recording:
        return
    log("🎙️ Recording started. Press 'Pause', 'Note', or 'Stop'.")
    start_time = time.time()
    notes.clear()
    frames.clear()
    for marker in progress_tags:
        progress_canvas.delete(marker)
    progress_tags.clear()
    recording = True
    paused = False
    pause_btn.configure(text="Pause")
    threading.Thread(target=audio_thread, daemon=True).start()
    update_timer()

def audio_thread():
    global recording
    try:
        with sd.InputStream(callback=audio_callback, channels=CHANNELS, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
            with sd.OutputStream(channels=CHANNELS, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE) as out_stream:
                while recording:
                    if not q.empty():
                        data = q.get()
                        out_stream.write(data)
    except Exception as e:
        log("❌ Error: " + str(e))
        stop_recording()

def pause_recording():
    global paused
    if not recording:
        return
    paused = not paused
    pause_btn.configure(text="Resume" if paused else "Pause")
    log("⏸️ Paused." if paused else "▶️ Resumed.")

def get_current_time():
    if recording and not paused:
        return time.time() - start_time
    elif is_playing:
        return time.time() - playback_start_time
    return 0.0

def take_note():
    timestamp = get_current_time()
    note = simpledialog.askstring("📝 Take Note", "Enter your note:")
    if note:
        notes.append((timestamp, note))
        log(f"[{timestamp:.2f} sec] 📝 {note}")

def add_color_tag(color):
    timestamp = get_current_time()
    tag_label = {"green": "🟢 Green Tag", "orange": "🟠 Orange Tag", "red": "🔴 Red Tag"}[color]
    notes.append((timestamp, tag_label))
    log(f"[{timestamp:.2f} sec] {tag_label}")
    draw_tag_marker(timestamp, color)

def stop_recording():
    global recording
    if not recording:
        return
    recording = False
    progress_canvas.coords(progress_fill, 0, 0, 0, 20)
    log("🛑 Recording stopped.\n🗒️ Your Notes:")
    for ts, note in notes:
        log(f"[{ts:.2f} sec] {note}")

def save_session():
    if not frames:
        messagebox.showwarning("Nothing to Save", "⚠️ No recording found. Start recording first.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
    if file_path:
        audio_data = np.concatenate(frames)
        sf.write(file_path, audio_data, SAMPLE_RATE)
        log(f"💾 Saved audio to: {file_path}")
        notes_file = file_path.replace(".wav", "_notes.txt")
        with open(notes_file, "w", encoding="utf-8") as f:
            for ts, note in notes:
                f.write(f"[{ts:.2f} sec] {note}\n")
        log(f"🗒️ Notes saved to: {notes_file}")

def drop_session():
    global recording, frames, notes, is_playing
    if messagebox.askyesno("Drop Session", "❌ Are you sure you want to discard the recording and notes?"):
        recording = False
        is_playing = False
        frames.clear()
        notes.clear()
        for marker in progress_tags:
            progress_canvas.delete(marker)
        progress_tags.clear()
        progress_canvas.coords(progress_fill, 0, 0, 0, 20)
        note_display.configure(state="normal")
        note_display.delete("1.0", "end")
        note_display.configure(state="disabled")
        log("🗑️ Session dropped.")

def play_audio():
    global is_playing, playback_start_time
    if not frames:
        messagebox.showinfo("Nothing to Play", "No recording available.")
        return
    try:
        audio_data = np.concatenate(frames)
        log("🔊 Playing back...")
        is_playing = True
        playback_start_time = time.time()
        update_timer()
        sd.play(audio_data, samplerate=SAMPLE_RATE)
        sd.wait()
        is_playing = False
        log("⏹️ Playback ended.")
    except Exception as e:
        is_playing = False
        log("❌ Playback error: " + str(e))

# Button Frame
btn_frame = ctk.CTkFrame(root)
btn_frame.pack(pady=10)

def create_button(text, command, color):
    return ctk.CTkButton(btn_frame, text=text, command=command, fg_color=color, hover_color="gray20", width=90)

create_button("Start", start_recording, "#4caf50").grid(row=0, column=0, padx=6, pady=5)
pause_btn = create_button("Pause", pause_recording, "#ff9800")
pause_btn.grid(row=0, column=1, padx=6, pady=5)
create_button("Note", take_note, "#2196f3").grid(row=0, column=2, padx=6, pady=5)
create_button("Stop", stop_recording, "#f44336").grid(row=0, column=3, padx=6, pady=5)
create_button("▶️ Play", play_audio, "#607d8b").grid(row=1, column=0, columnspan=2, padx=6, pady=5)
create_button("💾 Save", save_session, "#673ab7").grid(row=1, column=2, padx=6, pady=5)
create_button("🗑️ Drop", drop_session, "#9e9e9e").grid(row=1, column=3, padx=6, pady=5)

# Tag Grade Frame
grade_frame = ctk.CTkFrame(root)
grade_frame.pack(pady=8)
ctk.CTkLabel(grade_frame, text="Tag Grade:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)

def tag_button(color, emoji):
    return ctk.CTkButton(grade_frame, text=emoji, command=lambda: add_color_tag(color), width=35, fg_color=color, hover_color="gray20")

tag_button("green", "🟢").pack(side="left", padx=4)
tag_button("orange", "🟠").pack(side="left", padx=4)
tag_button("red", "🔴").pack(side="left", padx=4)

    # Run App
root.mainloop()

                
