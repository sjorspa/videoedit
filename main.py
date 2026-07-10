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
import tempfile


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
        self.playback_thread = None

        # Selection state
        self.start_slider = 0.0  # seconds
        self.end_slider = 0.0  # seconds
        self.crop_x = 0
        self.crop_y = 0
        self.crop_width = 0
        self.crop_height = 0
        self.is_dragging = False
        self.drag_start = None
        self.drag_edge = None  # 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'

        # UI state
        self.video_image = None  # Keep reference to prevent garbage collection
        self.canvas_image = None
        self.preview_image = None

        # Export state
        self.is_exporting = False

        # Build UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Video preview
        left_panel = ttk.LabelFrame(main_frame, text="Video Preview")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Canvas for video display with crop box
        self.canvas = tk.Canvas(
            left_panel,
            bg="black",
            width=720,
            height=405,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Right panel - Controls
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))

        # Upload button
        upload_btn = ttk.Button(
            right_panel,
            text="📁 Upload Video",
            command=self._upload_video
        )
        upload_btn.pack(fill=tk.X, padx=5, pady=5)

        # Playback controls
        playback_frame = ttk.LabelFrame(right_panel, text="Playback")
        playback_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_frame = ttk.Frame(playback_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.play_btn = ttk.Button(btn_frame, text="▶ Play", command=self._toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(btn_frame, text="⏸ Pause", command=self._pause).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="⏹ Stop", command=self._stop).pack(side=tk.LEFT, padx=2)

        # Frame scrubber
        scrub_frame = ttk.Frame(playback_frame)
        scrub_frame.pack(fill=tk.X, pady=5)

        ttk.Label(scrub_frame, text="Frame:").pack(side=tk.LEFT, padx=(0, 5))
        self.frame_entry = ttk.Entry(scrub_frame, width=8)
        self.frame_entry.pack(side=tk.LEFT, padx=2)
        self.frame_entry.bind("<Return>", self._on_frame_change)

        ttk.Label(scrub_frame, text="/").pack(side=tk.LEFT, padx=2)
        ttk.Label(scrub_frame, textvariable=tk.StringVar()).pack(side=tk.LEFT)
        self.total_frames_label = ttk.Label(scrub_frame, text="0")
        self.total_frames_label.pack(side=tk.LEFT, padx=2)

        # Info label
        self.info_label = ttk.Label(playback_frame, text="No video loaded")
        self.info_label.pack(pady=5)

        # Timeline selection
        timeline_frame = ttk.LabelFrame(right_panel, text="Timeline Selection")
        timeline_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(timeline_frame, text="Start (s):").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.start_scale = ttk.Scale(
            timeline_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self._on_start_slider
        )
        self.start_scale.pack(fill=tk.X, padx=5, pady=2)
        self.start_value_label = ttk.Label(timeline_frame, text="0.0s")
        self.start_value_label.pack(anchor=tk.W, padx=5)

        ttk.Label(timeline_frame, text="End (s):").pack(anchor=tk.W, padx=5, pady=(5, 0))
        self.end_scale = ttk.Scale(
            timeline_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self._on_end_slider
        )
        self.end_scale.pack(fill=tk.X, padx=5, pady=2)
        self.end_value_label = ttk.Label(timeline_frame, text="0.0s")
        self.end_value_label.pack(anchor=tk.W, padx=5)

        # Crop box controls
        crop_frame = ttk.LabelFrame(right_panel, text="Crop Box")
        crop_frame.pack(fill=tk.X, padx=5, pady=5)

        self.crop_info_label = ttk.Label(crop_frame, text="Drag box on preview")
        self.crop_info_label.pack(pady=5)

        ttk.Button(
            crop_frame,
            text="Reset Crop",
            command=self._reset_crop
        ).pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(
            crop_frame,
            text="Fit to Video",
            command=self._fit_crop
        ).pack(fill=tk.X, padx=5, pady=2)

        # Export
        export_frame = ttk.LabelFrame(right_panel, text="Export")
        export_frame.pack(fill=tk.X, padx=5, pady=5)

        self.export_btn = ttk.Button(
            export_frame,
            text="💾 Export Video",
            command=self._export_video
        )
        self.export_btn.pack(fill=tk.X, padx=5, pady=5)

        self.progress = ttk.Progressbar(
            export_frame,
            orient=tk.HORIZONTAL,
            length=200,
            mode="determinate"
        )
        self.progress.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(export_frame, text="Ready")
        self.status_label.pack(pady=5)

        # Status bar at bottom
        self.status_bar = ttk.Label(
            self.root,
            text="Ready - Upload a video to start",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _upload_video(self):
        """Open file dialog to upload a video."""
        file_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
                ("All files", "*.*")
            ]
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

            # Set up sliders
            self.start_scale.config(to=self.duration)
            self.end_scale.config(to=self.duration)
            self.end_scale.set(1.0)  # Default to end

            self.start_slider = 0.0
            self.end_slider = self.duration

            self.total_frames_label.config(text=str(self.total_frames))
            self.info_label.config(text=f"{self.fps:.1f} FPS | {self.total_frames} frames | {self.duration:.1f}s")

            # Reset crop to full video
            self._fit_crop()

            # Load first frame for preview
            self._update_preview()

            self.status_bar.config(text=f"Loaded: {os.path.basename(self.video_path)}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video:\n{str(e)}")

    def _update_preview(self):
        """Update the canvas with the current frame."""
        if not self.cap:
            return

        # Seek to current frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()

        if not ret:
            return

        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Scale to fit canvas
        canvas_width = self.canvas.winfo_width() or 720
        canvas_height = self.canvas.winfo_height() or 405

        h, w = frame.shape[:2]
        scale = min(canvas_width / w, canvas_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        frame_resized = cv2.resize(frame, (new_w, new_h))

        # Convert to PIL Image
        self.preview_image = Image.fromarray(frame_resized)

        # Draw crop box overlay
        self._draw_crop_box()

        # Convert to PhotoImage
        self.video_image = ImageTk.PhotoImage(self.preview_image)
        self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.video_image,
            anchor=tk.CENTER
        )

    def _draw_crop_box(self):
        """Draw the crop box overlay on the preview image."""
        if not self.preview_image:
            return

        canvas_width = self.canvas.winfo_width() or 720
        canvas_height = self.canvas.winfo_height() or 405

        # Redraw the image
        self.preview_image = Image.fromarray(
            cv2.cvtColor(
                cv2.resize(
                    cv2.imread(self.video_path),
                    (canvas_width, canvas_height)
                ) if False else None,
                cv2.COLOR_BGR2RGB
            )
        ) if False else Image.fromarray(
            np.array(self.preview_image)
        )

        # Draw semi-transparent overlay
        from PIL import ImageDraw
        draw = ImageDraw.Draw(self.preview_image)

        # Convert crop coordinates to canvas coordinates
        canvas_w = canvas_width
        canvas_h = canvas_height

        # Get video dimensions
        if self.cap:
            video_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            video_w, video_h = 1920, 1080

        scale_x = canvas_w / video_w
        scale_y = canvas_h / video_h

        # Draw dark overlay outside crop area
        draw.rectangle([0, 0, canvas_w, self.crop_y * scale_y], fill="gray", width=0)
        draw.rectangle([0, self.crop_y * scale_y, canvas_w, canvas_h], fill="gray", width=0)
        draw.rectangle([0, 0, self.crop_x * scale_x, canvas_h], fill="gray", width=0)
        draw.rectangle([self.crop_x * scale_x, 0, canvas_w, canvas_h], fill="gray", width=0)

        # Draw crop box border
        box_x = self.crop_x * scale_x
        box_y = self.crop_y * scale_y
        box_w = self.crop_width * scale_x
        box_h = self.crop_height * scale_y

        draw.rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            outline="red",
            width=3
        )

        # Draw corner handles
        handle_size = 8
        corners = [
            (box_x, box_y),
            (box_x + box_w, box_y),
            (box_x, box_y + box_h),
            (box_x + box_w, box_y + box_h)
        ]
        for cx, cy in corners:
            draw.rectangle(
                [cx - handle_size, cy - handle_size, cx + handle_size, cy + handle_size],
                fill="red"
            )

        # Draw edge handles
        edge_centers = [
            (box_x + box_w // 2, box_y),  # top
            (box_x + box_w // 2, box_y + box_h),  # bottom
            (box_x, box_y + box_h // 2),  # left
            (box_x + box_w, box_y + box_h // 2),  # right
        ]
        for ex, ey in edge_centers:
            draw.ellipse(
                [ex - 5, ey - 5, ex + 5, ey + 5],
                fill="white",
                outline="red"
            )

    def _on_canvas_click(self, event):
        """Handle mouse click on canvas to detect crop box interaction."""
        if not self.cap:
            return

        x, y = event.x, event.y

        # Check if click is on a handle or edge
        canvas_w = self.canvas.winfo_width() or 720
        canvas_h = self.canvas.winfo_height() or 405

        if self.cap:
            video_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            video_w, video_h = 1920, 1080

        scale_x = canvas_w / video_w
        scale_y = canvas_h / video_h

        box_x = self.crop_x * scale_x
        box_y = self.crop_y * scale_y
        box_w = self.crop_width * scale_x
        box_h = self.crop_height * scale_y

        # Check corners (larger hit area)
        handle_threshold = 15
        corners = [
            ('nw', box_x, box_y),
            ('se', box_x + box_w, box_y + box_h),
            ('ne', box_x + box_w, box_y),
            ('sw', box_x, box_y + box_h),
        ]

        for edge, ex, ey in corners:
            if abs(x - ex) < handle_threshold and abs(y - ey) < handle_threshold:
                self.is_dragging = True
                self.drag_edge = edge
                self.drag_start = (x, y)
                return

        # Check edges
        edge_threshold = 10
        edges = [
            ('n', box_x + box_w // 2, box_y),
            ('s', box_x + box_w // 2, box_y + box_h),
            ('e', box_x + box_w, box_y + box_h // 2),
            ('w', box_x, box_y + box_h // 2),
        ]

        for edge, ex, ey in edges:
            if edge in ('n', 's'):
                if abs(x - ex) < edge_threshold * 3 and abs(y - ey) < edge_threshold:
                    self.is_dragging = True
                    self.drag_edge = edge
                    self.drag_start = (x, y)
                    return
            else:
                if abs(x - ex) < edge_threshold and abs(y - ey) < edge_threshold * 3:
                    self.is_dragging = True
                    self.drag_edge = edge
                    self.drag_start = (x, y)
                    return

        # Check if inside box (for moving)
        if (box_x <= x <= box_x + box_w and
                box_y <= y <= box_y + box_h):
            self.is_dragging = True
            self.drag_edge = 'move'
            self.drag_start = (x, y)
            return

    def _on_canvas_drag(self, event):
        """Handle mouse drag to resize/move crop box."""
        if not self.is_dragging:
            return

        x, y = event.x, event.y
        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        if self.cap:
            video_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        else:
            return

        canvas_w = self.canvas.winfo_width() or 720
        canvas_h = self.canvas.winfo_height() or 405

        scale_x = video_w / canvas_w
        scale_y = video_h / canvas_h

        if self.drag_edge == 'move':
            # Move box
            new_x = self.crop_x + dx * scale_x
            new_y = self.crop_y + dy * scale_y
            # Clamp
            self.crop_x = max(0, min(new_x, video_w - self.crop_width))
            self.crop_y = max(0, min(new_y, video_h - self.crop_height))
        elif self.drag_edge == 'nw':
            new_x = self.crop_x + dx * scale_x
            new_y = self.crop_y + dy * scale_y
            new_w = self.crop_width - dx * scale_x
            new_h = self.crop_height - dy * scale_y
            if new_w > 20:
                self.crop_x = new_x
                self.crop_width = new_w
            if new_h > 20:
                self.crop_y = new_y
                self.crop_height = new_h
        elif self.drag_edge == 'se':
            new_w = self.crop_width + dx * scale_x
            new_h = self.crop_height + dy * scale_y
            if self.crop_x + new_w <= video_w and new_w > 20:
                self.crop_width = new_w
            if self.crop_y + new_h <= video_h and new_h > 20:
                self.crop_height = new_h
        elif self.drag_edge == 'ne':
            new_y = self.crop_y + dy * scale_y
            new_h = self.crop_height - dy * scale_y
            new_w = self.crop_width + dx * scale_x
            if new_h > 20:
                self.crop_y = new_y
                self.crop_height = new_h
            if self.crop_x + new_w <= video_w and new_w > 20:
                self.crop_width = new_w
        elif self.drag_edge == 'sw':
            new_x = self.crop_x + dx * scale_x
            new_w = self.crop_width - dx * scale_x
            new_h = self.crop_height + dy * scale_y
            if new_w > 20:
                self.crop_x = new_x
                self.crop_width = new_w
            if self.crop_y + new_h <= video_h and new_h > 20:
                self.crop_height = new_h
        elif self.drag_edge == 'n':
            new_y = self.crop_y + dy * scale_y
            new_h = self.crop_height - dy * scale_y
            if new_h > 20:
                self.crop_y = new_y
                self.crop_height = new_h
        elif self.drag_edge == 's':
            new_h = self.crop_height + dy * scale_y
            if self.crop_y + new_h <= video_h and new_h > 20:
                self.crop_height = new_h
        elif self.drag_edge == 'e':
            new_w = self.crop_width + dx * scale_x
            if self.crop_x + new_w <= video_w and new_w > 20:
                self.crop_width = new_w
        elif self.drag_edge == 'w':
            new_x = self.crop_x + dx * scale_x
            new_w = self.crop_width - dx * scale_x
            if new_w > 20:
                self.crop_x = new_x
                self.crop_width = new_w

        self.drag_start = (x, y)
        self._update_crop_info()
        self._redraw_canvas()

    def _on_canvas_release(self, event):
        """Handle mouse release."""
        self.is_dragging = False
        self.drag_edge = None

    def _update_crop_info(self):
        """Update the crop info label."""
        self.crop_info_label.config(
            text=f"X: {self.crop_x}, Y: {self.crop_y}\n"
                 f"Width: {self.crop_width}, Height: {self.crop_height}"
        )

    def _reset_crop(self):
        """Reset crop to full video."""
        if not self.cap:
            return
        video_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.crop_x = 0
        self.crop_y = 0
        self.crop_width = video_w
        self.crop_height = video_h
        self._update_crop_info()
        self._redraw_canvas()

    def _fit_crop(self):
        """Fit crop box to video dimensions."""
        self._reset_crop()

    def _redraw_canvas(self):
        """Redraw the canvas with current frame and crop box."""
        if not self.cap:
            return

        # Get current frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()

        if not ret:
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        canvas_width = self.canvas.winfo_width() or 720
        canvas_height = self.canvas.winfo_height() or 405

        h, w = frame.shape[:2]
        scale = min(canvas_width / w, canvas_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        frame_resized = cv2.resize(frame, (new_w, new_h))
        self.preview_image = Image.fromarray(frame_resized)

        # Draw crop box overlay
        from PIL import ImageDraw
        draw = ImageDraw.Draw(self.preview_image)

        canvas_w = canvas_width
        canvas_h = canvas_height

        video_w = w
        video_h = h

        scale_x = canvas_w / video_w
        scale_y = canvas_h / video_h

        # Dark overlay
        draw.rectangle([0, 0, canvas_w, int(self.crop_y * scale_y)], fill="gray", width=0)
        draw.rectangle([0, int(self.crop_y * scale_y), canvas_w, canvas_h], fill="gray", width=0)
        draw.rectangle([0, 0, int(self.crop_x * scale_x), canvas_h], fill="gray", width=0)
        draw.rectangle([int(self.crop_x * scale_x), 0, canvas_w, canvas_h], fill="gray", width=0)

        # Crop box
        box_x = int(self.crop_x * scale_x)
        box_y = int(self.crop_y * scale_y)
        box_w = int(self.crop_width * scale_x)
        box_h = int(self.crop_height * scale_y)

        draw.rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            outline="red",
            width=3
        )

        # Corner handles
        handle_size = 8
        corners = [
            (box_x, box_y),
            (box_x + box_w, box_y + box_h),
            (box_x + box_w, box_y),
            (box_x, box_y + box_h),
        ]
        for cx, cy in corners:
            draw.rectangle(
                [cx - handle_size, cy - handle_size, cx + handle_size, cy + handle_size],
                fill="red"
            )

        # Edge handles
        edge_centers = [
            (box_x + box_w // 2, box_y),
            (box_x + box_w // 2, box_y + box_h),
            (box_x, box_y + box_h // 2),
            (box_x + box_w, box_y + box_h // 2),
        ]
        for ex, ey in edge_centers:
            draw.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill="white", outline="red")

        self.video_image = ImageTk.PhotoImage(self.preview_image)

        # Clear and redraw
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.video_image,
            anchor=tk.CENTER
        )

    def _on_start_slider(self, value):
        """Handle start slider change."""
        self.start_slider = float(value)
        self.start_value_label.config(text=f"{self.start_slider:.2f}s")

        # Ensure start is before end
        if self.start_slider >= self.end_slider:
            self.start_slider = self.end_slider - 0.1
            if self.start_slider < 0:
                self.start_slider = 0
            self.start_scale.set(self.start_slider)
            self.start_value_label.config(text=f"{self.start_slider:.2f}s")

    def _on_end_slider(self, value):
        """Handle end slider change."""
        self.end_slider = float(value)
        self.end_value_label.config(text=f"{self.end_slider:.2f}s")

        # Ensure end is after start
        if self.end_slider <= self.start_slider:
            self.end_slider = self.start_slider + 0.1
            if self.end_slider > self.duration:
                self.end_slider = self.duration
            self.end_scale.set(self.end_slider)
            self.end_value_label.config(text=f"{self.end_slider:.2f}s")

    def _toggle_play(self):
        """Toggle play/pause."""
        if not self.cap:
            messagebox.showwarning("Warning", "Please upload a video first.")
            return

        if self.is_playing:
            self._pause()
        else:
            self._play()

    def _play(self):
        """Start playback."""
        if not self.cap:
            return

        self.is_playing = True
        self.play_btn.config(text="⏸ Pause")

        # Start playback thread
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()

    def _pause(self):
        """Pause playback."""
        self.is_playing = False
        self.play_btn.config(text="▶ Play")

    def _stop(self):
        """Stop playback and reset to beginning."""
        self.is_playing = False
        self.current_frame = 0
        self.play_btn.config(text="▶ Play")
        self._update_preview()
        self.frame_entry.delete(0, tk.END)
        self.frame_entry.insert(0, "0")

    def _playback_loop(self):
        """Playback loop running in a separate thread."""
        if not self.cap:
            return

        while self.is_playing:
            # Check if we've reached the end of the selection
            current_time = self.current_frame / self.fps
            if current_time >= self.end_slider:
                self.is_playing = False
                self.play_btn.config(text="▶ Play")
                break

            # Check if we're before the start (shouldn't happen normally)
            if current_time < self.start_slider and self.current_frame > 0:
                # Continue playing through the timeline
                pass

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
            ret, frame = self.cap.read()

            if not ret:
                break

            # Update UI in main thread
            self.root.after(0, self._update_ui_frame)
            self.current_frame += 1

            # Sleep to match FPS
            time.sleep(1.0 / self.fps)

        # Ensure final frame is shown
        self.root.after(0, self._update_preview)

    def _update_ui_frame(self):
        """Update UI with current frame (called from main thread)."""
        frame_time = self.current_frame / self.fps
        self.frame_entry.delete(0, tk.END)
        self.frame_entry.insert(0, str(self.current_frame))
        self._redraw_canvas()

    def _on_frame_change(self, event):
        """Handle frame entry change."""
        if not self.cap:
            return

        try:
            frame_num = int(self.frame_entry.get())
            if 0 <= frame_num < self.total_frames:
                self.current_frame = frame_num
                self._update_preview()
        except ValueError:
            pass

    def _export_video(self):
        """Export the selected portion of the video with crop box."""
        if not self.video_path:
            messagebox.showwarning("Warning", "Please upload a video first.")
            return

        if self.is_exporting:
            messagebox.showinfo("Info", "Export is already in progress.")
            return

        # Get output file path
        output_path = filedialog.asksaveasfilename(
            title="Save Video",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
            initialfile=os.path.splitext(os.path.basename(self.video_path))[0] + "_edited.mp4"
        )

        if not output_path:
            return

        # Start export in a thread
        self.is_exporting = True
        self.export_btn.config(state=tk.DISABLED)
        self.progress.config(value=0)
        self.status_label.config(text="Exporting...")

        export_thread = threading.Thread(
            target=self._export_thread,
            args=(output_path,),
            daemon=True
        )
        export_thread.start()

    def _export_thread(self, output_path):
        """Export video in a separate thread."""
        try:
            import subprocess

            start_time = self.start_slider
            end_time = self.end_slider
            duration = end_time - start_time

            if duration <= 0:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", "Invalid timeline selection."
                ))
                return

            # Input options
            input_args = [
                "-y",  # overwrite output
                "-ss", str(start_time),  # start time
                "-i", self.video_path,  # input file
                "-to", str(duration),  # duration
            ]

            # Crop filter
            crop_filter = (
                f"crop={self.crop_width}:{self.crop_height}:"
                f"{self.crop_x}:{self.crop_y}"
            )

            # Output args
            output_args = [
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",  # High quality (low CRF = high quality)
                "-pix_fmt", "yuv420p",
                "-an",  # No audio
                "-movflags", "+faststart",
                "-vf", crop_filter,
                output_path
            ]

            cmd = ["ffmpeg"] + input_args + output_args

            # Show progress
            self.root.after(0, lambda: self.status_label.config(text="Starting export..."))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor progress
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break

                # Try to parse progress
                if "time=" in line:
                    time_str = line.split("time=")[-1].split(" ")[0].strip()
                    try:
                        parts = time_str.split(":")
                        current_sec = (
                            int(parts[0]) * 3600 +
                            int(parts[1]) * 60 +
                            float(parts[2])
                        )
                        progress = min(int((current_sec / duration) * 100), 100)
                        self.root.after(0, lambda p=progress: self.progress.config(value=p))
                        self.root.after(0, lambda p=progress: self.status_label.config(text=f"Exporting... {p}%"))
                    except (ValueError, IndexError):
                        pass

            process.wait()

            if process.returncode == 0:
                self.root.after(0, lambda: self._export_complete(output_path))
            else:
                self.root.after(0, lambda: self._export_failed("FFmpeg error occurred"))

        except Exception as e:
            self.root.after(0, lambda: self._export_failed(str(e)))

    def _export_complete(self, output_path):
        """Handle successful export."""
        self.is_exporting = False
        self.export_btn.config(state=tk.NORMAL)
        self.progress.config(value=100)
        self.status_label.config(text="Export complete!")
        self.status_bar.config(text=f"Exported to: {output_path}")
        messagebox.showinfo("Success", f"Video exported successfully!\n\nSaved to:\n{output_path}")

    def _export_failed(self, error_msg):
        """Handle export failure."""
        self.is_exporting = False
        self.export_btn.config(state=tk.NORMAL)
        self.progress.config(value=0)
        self.status_label.config(text="Export failed")
        self.status_bar.config(text="Export failed")
        messagebox.showerror("Export Failed", f"Failed to export video:\n{error_msg}\n\nMake sure FFmpeg is installed and in your PATH.")

    def _cleanup(self):
        """Clean up resources."""
        if self.cap:
            self.cap.release()
        self.root.destroy()


def main():
    """Main entry point."""
    root = tk.Tk()
    app = VideoEditorApp(root)

    # Handle window close
    def on_closing():
        app._cleanup()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
