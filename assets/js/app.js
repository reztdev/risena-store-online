/* Batikku – logika tampilan. Data produk ada di data/products.js (jangan edit produk di sini). */
const {wa:WA,banner:BANNER,produk:_PRODUK}=window.BATIKKU;
const PRODUK=_PRODUK.filter(p=>p.aktif!==false);
const MOTIF={kawung:['Kawung Sogan','#cdb594','#eadfcb'],parang:['Parang Indigo','#9fb0c6','#dde4ec'],mega:['Mega Mendung','#c9a39a','#efe0db'],truntum:['Truntum Sage','#a3b5a0','#e2e9df']};
const IC={bag:'<path d="M5 8h14l-1 12H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',wallet:'<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><circle cx="16.5" cy="14.5" r=".6"/>',pouch:'<path d="M4 10h16v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M4 10l2-4h12l2 4"/>',key:'<circle cx="8" cy="12" r="3.5"/><path d="M11.5 12H21M17 12v3M20 12v2"/>'};
const icon=(k,c='ic')=>`<svg class="${c}" viewBox="0 0 24 24">${IC[k]}</svg>`;
const P=PRODUK.map(x=>[x.id,x.nama,x.kategori,x.harga,x.ikon||'bag',x.deskripsi,x.tag||'',x.terjual||0,x.spesifikasi.join('\n'),x.foto||'',x.shopee||'',x.harga_coret||0,x.label_diskon||'']);
const TAGN={best:'Best Seller',hot:'Hot',trendy:'Trendy'};
/* harga coret & label diskon: p[11]=harga coret, p[12]=label manual (kosong = otomatis -%) */
const pct=p=>Math.round((p[11]-p[3])/p[11]*100),ada=p=>p[11]>p[3],h=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])),badge=p=>p[12]?h(p[12]):(ada(p)?'-'+pct(p)+'%':'');
const rp=n=>'Rp '+n.toLocaleString('id-ID');
/* tanda petik tunggal dipakai di url() agar aman di dalam atribut style="..." */
const encSvg=t=>encodeURIComponent(t).replace(/'/g,'%27').replace(/\(/g,'%28').replace(/\)/g,'%29');
const pat=m=>{const [,a,b]=MOTIF[m];let s;
 if(m=='kawung')s=`<circle cx="10" cy="20" r="8" fill="${a}"/><circle cx="30" cy="20" r="8" fill="${a}"/><circle cx="20" cy="10" r="8" fill="${a}" opacity=".6"/><circle cx="20" cy="30" r="8" fill="${a}" opacity=".6"/>`;
 else if(m=='parang')s=`<path d="M-5 25L25 -5M5 45L45 5M-5 45L5 35" stroke="${a}" stroke-width="5" fill="none"/>`;
 else if(m=='mega')s=`<path d="M0 30Q10 10 20 30T40 30M0 14Q10 -6 20 14T40 14" stroke="${a}" stroke-width="3.5" fill="none"/>`;
 else s=`<path d="M20 6L23 17L34 20L23 23L20 34L17 23L6 20L17 17Z" fill="${a}"/>`;
 return `url('data:image/svg+xml,${encSvg(`<svg xmlns='http://www.w3.org/2000/svg' width='100%' height='100%'><defs><pattern id='p' width='64' height='64' patternUnits='userSpaceOnUse' viewBox='0 0 40 40'><rect width='40' height='40' fill='${b}'/>${s}</pattern></defs><rect width='100%' height='100%' fill='url(#p)'/></svg>`)}')`};
const bg=(u,m)=>u?`url('${String(u).replace(/'/g,'%27')}')`:pat(m);
const $=s=>document.querySelector(s),MK=Object.keys(MOTIF),mo=p=>MK[P.indexOf(p)%4];
let cat='Semua',cart=[],sel=null,mot='kawung',si=0,timer;
const newOid=()=>{const d=new Date();return 'BTK-'+String(d.getDate()).padStart(2,'0')+String(d.getMonth()+1).padStart(2,'0')+'-'+Math.floor(1000+Math.random()*9000)};
let oid=newOid();
try{cart=JSON.parse(localStorage.getItem('bk')||'[]').filter(c=>P.some(p=>p[0]==c.id)&&MOTIF[c.m])}catch(e){}
const save=()=>{try{localStorage.setItem('bk',JSON.stringify(cart))}catch(e){}};
const card=p=>`<button class="card" data-p="${p[0]}">${badge(p)?`<em class="dsc">${badge(p)}</em>`:''}${p[6]?`<span class="tag">${TAGN[p[6]]}</span>`:''}<div class="img" style="background-image:${bg(p[9],mo(p))}">${p[9]?'':icon(p[4])}</div><small>${p[2]}</small><b>${p[1]}</b><span>${rp(p[3])}</span>${ada(p)?` <s class="cr">${rp(p[11])}</s>`:''}</button>`;
/* slider */
const SL=BANNER.map((b,i)=>[b.atas,b.judul,['kawung','mega','truntum'][i%3],['bag','wallet','pouch'][i%3],b.foto||'']);
$('#sl').innerHTML=SL.map(s=>`<div class="sd" style="background-image:${bg(s[4],s[2])}">${s[4]?'':icon(s[3],'big')}<div class="sc"><div class="eb">${s[0]}</div><h1>${s[1]}</h1><button class="btn w" data-g="shop">Shop</button></div></div>`).join('');
$('#dots').innerHTML=SL.map(()=>'<i></i>').join('');
const sl=$('#sl'),dots=[...document.querySelectorAll('#dots i')];
const setDot=()=>{si=Math.round(sl.scrollLeft/sl.clientWidth);dots.forEach((d,i)=>d.classList.toggle('on',i==si))};
sl.addEventListener('scroll',setDot);setDot();
const auto=()=>{clearInterval(timer);timer=setInterval(()=>{if(!$('#v-home').classList.contains('on'))return;sl.scrollTo({left:((si+1)%SL.length)*sl.clientWidth,behavior:'smooth'})},5000)};
sl.addEventListener('pointerdown',()=>clearInterval(timer));sl.addEventListener('pointerup',auto);auto();
/* home sections */
$('#hsecs').innerHTML=[['best','Best Seller'],['hot','Hot'],['trendy','Trendy']].map(([t,n])=>`<section class="hs"><div class="row"><h2>${n}</h2><button class="more" data-g="shop">Lihat semua</button></div><div class="grid">${P.filter(p=>p[6]==t).slice(0,4).map(card).join('')}</div></section>`).join('');
/* shop */
function tabs(){$('#tabs').innerHTML=['Semua',...new Set(P.map(p=>p[2]))].map(c=>`<button class="tab ${c==cat?'on':''}" data-c="${c}">${c}</button>`).join('')}
function list(){const q=$('#q').value.toLowerCase(),s=$('#so').value;let r=P.filter(p=>(cat=='Semua'||p[2]==cat)&&p[1].toLowerCase().includes(q));
 if(s=='lo')r.sort((a,b)=>a[3]-b[3]);if(s=='hi')r.sort((a,b)=>b[3]-a[3]);if(s=='best')r.sort((a,b)=>b[7]-a[7]);
 $('#grid').innerHTML=r.length?r.map(card).join(''):'<div class="empty">Produk tidak ditemukan</div>'}
/* detail */
function drawItem(){const p=sel;$('#dt').innerHTML=`<div class="img" style="background-image:${bg(p[9],mot)}">${p[9]?'':icon(p[4])}</div>
<div><small style="color:var(--mut);letter-spacing:.14em;text-transform:uppercase;font-size:11px">${p[2]}${p[6]?' · '+TAGN[p[6]]:''}</small><h1>${p[1]}</h1><div class="pr">${rp(p[3])}${ada(p)?` <s class="cr big">${rp(p[11])}</s>`:''}${badge(p)?` <em class="dsc in">${badge(p)}</em>`:''}</div><div class="sold">Terjual ${p[7]}+ pcs</div>
<div class="lbl">Deskripsi</div><p style="margin:0">${p[5]}</p>
<div class="lbl">Spesifikasi</div><table class="spec">${p[8].split('\n').filter(Boolean).map(r=>{const i=r.indexOf(':'),a=r.slice(0,i),b=r.slice(i+1).trim();return `<tr><td>${a}</td><td>${b}</td></tr>`}).join('')}</table>
<div class="lbl">Pilih motif</div><div class="opts">${MK.map(k=>`<button class="sw ${k==mot?'on':''}" data-m="${k}"><s style="background:${MOTIF[k][1]}"></s>${MOTIF[k][0]}</button>`).join('')}</div>
<div class="acts"><button class="btn full" id="add">Tambah ke Keranjang</button>${/^https?:\/\//.test(p[10])?`<a class="btn o full" target="_blank" rel="noopener noreferrer" href="${h(p[10])}">Beli di Shopee</a><p class="note" style="margin:2px 0 0;text-align:center">Pilih Shopee jika ingin COD, voucher, atau garansi platform.</p>`:''}</div></div>`}
/* routing */
function show(v){document.querySelectorAll('.v').forEach(e=>e.classList.toggle('on',e.id=='v-'+v));$('#n-home').classList.toggle('on',v=='home');$('#n-shop').classList.toggle('on',v=='shop');$('#b-home').classList.toggle('on',v=='home');$('#b-shop').classList.toggle('on',v=='shop');window.scrollTo(0,0)}
function route(){const h=location.hash.slice(1);
 if(h.startsWith('item-')){const p=P.find(x=>x[0]==h.slice(5));if(p){if(sel!=p){sel=p;mot=mo(p)}drawItem();return show('item')}}
 if(h=='shop'){tabs();list();return show('shop')}
 show('home');setDot()}
const go=h=>{location.hash=h;if(!h)history.replaceState(null,'',location.pathname);route()};
addEventListener('hashchange',route);
/* cart */
function renderCart(){const n=cart.reduce((a,c)=>a+c.q,0);$('#cn').textContent=n;$('#cn2').textContent=n;$('#cn2').style.display=n?'grid':'none';
 if(!cart.length){$('#ci').innerHTML='<p style="color:var(--mut);padding:40px 0;text-align:center">Keranjang masih kosong</p>';$('#cf').innerHTML='';return}
 $('#ci').innerHTML=cart.map((c,i)=>{const p=P.find(x=>x[0]==c.id);return `<div class="item row"><div class="row" style="justify-content:flex-start;align-items:flex-start"><div class="th" style="background-image:${bg(p[9],c.m)}"></div><div><div>${p[1]}</div><small style="color:var(--mut)">${MOTIF[c.m][0]} · ${rp(p[3])}</small><div class="qty"><button data-d="${i}" data-v="-1">−</button>${c.q}<button data-d="${i}" data-v="1">+</button></div></div></div><div>${rp(p[3]*c.q)}</div></div>`}).join('');
 const tot=cart.reduce((a,c)=>a+c.q*P.find(x=>x[0]==c.id)[3],0);
 $('#cf').innerHTML=`<div class="row" style="margin:20px 0 8px"><span class="lbl" style="margin:0">Total</span><h3 style="font-size:26px">${rp(tot)}</h3></div><input id="nm" placeholder="Nama penerima *" autocomplete="name"><textarea id="al" rows="2" placeholder="Alamat lengkap dan kota *" autocomplete="street-address"></textarea><div class="lbl" style="margin:18px 0 0">Metode pembayaran</div><select id="pm"><option>Transfer Bank</option><option>QRIS</option><option>Belum tahu, tanya admin</option></select><div class="flow"><div class="lbl" style="margin:14px 0 8px">Alur pembayaran · ${oid}</div><ol><li>Kirim pesanan lewat WhatsApp dengan ID di atas.</li><li>Admin konfirmasi stok dan ongkir, lalu kirim instruksi bayar lewat chat.</li><li>Bayar dengan kode unik, maksimal 24 jam.</li><li>Setelah dana terverifikasi, pesanan diproses dan resi dikirim via WhatsApp.</li></ol><p class="note">Nomor rekening dan QRIS hanya dikirim lewat chat resmi, tidak dipajang di website.</p></div><p class="err" id="werr" role="alert"></p><a class="btn full" id="wa" target="_blank" rel="noopener">Pesan via WhatsApp</a>`;
 const up=()=>{let t=`Halo Batikku, saya ingin memesan.\nID Pesanan: ${oid}\n\n`+cart.map((c,i)=>{const p=P.find(x=>x[0]==c.id);return `${i+1}. ${p[1]} (${MOTIF[c.m][0]}) x${c.q} = ${rp(p[3]*c.q)}`}).join('\n')+`\n\nTotal: ${rp(tot)} (belum ongkir)\nNama: ${$('#nm').value||'-'}\nAlamat: ${$('#al').value||'-'}\nPembayaran: ${$('#pm').value}\n\nMohon konfirmasi stok, ongkir, dan instruksi pembayaran.`;const w=$('#wa'),v=salah();$('#werr').textContent='';$('#nm').classList.remove('bad');$('#al').classList.remove('bad');
  if(!v.bn&&!v.ba)w.href=`https://wa.me/${WA}?text=${encodeURIComponent(t)}`;else w.removeAttribute('href')};
 up();$('#nm').oninput=$('#al').oninput=$('#pm').onchange=up}
document.addEventListener('click',e=>{const t=e.target.closest('[data-g],[data-c],[data-p],[data-m],[data-x],[data-d],#add,#cb,[data-cart],#bk');if(!t)return;
 if('g' in t.dataset)go(t.dataset.g=='home'?'':t.dataset.g);
 else if(t.dataset.c){cat=t.dataset.c;tabs();list()}
 else if(t.dataset.p)go('item-'+t.dataset.p);
 else if(t.dataset.m){mot=t.dataset.m;drawItem()}
 else if('x' in t.dataset)$('#cart').classList.remove('show');
 else if(t.dataset.d){const c=cart[t.dataset.d];c.q+=+t.dataset.v;if(c.q<1)cart.splice(t.dataset.d,1);save();renderCart()}
 else if(t.id=='add'){const f=cart.find(c=>c.id==sel[0]&&c.m==mot);f?f.q++:cart.push({id:sel[0],m:mot,q:1});save();renderCart();$('#cart').classList.add('show')}
 else if(t.id=='cb'||'cart' in t.dataset){renderCart();$('#cart').classList.add('show')}
 else if(t.id=='bk')history.length>1?history.back():go('shop')});
$('#cart').addEventListener('click',e=>{if(e.target.id=='cart')e.target.classList.remove('show')});
$('#q').oninput=list;$('#so').onchange=list;renderCart();route();
/* Catat pesanan ke admin panel bila backend aktif. Tanpa backend: diabaikan, WhatsApp tetap jalan. */
function kirimPesanan(){try{fetch('api/pesanan',{method:'POST',headers:{'Content-Type':'application/json'},keepalive:true,body:JSON.stringify({id:oid,nama:($('#nm')||{}).value||'',alamat:($('#al')||{}).value||'',metode:($('#pm')||{}).value||'',items:cart.map(c=>({id:c.id,motif:MOTIF[c.m][0],qty:c.q}))})}).catch(()=>{})}catch(e){}}
/* Nama dan alamat wajib diisi sebelum checkout WhatsApp */
function salah(){return{bn:($('#nm')||{value:''}).value.trim().length<2,ba:($('#al')||{value:''}).value.trim().length<8}}
document.addEventListener('click',e=>{if(!e.target.closest('#wa'))return;const v=salah(),n=$('#nm'),a=$('#al');
 if(v.bn||v.ba){e.preventDefault();n.classList.toggle('bad',v.bn);a.classList.toggle('bad',v.ba);
  $('#werr').textContent=v.bn?'Nama penerima wajib diisi.':'Alamat lengkap wajib diisi (nama jalan dan kota).';(v.bn?n:a).focus();return}
 kirimPesanan();setTimeout(()=>{oid=newOid();renderCart()},800)});
