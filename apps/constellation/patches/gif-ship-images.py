from pathlib import Path

root = Path("apps/constellation")
app = root / "src" / "app.js"
css = root / "src" / "styles.css"
html = root / "src" / "index.html"

app_text = app.read_text(encoding="utf-8")
old = '''function cardHTML(x) {
  const cat = x.category === "platonic" ? "Platonic" : "Romantic";
  const artStyle = x.image ? `style="background-image:url('${x.image.replace(/'/g, "%27")}')"` : "";
  return `
    <article class="ship-card">
      <div class="card-art ${x.image ? "has-image" : ""}" ${artStyle}></div>
'''
new = '''function cardHTML(x) {
  const cat = x.category === "platonic" ? "Platonic" : "Romantic";
  const artHTML = x.image ? `<img class="card-art-image" src="${esc(x.image)}" alt="" />` : "";
  return `
    <article class="ship-card">
      <div class="card-art ${x.image ? "has-image" : ""}">${artHTML}</div>
'''
if old not in app_text:
    raise SystemExit("Could not find Constellation card image block to patch.")
app.write_text(app_text.replace(old, new, 1), encoding="utf-8")

css_text = css.read_text(encoding="utf-8")
needle = '''.card-art.has-image{
  background-size:cover!important;
  background-position:center!important;
}
.card-art.has-image:after{content:"";display:none}
'''
replacement = '''.card-art.has-image{
  background:none!important;
}
.card-art.has-image:after{content:"";display:none}
.card-art-image{
  width:100%;
  height:100%;
  display:block;
  object-fit:cover;
  object-position:center;
}
'''
if needle not in css_text:
    raise SystemExit("Could not find Constellation card image CSS to patch.")
css.write_text(css_text.replace(needle, replacement, 1), encoding="utf-8")

html_text = html.read_text(encoding="utf-8")
html_text = html_text.replace('id="editImage" type="file" accept="image/*"', 'id="editImage" type="file" accept="image/png,image/jpeg,image/webp,image/gif"', 1)
html.write_text(html_text, encoding="utf-8")

print("GIF ship-image support applied.")
