using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace JarvisLauncher
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string venvPython = Path.Combine(baseDir, "jarvis_project", ".venv", "Scripts", "python.exe");
                string workingDir = Path.Combine(baseDir, "jarvis_project");

                if (!File.Exists(venvPython))
                {
                    MessageBox.Show(
                        "Could not find Python virtual environment at:\n" + venvPython,
                        "JARVIS Launcher Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = venvPython;
                psi.Arguments = "main.py --gui";
                psi.WorkingDirectory = workingDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Failed to start JARVIS:\n" + ex.Message,
                    "JARVIS Launcher Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }
}
