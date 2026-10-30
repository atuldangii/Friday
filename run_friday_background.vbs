' FRIDAY AI - Silent Background Launcher
Set WshShell = CreateObject("WScript.Shell")
strPath = "C:\Users\atul.dangi\Desktop\Friday"
WshShell.CurrentDirectory = strPath
WshShell.Run Chr(34) & strPath & "\.venv\Scripts\pythonw.exe" & Chr(34) & " " & Chr(34) & strPath & "\friday.py" & Chr(34), 0, False

