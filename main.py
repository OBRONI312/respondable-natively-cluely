import sys
import os

# Ensure the core module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.app import LectureAssistantApp

def main():
    app = LectureAssistantApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()
