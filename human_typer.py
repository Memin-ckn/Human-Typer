"""
global_typing_simulator.py

A Tkinter GUI application that simulates human-like typing to ANY active window.
After clicking "Type", you have 5 seconds to click into your target text field.

Requirements:
    pip install pynput

Features:
 - Types to any active text field on your computer
 - Adjustable WPM, Typo Rate, Pause Frequency, and more
 - 5-second delay to switch windows after clicking "Type"
 - Emergency stop: Ctrl+Alt+D
 - Realistic pauses after sentences and paragraphs
 - Human-like typing with varied speeds, typos, and pauses
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import random
import string

try:
    from pynput.keyboard import Controller, Key
except ImportError:
    print("Error: pynput not installed. Run: pip install pynput")
    exit(1)


class GlobalTypingSimulator:
    def __init__(self, wpm_getter, typo_rate_getter, pause_freq_getter, 
                 sentence_pause_getter, paragraph_pause_getter, 
                 speed_variation_getter, mistake_correction_delay_getter,
                 root: tk.Tk, stop_callback=None):
        """
        Global typing simulator using pynput keyboard controller.
        Types to whatever window is currently active.
        """
        self.keyboard = Controller()
        self.get_wpm = wpm_getter
        self.get_typo_rate = typo_rate_getter
        self.get_pause_freq = pause_freq_getter
        self.get_sentence_pause = sentence_pause_getter
        self.get_paragraph_pause = paragraph_pause_getter
        self.get_speed_variation = speed_variation_getter
        self.get_mistake_correction_delay = mistake_correction_delay_getter
        self.root = root
        self._stop_event = threading.Event()
        self._thread = None
        self.stop_callback = stop_callback

    def start(self, full_text: str):
        """Starts the typing simulation in a background thread."""
        if self._thread and self._thread.is_alive():
            return  # already running
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, args=(full_text,), daemon=True)
        self._thread.start()

    def stop(self):
        """Requests the simulator stop."""
        self._stop_event.set()

    def _run(self, full_text: str):
        """
        Core simulator loop with 5-second countdown to switch windows.
        """
        # 5-second wait to allow user to switch to target window
        countdown = 5
        for i in range(countdown, 0, -1):
            if self._stop_event.is_set():
                self._on_finished()
                return
            self._schedule_status(f"Switch to target window! Starting in {i}s...")
            time.sleep(1)
        
        self._schedule_status("Typing...")
        time.sleep(0.2)  # small buffer

        # Split into lines first to preserve line breaks
        lines = full_text.split("\n")
        
        for line_idx, line in enumerate(lines):
            if self._stop_event.is_set():
                self._on_finished()
                return
            
            # Check if this is a paragraph break (empty line before this)
            is_paragraph_start = line_idx > 0 and lines[line_idx - 1].strip() == "" and line.strip() != ""
            
            # Add extra pause before new paragraph
            if is_paragraph_start:
                paragraph_pause = self.get_paragraph_pause()
                time.sleep(random.uniform(paragraph_pause * 0.8, paragraph_pause * 1.3))
            
            # Process each line as words
            words = line.split(" ") if line.strip() else [""]

            for w_idx, word in enumerate(words):
                if self._stop_event.is_set():
                    self._on_finished()
                    return

                # Skip empty words
                if not word:
                    continue

                # Calculate typing speed for this word
                wpm = max(1, self.get_wpm())
                base_cps = (wpm * 5) / 60.0  # characters per second
                speed_variation = self.get_speed_variation()
                word_speed_multiplier = random.uniform(1.0 - speed_variation, 1.0 + speed_variation)
                effective_cps = base_cps * word_speed_multiplier
                char_delay = 1.0 / effective_cps if effective_cps > 0 else 0.12

                # Type each character in the word
                for c_idx, ch in enumerate(word):
                    if self._stop_event.is_set():
                        self._on_finished()
                        return

                    # Decide if a typo occurs
                    typo_rate = self.get_typo_rate()
                    make_typo = random.random() < typo_rate

                    if make_typo and ch.isalpha():
                        # Type wrong character
                        wrong_char = self._choose_typo_char(ch)
                        self._type_char(wrong_char)
                        time.sleep(char_delay * random.uniform(0.8, 1.6))
                        
                        # Correction delay (noticing the mistake)
                        correction_delay = self.get_mistake_correction_delay()
                        time.sleep(correction_delay * random.uniform(0.8, 1.2))
                        
                        # Backspace
                        self.keyboard.press(Key.backspace)
                        self.keyboard.release(Key.backspace)
                        time.sleep(0.05 + random.random() * 0.12)

                    # Type correct character
                    self._type_char(ch)
                    jitter = random.uniform(-0.4, 0.6) * char_delay
                    sleep_time = max(0.01, char_delay + jitter)
                    time.sleep(sleep_time)

                # Space between words (unless last word in line)
                if w_idx < len(words) - 1:
                    if self._stop_event.is_set():
                        self._on_finished()
                        return
                    
                    self.keyboard.press(Key.space)
                    self.keyboard.release(Key.space)
                    
                    # Check for sentence-ending punctuation
                    last_char = word[-1] if word else ""
                    pause_prob = self.get_pause_freq()
                    
                    if last_char in ".!?":
                        # Longer pause after sentence
                        sentence_pause = self.get_sentence_pause()
                        pause_time = random.uniform(sentence_pause * 0.7, sentence_pause * 1.4)
                        time.sleep(pause_time)
                    elif last_char in ",;:":
                        # Medium pause after comma/semicolon
                        time.sleep(random.uniform(0.15, 0.45))
                    elif random.random() < pause_prob:
                        # Occasional thoughtful pause between words
                        time.sleep(random.uniform(0.2, 0.9))
                    else:
                        # Normal inter-word delay (short)
                        time.sleep(random.uniform(0.02, 0.12))
            
            # Press Enter at end of line (unless it's the last line)
            if line_idx < len(lines) - 1:
                if self._stop_event.is_set():
                    self._on_finished()
                    return
                
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
                
                # Extra pause if the next line is empty (paragraph break)
                if line_idx + 1 < len(lines) and lines[line_idx + 1].strip() == "":
                    time.sleep(random.uniform(0.1, 0.25))
                else:
                    time.sleep(random.uniform(0.05, 0.15))

        # Done typing
        self._schedule_status("Done!")
        self._on_finished()

    def _type_char(self, ch: str):
        """Type a single character using pynput."""
        try:
            self.keyboard.press(ch)
            self.keyboard.release(ch)
        except Exception as e:
            # Some special characters might fail; skip them
            pass

    def _choose_typo_char(self, correct_char: str):
        """Return a plausible wrong character."""
        if random.random() < 0.15:
            return correct_char.swapcase()
        if correct_char.lower() in "aeiou":
            return random.choice("aeiou")
        if correct_char.lower() in "bcdfghjklmnpqrstvwxyz":
            return random.choice("bcdfghjklmnpqrstvwxyz")
        return random.choice(string.ascii_letters)

    def _schedule_status(self, msg: str):
        """Update status in window title."""
        def do_status():
            try:
                self.root.title(f"Global Typing Simulator — {msg}")
            except tk.TclError:
                pass
        self.root.after(0, do_status)

    def _on_finished(self):
        """Called when typing finishes or stops."""
        if self.stop_callback:
            self.root.after(0, self.stop_callback)


def build_gui():
    root = tk.Tk()
    root.geometry("700x700")
    root.title("Global Typing Simulator")

    mainframe = ttk.Frame(root, padding="15")
    mainframe.pack(fill=tk.BOTH, expand=True)

    # Instructions
    instructions = ttk.Label(
        mainframe,
        text="This will type to ANY active window on your computer.\n"
             "After clicking 'Type', you have 5 seconds to click into your target text field!\n"
             "🚨 A PANIC STOP button will appear - click it with your mouse to stop! 🚨",
        justify=tk.CENTER,
        foreground="blue",
        font=("TkDefaultFont", 10, "bold")
    )
    instructions.pack(pady=(0, 15))

    # Source text input
    ttk.Label(mainframe, text="Text to type:", font=("TkDefaultFont", 10, "bold")).pack(anchor=tk.W)
    source_text = scrolledtext.ScrolledText(mainframe, wrap=tk.WORD, height=12)
    source_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=(4, 15))
    
    default_text = (
        "Hello! This is a demonstration of human-like typing.\n"
        "After you click Type, switch to any text field on your computer.\n\n"
        "The simulator will type there with realistic speed variations, "
        "occasional typos and corrections, and thoughtful pauses.\n\n"
        "Notice how it pauses after sentences and paragraphs!"
    )
    source_text.insert("1.0", default_text)

    # Controls frame with scrollbar for many parameters
    controls_container = ttk.Frame(mainframe)
    controls_container.pack(fill=tk.BOTH, expand=False, pady=(0, 10))
    
    # Canvas and scrollbar for controls
    canvas = tk.Canvas(controls_container, height=280)
    scrollbar = ttk.Scrollbar(controls_container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    controls_frame = ttk.LabelFrame(scrollable_frame, text="Typing Parameters", padding="10")
    controls_frame.pack(fill=tk.X, padx=5, pady=5)

    # Helper function to create parameter controls
    def create_param_control(parent, label_text, from_val, to_val, default_val, resolution=1, format_str="{:.0f}"):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=4)
        ttk.Label(frame, text=label_text).pack(side=tk.LEFT)
        val_label = ttk.Label(frame, text=format_str.format(default_val), width=10)
        val_label.pack(side=tk.RIGHT)

        def update_label(v):
            val_label.config(text=format_str.format(float(v)))

        scale = ttk.Scale(parent, from_=from_val, to=to_val, orient=tk.HORIZONTAL, command=update_label)
        scale.set(default_val)
        scale.pack(fill=tk.X, padx=2, pady=(0, 8))
        
        return scale, val_label

    # Core parameters
    wpm_scale, wpm_label = create_param_control(
        controls_frame, "Words Per Minute (WPM):", 10, 200, 60, format_str="{:.0f}"
    )

    typo_scale, typo_label = create_param_control(
        controls_frame, "Typo Rate (per character):", 0.0, 0.25, 0.03, format_str="{:.3f}"
    )

    pause_scale, pause_label = create_param_control(
        controls_frame, "Random Pause Frequency:", 0.0, 0.5, 0.08, format_str="{:.2f}"
    )

    # New parameters
    ttk.Separator(controls_frame, orient='horizontal').pack(fill='x', pady=10)
    ttk.Label(controls_frame, text="Realistic Pauses", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

    sentence_pause_scale, sentence_pause_label = create_param_control(
        controls_frame, "Sentence Pause (seconds):", 0.2, 3.0, 1.0, format_str="{:.1f}s"
    )

    paragraph_pause_scale, paragraph_pause_label = create_param_control(
        controls_frame, "Paragraph Pause (seconds):", 0.5, 5.0, 2.0, format_str="{:.1f}s"
    )

    ttk.Separator(controls_frame, orient='horizontal').pack(fill='x', pady=10)
    ttk.Label(controls_frame, text="Typing Behavior", font=("TkDefaultFont", 9, "bold")).pack(anchor=tk.W)

    speed_variation_scale, speed_variation_label = create_param_control(
        controls_frame, "Speed Variation (0=steady, 1=wild):", 0.0, 1.0, 0.4, format_str="{:.2f}"
    )

    mistake_delay_scale, mistake_delay_label = create_param_control(
        controls_frame, "Mistake Correction Delay (seconds):", 0.0, 2.0, 0.3, format_str="{:.2f}s"
    )

    # Buttons
    button_frame = ttk.Frame(mainframe)
    button_frame.pack(fill=tk.X, pady=(10, 0))

    type_button = ttk.Button(button_frame, text="Type (5s delay)")
    type_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

    stop_button = ttk.Button(button_frame, text="Stop", state=tk.DISABLED)
    stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Status
    status_label = ttk.Label(mainframe, text="Ready - Click 'Type' then switch to target window", 
                            anchor=tk.CENTER, relief=tk.SUNKEN, padding=5)
    status_label.pack(fill=tk.X, pady=(10, 0))

    # Getters
    def get_wpm():
        return int(float(wpm_scale.get()))

    def get_typo_rate():
        return float(typo_scale.get())

    def get_pause_freq():
        return float(pause_scale.get())
    
    def get_sentence_pause():
        return float(sentence_pause_scale.get())
    
    def get_paragraph_pause():
        return float(paragraph_pause_scale.get())
    
    def get_speed_variation():
        return float(speed_variation_scale.get())
    
    def get_mistake_correction_delay():
        return float(mistake_delay_scale.get())

    # Reset UI callback
    def on_finished_reset_ui():
        type_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        source_text.config(state=tk.NORMAL)
        wpm_scale.state(["!disabled"])
        typo_scale.state(["!disabled"])
        pause_scale.state(["!disabled"])
        sentence_pause_scale.state(["!disabled"])
        paragraph_pause_scale.state(["!disabled"])
        speed_variation_scale.state(["!disabled"])
        mistake_delay_scale.state(["!disabled"])
        status_label.config(text="Ready - Click 'Type' then switch to target window")
        root.title("Global Typing Simulator")
        # Close panic window if it exists
        if hasattr(root, 'panic_window') and root.panic_window:
            try:
                root.panic_window.destroy()
            except:
                pass
            root.panic_window = None

    # Create simulator
    simulator = GlobalTypingSimulator(
        wpm_getter=get_wpm,
        typo_rate_getter=get_typo_rate,
        pause_freq_getter=get_pause_freq,
        sentence_pause_getter=get_sentence_pause,
        paragraph_pause_getter=get_paragraph_pause,
        speed_variation_getter=get_speed_variation,
        mistake_correction_delay_getter=get_mistake_correction_delay,
        root=root,
        stop_callback=on_finished_reset_ui,
    )

    # Button handlers
    def start_typing():
        full_text = source_text.get("1.0", tk.END).rstrip("\n")
        if not full_text.strip():
            messagebox.showinfo("No text", "Please provide some text to type.")
            return
        
        # Disable controls
        type_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
        source_text.config(state=tk.DISABLED)
        wpm_scale.state(["disabled"])
        typo_scale.state(["disabled"])
        pause_scale.state(["disabled"])
        sentence_pause_scale.state(["disabled"])
        paragraph_pause_scale.state(["disabled"])
        speed_variation_scale.state(["disabled"])
        mistake_delay_scale.state(["disabled"])
        status_label.config(text="Switch to your target window NOW! (5 seconds...)")
        
        # Create always-on-top panic stop window
        create_panic_window()
        
        simulator.start(full_text)

    def stop_typing():
        stop_button.config(state=tk.DISABLED)
        simulator.stop()
        status_label.config(text="Stopping...")

    def create_panic_window():
        """Create a circular red STOP button that's always on top."""
        panic = tk.Toplevel(root)
        panic.title("STOP")
        panic.geometry("180x180")
        panic.attributes('-topmost', True)  # Always on top
        panic.resizable(False, False)
        panic.overrideredirect(True)  # Remove window decorations
        
        # Store reference so we can close it later
        root.panic_window = panic
        
        # Create canvas for circular button
        canvas = tk.Canvas(panic, width=180, height=180, bg='black', highlightthickness=0)
        canvas.pack()
        
        def panic_stop():
            simulator.stop()
            status_label.config(text="🚨 PANIC STOP ACTIVATED!")
        
        # Draw circular button
        circle = canvas.create_oval(10, 10, 170, 170, fill="#D32F2F", outline="#B71C1C", width=4)
        text = canvas.create_text(90, 90, text="STOP", fill="white", 
                                 font=("Arial", 32, "bold"))
        
        # Track if we're dragging or clicking
        panic.is_dragging = False
        panic.drag_start_x = 0
        panic.drag_start_y = 0
        
        # Hover effects
        def on_enter(event):
            canvas.itemconfig(circle, fill="#B71C1C")
        
        def on_leave(event):
            canvas.itemconfig(circle, fill="#D32F2F")
        
        def on_press(event):
            panic.is_dragging = False
            panic.drag_start_x = event.x
            panic.drag_start_y = event.y
            panic.press_x = event.x_root
            panic.press_y = event.y_root
        
        def on_motion(event):
            # If mouse moved more than 5 pixels, it's a drag
            if abs(event.x - panic.drag_start_x) > 5 or abs(event.y - panic.drag_start_y) > 5:
                panic.is_dragging = True
                deltax = event.x_root - panic.press_x
                deltay = event.y_root - panic.press_y
                x = panic.winfo_x() + deltax
                y = panic.winfo_y() + deltay
                panic.geometry(f"+{x}+{y}")
                panic.press_x = event.x_root
                panic.press_y = event.y_root
        
        def on_release(event):
            # Only trigger stop if we didn't drag
            if not panic.is_dragging:
                canvas.itemconfig(circle, fill="#8B0000")
                panic.after(100, panic_stop)
        
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_motion)
        canvas.bind("<ButtonRelease-1>", on_release)

    type_button.config(command=start_typing)
    stop_button.config(command=stop_typing)

    root.title("Global Typing Simulator — Ready")
    return root


if __name__ == "__main__":
    app = build_gui()
    app.mainloop()