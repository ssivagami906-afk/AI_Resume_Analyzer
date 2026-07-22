import os
import subprocess

vbs_script = r'''
Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
Set oShellLink = WshShell.CreateShortcut(strDesktop & "\AI Resume Analyzer.lnk")
oShellLink.TargetPath = "e:\siva project\AI_Resume_Analyzer\Launch_AI_Resume_Analyzer.bat"
oShellLink.WorkingDirectory = "e:\siva project\AI_Resume_Analyzer"
oShellLink.IconLocation = "e:\siva project\AI_Resume_Analyzer\app_icon.ico"
oShellLink.WindowStyle = 1
oShellLink.Description = "AI Resume Analyzer App"
oShellLink.Save
'''

vbs_file = os.path.join(os.path.dirname(__file__), "create_shortcut.vbs")
with open(vbs_file, "w") as f:
    f.write(vbs_script)

subprocess.run(["cscript", "//nologo", vbs_file], check=True)
if os.path.exists(vbs_file):
    os.remove(vbs_file)
print("Desktop shortcut successfully created!")
