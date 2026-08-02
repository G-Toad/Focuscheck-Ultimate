"""Website flags settings tab mixin."""

from tkinter import ttk, messagebox
from ..modern_widgets import InfoPanel, SectionHeader


class WebsiteFlagsTabMixin:
    """Mixin providing Website Flags tab for settings window."""

    def _create_website_flags_tab(self):
        tab = self._create_scrollable_tab(self.notebook, "Website Flags")

        InfoPanel(
            tab,
            "Flag high-risk domains (reddit.com, youtube.com, etc.). "
            "Version 2 uses these to trigger immediate sub-popups.",
            panel_type="info",
        ).pack(fill="x", pady=(0, 10))

        SectionHeader(tab, "Flagged Domains").pack(fill="x")

        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, pady=(4, 8))

        columns = ("enabled", "domain", "severity", "cooldown", "allow_once")
        self._website_flags_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=8,
        )
        self._website_flags_tree.heading("enabled", text="Enabled")
        self._website_flags_tree.heading("domain", text="Domain")
        self._website_flags_tree.heading("severity", text="Severity")
        self._website_flags_tree.heading("cooldown", text="Cooldown (min)")
        self._website_flags_tree.heading("allow_once", text="Allow Once")

        self._website_flags_tree.column("enabled", width=70, anchor="center")
        self._website_flags_tree.column("domain", width=180, anchor="w")
        self._website_flags_tree.column("severity", width=70, anchor="center")
        self._website_flags_tree.column("cooldown", width=110, anchor="center")
        self._website_flags_tree.column("allow_once", width=90, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._website_flags_tree.yview)
        self._website_flags_tree.configure(yscroll=scrollbar.set)

        self._website_flags_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        btns = ttk.Frame(tab)
        btns.pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Add", command=self._add_website_flag).pack(side="left")
        ttk.Button(btns, text="Edit", command=self._edit_website_flag).pack(side="left", padx=(6, 0))
        ttk.Button(btns, text="Delete", command=self._delete_website_flag).pack(side="left", padx=(6, 0))

        InfoPanel(
            tab,
            "Add: create a new flagged domain. Edit: change the selected row. "
            "Delete: remove the selected row.\n"
            "Enabled controls whether the rule is active. Allow Once lets you dismiss a flag one time before cooldown.",
            panel_type="info",
        ).pack(fill="x", pady=(4, 8))

        InfoPanel(
            tab,
            "Severity levels: 1 = warning only, 2 = warning + ask intervention, "
            "3 = immediate intervention. Cooldown prevents repeated prompts.",
            panel_type="info",
        ).pack(fill="x", pady=(8, 0))

        self._refresh_website_flags_tree()

    def _refresh_website_flags_tree(self):
        tree = getattr(self, "_website_flags_tree", None)
        if tree is None:
            return
        tree.delete(*tree.get_children())
        for idx, entry in enumerate(self.website_flags_list or []):
            enabled = "Yes" if entry.get("enabled", True) else "No"
            domain = entry.get("domain", "")
            severity = entry.get("severity", 1)
            cooldown = entry.get("cooldown_minutes", 5)
            allow_once = "Yes" if entry.get("allow_once", False) else "No"
            tree.insert("", "end", iid=str(idx), values=(enabled, domain, severity, cooldown, allow_once))

    def _get_selected_flag_index(self):
        tree = getattr(self, "_website_flags_tree", None)
        if tree is None:
            return None
        selection = tree.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except Exception:
            return None

    def _add_website_flag(self):
        from ..dialogs.website_flag_dialog import WebsiteFlagDialog

        def _on_save(payload):
            self.website_flags_list.append(payload)
            self._refresh_website_flags_tree()

        WebsiteFlagDialog(self, title="Add Website Flag", on_save=_on_save)

    def _edit_website_flag(self):
        idx = self._get_selected_flag_index()
        if idx is None:
            messagebox.showinfo("Select a row", "Please select a website flag to edit.")
            return
        from ..dialogs.website_flag_dialog import WebsiteFlagDialog

        initial = self.website_flags_list[idx]

        def _on_save(payload):
            self.website_flags_list[idx] = payload
            self._refresh_website_flags_tree()

        WebsiteFlagDialog(self, title="Edit Website Flag", initial=initial, on_save=_on_save)

    def _delete_website_flag(self):
        idx = self._get_selected_flag_index()
        if idx is None:
            messagebox.showinfo("Select a row", "Please select a website flag to delete.")
            return
        try:
            entry = self.website_flags_list[idx]
        except Exception:
            return
        confirm = messagebox.askyesno("Delete Flag", f"Remove flag for {entry.get('domain', '')}?")
        if not confirm:
            return
        try:
            del self.website_flags_list[idx]
        except Exception:
            pass
        self._refresh_website_flags_tree()


__all__ = ["WebsiteFlagsTabMixin"]
