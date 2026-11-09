// Pratinjau foto sebelum upload
document.querySelectorAll('input[type=file][data-preview]').forEach(inp => {
  inp.addEventListener('change', () => {
    const box = document.getElementById(inp.dataset.preview), f = inp.files[0];
    if (!box || !f) return;
    box.style.backgroundImage = `url(${URL.createObjectURL(f)})`;
    box.textContent = '';
  });
});
// Konfirmasi sebelum menghapus
document.querySelectorAll('form[data-confirm]').forEach(f =>
  f.addEventListener('submit', e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
// Pencarian produk di dashboard
const cari = document.getElementById('cari');
if (cari) cari.addEventListener('input', () => {
  const q = cari.value.toLowerCase();
  document.querySelectorAll('#list .row').forEach(r => r.style.display = r.dataset.nama.includes(q) ? '' : 'none');
});
