"""Dialog for entering and testing WooCommerce API credentials."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QThread
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .credential_store import save_credentials
from .woocommerce_client import WooCommerceClient
from .woocommerce_models import WooCredentials


class _TestConnectionWorker(QThread):
    """Background worker that tests a WooCommerce connection."""

    result = Signal(bool, str)  # (success, message)

    def __init__(self, client: WooCommerceClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            categories = self._client.get_categories()
            n = len(categories)
            self.result.emit(True, f"{n} categories found")
        except Exception as exc:
            self.result.emit(False, str(exc))


class CredentialsDialog(QDialog):
    """Dialog for configuring WooCommerce REST API credentials."""

    credentials_saved = Signal(WooCredentials)

    def __init__(self, credentials: WooCredentials, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("WooCommerce Credentials")
        self.setMinimumWidth(420)

        self._worker: _TestConnectionWorker | None = None

        # --- Fields ---
        self._url_edit = QLineEdit(credentials.store_url)
        self._url_edit.setPlaceholderText("https://mystore.com")

        self._key_edit = QLineEdit(credentials.consumer_key)
        self._key_edit.setPlaceholderText("ck_...")

        self._secret_edit = QLineEdit(credentials.consumer_secret)
        self._secret_edit.setPlaceholderText("cs_...")
        self._secret_edit.setEchoMode(QLineEdit.EchoMode.Password)

        # --- Form ---
        form = QFormLayout()
        form.addRow("Store URL", self._url_edit)
        form.addRow("Consumer Key", self._key_edit)
        form.addRow("Consumer Secret", self._secret_edit)

        # --- Buttons ---
        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._on_test)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._test_btn)
        btn_row.addStretch()
        btn_row.addWidget(button_box)

        # --- Main layout ---
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _current_credentials(self) -> WooCredentials:
        return WooCredentials(
            store_url=self._url_edit.text().strip(),
            consumer_key=self._key_edit.text().strip(),
            consumer_secret=self._secret_edit.text().strip(),
        )

    def _on_test(self) -> None:
        self._test_btn.setEnabled(False)
        client = WooCommerceClient(self._current_credentials())
        self._worker = _TestConnectionWorker(client, self)
        self._worker.result.connect(self._on_test_result)
        self._worker.start()

    def _on_test_result(self, success: bool, message: str) -> None:
        self._test_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Connection Test", f"\u2713 Connected \u2014 {message}")
        else:
            QMessageBox.warning(
                self,
                "Connection Test",
                f"\u2717 Connection failed \u2014 check your credentials and store URL",
            )

    def _on_save(self) -> None:
        url = self._url_edit.text().strip()
        if url and not url.startswith("https://"):
            result = QMessageBox.warning(
                self,
                "Insecure Connection",
                "The store URL does not use HTTPS. Your credentials will be sent "
                "unencrypted over the network.\n\nContinue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return
        credentials = self._current_credentials()
        save_credentials(credentials.consumer_key, credentials.consumer_secret)
        self.credentials_saved.emit(credentials)
        self.accept()
