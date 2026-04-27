# This script sets up the Python environment for CircuitTikZ Visualizer, including installing dependencies and checking LaTeX availability
# It should be run before running the project for the first time

$repoRoot = Split-Path -Parent $PSCommandPath
Push-Location $repoRoot

Write-Host "Setting up the Python environment for CircuitTikZ Visualizer...`n"

# Check if the latest version of uv is installed, if not install it
pip install --upgrade uv

# Create virtual environment and install dependencies
Write-Host "`nCreating virtual environment and installing dependencies..."
uv sync

# Check for pdflatex
Write-Host "`nChecking LaTeX installation..."
if (Get-Command pdflatex -ErrorAction SilentlyContinue) {
    Write-Host "pdflatex found: $($(Get-Command pdflatex).Source)"
} else {
    Write-Host "`nWARNING: pdflatex not found. Please install MiKTeX or TeX Live."
    Write-Host "  Windows (MiKTeX): winget install MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements"
    Write-Host "  Then install packages: miktex packages install circuitikz standalone siunitx"
}

Pop-Location

Write-Host "`nSetup complete. Activate the environment with: .\.venv\Scripts\Activate.ps1"
Write-Host "Run the app with: python main.py"
Write-Host "`nPress any key to exit."
[void][System.Console]::ReadKey()