import os
import re
import threading
from tkinter import Tk, Label, Button, Entry, StringVar, filedialog, ttk, messagebox, Text, Scrollbar, Frame, Toplevel
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
import speech_recognition as sr
from pydub import AudioSegment

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader & Transcriber")
        self.root.geometry("600x750")
        self.root.resizable(False, False)

        # Variables
        self.url_var = StringVar()
        self.download_folder = StringVar()

        # Top Section
        Label(root, text="YouTube Downloader & Transcriber", font=("Arial", 16)).pack(pady=10)
        Label(root, text="Enter Video URL:").pack(pady=5)
        Entry(root, textvariable=self.url_var, width=60).pack(pady=5)

        Button(root, text="Select Folder", command=self.select_folder).pack(pady=5)
        Label(root, textvariable=self.download_folder, fg="blue").pack(pady=5)

        Label(root, text="Select Resolution:").pack(pady=5)
        self.resolution_options = ttk.Combobox(root, values=["144p", "360p", "480p", "720p", "1080p", "4K", "8K"])
        self.resolution_options.set("1080p")
        self.resolution_options.pack(pady=5)

        Label(root, text="Select Download Type:").pack(pady=5)
        self.download_type = ttk.Combobox(root, values=["Audio Only", "Video Only", "Video + Audio"])
        self.download_type.set("Video + Audio")
        self.download_type.pack(pady=5)

        Button(root, text="Download", command=self.start_download).pack(pady=10)

        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Transcript Section
        Button(root, text="Get Transcript", command=self.start_transcript_extraction).pack(pady=10)
        Label(root, text="Transcript Output:").pack(pady=5)

        # Transcript Frame: holds the Text widget and its scrollbar
        transcript_frame = Frame(root)
        transcript_frame.pack(pady=5)
        self.transcript_text = Text(transcript_frame, height=10, width=70, wrap="word")
        self.transcript_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = Scrollbar(transcript_frame, command=self.transcript_text.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.transcript_text.config(yscrollcommand=scrollbar.set)

        # Buttons for transcript actions
        btn_frame = Frame(root)
        btn_frame.pack(pady=10)
        Button(btn_frame, text="Copy Transcript", command=self.copy_transcript).pack(side="left", padx=5)
        Button(btn_frame, text="Download Transcript", command=self.download_transcript).pack(side="left", padx=5)

        # About Section Button
        Button(root, text="About", command=self.show_about).pack(pady=10)

    def show_about(self):
        about_window = Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("400x300")
        about_window.resizable(False, False)

        Label(about_window, text="About This Application", font=("Arial", 14)).pack(pady=10)
        Label(about_window, text="Developer: Ishant Singh", font=("Arial", 12)).pack(pady=5)
        Label(about_window, text="Instagram: @fissile_u235", font=("Arial", 12)).pack(pady=5)
        Label(about_window, text="GitHub: github.com/0pen-Sourcer", font=("Arial", 12)).pack(pady=5)
        Label(about_window, text="Contact: ishantstech@gmail.com", font=("Arial", 12)).pack(pady=5)

        Button(about_window, text="Close", command=about_window.destroy).pack(pady=20)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_folder.set(folder)

    def start_download(self):
        if not self.url_var.get().strip():
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        if not self.download_folder.get():
            messagebox.showerror("Error", "Please select a folder")
            return
        threading.Thread(target=self.download_video_or_audio, daemon=True).start()

    def download_video_or_audio(self):
        try:
            url = self.url_var.get().strip()
            output_path = self.download_folder.get()
            download_type = self.download_type.get()
            resolution = self.resolution_options.get()

            ydl_opts = {
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.update_progress_bar],
                'noplaylist': True,
                'merge_output_format': 'mp4',
            }

            if download_type == "Audio Only":
                ydl_opts['format'] = 'bestaudio'
            elif download_type == "Video Only":
                ydl_opts['format'] = self.get_format(resolution, video_only=True)
            else:
                ydl_opts['format'] = self.get_format(resolution, video_only=False)

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            self.root.after(0, lambda: messagebox.showinfo("Success", "Download completed successfully!"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {e}"))

    def get_format(self, resolution, video_only=False):
        resolution_map = {
            "144p": "144",
            "360p": "360",
            "480p": "480",
            "720p": "720",
            "1080p": "1080",
            "4K": "2160",
            "8K": "4320"
        }
        res_code = resolution_map.get(resolution, "720")
        if video_only:
            return f"bestvideo[height<={res_code}]"
        else:
            return f"bestvideo[height<={res_code}]+bestaudio"

    def update_progress_bar(self, d):
        if d.get('status') == 'downloading':
            percent_str = d.get('_percent_str', '0.0%').strip()
            try:
                percent = float(percent_str.strip('%'))
            except ValueError:
                percent = 0
            self.root.after(0, lambda: self.progress_bar.config(value=percent))
        elif d.get('status') == 'finished':
            self.root.after(0, lambda: self.progress_bar.config(value=100))

    def start_transcript_extraction(self):
        if not self.url_var.get().strip():
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        threading.Thread(target=self.get_transcript, daemon=True).start()

    def extract_video_id(self, url):
        """
        Extracts the video ID from various YouTube URL formats,
        including standard URLs and YouTube Shorts.
        """
        video_id = None
        if "youtube.com/shorts/" in url:
            parts = url.split("youtube.com/shorts/")
            if len(parts) > 1:
                video_id = parts[1].split("?")[0]
        elif "v=" in url:
            match = re.search(r"v=([^&]+)", url)
            if match:
                video_id = match.group(1)
        else:
            video_id = url.rstrip("/").split("/")[-1]
        return video_id

    def get_transcript(self):
        try:
            url = self.url_var.get().strip()
            video_id = self.extract_video_id(url)
            if not video_id:
                raise Exception("Unable to extract video ID from URL.")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = "\n".join([entry["text"] for entry in transcript])
            self.root.after(0, lambda: self.transcript_text.delete("1.0", "end"))
            self.root.after(0, lambda: self.transcript_text.insert("1.0", transcript_text))
        except Exception as e:
            # If subtitles are not available, attempt audio transcription.
            self.root.after(0, lambda: self.transcript_text.delete("1.0", "end"))
            self.root.after(0, lambda: self.transcript_text.insert("1.0", "No subtitles found. Attempting audio transcription..."))
            threading.Thread(target=self.download_and_transcribe_audio, daemon=True).start()

    def download_and_transcribe_audio(self):
        try:
            url = self.url_var.get().strip()
            output_folder = self.download_folder.get()
            audio_path = os.path.join(output_folder, "audio_temp.mp3")
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
                'outtmpl': audio_path,
                'noplaylist': True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            wav_file = self.convert_audio_to_wav(audio_path)
            transcript = self.transcribe_audio(wav_file)
            self.root.after(0, lambda: self.transcript_text.delete("1.0", "end"))
            self.root.after(0, lambda: self.transcript_text.insert("1.0", transcript))
            if os.path.exists(audio_path):
                os.remove(audio_path)
            if os.path.exists(wav_file):
                os.remove(wav_file)
        except Exception as e:
            self.root.after(0, lambda: self.transcript_text.delete("1.0", "end"))
            self.root.after(0, lambda: self.transcript_text.insert("1.0", f"Error: {e}"))

    def convert_audio_to_wav(self, audio_path):
        wav_path = os.path.join(os.path.dirname(audio_path), "converted_temp.wav")
        audio = AudioSegment.from_file(audio_path)
        audio.export(wav_path, format="wav")
        return wav_path

    def transcribe_audio(self, audio_path):
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return "Could not understand audio."
        except sr.RequestError:
            return "Error connecting to Google Speech API."

    def copy_transcript(self):
        transcript = self.transcript_text.get("1.0", "end").strip()
        if transcript:
            self.root.clipboard_clear()
            self.root.clipboard_append(transcript)
            messagebox.showinfo("Copied", "Transcript copied to clipboard!")
        else:
            messagebox.showwarning("Warning", "No transcript available to copy.")

    def download_transcript(self):
        transcript = self.transcript_text.get("1.0", "end").strip()
        if transcript:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                     filetypes=[("Text files", "*.txt")],
                                                     title="Save Transcript As")
            if file_path:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(transcript)
                    messagebox.showinfo("Saved", f"Transcript saved to {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save transcript: {e}")
        else:
            messagebox.showwarning("Warning", "No transcript available to save.")

if __name__ == "__main__":
    root = Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
