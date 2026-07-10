\
"""
SuperBasic Video Editor
A simple video editor with timeline selection, crop box, and export functionality.
Runs on Windows with tkinter GUI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import time
import threading
import cv2
import numpy as np
from PIL import Image, ImageTk
import subprocess


class VideoEditorApp:
    """Main application class for the video editor."""

    def __init__(self, root):
        self.root = root
        self.root.title("SuperBasic Video Editor")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # Video state
        self.video_path = None
        self.cap = None
        self.fps = 30
        self.total_frames = 0
        self.duration = 0
        self.current_frame = 0
        self.is_playing = False

        # Timeline selection
        self.start_time = 0.0
        self.end_time = 0.0

        # Crop box in CANVAS pixels (direct mouse interaction)
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 0
        self.crop_h = 0

        # Video display info (where video is drawn on canvas)
        self.video_display_x = 0
        self.video_display_y = 0
        self.video_display_w = 0
        self.video_display_h = 0
        self.video_orig_w = 0
        self.video_orig_h = 0

        # Drag state
        self.is_dragging = False
        self.drag_start = None
        self.drag_edge = None

        # UI reference
        self.video_image = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Video preview + Timeline
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Video preview
        preview_frame = ttk.LabelFrame(left_panel, text="Video Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))

        self.canvas = tk.Canvas(preview_frame, bg="black", width=720, height=405, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind events for crop box interaction
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Timeline selection (visual timeline under video)
        timeline_frame = ttk.Frame(left_panel)
        timeline_frame.pack(fill=tk.X, padx=5, pady=(5, 5))
        ttk.Label(timeline_frame, text="Timeline Selection", font=("", 9, "bold")).pack(anchor=tk.W)

        self.timeline_canvas = tk.Canvas(timeline_frame, height=60, bg="#1a1a2e", cursor="hand2")
        self.timeline_canvas.pack(fill=tk.X, padx=5, pady=5)
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self._on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._on_timeline_release)

        # Timeline info labels
        info_frame = ttk.Frame(timeline_frame)
        info_frame.pack(fill=tk.X)
        self.timeline_start_label = ttk.Label(info_frame, text="Start: 0.0s", font=("", 8))
        self.timeline_start_label.pack(side=tk.LEFT, padx=5)
        self.timeline_duration_label = ttk.Label(info_frame, text="Duration: 0.0s", font=("", 8))
        self.timeline_duration_label.pack(side=tk.LEFT, padx=5)
        self.timeline_end_label = ttk.Label(info_frame, text="End: 0.0s", font=("", 8))
        self.timeline_end_label.pack(side=tk.RIGHT, padx=5)

        # Right panel - Controls
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        # Upload
        ttk.Button(right_panel, text="Upload Video", command=self._upload_video).pack(fill=tk.X, padx=5, pady=5)

        # Playback
        playback_frame = ttk.LabelFrame(right_panel, text="Playback")
        playback_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_frame = ttk.Frame(playback_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        self.play_btn = ttk.Button(btn_frame, text="Play", command=self._toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Pause", command=self._pause).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Stop", command=self._stop).pack(side=tk.LEFT, padx=2)

        # Frame scrubber
        scrub_frame = ttk.Frame(playback_frame)
        scrub_frame.pack(fill=tk.X, pady=5)
        ttk.Label(scrub_frame, text="Frame:").pack(side=tk.LEFT, padx=(0, 5))
        self.frame_entry = ttk.Entry(scrub_frame, width=8)
        self.frame_entry.pack(side=tk.LEFT, padx=2)
        self.frame_entry.bind("<Return>", self._on_frame_change)
        self.total_frames_label = ttk.Label(scrub_frame, text="0")
        self.total_frames_label.pack(side=tk.LEFT, padx=2)

        self.info_label = ttk.Label(playback_frame, text="No video loaded")
        self.info_label.pack(pady=5)

        # Crop
        crop_frame = ttk.LabelFrame(right_panel, text="Crop Box")
        crop_frame.pack(fill=tk.X, padx=5, pady=5)
        self.crop_label = ttk.Label(crop_frame, text="Drag box on preview")
        self.crop_label.pack(pady=5)
        ttk.Button(crop_frame, text="Reset Crop", command=self._reset_crop).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(crop_frame, text="Fit to Video", command=self._fit_crop).pack(fill=tk.X, padx=5, pady=2)

        # Export
        export_frame = ttk.LabelFrame(right_panel, text="Export")
        export_frame.pack(fill=tk.X, padx=5, pady=5)
        self.export_btn = ttk.Button(export_frame, text="Export Video", command=self._export_video)
        self.export_btn.pack(fill=tk.X, padx=5, pady=5)
        self.progress = ttk.Progressbar(export_frame, orient=tk.HORIZONTAL, length=200, mode="determinate")
        self.progress.pack(fill=tk.X, padx=5, pady=5)
        self.status_label = ttk.Label(export_frame, text="Ready")
        self.status_label.pack(pady=5)

        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready - Upload a video to start", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_canvas_resize(self, event):
        """Handle canvas resize."""
        if self.cap:
            self._recalc_video_display()
            self._redraw()

    def _recalc_video_display(self):
        """Recalculate where the video is drawn on the canvas."""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 0:
            canvas_w = 720
        if canvas_h <= 0:
            canvas_h = 405

        scale = min(canvas_w / self.video_orig_w, canvas_h / self.video_orig_h)
        self.video_display_w = int(self.video_orig_w * scale)
        self.video_display_h = int(self.video_orig_h * scale)
        self.video_display_x = (canvas_w - self.video_display_w) // 2
        self.video_display_y = (canvas_h - self.video_display_h) // 2

    def _upload_video(self):
        """Open file dialog to upload a video."""
        file_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"), ("All files", "*.*")]
        )
        if not file_path:
            return
        self.video_path = file_path
        self._load_video()

    def _load_video(self):
        """Load video with OpenCV."""
        self.status_bar.config(text="Loading video...")
        self.root.update()

        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Failed to open video file.")
                return

            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.duration = self.total_frames / self.fps

            self.video_orig_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_orig_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.start_scale.config(to=self.duration)
            self.end_scale.config(to=self.duration)
            self.start_time = 0.0
            self.end_time = self.duration
            self.start_scale.set(0)
            self.end_scale.set(1.0)
            self.start_label.config(text="0.0s")
            self.end_label.config(text=f"{self.duration:.1f}s")

            self.total_frames_label.config(text=str(self.total_frames))
            self.info_label.config(text=f"{self.fps:.1f} FPS | {self.total_frames} frames | {self.duration:.1f}s")

            self._recalc_video_display()
            self._fit_crop()

            self.current_frame = 0
            self._redraw()

            # Initialize timeline
            self._draw_timeline()

            self.status_bar.config(text=f"Loaded: {os.path.basename(self.video_path)}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video:\\n{str(e)}")

    def _fit_crop(self):
        """Fit crop box to the video display area on canvas."""
        self.crop_x = self.video_display_x
        self.crop_y = self.video_display_y
        self.crop_w = self.video_display_w
        self.crop_h = self.video_display_h
        self._update_crop_label()
        self._redraw()

    def _reset_crop(self):
        """Reset crop to full canvas."""
        canvas_w = self.canvas.winfo_width() or 720
        canvas_h = self.canvas.winfo_height() or 405
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = canvas_w
        self.crop_h = canvas_h
        self._update_crop_label()
        self._redraw()

    def _update_crop_label(self):
        """Update crop info label."""
        self.crop_label.config(text=f"X={self.crop_x} Y={self.crop_y} W={self.crop_w} H={self.crop_h}")

    def _draw_timeline(self):
        """Draw the visual timeline."""
        if not self.cap or not hasattr(self, 'timeline_canvas'):
            return

        self.timeline_canvas.delete("all")
        tw = self.timeline_canvas.winfo_width() or 700
        th = 60

        if tw <= 1:
            return

        # Draw video bar (full duration)
        margin = 5
        bar_h = 20
        bar_y = 10
        self.timeline_canvas.create_rectangle(
            margin, bar_y, tw - margin, bar_y + bar_h,
            fill="#3a3a5c", outline="white", width=1
        )

        # Draw selected region
        start_x = margin + (self.start_time / self.duration) * (tw - 2 * margin)
        end_x = margin + (self.end_time / self.duration) * (tw - 2 * margin)

        self.timeline_canvas.create_rectangle(
            start_x, bar_y, end_x, bar_y + bar_h,
            fill="#4a90d9", outline="red", width=2
        )

        # Draw start marker
        self.start_marker = self.timeline_canvas.create_line(
            start_x, bar_y, start_x, bar_y + bar_h + 10,
            fill="red", width=3
        )

        # Draw end marker
        self.end_marker = self.timeline_canvas.create_line(
            end_x, bar_y, end_x, bar_y + bar_h + 10,
            fill="red", width=3
        )

        # Draw playhead
        play_x = margin + (self.current_frame / self.total_frames) * (tw - 2 * margin)
        self.playhead = self.timeline_canvas.create_line(
            play_x, 0, play_x, th,
            fill="yellow", width=2, dash=(4, 2)
        )

        # Time labels
        self.timeline_start_label.config(text=f"Start: {self.start_time:.2f}s")
        self.timeline_end_label.config(text=f"End: {self.end_time:.2f}s")
        self.timeline_duration_label.config(text=f"Duration: {self.end_time - self.start_time:.2f}s")

    def _on_timeline_click(self, event):
        """Handle click on timeline."""
        if not self.cap:
            return

        tw = self.timeline_canvas.winfo_width()
        margin = 5
        bar_y = 10
        bar_h = 20

        # Check if click is on start marker
        start_x = margin + (self.start_time / self.duration) * (tw - 2 * margin)
        if abs(event.x - start_x) < 10:
            self.is_dragging_timeline = True
            self.dragging_timeline = 'start'
            return

        # Check if click is on end marker
        end_x = margin + (self.end_time / self.duration) * (tw - 2 * margin)
        if abs(event.x - end_x) < 10:
            self.is_dragging_timeline = True
            self.dragging_timeline = 'end'
            return

        # Click on bar - jump playhead
        if bar_y <= event.y <= bar_y + bar_h:
            frac = (event.x - margin) / (tw - 2 * margin)
            frac = max(0, min(1, frac))
            self.current_frame = int(frac * self.total_frames)
            self._redraw()
            self._update_playhead()
        else:
            # Determine if closer to start or end
            if abs(event.x - start_x) < abs(event.x - end_x):
                self.is_dragging_timeline = True
                self.dragging_timeline = 'start'
            else:
                self.is_dragging_timeline = True
                self.dragging_timeline = 'end'

    def _on_timeline_drag(self, event):
        """Handle drag on timeline."""
        if not hasattr(self, 'is_dragging_timeline') or not self.is_dragging_timeline:
            return

        tw = self.timeline_canvas.winfo_width()
        margin = 5
        frac = (event.x - margin) / (tw - 2 * margin)
        frac = max(0, min(1, frac))
        new_time = frac * self.duration

        if self.dragging_timeline == 'start':
            self.start_time = new_time
            if self.start_time >= self.end_time:
                self.start_time = max(0, self.end_time - 0.1)
        elif self.dragging_timeline == 'end':
            self.end_time = new_time
            if self.end_time <= self.start_time:
                self.end_time = min(self.duration, self.start_time + 0.1)

        self._draw_timeline()

    def _on_timeline_release(self, event):
        """Handle release on timeline."""
        self.is_dragging_timeline = False
        self.dragging_timeline = None

    def _update_playhead(self):
        """Update playhead position on timeline."""
        if not hasattr(self, 'timeline_canvas') or not self.cap:
            return
        tw = self.timeline_canvas.winfo_width()
        margin = 5
        play_x = margin + (self.current_frame / self.total_frames) * (tw - 2 * margin)
        self.timeline_canvas.coords(self.playhead, play_x, 0, play_x, 60)

    def _redraw(self):
        """Redraw the canvas with current frame and crop overlay."""
        if not self.cap:
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame, (self.video_display_w, self.video_display_h))
        self.video_image = ImageTk.PhotoImage(Image.fromarray(frame_resized))

        canvas_w = self.canvas.winfo_width() or 720
        canvas_h = self.canvas.winfo_height() or 405
        self.canvas.delete("all")
        self.canvas.create_image(
            self.video_display_x + self.video_display_w // 2,
            self.video_display_y + self.video_display_h // 2,
            image=self.video_image,
            anchor=tk.CENTER
        )
        self._draw_crop_overlay()

    def _draw_crop_overlay(self):
        """Draw the crop box overlay on the canvas."""
        canvas_h = self.canvas.winfo_height() or 405
        canvas_w = self.canvas.winfo_width() or 720

        # Dark overlay outside crop area
        if self.crop_y > 0:
            self.canvas.create_rectangle(0, 0, canvas_w, self.crop_y, fill="#333333", outline="")
        if self.crop_y + self.crop_h < canvas_h:
            self.canvas.create_rectangle(0, self.crop_y + self.crop_h, canvas_w, canvas_h, fill="#333333", outline="")
        if self.crop_x > 0:
            self.canvas.create_rectangle(0, 0, self.crop_x, canvas_h, fill="#333333", outline="")
        if self.crop_x + self.crop_w < canvas_w:
            self.canvas.create_rectangle(self.crop_x + self.crop_w, 0, canvas_w, canvas_h, fill="#333333", outline="")

        # Crop box border
        self.canvas.create_rectangle(
            self.crop_x, self.crop_y,
            self.crop_x + self.crop_w, self.crop_y + self.crop_h,
            outline="red", width=4
        )

        # Corner handles
        hs = 10
        corners = [
            (self.crop_x, self.crop_y),
            (self.crop_x + self.crop_w, self.crop_y + self.crop_h),
            (self.crop_x + self.crop_w, self.crop_y),
            (self.crop_x, self.crop_y + self.crop_h),
        ]
        for cx, cy in corners:
            self.canvas.create_rectangle(
                cx - hs, cy - hs, cx + hs, cy + hs,
                fill="red", outline="white", width=2
            )

        # Edge handles
        edges = [
            (self.crop_x + self.crop_w // 2, self.crop_y),
            (self.crop_x + self.crop_w // 2, self.crop_y + self.crop_h),
            (self.crop_x, self.crop_y + self.crop_h // 2),
            (self.crop_x + self.crop_w, self.crop_y + self.crop_h // 2),
        ]
        for ex, ey in edges:
            self.canvas.create_oval(
                ex - 6, ey - 6, ex + 6, ey + 6,
                fill="white", outline="red", width=2
            )

    def _get_hit_edge(self, x, y):
        """Check if click is on a crop handle or inside the box."""
        hs = 15
        corners = [
            ("nw", self.crop_x, self.crop_y),
            ("se", self.crop_x + self.crop_w, self.crop_y + self.crop_h),
            ("ne", self.crop_x + self.crop_w, self.crop_y),
            ("sw", self.crop_x, self.crop_y + self.crop_h),
        ]
        for edge, ex, ey in corners:
            if abs(x - ex) < hs and abs(y - ey) < hs:
                return edge

        et = 10
        edges = [
            ("n", self.crop_x + self.crop_w // 2, self.crop_y),
            ("s", self.crop_x + self.crop_w // 2, self.crop_y + self.crop_h),
            ("e", self.crop_x + self.crop_w, self.crop_y + self.crop_h // 2),
            ("w", self.crop_x, self.crop_y + self.crop_h // 2),
        ]
        for edge, ex, ey in edges:
            if edge in ("n", "s"):
                if abs(x - ex) < et * 3 and abs(y - ey) < et:
                    return edge
            else:
                if abs(x - ex) < et and abs(y - ey) < et * 3:
                    return edge

        if (self.crop_x <= x <= self.crop_x + self.crop_w and
                self.crop_y <= y <= self.crop_y + self.crop_h):
            return "move"

        return None

    def _on_click(self, event):
        """Handle mouse click on canvas."""
        edge = self._get_hit_edge(event.x, event.y)
        if edge:
            self.is_dragging = True
            self.drag_edge = edge
            self.drag_start = (event.x, event.y)

    def _on_drag(self, event):
        """Handle mouse drag to resize/move crop box."""
        if not self.is_dragging:
            return

        x, y = event.x, event.y
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        canvas_w = self.canvas.winfo_width() or 720
        canvas_h = self.canvas.winfo_height() or 405

        if self.drag_edge == "move":
            self.crop_x = max(0, min(self.crop_x + dx, canvas_w - self.crop_w))
            self.crop_y = max(0, min(self.crop_y + dy, canvas_h - self.crop_h))
        elif self.drag_edge == "nw":
            new_x = self.crop_x + dx
            new_y = self.crop_y + dy
            new_w = self.crop_w - dx
            new_h = self.crop_h - dy
            if new_w > 30:
                self.crop_x = new_x
                self.crop_w = new_w
            if new_h > 30:
                self.crop_y = new_y
                self.crop_h = new_h
        elif self.drag_edge == "se":
            new_w = self.crop_w + dx
            new_h = self.crop_h + dy
            if self.crop_x + new_w <= canvas_w and new_w > 30:
                self.crop_w = new_w
            if self.crop_y + new_h <= canvas_h and new_h > 30:
                self.crop_h = new_h
        elif self.drag_edge == "ne":
            new_y = self.crop_y + dy
            new_h = self.crop_h - dy
            new_w = self.crop_w + dx
            if new_h > 30:
                self.crop_y = new_y
                self.crop_h = new_h
            if self.crop_x + new_w <= canvas_w and new_w > 30:
                self.crop_w = new_w
        elif self.drag_edge == "sw":
            new_x = self.crop_x + dx
            new_w = self.crop_w - dx
            new_h = self.crop_h + dy
            if new_w > 30:
                self.crop_x = new_x
                self.crop_w = new_w
            if self.crop_y + new_h <= canvas_h and new_h > 30:
                self.crop_h = new_h
        elif self.drag_edge == "n":
            new_y = self.crop_y + dy
            new_h = self.crop_h - dy
            if new_h > 30:
                self.crop_y = new_y
                self.crop_h = new_h
        elif self.drag_edge == "s":
            new_h = self.crop_h + dy
            if self.crop_y + new_h <= canvas_h and new_h > 30:
                self.crop_h = new_h
        elif self.drag_edge == "e":
            new_w = self.crop_w + dx
            if self.crop_x + new_w <= canvas_w and new_w > 30:
                self.crop_w = new_w
        elif self.drag_edge == "w":
            new_x = self.crop_x + dx
            new_w = self.crop_w - dx
            if new_w > 30:
                self.crop_x = new_x
                self.crop_w = new_w

        self.drag_start = (x, y)
        self._update_crop_label()
        self._redraw()

    def _on_release(self, event):
        """Handle mouse release."""
        self.is_dragging = False
        self.drag_edge = None

    def _on_start(self, value):
        self.start_time = float(value)
        self.start_label.config(text=f"{self.start_time:.2f}s")
        if self.start_time >= self.end_time:
            self.start_time = max(0, self.end_time - 0.1)
            self.start_scale.set(self.start_time)
            self.start_label.config(text=f"{self.start_time:.2f}s")

    def _on_end(self, value):
        self.end_time = float(value)
        self.end_label.config(text=f"{self.end_time:.2f}s")
        if self.end_time <= self.start_time:
            self.end_time = min(self.duration, self.start_time + 0.1)
            self.end_scale.set(self.end_time)
            self.end_label.config(text=f"{self.end_time:.2f}s")

    def _toggle_play(self):
        if not self.cap:
            messagebox.showwarning("Warning", "Please upload a video first.")
            return
        if self.is_playing:
            self._pause()
        else:
            self._play()

    def _play(self):
        if not self.cap:
            return
        self.is_playing = True
        self.play_btn.config(text="Pause")
        threading.Thread(target=self._playback_loop, daemon=True).start()

    def _pause(self):
        self.is_playing = False
        self.play_btn.config(text="Play")

    def _stop(self):
        self.is_playing = False
        self.current_frame = 0
        self.play_btn.config(text="Play")
        self.frame_entry.delete(0, tk.END)
        self.frame_entry.insert(0, "0")
        self._redraw()

    def _playback_loop(self):
        if not self.cap:
            return
        while self.is_playing:
            current_time = self.current_frame / self.fps
            if current_time >= self.end_time:
                self.is_playing = False
                self.play_btn.config(text="Play")
                break
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()
            if not ret:
                break
            self.root.after(0, self._update_frame)
            self.current_frame += 1
            time.sleep(1.0 / self.fps)
        self.root.after(0, self._redraw)

    def _update_frame(self):
        self.frame_entry.delete(0, tk.END)
        self.frame_entry.insert(0, str(self.current_frame))
        self._redraw()
        self._update_playhead()

    def _on_frame_change(self, event):
        if not self.cap:
            return
        try:
            frame_num = int(self.frame_entry.get())
            if 0 <= frame_num < self.total_frames:
                self.current_frame = frame_num
                self._redraw()
        except ValueError:
            pass

    def _export_video(self):
        if not self.video_path:
            messagebox.showwarning("Warning", "Please upload a video first.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Video",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
            initialfile=os.path.splitext(os.path.basename(self.video_path))[0] + "_edited.mp4"
        )
        if not output_path:
            return

        video_x, video_y, video_w, video_h = self._canvas_to_video_crop()

        self.export_btn.config(state=tk.DISABLED)
        self.progress.config(value=0)
        self.status_label.config(text="Exporting...")

        threading.Thread(
            target=self._do_export,
            args=(output_path, video_x, video_y, video_w, video_h),
            daemon=True
        ).start()

    def _canvas_to_video_crop(self):
        """Convert canvas crop coordinates to video coordinates."""
        canvas_w = self.canvas.winfo_width() or 720
        canvas_h = self.canvas.winfo_height() or 405

        scale_x = self.video_display_w / self.video_orig_w
        scale_y = self.video_display_h / self.video_orig_h

        rel_x = self.crop_x - self.video_display_x
        rel_y = self.crop_y - self.video_display_y

        video_x = int(rel_x / scale_x)
        video_y = int(rel_y / scale_y)
        video_w = int(self.crop_w / scale_x)
        video_h = int(self.crop_h / scale_y)

        video_x = max(0, min(video_x, self.video_orig_w))
        video_y = max(0, min(video_y, self.video_orig_h))
        video_w = max(1, min(video_w, self.video_orig_w - video_x))
        video_h = max(1, min(video_h, self.video_orig_h - video_y))

        return video_x, video_y, video_w, video_h

    def _do_export(self, output_path, crop_x, crop_y, crop_w, crop_h):
        try:
            duration = self.end_time - self.start_time
            if duration <= 0:
                self.root.after(0, self._show_error, "Error", "Invalid timeline selection.")
                return

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(self.start_time),
                "-i", self.video_path,
                "-t", str(duration),
                "-vf", f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-an",
                "-movflags", "+faststart",
                output_path
            ]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                if "time=" in line:
                    time_str = line.split("time=")[-1].split(" ")[0].strip()
                    try:
                        parts = time_str.split(":")
                        current_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        pct = min(int((current_sec / duration) * 100), 100)
                        self.root.after(0, self._update_progress, pct)
                    except (ValueError, IndexError):
                        pass

            process.wait()

            if process.returncode == 0:
                self.root.after(0, self._export_done, output_path)
            else:
                error_output = ""
                if process.stderr:
                    error_output = process.stderr.strip()
                self.root.after(0, self._show_error, "Export Failed",
                    f"FFmpeg failed with code {process.returncode}\n\n"
                    f"Command: {' '.join(cmd)}\n\n"
                    f"Output:\n{error_output[:1000]}"
                )

        except FileNotFoundError:
            self.root.after(0, self._show_error, "Export Failed",
                "FFmpeg is not found in your system PATH.\n\n"
                "To fix this on Windows:\n"
                "1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/\n"
                "2. Extract the zip file\n"
                "3. Add the 'bin' folder to your PATH:\n"
                "   - Right-click 'This PC' > Properties > Advanced System Settings\n"
                "   - Click 'Environment Variables'\n"
                "   - Under 'System variables', find 'Path' and click Edit\n"
                "   - Add a new entry with the path to the FFmpeg 'bin' folder\n"
                "4. Restart this application\n\n"
                "Alternatively, you can place ffmpeg.exe in the same folder as this script."
            )
        except Exception as e:
            self.root.after(0, self._show_error, "Export Failed", f"Error: {str(e)}")

    def _show_error(self, title, message):
        """Show error message safely from any thread."""
        messagebox.showerror(title, message)

    def _update_progress(self, pct):
        self.progress.config(value=pct)
        self.status_label.config(text=f"Exporting... {pct}%")

    def _export_done(self, path):
        self.export_btn.config(state=tk.NORMAL)
        self.progress.config(value=100)
        self.status_label.config(text="Export complete!")
        self.status_bar.config(text=f"Exported to: {path}")
        messagebox.showinfo("Success", f"Video exported!\\n\\n{path}")

    def _cleanup(self):
        if self.cap:
            self.cap.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = VideoEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app._cleanup)
    root.mainloop()


if __name__ == "__main__":
    main()
