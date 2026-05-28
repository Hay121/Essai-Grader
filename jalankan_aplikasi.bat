@echo off
cd /d "%~dp0"
echo ==============================================
echo Menjalankan EssayGrader System (Hybrid Edition)
echo ==============================================

echo [1/3] Menyiapkan Virtual Environment dan Dependensi...
cd engine

set VENV_PYTHON=
if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" (
    set VENV_PYTHON="%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
)

if not defined VENV_PYTHON (
    where py >nul 2>nul
    if not errorlevel 1 set VENV_PYTHON=py
)

if not defined VENV_PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 set VENV_PYTHON=python
)

if not defined VENV_PYTHON (
    echo [ERROR] Python tidak ditemukan! Pastikan Anda sudah menginstal Python dan mencentang "Add Python to PATH".
    pause
    exit /b 1
)

if not exist "..\.venv" (
    echo Membuat Virtual Environment baru menggunakan: %VENV_PYTHON%
    %VENV_PYTHON% -m venv "..\.venv"
)

set PYTHON_CMD=..\.venv\Scripts\python.exe


echo Menggunakan Python: %PYTHON_CMD%
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt

if errorlevel 1 (
    echo [PERINGATAN] Gagal menginstal beberapa dependensi.
    echo Sistem akan tetap berjalan menggunakan mode Fallback Lexical TF-IDF.
) else (
    echo [OK] Dependensi terinstal.
)
cd ..

echo [2/3] Menjalankan Backend (Mesin AI)...
start "" cmd /k "cd engine && title AI Backend Server && echo Memulai Server AI... && "%PYTHON_CMD%" main.py"

echo [3/3] Menjalankan Frontend (UI Web)...
start "" cmd /k "cd frontend && title Web Frontend && echo Memulai Server Frontend... && "%PYTHON_CMD%" -m http.server 3000"

echo.
echo [4/4] Menjalankan Ngrok (Jembatan Internet)...
start "" cmd /k "%USERPROFILE%\ngrok.exe http --url=kortney-hamulate-annamarie.ngrok-free.dev 8000"

echo.
echo Semua server dan koneksi Ngrok telah dijalankan di jendela terpisah!
echo Silakan buka browser Anda ke alamat: http://localhost:3000
echo ==============================================
