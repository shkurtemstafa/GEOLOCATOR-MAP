"""
Test script to check if "Find Coordinates" button is visible
Run this to debug the visibility issue
"""
import tkinter as tk

root = tk.Tk()
root.title("Test Visibility")
root.geometry("500x300")

# Test if button appears
test_frame = tk.Frame(root, bg="white")
test_frame.pack(fill="both", expand=True, padx=10, pady=10)

test_label = tk.Label(test_frame, text="If you see this, the issue is with the scrollable frame", bg="yellow")
test_label.pack(pady=10)

test_button = tk.Button(test_frame, text="Find Coordinates TEST", bg="blue", fg="white", command=lambda: print("Button clicked!"))
test_button.pack(pady=10)

print("Test window opened. Check if button is visible.")
root.mainloop()

