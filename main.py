#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from app import GoogleSheetsSyncApp

def main():
    root = tk.Tk()
    app = GoogleSheetsSyncApp(root)
    app.run()

if __name__ == '__main__':
    main()