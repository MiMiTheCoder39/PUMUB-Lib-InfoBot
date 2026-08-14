# Lib InfoBot — Windows/XAMPP Setup Guide

This archive contains the existing **PU Maubin Digital Library / Lib InfoBot** Flask application. It preserves the Flask + MySQL architecture, existing authentication, Book Search, Book Information, TF-IDF + Cosine Similarity recommendations, PDF workflows, and server-side AI services.

## Important DLL Error Diagnosis

If startup fails with:

```text
ImportError: DLL load failed while importing _mysql:
An Application Control policy has blocked this file.
```

this is a Windows execution-policy failure while importing the native `mysqlclient` extension used by `Flask-MySQLdb`. It is not an application-route, AI, PDF, search, or database-schema error. Installing the Python package successfully does not guarantee that Windows security policy will allow its native `_mysql` DLL to load.

Do not replace MySQL with SQLite and do not change the Flask-MySQLdb architecture. Ask the computer administrator to allow the signed/approved Python environment and the `mysqlclient` native extension under the organization's Application Control policy. Do not download or execute untrusted DLLs.

## Prerequisites

Install the following on Windows before running the project:

1. Python 3.11 or 3.12, preferably from the official Python installer, with **Add Python to PATH** enabled.
2. XAMPP with the existing MySQL/MariaDB service.
3. The existing `digital_library_db` database and the project's `library_db.sql` schema/seed data, if the database has not already been created.
4. Permission from the organization's Windows administrator for Python native extensions if Application Control blocks `_mysql`.

## Install and Run

Open PowerShell in the extracted project directory:

```powershell
py -3.12 -m venv myenv
.\myenv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy the non-secret environment template and edit only local values:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DB` to match the **existing XAMPP/MySQL installation**. Keep the OpenAI key server-side in `.env`; never put it in JavaScript or templates.

Start MySQL from the XAMPP Control Panel, then verify that the existing database is reachable. The application expects the default local configuration unless `.env` intentionally overrides it:

```text
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_DB=digital_library_db
```

Start Flask:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000/
```

## If PowerShell Blocks Script Activation

If PowerShell refuses to run `Activate.ps1`, use Command Prompt instead:

```bat
myenv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
```

Do not weaken system security policy globally just to activate a virtual environment.

## If `_mysql` Is Blocked by Application Control

The following error means the operating system blocked the native extension before Flask could start:

```text
Application Control policy has blocked this file
```

The safe resolution is administrative approval of the existing Python environment/native package. The project code should not be changed to bypass this policy. Verify the package in the activated environment with:

```powershell
python -c "import MySQLdb; print('MySQLdb import OK')"
```

If that command is blocked, stop and contact the system administrator. Do not copy random `_mysql.pyd` or DLL files into the virtual environment.

## Project Handle

The Manus project handle for this application is documented in `PROJECT_HANDLE.md`. It identifies the continuing project context only; it is not a password, API key, database credential, or runtime environment variable.

## Scope of This Archive

This archive does not change database schema, application credentials, or MySQL configuration. It adds documentation/setup guidance only. Existing AI, LibInfoBot, PDF, Book Search, recommendation, authentication, and authorization code remains unchanged by this setup guide.
