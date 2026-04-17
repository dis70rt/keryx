from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from src.core.config import Settings


SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class SheetsManager:
    """Google Sheets handler with 3-tab append-only architecture."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            str(settings.google_sheets_cred_path), SCOPES
        )
        client = gspread.authorize(creds)
        self.spreadsheet = client.open(settings.target_sheet_name)

        self.targets_ws = self.spreadsheet.worksheet(settings.sheet_tab_targets)
        self.notes_ws = self.spreadsheet.worksheet(settings.sheet_tab_notes)
        self.dms_ws = self.spreadsheet.worksheet(settings.sheet_tab_dms)

    def fetch_pending_targets(self) -> list[dict[str, str]]:
        """Fetch rows from Targets sheet where Status is empty or 'Pending'."""
        all_records = self.targets_ws.get_all_records()
        return [
            row
            for row in all_records
            if str(row.get("Status", "")).strip() in ("", "Pending")
        ]

    def batch_update_results(
        self, results: list[dict[str, str]]
    ) -> None:
        """Batch-write generated messages to all 3 sheets.

        Each result dict must have: linkedin_url, name, connection_note,
        dm_message, char_count, word_count.
        """
        if not results:
            return

        targets_records = self.targets_ws.get_all_records()
        url_to_row: dict[str, int] = {}
        for idx, record in enumerate(targets_records):
            url_to_row[str(record.get("LinkedIn URL", "")).strip()] = idx + 2

        targets_batch: list[gspread.cell.Cell] = []
        notes_rows: list[list[str]] = []
        dms_rows: list[list[str]] = []

        for result in results:
            url = result["linkedin_url"]
            row_num = url_to_row.get(url)

            if row_num:
                targets_batch.append(
                    gspread.cell.Cell(row=row_num, col=4, value=result.get("status", "Done"))
                )
                processed_at = result.get("processed_at", "")
                targets_batch.append(
                    gspread.cell.Cell(row=row_num, col=5, value=processed_at)
                )

            notes_rows.append([
                url,
                result.get("name", ""),
                result.get("connection_note", ""),
                str(result.get("char_count", "")),
            ])

            dms_rows.append([
                url,
                result.get("name", ""),
                result.get("dm_message", ""),
                str(result.get("word_count", "")),
            ])

        if targets_batch:
            self.targets_ws.update_cells(targets_batch)

        if notes_rows:
            self.notes_ws.append_rows(notes_rows, value_input_option="RAW")

        if dms_rows:
            self.dms_ws.append_rows(dms_rows, value_input_option="RAW")
