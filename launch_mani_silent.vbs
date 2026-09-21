Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
ScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = ScriptDir
WshShell.Run Chr(34) & ScriptDir & "\.venv\Scripts\pythonw.exe" & Chr(34) & " run_jarvis.py", 0, False
