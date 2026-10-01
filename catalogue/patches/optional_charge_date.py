from pathlib import Path

source = Path(__file__).resolve().parents[1] / 'catalogue.py'
s = source.read_text(encoding='utf-8')
changes = [
    ("    def status(self,s,d=None):\n        d=d or self.period(s)\n        if s['state'] not in ('Active','Free trial'):return s['state']\n", "    def status(self,s,d=None):\n        d=d or self.period(s)\n        if s['state'] not in ('Active','Free trial'):return s['state']\n        if d is None:return 'No date set'\n"),
    ("        label=f'✓ Paid ({display(d)})' if paid else f'☐ Mark Paid ({display(d)})'\n        self.button(buttons,label,lambda:self.change_paid(s,d,not paid),filled=paid).pack(fill='x',pady=3)\n", "        if d is None:\n            self.button(buttons,'Set Charge Date',lambda:self.edit_subscription(s['id'])).pack(fill='x',pady=3)\n        else:\n            label=f'✓ Paid ({display(d)})' if paid else f'☐ Mark Paid ({display(d)})'\n            self.button(buttons,label,lambda:self.change_paid(s,d,not paid),filled=paid).pack(fill='x',pady=3)\n"),
    ("        charge=formline('First / anchor charge date (YYYY-MM-DD)',old['charge_anchor'] if old else TODAY().isoformat())\n", "        charge=formline('First / anchor charge date (YYYY-MM-DD) — optional',old['charge_anchor'] if old else '')\n"),
    ("        self.text(fields,'Example: enter the 14th to renew monthly on the 14th.',8,fg=MUTED).pack(anchor='w',pady=(3,0))\n", "        self.button(fields,'Clear Date',lambda:charge.set('')).pack(anchor='w',pady=(5,0))\n        self.text(fields,'Leave blank if the charge date is unknown. You can add it later.',8,fg=MUTED).pack(anchor='w',pady=(3,0))\n"),
    ("            if not d or (start.get().strip() and not sd) or not eff:\n", "            if (charge.get().strip() and not d) or (start.get().strip() and not sd) or not eff:\n"),
    ("charge_anchor=d.isoformat(),\n", "charge_anchor=d.isoformat() if d else '',\n"),
    ("        self.text(col,'Next Charge: '+display(future_occurrence(iso(s['charge_anchor']),s['cycle'],TODAY())),9).pack(anchor='w',pady=3)\n", "        next_charge=future_occurrence(iso(s['charge_anchor']),s['cycle'],TODAY())\n        self.text(col,'Next Charge: '+(display(next_charge) if next_charge else 'Not set'),9).pack(anchor='w',pady=3)\n"),
]
for old, new in changes:
    if s.count(old) != 1:
        raise SystemExit(f'Expected exactly one match, got {s.count(old)}: {old[:90]!r}')
    s = s.replace(old,new,1)
source.write_text(s,encoding='utf-8')
print('Applied optional charge dates to Catalogue')
