import sys

from PySide6.QtWidgets import QApplication

from jarvis.ui.window import Window


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
