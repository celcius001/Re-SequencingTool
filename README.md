# RSTool

A Python Tkinter desktop application for managing and resequencing account numbers in Microsoft SQL Server.

The application allows users to connect to a SQL Server instance, select an accessible database, enter account numbers, apply an account prefix, preview new sequence assignments, and execute database updates safely within a transaction.

---

## Features

- **SQL Server Connection**
  - Supports Windows Authentication.
  - Supports SQL Server Authentication.
  - Automatically detects installed SQL Server ODBC drivers.
  - Loads accessible databases from the connected server.

- **Database Selection**
  - Select the target database.
  - Test the selected database connection before executing updates.
  - Display server, database, and login information.

- **Account Management**
  - Enter multiple account numbers (one per line).
  - Maximum of 19 accounts per operation.
  - Requires exactly 4 characters per account number.
  - Detects duplicate account numbers.

- **Account Prefix**
  - Apply a custom prefix to account numbers.
  - Requires exactly 6 characters.
  - Automatically applies the prefix during preview.
  - Original account entries remain unchanged.

- **Sequence Management**
  - Specify the starting sequence number.
  - Automatically assign consecutive sequence numbers.
  - Increment the sequence by 1 for every account.

- **Preview**
  - Review account numbers and their proposed sequence numbers before execution.
  - Prevent accidental updates by allowing verification before committing changes.

- **Manual Database Update**
  - Updates `dbo.AccountMaster`.
  - Uses parameterized SQL queries.
  - Executes all updates within one database transaction.
  - Automatically rolls back changes if an account does not match exactly one row.

- **Stored Procedure Execution**
  - Execute `dbo.sp_ResequenceRoute`.
  - Accepts Route, Start Value, and Interval parameters.

- **User Interface**
  - Tkinter-based desktop interface.
  - Scrollable application window.
  - Separate preview table.
  - Status messages and error dialogs.

---

## Requirements

### Software

- Windows 10 or Windows 11
- Python 3.9 or later
- Microsoft SQL Server
- Microsoft ODBC Driver 17 or 18 for SQL Server

### Python Dependency

```bash
pip install pyodbc
```

---

## Installation

### 1. Install Python

Download Python from:

https://www.python.org/downloads/

During installation, enable **Add Python to PATH**.

### 2. Install Microsoft ODBC Driver

Install either:

- Microsoft ODBC Driver 17 for SQL Server
- Microsoft ODBC Driver 18 for SQL Server

Official download:

https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 3. Install Python Dependencies

Open Command Prompt in the project directory.

```bash
pip install pyodbc
```

If using Pipenv:

```bash
pipenv install pyodbc
```

### 4. Run the Application

```bash
python main.py
```

If using Pipenv:

```bash
pipenv run python main.py
```

---

## Application Guide

### Step 1: Connect to SQL Server

Enter the following connection details:

| Field | Description |
|---|---|
| ODBC Driver | Installed SQL Server ODBC driver |
| Server | SQL Server hostname or IP address |
| Authentication | Windows or SQL Server |
| Username | SQL Server login username |
| Password | SQL Server login password |

Click **Connect / Load Databases**.

The application will retrieve accessible databases.

### Step 2: Select the Target Database

Choose the database where `dbo.AccountMaster` is located.

Click **Test Selected Database** to verify the connection.

Always confirm the selected server and database before proceeding.

### Step 3: Enter Account Numbers

Enter account numbers in the text area, one per line.

Example:

```text
1234
5678
9012
3456
```

**Input restrictions:**
- Maximum of 19 accounts.
- Each account number must contain exactly 4 characters.
- Duplicate account numbers are not allowed.

### Step 4: Apply Account Prefix

Enter a 6-character prefix in the **Account Prefix** field.

Example:

```text
ABCDEF
```

The application automatically prepends the prefix when generating the preview.

Example:

| Original Account | Prefixed Account |
|---|---|
| 1234 | ABCDEF1234 |
| 5678 | ABCDEF5678 |
| 9012 | ABCDEF9012 |

The original account list is not modified.

### Step 5: Set Starting Sequence

