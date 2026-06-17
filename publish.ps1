param(
    [Parameter(Mandatory = $true, HelpMessage = "Target: 'test' for TestPyPI, 'prod' for PyPI")]
    [ValidateSet("test", "prod")]
    [string]$Target
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "pyproject.toml")) {
    Write-Error "Run this script from the repository root."
    exit 1
}

$VenvDir = ".venv"
$VenvCreated = $false

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..."
    python -m venv $VenvDir
    $VenvCreated = $true
}

$Python = Join-Path $VenvDir "Scripts\python.exe"
$Pip = Join-Path $VenvDir "Scripts\pip.exe"

Write-Host "Installing build dependencies..."
& $Pip install --quiet --upgrade pip
& $Pip install --quiet build twine

foreach ($dir in @("dist", "build")) {
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
}

Write-Host "Building distribution..."
& $Python -m build

Write-Host "Checking distribution..."
& $Python -m twine check "dist/*"

if ($Target -eq "test") {
    Write-Host "Uploading to TestPyPI..."
    & $Python -m twine upload --repository testpypi "dist/*"
} else {
    Write-Host "Uploading to PyPI..."
    & $Python -m twine upload "dist/*"
}

if ($VenvCreated) {
    Write-Host "Removing virtual environment..."
    Remove-Item -Recurse -Force $VenvDir
}

Write-Host "Done."
