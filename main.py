"""
AccountMaster Sequence Resequencer
----------------------------------
Requirements:
    pip install pyodbc

Also install Microsoft ODBC Driver 17 or 18 for SQL Server.

Features:
- SQL Server connection using Windows or SQL Server authentication.
- Select an accessible database.
- Enter account numbers (one per line).
- Assign consecutive SequenceNumber values starting from a chosen number.
- Preview the proposed resequencing.
- Update dbo.AccountMaster in one transaction.
- Roll back all changes if any account does not match exactly one row.

IMPORTANT:
- Test against a non-production database first.
- Confirm the selected server and database before executing.
- This application assumes the table is dbo.AccountMaster and the columns
  are AccountNumber and SequenceNumber.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import pyodbc

APP_TITLE = "AccountMaster Sequence Resequencer"


class AccountResequencer:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1080x750")
        self.root.minsize(850, 500)

        # Connection settings
        self.driver_var = tk.StringVar(value=self._default_driver())
        self.server_var = tk.StringVar(value="localhost")
        self.auth_var = tk.StringVar(value="Windows")
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.database_var = tk.StringVar()

        # Resequencing settings
        self.sequence_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value="Not connected")

        self._build_ui()
        self._toggle_auth_fields()

    @staticmethod
    def _default_driver():
        installed = list(pyodbc.drivers())
        preferred = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "SQL Server",
        ]
        for name in preferred:
            if name in installed:
                return name
        return installed[-1] if installed else ""

    def _build_ui(self):
        # Main scrollable container
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview
        )

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        outer = ttk.Frame(canvas, padding=12)

        canvas_window = canvas.create_window((0, 0), window=outer, anchor="nw")

        # Automatically adjust the scroll region when the outer frame changes size
        def update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def resize_inner_frame(event):
            canvas.itemconfig(canvas_window, width=event.width)

        outer.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", resize_inner_frame)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Linux mouse wheel support
        canvas.bind_all(
            "<Button-4>",
            lambda event: canvas.yview_scroll(-1, "units")
        )
        canvas.bind_all(
            "<Button-5>",
            lambda event: canvas.yview_scroll(1, "units")
        )

        # SQL Server connection
        connection_frame = ttk.LabelFrame(
            outer, text="1. SQL Server Connection", padding=10
        )
        connection_frame.pack(fill="x")

        ttk.Label(connection_frame, text="ODBC Driver").grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        self.driver_combo = ttk.Combobox(
            connection_frame,
            textvariable=self.driver_var,
            values=list(pyodbc.drivers()),
            state="readonly",
            width=32,
        )
        self.driver_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        ttk.Label(connection_frame, text="Server").grid(
            row=0, column=2, sticky="w", padx=4, pady=4
        )
        ttk.Entry(connection_frame, textvariable=self.server_var, width=28).grid(
            row=0, column=3, sticky="ew", padx=4, pady=4
        )

        ttk.Label(connection_frame, text="Authentication").grid(
            row=1, column=0, sticky="w", padx=4, pady=4
        )
        self.auth_combo = ttk.Combobox(
            connection_frame,
            textvariable=self.auth_var,
            values=["Windows", "SQL Server"],
            state="readonly",
            width=18,
        )
        self.auth_combo.grid(row=1, column=1, sticky="w", padx=4, pady=4)
        self.auth_combo.bind("<<ComboboxSelected>>", self._toggle_auth_fields)

        ttk.Label(connection_frame, text="Username").grid(
            row=1, column=2, sticky="w", padx=4, pady=4
        )
        self.username_entry = ttk.Entry(
            connection_frame, textvariable=self.username_var, width=28
        )
        self.username_entry.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        ttk.Label(connection_frame, text="Password").grid(
            row=2, column=2, sticky="w", padx=4, pady=4
        )
        self.password_entry = ttk.Entry(
            connection_frame,
            textvariable=self.password_var,
            show="*",
            width=28,
        )
        self.password_entry.grid(row=2, column=3, sticky="ew", padx=4, pady=4)

        ttk.Button(
            connection_frame,
            text="Connect / Load Databases",
            command=self.connect_server,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=6)

        ttk.Button(
            connection_frame,
            text="Test Selected Database",
            command=self.test_database_connection,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        connection_frame.columnconfigure(1, weight=1)
        connection_frame.columnconfigure(3, weight=1)

        # Database selection
        database_frame = ttk.LabelFrame(outer, text="2. Target Database", padding=10)
        database_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(database_frame, text="Database").grid(
            row=0, column=0, sticky="w", padx=4, pady=4
        )
        self.database_combo = ttk.Combobox(
            database_frame,
            textvariable=self.database_var,
            state="readonly",
            width=45,
        )
        self.database_combo.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        database_frame.columnconfigure(1, weight=1)

        # Stored Procedure Button
        ttk.Button(
            outer,
            text="OPEN RE-SEQUNCING ROUTE",
            command=self.open_procedure_window
        ).pack(anchor="w", pady=(10, 0))
        # End of Stored Procedure Button

        # Accounts and starting sequence
        input_frame = ttk.LabelFrame(
            outer, text="3. Accounts and Starting Sequence", padding=10
        )
        input_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Prefix field
        self.prefix_var = tk.StringVar()
        prefix_frame = ttk.LabelFrame(input_frame, text="Optional Prefix", padding=10)
        prefix_frame.pack(side="top", fill="x", pady=(0, 8))

        ttk.Label(prefix_frame, text="Account Prefix:").pack(side="left", padx=(0, 8))
        ttk.Entry(prefix_frame, textvariable=self.prefix_var, width=15).pack(side="left")
        ttk.Label(
            prefix_frame,
            text=" (If set, this will be prepended to all account numbers below)"
        ).pack(side="left", padx=8)

        ttk.Label(
            input_frame,
            text="Enter AccountNumber values (one account per line):",
        ).pack(anchor="w")

        self.accounts_text = tk.Text(input_frame, height=10, wrap="none", undo=True)
        self.accounts_text.pack(fill="both", expand=True, pady=(5, 8))

        def apply_prefix():
            prefix = self.prefix_var.get().strip()
            if not prefix:
                return

            raw_content = self.accounts_text.get("1.0", "end-1c")
            if not raw_content.strip():
                return

            lines = raw_content.splitlines()
            prefixed_lines = [f"{prefix}{line.strip()}" for line in lines if line.strip()]

            self.accounts_text.delete("1.0", "end")
            self.accounts_text.insert("1.0", "\n".join(prefixed_lines))

        ttk.Button(
            prefix_frame,
            text="Apply Prefix to List",
            command=apply_prefix
        ).pack(side="left", padx=8)

        sequence_row = ttk.Frame(input_frame)
        sequence_row.pack(fill="x")

        ttk.Label(sequence_row, text="Starting sequence:").pack(
            side="left", padx=(0, 8)
        )
        ttk.Entry(sequence_row, textvariable=self.sequence_var, width=15).pack(
            side="left"
        )

        ttk.Label(
            sequence_row,
            text="Sequence numbers will increase by 1 for each account.",
        ).pack(side="left", padx=12)

        # Preview and actions
        action_frame = ttk.LabelFrame(outer, text="4. Preview and Execute", padding=10)
        action_frame.pack(fill="both", expand=True, pady=(10, 0))

        columns = ("account", "sequence")
        self.preview = ttk.Treeview(
            action_frame, columns=columns, show="headings", height=8
        )
        self.preview.heading("account", text="Account Number")
        self.preview.heading("sequence", text="New Sequence Number")
        self.preview.column("account", width=350, anchor="w")
        self.preview.column("sequence", width=220, anchor="center")
        self.preview.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            action_frame, orient="vertical", command=self.preview.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.preview.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(10, 0))

        ttk.Button(
            buttons, text="Preview Resequencing", command=self.preview_updates
        ).pack(side="left")

        ttk.Button(buttons, text="Clear Accounts", command=self.clear_accounts).pack(
            side="left", padx=8
        )

        ttk.Button(buttons, text="EXECUTE UPDATE", command=self.execute_manual).pack(
            side="right"
        )

        ttk.Label(
            outer, textvariable=self.status_var, relief="sunken", anchor="w"
        ).pack(fill="x", pady=(8, 0))

    def open_procedure_window(self):
        window = tk.Toplevel(self.root)
        window.title("Re-Sequencing Route")
        window.geometry("400x230")
        window.resizable(False, False)

        window.transient(self.root)
        window.grab_set()

        route_var = tk.StringVar()
        start_value_var = tk.StringVar(value="20")
        interval_var = tk.StringVar(value="20")

        frame = ttk.LabelFrame(window, text="Procedure Parameters", padding=15)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(frame, text="Route:").grid(row=0, column=0, sticky="w", padx=5, pady=8)
        ttk.Entry(frame, textvariable=route_var, width=25).grid(row=0, column=1, sticky="w", padx=5, pady=8)

        ttk.Label(frame, text="Start Value:").grid(row=1, column=0, sticky="w", padx=5, pady=8)
        ttk.Entry(frame, textvariable=start_value_var, width=25).grid(row=1, column=1, sticky="w", padx=5, pady=8)

        ttk.Label(frame, text="Interval:").grid(row=2, column=0, sticky="w", padx=5, pady=8)
        ttk.Entry(frame, textvariable=interval_var, width=25).grid(row=2, column=1, sticky="w", padx=5, pady=8)

        ttk.Button(frame, text="Execute Procedure", command=lambda: self.execute_procedure(route_var.get(), start_value_var.get(), interval_var.get())).grid(row=3, column=0, columnspan=2, pady=15)

    def _toggle_auth_fields(self, _event=None):
        is_sql = self.auth_var.get() == "SQL Server"
        state = "normal" if is_sql else "disabled"
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)

    def _connection_string(self, database="master"):
        driver = self.driver_var.get().strip()
        server = self.server_var.get().strip()

        if not driver:
            raise ValueError(
                "No SQL Server ODBC driver was found. Install ODBC Driver 17 or 18."
            )
        if not server:
            raise ValueError("Enter the SQL Server name or IP address.")

        # ODBC connection-string values are enclosed in braces so that
        # semicolons and closing braces in values are handled safely.
        def odbc_value(value):
            return "{" + str(value).replace("}", "}}") + "}"

        parts = [
            f"DRIVER={odbc_value(driver)}",
            f"SERVER={odbc_value(server)}",
            f"DATABASE={odbc_value(database)}",
            "TrustServerCertificate=yes",
            "Connection Timeout=15",
        ]

        if self.auth_var.get() == "Windows":
            parts.append("Trusted_Connection=yes")
        else:
            username = self.username_var.get().strip()
            password = self.password_var.get()
            if not username:
                raise ValueError("Enter the SQL Server username.")
            parts.append(f"UID={odbc_value(username)}")
            parts.append(f"PWD={odbc_value(password)}")

        return ";".join(parts) + ";"

    def get_connection(self):
        database = self.database_var.get().strip()
        if not database:
            raise ValueError("Select a database first.")

        return pyodbc.connect(
            self._connection_string(database),
            autocommit=False,
        )

    def connect_server(self):
        conn = None
        try:
            conn = pyodbc.connect(
                self._connection_string("master"),
                autocommit=True,
            )
            cursor = conn.cursor()
            rows = cursor.execute(
                """
                SELECT name
                FROM sys.databases
                WHERE state_desc = 'ONLINE'
                  AND HAS_DBACCESS(name) = 1
                ORDER BY name
                """
            ).fetchall()

            databases = [row[0] for row in rows]
            self.database_combo["values"] = databases

            if not databases:
                raise RuntimeError(
                    "The login connected, but no accessible databases were found."
                )

            current = self.database_var.get()
            if current not in databases:
                self.database_var.set(databases[0])

            self.status_var.set(
                f"Connected to SQL Server. {len(databases)} accessible database(s)."
            )
            messagebox.showinfo(
                "Connected",
                f"Successfully connected to SQL Server.\n"
                f"Found {len(databases)} accessible database(s).\n\n"
                f"Selected database: {self.database_var.get()}",
            )

        except pyodbc.Error as exc:
            self.status_var.set("Connection failed.")
            messagebox.showerror("Connection Error", str(exc))
        finally:
            if conn:
                conn.close()

    def test_database_connection(self):
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT @@SERVERNAME, DB_NAME(), SUSER_SNAME()
                """
            )
            row = cursor.fetchone()
            if row:
                server, database, login = row
            else:
                server, database, login = "Unknown", "Unknown", "Unknown"

            self.status_var.set(f"Connected: {server} | {database} | {login}")
            messagebox.showinfo(
                "Database Connection Verified",
                f"Server: {server}\nDatabase: {database}\nLogin: {login}",
            )
        except pyodbc.Error as exc:
            self.status_var.set("Database connection failed.")
            messagebox.showerror("Connection Error", str(exc))
        finally:
            if conn:
                conn.close()

    def get_accounts(self):
        raw_text = self.accounts_text.get("1.0", "end").strip()
        if not raw_text:
            raise ValueError("Enter at least one account number.")

        accounts = []
        for line_number, line in enumerate(raw_text.splitlines(), start=1):
            account = line.strip()
            if not account:
                continue
            accounts.append(account)

        if not accounts:
            raise ValueError("No valid account numbers were entered.")

        # Prevent accidental duplicate updates in the same run.
        seen = set()
        duplicates = []
        for account in accounts:
            if account in seen and account not in duplicates:
                duplicates.append(account)
            seen.add(account)

        if duplicates:
            messagebox.showerror(
                "Duplicate Accounts",
                "Duplicate account number(s) found:\n" + "\n".join(duplicates),
            )

        return accounts

    def _get_start_and_accounts(self):
        accounts = self.get_accounts()
        try:
            start = int(self.sequence_var.get().strip())
        except ValueError:
            raise ValueError("Starting sequence must be a whole number.")

        if start < 0:
            raise ValueError("Sequence cannot be negative.")

        return accounts, start

    def preview_updates(self):
        try:
            accounts, start = self._get_start_and_accounts()

            for item in self.preview.get_children():
                self.preview.delete(item)

            for index, account in enumerate(accounts):
                self.preview.insert(
                    "",
                    "end",
                    values=(account, start + index),
                )

            self.status_var.set(
                f"Preview ready: {len(accounts)} account(s), "
                f"sequence {start} through {start + len(accounts) - 1}."
            )
        except pyodbc.Error as exc:
            messagebox.showerror("Preview Error", str(exc))

    def clear_accounts(self):
        self.accounts_text.delete("1.0", "end")
        for item in self.preview.get_children():
            self.preview.delete(item)
        self.status_var.set("Account list cleared.")

    def execute_manual(self):
        conn = None
        try:
            accounts, start = self._get_start_and_accounts()
            end = start + len(accounts) - 1

            if not messagebox.askyesno(
                "Confirm Execution",
                f"Database: {self.database_var.get()}\n"
                f"Table: dbo.AccountMaster\n\n"
                f"Accounts to update: {len(accounts)}\n"
                f"Starting sequence: {start}\n"
                f"Ending sequence: {end}\n\n"
                "All updates will run in one transaction.\n"
                "If any account does not match exactly one row, "
                "the entire transaction will be rolled back.\n\n"
                "Continue?",
            ):
                return

            # Same connection approach as the working JSON importer.
            conn = self.get_connection()
            cursor = conn.cursor()

            # Identify the actual database connection.
            cursor.execute(
                """
                SELECT @@SERVERNAME, DB_NAME(), SUSER_SNAME()
                """
            )
            row = cursor.fetchone()
            if row:
                server, database, login = row
            else:
                server, database, login = "Unknown", "Unknown", "Unknown"

            results = []
            total_updated = 0

            for index, account in enumerate(accounts):
                sequence = start + index

                cursor.execute(
                    """
                    UPDATE dbo.AccountMaster
                    SET SequenceNumber = ?
                    WHERE AccountNumber = ?
                    """,
                    (sequence, account),
                )

                affected = cursor.rowcount

                if affected != 1:
                    raise RuntimeError(
                        f"Account: {account}\n"
                        f"Expected exactly 1 updated row, "
                        f"but SQL Server reported: {affected}\n\n"
                        "The transaction will be rolled back. "
                        "Check whether the account exists and is unique."
                    )

                total_updated += affected
                results.append(
                    f"Account: {account} | Sequence: {sequence} | Updated: {affected}"
                )

            conn.commit()

            report = (
                f"Server: {server}\n"
                f"Database: {database}\n"
                f"Login: {login}\n\n"
                f"Total accounts updated: {total_updated}\n\n" + "\n".join(results)
            )

            self.status_var.set(f"Successfully updated {total_updated} accounts.")

            messagebox.showinfo("Resequencing Successful", report)

        except pyodbc.Error as exc:
            if conn:
                try:
                    conn.rollback()
                except pyodbc.Error:
                    pass

            self.status_var.set("Execution failed. Database changes rolled back.")
            messagebox.showerror(
                "Execution Failed",
                f"Transaction rolled back.\n\n{exc}",
            )
        finally:
            if conn:
                conn.close()

    def execute_procedure(self, route, start_value, interval):
        conn = None
        try:
            if not route.strip():
                messagebox.showerror("Input Error", "Route cannot be empty.")
            start_value_int = int(start_value)
            interval_int = int(interval)

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                EXEC dbo.sp_ResequenceRoute @Route=?, @StartValue=?, @Interval=?
                """,
                (route, start_value_int, interval_int),
            )

            conn.commit()

            self.status_var.set(f"Stored procedure executed successfully for route '{route}'.")

            messagebox.showinfo(
                "Procedure Executed",
                f"Stored procedure executed successfully for route '{route}'."
            )

        except pyodbc.Error as exc:
            if conn:
                try:
                    conn.rollback()
                except pyodbc.Error:
                    messagebox.showerror(
                        "Rollback Failed",
                        "An error occurred while rolling back the transaction. "
                        "Please check the database state manually.")

            self.status_var.set("Procedure execution failed. Database changes rolled back.")
            messagebox.showerror(
                "Execution Failed",
                f"Transaction rolled back.\n\n{exc}",
            )
        finally:
            if conn:
                conn.close()


def main():
    root = tk.Tk()

    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except tk.TclError:
        pass

    AccountResequencer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