Enter the starting sequence number.

Example:

```text
100
```

The application automatically increments the sequence number by 1 for each account.

### Step 6: Preview Resequencing

Click **Preview Resequencing**.

Example preview:

| Account Number | New Sequence Number |
|---|---:|
| ABCDEF1234 | 100 |
| ABCDEF5678 | 101 |
| ABCDEF9012 | 102 |
| ABCDEF3456 | 103 |

Review all account numbers and sequence assignments before proceeding.

### Step 7: Execute Update

Click **EXECUTE UPDATE**.

The application will display a confirmation dialog containing the target database and the number of accounts to update.

Confirm the operation to proceed.

All updates are executed in a single transaction.

---

## Stored Procedure: Route Resequencing

The application also provides a separate stored procedure execution window.

Click **OPEN RE-SEQUNCING ROUTE**.

Enter the following parameters:

| Parameter | Description |
|---|---|
| Route | Target route |
| Start Value | Starting sequence value |
| Interval | Sequence increment interval |

The application executes:

```sql
EXEC dbo.sp_ResequenceRoute
    @Route = ?,
    @StartValue = ?,
    @Interval = ?;
```

The stored procedure must already exist in the selected database.

---

## Database Requirements

### Target Table

The application expects the following SQL Server table:

**dbo.AccountMaster**

| Column | Expected Usage |
|---|---|
| AccountNumber | Account identifier |
| SequenceNumber | Sequence number to update |

### Manual Update Query

The application executes the following parameterized SQL statement:

```sql
UPDATE dbo.AccountMaster
SET SequenceNumber = ?
WHERE AccountNumber = ?;
```

Each account must match exactly one row.

---

## Transaction Safety

Database updates are performed using a single transaction.

The application checks the affected row count for every account.

| Condition | Result |
|---|---|
| Exactly 1 row updated | Continue |
| No matching account | Rollback |
| Multiple matching accounts | Rollback |
| SQL execution error | Rollback |
| All accounts successfully updated | Commit |

**Important:** If any account fails validation during database execution, all changes made in that transaction are rolled back.

---

## Building a Windows Executable

The application can be packaged into a standalone Windows executable using PyInstaller.

Install PyInstaller:

```bash
pip install pyinstaller
```

Build the executable:

```bash
pyinstaller --onefile --windowed --name RSTool main.py
```

The generated executable will be located in:

```text
dist/AccountMaster_Resequencer.exe
```

The target computer must still have a compatible Microsoft SQL Server ODBC driver installed.

---

## Troubleshooting

### ModuleNotFoundError: No module named 'pyodbc'

Install the missing dependency:

```bash
pip install pyodbc
```

### No SQL Server ODBC Driver Found

Install Microsoft ODBC Driver 17 or 18.

Verify installed drivers:

```python
import pyodbc

print(pyodbc.drivers())
```

### SQL Server Connection Failed

Check the following:

- SQL Server hostname or IP address.
- SQL Server network accessibility.
- Firewall and SQL Server TCP/IP configuration.
- Authentication credentials.
- Database permissions.

### Account Does Not Match Exactly One Row

Verify that:

- The account number exists.
- The prefix is correct.
- The account number is unique.
- The selected database is correct.

---

## Important Notes

1. Always test the application against a development or test database first.
2. Verify the server and database before executing updates.
3. Confirm that the account prefix is correct.
4. Ensure that the SQL Server login has the necessary permissions.
5. Back up the database before performing production resequencing.
6. The application assumes that account numbers are unique in `dbo.AccountMaster`.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application programming language |
| Tkinter | Desktop graphical interface |
| PyODBC | SQL Server connectivity |
| Microsoft SQL Server | Database management |
| PyInstaller | Windows executable packaging |

---

## Project Structure

```text
RSTool/
│
├── main.py
├── README.md
├── requirements.txt
│
└── dist/
    └── RSTool.exe
```

### requirements.txt

```text
pyodbc
```

---

**AccountMaster Sequence Resequencer**

A desktop utility designed to simplify account resequencing, reduce manual encoding errors, and provide safer database update operations through transaction-based execution.
