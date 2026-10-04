import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from bookflow import __version__
from bookflow.cli.commands import Args
from bookflow.pipeline import ConvertError, Result, convert

from .form import LANGUAGES, Form, FormError, default_output, to_args

# How often the window checks on a conversion running in the background, in ms.
POLL = 100

PAD = 8

# A message from the conversion thread: its progress, its result, or its error.
Message = tuple[str, str | Result | Exception]


class App(ttk.Frame):
    """One window: choose a PDF, optionally fill in the book's details, convert."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=2 * PAD)
        self.root = root
        self.messages: queue.Queue[Message] = queue.Queue()
        self.output: Path | None = None
        # The output follows the PDF until the user picks a place of their own.
        self.output_chosen = False

        self.pdf = tk.StringVar()
        self.save_as = tk.StringVar()
        self.book_title = tk.StringVar()
        self.author = tk.StringVar()
        self.language = tk.StringVar(value=next(iter(LANGUAGES)))
        self.pages = tk.StringVar()
        self.cover = tk.StringVar()
        self.status = tk.StringVar(value="Choose a PDF book to convert.")
        self.pdf.trace_add("write", lambda *_: self.follow_pdf())

        self.build()
        self.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

    # Layout

    def build(self) -> None:
        self.columnconfigure(1, weight=1)

        self.file_row(0, "PDF book", self.pdf, "Choose…", self.choose_pdf)
        self.file_row(1, "Save as", self.save_as, "Change…", self.choose_output)

        # The details line up with the rows above: labels, fields, buttons.
        details = ttk.LabelFrame(self, text="Book details (optional)", padding=PAD)
        details.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(PAD, 0))
        details.columnconfigure(1, weight=1)
        self.label(details, 0, "Title")
        ttk.Entry(details, textvariable=self.book_title).grid(
            row=0, column=1, columnspan=2, sticky="ew", pady=2
        )
        self.label(details, 1, "Author")
        ttk.Entry(details, textvariable=self.author).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=2
        )

        self.label(details, 2, "Language")
        ttk.Combobox(
            details, textvariable=self.language, values=list(LANGUAGES), state="readonly"
        ).grid(row=2, column=1, sticky="w", pady=2)

        self.label(details, 3, "Pages")
        pages = ttk.Frame(details)
        pages.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Entry(pages, textvariable=self.pages, width=16).grid(row=0, column=0)
        ttk.Label(pages, text="all, or e.g. 1-20, 35", style="Hint.TLabel").grid(
            row=0, column=1, padx=(PAD, 0)
        )

        self.label(details, 4, "Cover image")
        ttk.Entry(details, textvariable=self.cover).grid(row=4, column=1, sticky="ew", pady=2)
        ttk.Button(details, text="Choose…", command=self.choose_cover).grid(
            row=4, column=2, sticky="ew", padx=(PAD, 0), pady=2
        )
        ttk.Label(
            details, text="Used only when the PDF has no cover of its own.", style="Hint.TLabel"
        ).grid(row=5, column=1, columnspan=2, sticky="w")

        # Empty while idle; a moving block while converting.
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(2 * PAD, PAD))
        status = ttk.Label(self, textvariable=self.status, justify="left")
        status.grid(row=4, column=0, columnspan=3, sticky="ew")
        # Wrap at the window's width, whatever the screen's scaling.
        status.bind("<Configure>", lambda event: status.configure(wraplength=event.width))

        buttons = ttk.Frame(self)
        buttons.grid(row=5, column=0, columnspan=3, sticky="e", pady=(2 * PAD, 0))
        self.show_button = ttk.Button(
            buttons, text="Show in folder", command=self.show_output, state="disabled"
        )
        self.show_button.grid(row=0, column=0, padx=(0, PAD))
        self.convert_button = ttk.Button(buttons, text="Convert", command=self.start)
        self.convert_button.grid(row=0, column=1)

        ttk.Style(self).configure("Hint.TLabel", foreground="gray40")
        self.root.bind("<Return>", lambda _: self.start())

    def file_row(
        self, row: int, label: str, variable: tk.StringVar, button: str, command: Callable[[], None]
    ) -> None:
        self.label(self, row, label)
        ttk.Entry(self, textvariable=variable, width=50).grid(
            row=row, column=1, sticky="ew", pady=2
        )
        ttk.Button(self, text=button, command=command).grid(
            row=row, column=2, sticky="ew", padx=(PAD, 0), pady=2
        )

    @staticmethod
    def label(parent: tk.Misc, row: int, text: str) -> None:
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", padx=(0, PAD), pady=2)

    # Choosing files

    def choose_pdf(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a PDF book",
            filetypes=[("PDF books", "*.pdf"), ("All files", "*")],
        )
        if path:
            self.pdf.set(path)

    def choose_output(self) -> None:
        current = Path(self.save_as.get() or default_output(self.pdf.get()) or "book.epub")
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save the EPUB as",
            initialdir=str(current.parent),
            initialfile=current.name,
            defaultextension=".epub",
            filetypes=[("EPUB books", "*.epub")],
        )
        if path:
            self.output_chosen = True
            self.save_as.set(path)

    def choose_cover(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a cover image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif *.bmp"), ("All files", "*")],
        )
        if path:
            self.cover.set(path)

    def follow_pdf(self) -> None:
        if not self.output_chosen:
            self.save_as.set(default_output(self.pdf.get()))

    # Converting

    def form(self) -> Form:
        return Form(
            pdf=self.pdf.get(),
            output=self.save_as.get(),
            title=self.book_title.get(),
            author=self.author.get(),
            language=self.language.get(),
            pages=self.pages.get(),
            cover=self.cover.get(),
        )

    def start(self) -> None:
        if str(self.convert_button["state"]) == "disabled":
            return
        try:
            args = to_args(self.form())
        except FormError as e:
            messagebox.showwarning("Bookflow", str(e), parent=self.root)
            return

        self.convert_button["state"] = "disabled"
        self.show_button["state"] = "disabled"
        self.progress.configure(mode="indeterminate")
        self.progress.start()
        self.status.set("Starting…")
        # Conversion takes seconds; in a thread of its own the window stays responsive.
        threading.Thread(target=self.work, args=(args,), daemon=True).start()
        self.after(POLL, self.poll)

    def work(self, args: Args) -> None:
        """Runs in the conversion thread: it may only talk to the window through the queue."""
        try:
            result = convert(args, lambda step: self.messages.put(("progress", step)))
        except Exception as e:  # a bug too: say so rather than leave the window spinning
            self.messages.put(("error", e))
        else:
            self.messages.put(("done", result))

    def poll(self) -> None:
        while True:
            try:
                kind, value = self.messages.get_nowait()
            except queue.Empty:
                self.after(POLL, self.poll)
                return
            if kind == "progress":
                self.status.set(f"{value}…")
            elif kind == "done" and isinstance(value, Result):
                self.finish(value)
                return
            elif kind == "error" and isinstance(value, Exception):
                self.fail(value)
                return

    def finish(self, result: Result) -> None:
        self.stop()
        self.output = result.output
        self.show_button["state"] = "normal"
        self.status.set(
            f"Done: {result.output.name}\n{result.headings} headings, "
            f"{result.paragraphs} paragraphs, {result.notes} notes, {result.cover}."
        )

    def fail(self, error: Exception) -> None:
        self.stop()
        known = isinstance(error, ConvertError)
        message = str(error) if known else f"Something went wrong: {error!r}"
        self.status.set(f"Not converted: {message}")
        messagebox.showerror(
            "Bookflow", f"The book wasn't converted.\n\n{message}", parent=self.root
        )

    def stop(self) -> None:
        self.progress.stop()
        self.progress.configure(mode="determinate", value=0)
        self.convert_button["state"] = "normal"

    def show_output(self) -> None:
        if self.output is not None:
            show_in_folder(self.output)


def show_in_folder(path: Path) -> None:
    """Open the file manager at the folder holding the file."""
    folder = path.parent
    if sys.platform == "win32":
        os.startfile(folder)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])


def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError:
        # No screen, as over SSH: the command line still works.
        print("bookflow: no display to open the window on; use bookflow book.pdf", file=sys.stderr)
        return 1
    root.title(f"Bookflow {__version__}")
    root.minsize(520, 0)
    App(root)
    root.mainloop()
    return 0
