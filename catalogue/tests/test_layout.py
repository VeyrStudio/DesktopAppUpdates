import os, sys, tempfile
os.environ['APPDATA'] = tempfile.mkdtemp(prefix='catalogue-layout-')
from catalogue import Catalogue, Scroller
app = Catalogue()
try:
    app.update_idletasks()
    content = app.content.winfo_children()[-1]
    scroll = next(w for w in content.winfo_children() if isinstance(w, Scroller))
    blocks = [w for w in scroll.inner.winfo_children() if w.winfo_class() == 'Frame']
    sizes = [(w.winfo_width(), w.winfo_height()) for w in blocks]
    print('Catalogue dashboard section geometry:', sizes, flush=True)
    assert len(blocks) >= 3, 'Main dashboard sections are missing'
    assert blocks[0].winfo_height() > 100, 'Dashboard summary cards collapsed'
    assert blocks[1].winfo_height() > 120, 'Breakdown and payday panels collapsed'
    assert blocks[2].winfo_height() > 100, 'Upcoming charges/subscriptions panels collapsed'
    print('PASS: dashboard summary, breakdown and lists have visible height', flush=True)
finally:
    app.destroy()
