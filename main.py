import tkinter as tk
from tkinter import ttk
import sys

class SimpleRename:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Simple Rename")
        self.root.geometry("800x600")
        
        # Set up the main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.setup_ui()
    
    def setup_ui(self):
        # Placeholder for UI components
        title_label = ttk.Label(self.main_frame, text="Simple Rename")
        title_label.pack(pady=10)
    
    def run(self):
        self.root.mainloop()

def main():
    app = SimpleRename()
    app.run()

if __name__ == "__main__":
    main()
