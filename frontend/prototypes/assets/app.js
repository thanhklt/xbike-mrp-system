(() => {
  'use strict';
  const $ = (s, root=document) => root.querySelector(s);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = n => new Intl.NumberFormat('vi-VN').format(n);
  const money = n => `${fmt(n)} ₫`;
  const date = value => value ? new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'Asia/Ho_Chi_Minh'}).format(new Date(value)) : '—';
  const time = value => new Intl.DateTimeFormat('vi-VN',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Ho_Chi_Minh'}).format(new Date(value));
  const labels={nguyen_vat_lieu:'Nguyên vật liệu',linh_kien:'Linh kiện',ban_thanh_pham:'Bán thành phẩm',thanh_pham:'Thành phẩm',nhap:'Nháp',da_gui:'Đã gửi',dang_thuc_hien:'Đang thực hiện',hoan_thanh:'Hoàn thành',da_huy:'Đã hủy',da_xac_nhan:'Đã xác nhận',loi:'Lỗi',nhap_vat_tu:'Nhập vật tư',xuat_vat_tu:'Xuất vật tư',nhap_san_pham_san_xuat:'Nhập đầu ra sản xuất',xuat_thanh_pham:'Xuất thành phẩm',dieu_chinh_ton_kho:'Điều chỉnh tồn kho',cay:'cây',cai:'cái',bo:'bộ',chiec:'chiếc',kg:'kg',den:'Đen',bac:'Bạc',trang:'Trắng',xanh_navy:'Xanh navy',cho_xu_ly:'Chờ xử lý',dang_xu_ly:'Đang xử lý',da_xu_ly:'Đã xử lý'};
  const text = v => labels[v] || v;
  const paths={box:'<path d="m3 7 9-4 9 4-9 4-9-4Zm0 0v10l9 4 9-4V7M12 11v10M7 5l10 4"/>',list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',factory:'<path d="M3 21V9l6 3V7l6 3V3h4l2 18ZM7 17h1m4 0h1m4 0h1"/>',adjust:'<path d="M4 7h16M4 17h16M8 4v6m8 4v6"/>',search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',plus:'<path d="M12 5v14M5 12h14"/>',arrow:'<path d="M4 12h16m-5-5 5 5-5 5"/>',chevron:'<path d="m9 5 7 7-7 7"/>',close:'<path d="m6 6 12 12M6 18 18 6"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 4v3"/>',refresh:'<path d="M20 7v5h-5M4 17v-5h5m10-4a8 8 0 0 0-14-2m0 10a8 8 0 0 0 14 2"/>',menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',bike:'<circle cx="5" cy="16" r="4"/><circle cx="19" cy="16" r="4"/><path d="m5 16 5-9 5 9H5m4-12h4m-3 3 5 9m1-12h3l-2 4 2 8"/>'};
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name]||paths.box}</svg>`;
  const badge = state => `<span class="badge ${['hoan_thanh','da_xac_nhan','active'].includes(state)?'good':['da_gui','loi'].includes(state)?state==='loi'?'bad':'warning':['da_huy','inactive','nhap'].includes(state)?'neutral':''}">${state==='active'?'Hoạt động':state==='inactive'?'Ngừng hoạt động':esc(text(state))}</span>`;
  const pages={mathang:{title:'Mặt hàng và tồn kho',group:'Quản lý kho',desc:'Tra cứu danh mục, giá và số lượng tồn hiện tại.',icon:'box',new:'Thêm mặt hàng',newAction:'item-new'},giaodichkho:{title:'Giao dịch kho',group:'Kiểm soát',desc:'Theo dõi từng biến động và truy vết chứng từ đã ghi sổ.',icon:'list'},dieuchinhkho:{title:'Điều chỉnh kho',group:'Kiểm soát',desc:'Đối chiếu và điều chỉnh số lượng trên phiếu nhập đã hoàn thành.',icon:'adjust',new:'Tạo phiếu điều chỉnh',newAction:'adjust-new'},lenhsanxuat:{title:'Lệnh sản xuất',group:'Sản xuất',desc:'Theo dõi giao việc, cấp vật tư và tiến độ sản xuất.',icon:'factory'}};
  const page = document.body.dataset.page;
  const config = pages[page];
  const storageKey='xbike-html-prototype-v1';
  let db, storageAvailable=true;
  let role='Q';
  try {
    const saved=JSON.parse(sessionStorage.getItem(storageKey)||'null');
    db=saved && ['items','ledger','orders','adjustments','tickets'].every(k=>Array.isArray(saved[k])) ? saved : structuredClone(XBikeData.initial);
    role=sessionStorage.getItem('xbike-prototype-role')||'Q';
  } catch { db=structuredClone(XBikeData.initial); storageAvailable=false; }
  if(!['Q','N','A'].includes(role)) role='Q';
  const persist = () => {try{sessionStorage.setItem(storageKey,JSON.stringify(db));}catch{storageAvailable=false;}};
  const item = id => db.items.find(x=>x.id===Number(id));
  const stock = id => XBikeData.stock(db,Number(id));
  const effective = id => XBikeData.effective(db,Number(id));
  const name = id => db.names[id]||`Nhân viên #${id}`;
  const unit = id => text(item(id)?.don_vi_tinh||'');
  const now=()=>new Date().toISOString();
  const state={q:'',tab:'all',type:'',person:'',from:'',to:'',unit:'',color:'',priceMin:'',priceMax:'',request:'',parent:'',item:'',receipt:'',sort:page==='giaodichkho'?'-posted_at':page==='mathang'?'ma_mat_hang':'-created_at',page:1,size:6,scenario:'normal'};
  const options=(values,selected='',all='Tất cả')=>`<option value="">${all}</option>`+values.map(([v,l])=>`<option value="${esc(v)}" ${String(v)===String(selected)?'selected':''}>${esc(l)}</option>`).join('');
  const types=Object.keys(labels).slice(0,4).map(v=>[v,text(v)]);
  const people=Object.entries(db.names);
  const btn=(label,action,id='',className='',disabled=false)=>`<button type="button" class="${className}" data-action="${action}" data-id="${id}" ${disabled?'disabled':''}>${label}</button>`;
  const detailLink=(label,action,id)=>`<button class="row-link" data-action="${action}" data-id="${id}">${esc(label)}</button>`;
  function toast(message){$('#toast').textContent=message;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').textContent='',5000);}
  function field(label,content,extra=''){return `<div class="field ${extra}">${label}${content}</div>`;}
  function selectFilter(label,key,values){return field(`<label for="f-${key}">${label}</label>`,`<select id="f-${key}" data-filter="${key}">${options(values,state[key])}</select>`);}
  function shell(){
    const actor=role==='N'?21:10;
    document.title=`${config.title} · xBike`;
    $('#app').innerHTML=`<a class="skip" href="#main">Đến nội dung chính</a>
      <header class="topbar"><button class="icon-button mobile-menu" data-action="menu" aria-label="Mở điều hướng" aria-expanded="false" aria-controls="sidebar">${icon('menu')}</button><a class="brand" href="../mathang/">${icon('bike')}<span>XBIKE<small>QUẢN LÝ KHO & SẢN XUẤT</small></span></a><span class="top-context">Bàn làm việc / ${config.group}</span><span class="top-date">Dữ liệu mẫu · 04/11/2026</span><div class="profile"><div class="avatar">${role==='N'?'MT':'VA'}</div><div>${role==='A'?'Quản trị viên':esc(name(actor))}<small>${role==='Q'?'Quản lý kho':role==='N'?'Nhân viên sản xuất':'Quản trị tài khoản'}</small></div></div></header>
      <aside class="sidebar" id="sidebar"><nav aria-label="Điều hướng nghiệp vụ"><p class="nav-section">Quản lý kho</p>${nav('mathang')}<p class="nav-section">Sản xuất</p>${nav('lenhsanxuat')}<p class="nav-section">Kiểm soát</p>${nav('giaodichkho')}${nav('dieuchinhkho')}</nav><div class="sidebar-foot"><label for="role">Xem giao diện theo vai trò</label><select id="role"><option value="Q" ${role==='Q'?'selected':''}>Quản lý kho</option><option value="N" ${role==='N'?'selected':''}>Nhân viên · Minh Tuấn</option><option value="A" ${role==='A'?'selected':''}>Quản trị viên</option></select><div class="demo-tag"><span class="demo-dot"></span>Bản thiết kế · Dữ liệu minh họa</div></div></aside>
      <main class="main" id="main" tabindex="-1"><div class="breadcrumb">${config.group}<span>/</span><span>${config.title}</span></div><div class="page-heading"><div><h1>${config.title}</h1><p>${config.desc}</p></div>${config.new&&role==='Q'?btn(icon('plus')+config.new,config.newAction,'','primary'):''}</div><div id="workspace"></div></main>
      <dialog id="dialog" aria-labelledby="dialog-title"></dialog><div class="toast" id="toast" role="status" aria-live="polite"></div>`;
    $('#role').addEventListener('change',e=>{role=e.target.value;try{sessionStorage.setItem('xbike-prototype-role',role);}catch{}state.page=1;shell();});
    workspace();
  }
  function nav(key){return `<a class="nav-link ${key===page?'active':''}" href="../${key}/" ${key===page?'aria-current="page"':''}>${icon(pages[key].icon)}${pages[key].title}</a>`;}
  function tabs(){
    const variants=page==='mathang'?[['all','Tất cả'],['true','Hoạt động'],['false','Ngừng hoạt động']]:page==='dieuchinhkho'?[['all','Tất cả'],['nhap','Nháp'],['da_xac_nhan','Đã xác nhận'],['loi','Lỗi']]:page==='lenhsanxuat'?[['all','Tất cả'],['nhap','Nháp'],['da_gui','Đã gửi'],['dang_thuc_hien','Đang thực hiện'],['hoan_thanh','Hoàn thành'],['da_huy','Đã hủy']]:[['all','Tất cả giao dịch'],['nhap_vat_tu','Nhập vật tư'],['xuat_vat_tu','Xuất vật tư'],['dieu_chinh_ton_kho','Điều chỉnh']];
    return variants.map(([v,l])=>`<button role="tab" aria-selected="${state.tab===v}" aria-controls="results" class="tab" data-action="tab" data-id="${v}">${l} <span class="count">${baseRows().filter(x=>v==='all'||(page==='mathang'?String(x.is_active)===v:page==='giaodichkho'?x.loai_giao_dich===v:x.trang_thai===v)).length}</span></button>`).join('');
  }
  function workspace(){
    const denied=role==='A'||role==='N'&&['dieuchinhkho','giaodichkho'].includes(page);
    if(denied){$('#workspace').innerHTML=`<section class="panel blocked"><div class="empty">${icon('lock')}<h2>Bạn không có quyền truy cập</h2><p>${role==='A'?'Quản trị viên chỉ quản lý tài khoản và vai trò.':'Nghiệp vụ này dành cho quản lý kho.'}<br>Chọn vai trò phù hợp trong phần dữ liệu minh họa để xem màn hình.</p><span class="badge neutral">403 · Không đủ quyền</span></div></section>`;return;}
    const note=page==='mathang'?'<strong>Tồn kho được tính từ giao dịch đã ghi sổ.</strong> Ngừng hoạt động không xóa mặt hàng hoặc thay đổi số dư.':page==='giaodichkho'?'<strong>Mỗi biến động đều có chứng từ nguồn.</strong> Giao dịch đã ghi sổ không được sửa hoặc xóa.':page==='dieuchinhkho'?'<strong>Chỉ điều chỉnh phiếu nhập đã hoàn thành.</strong> Tồn kho thay đổi khi xác nhận thành công.':'<strong>'+ (role==='N'?'Công việc được giao cho bạn.':'Lệnh được sinh từ yêu cầu sản xuất.')+'</strong> Bắt đầu lệnh không làm thay đổi tồn kho.';
    const sortValues=page==='mathang'?[['ten_mat_hang','Tên mặt hàng A–Z'],['-don_gia','Giá cao đến thấp'],['don_gia','Giá thấp đến cao'],['ma_mat_hang','Mã mặt hàng']]:page==='giaodichkho'?[['-posted_at','Ghi sổ mới nhất'],['posted_at','Ghi sổ cũ nhất']]:[['-created_at','Tạo mới nhất'],['created_at','Tạo cũ nhất']];
    let filters=page==='mathang'?selectFilter('Loại mặt hàng','type',types):page==='giaodichkho'?selectFilter('Mặt hàng','item',db.items.map(x=>[x.id,x.ten_mat_hang])):page==='lenhsanxuat'&&role==='Q'?selectFilter('Người thực hiện','person',people):'';
    if(page==='dieuchinhkho')filters=selectFilter('Phiếu nhập nguồn','receipt',[[41,'PN-202611-000041']]);
    const advanced=page==='mathang'?`${selectFilter('Đơn vị tính','unit',[...new Set(db.items.map(x=>x.don_vi_tinh))].map(v=>[v,text(v)]))}${selectFilter('Màu sắc','color',[...new Set(db.items.map(x=>x.mau_sac))].map(v=>[v,text(v)]))}${field('<label for="f-priceMin">Đơn giá từ (₫)</label>','<input id="f-priceMin" type="number" min="0" step="1" data-filter="priceMin">')}${field('<label for="f-priceMax">Đơn giá đến (₫)</label>','<input id="f-priceMax" type="number" min="0" step="1" data-filter="priceMax">')}`:`${page==='giaodichkho'?selectFilter('Loại giao dịch','type',['nhap_vat_tu','xuat_vat_tu','nhap_san_pham_san_xuat','xuat_thanh_pham','dieu_chinh_ton_kho'].map(v=>[v,text(v)]))+selectFilter('Người ghi sổ','person',people):page==='lenhsanxuat'?selectFilter('Mặt hàng đầu ra','item',db.items.filter(x=>['thanh_pham','ban_thanh_pham'].includes(x.loai_mat_hang)).map(x=>[x.id,x.ten_mat_hang]))+selectFilter('Yêu cầu sản xuất','request',[[61,'YCSX-202611-000061'],[62,'YCSX-202611-000062']])+selectFilter('Lệnh cha','parent',db.orders.map(x=>[x.id,x.ma_lenh_san_xuat])):selectFilter('Người lập','person',people)}${field('<label for="f-from">Từ ngày</label>','<input id="f-from" type="date" data-filter="from">')}${field('<label for="f-to">Đến ngày</label>','<input id="f-to" type="date" data-filter="to">')}`;
    $('#workspace').innerHTML=`<div class="info-strip">${icon('info')}<span>${note}</span></div><section class="panel" aria-label="Danh sách ${config.title.toLowerCase()}"><div class="tabs" role="tablist" aria-label="Lọc theo trạng thái">${tabs()}</div><div class="toolbar">${field(`<label for="search">${page==='giaodichkho'?'Tìm trong dữ liệu đang hiển thị':'Tìm kiếm'}</label>`,`<div class="search-control">${icon('search')}<input id="search" data-filter="q" value="${esc(state.q)}" type="search" placeholder="${page==='mathang'?'Tìm mã, tên hoặc SKU…':page==='lenhsanxuat'?'Tìm mã lệnh sản xuất…':page==='dieuchinhkho'?'Tìm mã phiếu, lý do…':'Mã giao dịch, mặt hàng, chứng từ…'}"></div>`,'search')}${filters}${selectFilter('Sắp xếp','sort',sortValues)}${btn(icon('refresh'),'refresh','','icon-button')}</div><details class="advanced"><summary>Bộ lọc bổ sung</summary><div class="toolbar">${advanced}${btn('Xóa bộ lọc','clear')}</div></details><div class="filter-summary" id="filter-summary"></div><div id="results" role="tabpanel"></div></section><div class="page-foot"><span>${icon('lock')} ${page==='giaodichkho'?'Sổ kho chỉ đọc · Số lượng nguyên, biến động có dấu':page==='dieuchinhkho'?'Phiếu đã xác nhận hoặc lỗi không thể sửa':'Múi giờ hiển thị: Việt Nam (UTC+07)'}</span><span>Giá trị minh họa · Chưa kết nối API</span></div><div class="scenario-bar"><label for="scenario">Xem trạng thái mẫu</label><select id="scenario"><option value="normal">Có dữ liệu</option><option value="empty">Chưa có dữ liệu</option><option value="loading">Đang tải</option><option value="error">Lỗi tải dữ liệu</option></select><details><summary>Về bản thiết kế</summary><p class="inline-note">Dữ liệu được lưu trong phiên trình duyệt này. Thay đổi chỉ có tác dụng minh họa.</p>${btn('Khôi phục dữ liệu mẫu','reset')}</details></div>`;
    $('[data-action=refresh]').setAttribute('aria-label','Tải lại danh sách');
    $('#scenario').add(new Option('Dữ liệu đã thay đổi (412)','conflict'));
    $('#scenario').value=state.scenario;
    $('#scenario').addEventListener('change',e=>{state.scenario=e.target.value;renderResults();});
    document.querySelectorAll('[data-filter]').forEach(el=>el.addEventListener(el.tagName==='SELECT'?'change':'input',()=>{state[el.dataset.filter]=el.value;state.page=1;renderResults();}));
    renderResults();
  }
  function baseRows(){return page==='mathang'?db.items:page==='giaodichkho'?db.ledger:page==='dieuchinhkho'?db.adjustments:db.orders.filter(x=>role!=='N'||x.nhan_vien_id===21);}
  function matchingRows(){
    const q=state.q.toLocaleLowerCase('vi').trim();
    return baseRows().filter(x=>{
      if(state.tab!=='all' && (page==='mathang'?String(x.is_active):page==='giaodichkho'?x.loai_giao_dich:x.trang_thai)!==state.tab)return false;
      if(q&&!JSON.stringify(page==='giaodichkho'?{...x,ten:item(x.mat_hang_id)?.ten_mat_hang}:x).toLocaleLowerCase('vi').includes(q))return false;
      if(state.type&&(page==='mathang'?x.loai_mat_hang:x.loai_giao_dich)!==state.type)return false;
      if(state.person&&String(x.nhan_vien_id)!==state.person)return false;
      if(state.item&&String(x.mat_hang_id)!==state.item)return false;
      if(state.request&&String(x.yeu_cau_san_xuat_id)!==state.request)return false;
      if(state.parent&&String(x.lenh_san_xuat_cha_id)!==state.parent)return false;
      if(state.receipt&&String(x.phieu_nhap_id)!==state.receipt)return false;
      if(state.unit&&x.don_vi_tinh!==state.unit||state.color&&x.mau_sac!==state.color)return false;
      if(state.priceMin!==''&&x.don_gia<Number(state.priceMin)||state.priceMax!==''&&x.don_gia>Number(state.priceMax))return false;
      const stamp=x.posted_at||x.created_at; const d=stamp?new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(stamp)):'';
      return !(state.from&&d<state.from||state.to&&d>state.to);
    }).sort((a,b)=>{const sort=state.sort||'-id';const key=sort.replace('-','');const v=typeof a[key]==='number'?a[key]-b[key]:String(a[key]??'').localeCompare(String(b[key]??''),'vi');return (sort.startsWith('-')?-1:1)*(v||a.id-b.id);});
  }
  function renderResults(){
    const invalid=state.from&&state.to&&state.from>state.to?'Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.':state.priceMin!==''&&state.priceMax!==''&&Number(state.priceMin)>Number(state.priceMax)?'Giá tối thiểu phải nhỏ hơn hoặc bằng giá tối đa.':'';
    const rows=matchingRows();const total=rows.length;const max=Math.max(1,Math.ceil(total/state.size));state.page=Math.min(state.page,max);
    $('#filter-summary').innerHTML=invalid?`<span class="negative" role="alert">${invalid}</span>`:`<span><strong>${total}</strong> ${page==='mathang'?'mặt hàng':page==='giaodichkho'?'giao dịch':page==='dieuchinhkho'?'phiếu điều chỉnh':'lệnh sản xuất'}${state.q?' phù hợp':''}</span>${state.q||state.type||state.person||state.item?btn('Xóa bộ lọc','clear','','text'):''}`;
    const result=$('#results');
    if(state.scenario==='loading'){result.innerHTML='<div class="empty" role="status" aria-busy="true"><span class="spinner"></span><p>Đang tải danh sách…</p></div>';return;}
    if(state.scenario==='error'){result.innerHTML=`<div class="empty" role="alert">${icon('info')}<h2>${page==='mathang'?'Danh mục chưa sẵn sàng':'Chưa tải được dữ liệu'}</h2><p>${page==='mathang'?'503 · Snapshot danh mục chưa sẵn sàng. Vui lòng thử lại.':'Kết nối bị gián đoạn. Dữ liệu chưa được cập nhật.'}</p>${btn('Thử lại','refresh','','primary')}</div>`;return;}
    if(invalid||!total||state.scenario==='empty'){result.innerHTML=`<div class="empty">${icon('search')}<h2>${state.scenario==='empty'?'Chưa có dữ liệu':'Không tìm thấy kết quả'}</h2><p>${invalid||'Thử thay đổi từ khóa hoặc bỏ bớt bộ lọc.'}</p>${btn('Xem tất cả','clear')}</div>`;return;}
    const headers=page==='mathang'?['Mặt hàng','Loại mặt hàng','Đơn vị','Đơn giá','Tồn hiện tại','Trạng thái','']:page==='giaodichkho'?['Giao dịch / Ghi sổ','Mặt hàng','Loại giao dịch','Biến động','Chứng từ nguồn','Người thực hiện','']:page==='dieuchinhkho'?['Phiếu điều chỉnh','Phiếu nhập nguồn','Lý do','Trạng thái','Người lập','']:['Lệnh sản xuất','Mặt hàng đầu ra','Số lượng / Tiến độ','Người thực hiện','Trạng thái',''];
    const shown=rows.slice((state.page-1)*state.size,state.page*state.size);
    result.innerHTML=`<div class="table-scroll" tabindex="0" role="region" aria-label="Bảng dữ liệu, có thể cuộn ngang"><table><thead><tr>${headers.map((h,i)=>`<th scope="col" ${page==='mathang'&&[3,4].includes(i)||page==='giaodichkho'&&i===3?'class="num"':''}>${h||'<span class="tiny-label">Thao tác</span>'}</th>`).join('')}</tr></thead><tbody>${shown.map(row).join('')}</tbody></table></div><div class="pagination"><span>Hiển thị ${(state.page-1)*state.size+1}–${Math.min(state.page*state.size,total)} trên ${total} kết quả</span><div class="pages">${btn('Trước','prev','','',state.page===1)}${Array.from({length:max},(_,i)=>btn(String(i+1),'page',i+1,i+1===state.page?'current':'')).join('')}${btn('Sau','next','','',state.page===max)}</div></div>${page==='giaodichkho'?`<div class="lock-note">${icon('info')}Dấu + là nhập kho; dấu − là xuất hoặc điều chỉnh giảm. Không cộng gộp các mặt hàng khác đơn vị.</div>`:''}`;
    document.querySelectorAll('.pages .current').forEach(b=>b.setAttribute('aria-current','page'));
  }
  function row(x){
    if(page==='mathang')return `<tr><td>${detailLink(x.ten_mat_hang,'item',x.id)}<span class="subline">${esc(x.ma_mat_hang)} · ${esc(x.sku)}</span></td><td>${text(x.loai_mat_hang)}</td><td>${esc(text(x.don_vi_tinh))}</td><td class="num">${money(x.don_gia)}</td><td class="num"><strong>${fmt(stock(x.id))}</strong><span class="subline">${esc(text(x.don_vi_tinh))}</span></td><td>${badge(x.is_active?'active':'inactive')}</td><td class="action-cell">${btn('Chi tiết','item',x.id,'text')}</td></tr>`;
    if(page==='giaodichkho')return `<tr><td>${detailLink('GD-'+x.id,'ledger',x.id)}<span class="subline">${date(x.posted_at)} · ${time(x.posted_at)}</span></td><td class="cell-title">${esc(item(x.mat_hang_id)?.ten_mat_hang)}<span class="subline">${item(x.mat_hang_id)?.ma_mat_hang}</span></td><td>${badge(x.loai_giao_dich)}</td><td class="num ${x.so_luong_bien_dong>0?'positive':'negative'}"><strong>${x.so_luong_bien_dong>0?'+':'−'}${fmt(Math.abs(x.so_luong_bien_dong))}</strong><span class="subline">${esc(unit(x.mat_hang_id))}</span></td><td class="document-code">${esc(x.source)}</td><td>${esc(name(x.nhan_vien_id))}</td><td class="action-cell">${btn('Truy vết','ledger',x.id,'text')}</td></tr>`;
    if(page==='dieuchinhkho')return `<tr><td>${detailLink(x.ma_phieu,'adjust',x.id)}<span class="subline">${date(x.created_at)} · ${x.chi_tiet.length} mặt hàng</span></td><td class="document-code">PN-202611-${String(x.phieu_nhap_id).padStart(6,'0')}</td><td style="max-width:280px">${esc(x.ly_do)}</td><td>${badge(x.trang_thai)}</td><td>${esc(name(x.nhan_vien_id))}</td><td class="action-cell">${btn(x.trang_thai==='nhap'?'Xử lý':'Chi tiết','adjust',x.id,'text')}</td></tr>`;
    return `<tr><td>${detailLink(x.ma_lenh_san_xuat,'order',x.id)}<span class="subline">YCSX-202611-${String(x.yeu_cau_san_xuat_id).padStart(6,'0')}${x.lenh_san_xuat_cha_id?' · Lệnh con':''}</span></td><td class="cell-title">${esc(item(x.mat_hang_id)?.ten_mat_hang)}<span class="subline">${item(x.mat_hang_id)?.ma_mat_hang}</span></td><td><span class="num">${fmt(x.so_luong_da_hoan_thanh)} / ${fmt(x.so_luong)} ${unit(x.mat_hang_id)}</span><div class="progress" role="progressbar" aria-label="Đầu ra đã duyệt" aria-valuenow="${x.so_luong_da_hoan_thanh}" aria-valuemin="0" aria-valuemax="${x.so_luong}"><span style="width:${x.so_luong_da_hoan_thanh/x.so_luong*100}%"></span></div></td><td>${x.nhan_vien_id?esc(name(x.nhan_vien_id)):'<span class="muted">Chưa giao</span>'}</td><td>${badge(x.trang_thai)}</td><td class="action-cell">${btn('Chi tiết','order',x.id,'text')}</td></tr>`;
  }
  let restoreFocus;
  function openDialog(title,subtitle,body,actions='',onSubmit){
    const dialog=$('#dialog');if(!dialog.open)restoreFocus=document.activeElement;dialog.close();
    dialog.innerHTML=`<form id="dialog-form"><div class="dialog-head"><div><h2 id="dialog-title">${esc(title)}</h2><p>${subtitle}</p></div>${btn(icon('close'),'close','','icon-button')}</div><div class="dialog-body"><div id="form-error" class="form-error" role="alert" tabindex="-1"></div>${body}</div><div class="dialog-actions">${btn('Đóng','close')}${actions}</div></form>`;
    $('[data-action=close]',dialog).setAttribute('aria-label','Đóng hộp thoại');
    $('#dialog-form').addEventListener('submit',e=>{e.preventDefault();if(state.scenario==='conflict')return fail('412 · Dữ liệu đã được người khác cập nhật. Đóng hộp thoại, tải lại danh sách và kiểm tra trước khi lưu lại.');if(onSubmit)onSubmit(new FormData(e.target));});
    dialog.showModal();
  }
  const submit=(label,extra='')=>`<button class="primary" type="submit" ${extra}>${label}</button>`;
  function fail(message){$('#form-error').textContent=message;$('#form-error').focus();}
  function closeDialog(){ $('#dialog').close();if(restoreFocus?.isConnected)restoreFocus.focus(); }
  function saved(message){persist();closeDialog();workspace();toast(message);}
  function details(values){return `<dl class="detail-grid">${values.map(([k,v])=>`<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>`;}
  const itemIdentity=x=>`${esc(x.ten_mat_hang)}<span class="subline">${x.ma_mat_hang} · ${esc(x.sku)}</span>`;
  function showItem(id){
    const x=item(id);if(!x)return;
    openDialog(x.ten_mat_hang,`${x.ma_mat_hang} · ${esc(x.sku)}`,`${badge(x.is_active?'active':'inactive')}${details([['Loại mặt hàng',text(x.loai_mat_hang)],['Đơn vị tính',esc(text(x.don_vi_tinh))],['Màu sắc',esc(text(x.mau_sac||'—'))],['Đơn giá',money(x.don_gia)],['Tồn hiện tại',`${fmt(stock(id))} ${esc(unit(id))}`],['Cập nhật tồn',date(db.ledger.filter(y=>y.mat_hang_id===x.id).sort((a,b)=>b.posted_at.localeCompare(a.posted_at))[0]?.posted_at)]])}<h3>Mô tả</h3><p class="inline-note">${esc(x.mo_ta||'Chưa có mô tả.')}</p><div class="notice">Số lượng tồn là dữ liệu chỉ đọc, được cập nhật qua giao dịch kho.</div>`,role==='Q'?`${btn('Chỉnh sửa','item-edit',id)}${x.is_active?btn('Ngừng hoạt động','item-disable',id,'danger'):btn('Kích hoạt lại','item-enable',id,'primary')}`:'');
  }
  function editItem(id){
    const x=item(id)||{};const editing=!!id;const referenced=editing&&db.ledger.some(y=>y.mat_hang_id===x.id);
    const input=(key,label,required=true,type='text',readonly=false)=>field(`<label for="${key}">${label}${required?' *':''}</label>`,`<input id="${key}" name="${key}" type="${type}" value="${esc(x[key]??'')}" ${required?'required':''} ${readonly?'readonly':''} ${type==='number'?'min="0" step="1"':''}>`);
    openDialog(editing?'Chỉnh sửa mặt hàng':'Thêm mặt hàng',editing?`${x.ma_mat_hang} · Thông tin danh mục`:'Các trường có dấu * là bắt buộc.',`<div class="form-grid">${input('ma_mat_hang','Mã mặt hàng',true,'text',referenced)}${input('sku','SKU',true,'text',referenced)}${input('ten_mat_hang','Tên mặt hàng')}${field('<label for="loai_mat_hang">Loại mặt hàng *</label>',`<select id="loai_mat_hang" name="loai_mat_hang" required ${referenced?'disabled':''}>${options(types,x.loai_mat_hang||'','Chọn loại mặt hàng')}</select>`)}${input('don_vi_tinh','Đơn vị tính (snake_case)',true,'text',referenced)}${input('don_gia','Đơn giá (VND)',true,'number')}${input('mau_sac','Màu sắc (snake_case)',false)}${field('<label for="mo_ta">Mô tả</label>',`<textarea id="mo_ta" name="mo_ta">${esc(x.mo_ta||'')}</textarea>`,'span-2')}</div>${referenced?'<div class="notice">Mặt hàng đã có chứng từ tham chiếu: mã, SKU, loại và đơn vị tính được giữ nguyên.</div>':'<p class="inline-note">Mã theo định dạng MH-NNNNNN. Tồn kho khi tạo mới bằng 0.</p>'}`,submit(editing?'Lưu thay đổi':'Thêm mặt hàng'),fd=>{
      if(role!=='Q')return fail('Bạn không có quyền thay đổi mặt hàng.');
      const values=Object.fromEntries(fd);Object.keys(values).forEach(k=>values[k]=values[k].trim());
      if(referenced)values.loai_mat_hang=x.loai_mat_hang;
      if(!/^MH-(?!000000)\d{6}$/.test(values.ma_mat_hang))return fail('Mã mặt hàng phải có dạng MH-000015, phần số khác 000000.');
      if(!values.ten_mat_hang||!values.sku)return fail('Tên mặt hàng và SKU không được để trống.');
      if(!/^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(values.don_vi_tinh)||values.mau_sac&&!/^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$/.test(values.mau_sac))return fail('Đơn vị tính và màu sắc dùng snake_case không dấu.');
      if(!types.some(([v])=>v===values.loai_mat_hang))return fail('Chọn loại mặt hàng hợp lệ.');
      values.don_gia=Number(values.don_gia);
      if(!Number.isSafeInteger(values.don_gia)||values.don_gia<0)return fail('Đơn giá phải là số nguyên không âm, đơn vị VND.');
      if(db.items.some(y=>y.id!==x.id&&(y.ma_mat_hang===values.ma_mat_hang||y.sku===values.sku)))return fail('Mã mặt hàng hoặc SKU đã tồn tại, kể cả mặt hàng ngừng hoạt động.');
      if(editing)Object.assign(x,values);else db.items.push({...values,id:Math.max(...db.items.map(y=>y.id))+1,is_active:true});
      saved(editing?'Đã lưu thay đổi mặt hàng trong bản minh họa.':'Đã thêm mặt hàng. Tồn ban đầu: 0.');
    });
  }
  function disableItem(id){const x=item(id);openDialog('Ngừng hoạt động mặt hàng',x.ma_mat_hang,`<p>Bạn muốn ngừng hoạt động <strong>${esc(x.ten_mat_hang)}</strong>?</p><div class="notice warning">Tồn hiện tại: ${fmt(stock(id))} ${unit(id)}. Thao tác này giữ nguyên số dư và chứng từ cũ; mặt hàng sẽ không được dùng cho chứng từ mới.</div>`,submit('Xác nhận ngừng hoạt động'),()=>{if(role!=='Q')return fail('Không đủ quyền.');x.is_active=false;saved('Đã ngừng hoạt động mặt hàng. Số dư không thay đổi.');});}
  function showLedger(id){
    const x=db.ledger.find(y=>y.id===Number(id));if(!x)return;
    const incoming=x.loai_giao_dich==='nhap_vat_tu';
    const related=incoming?db.adjustments.filter(a=>a.trang_thai==='da_xac_nhan'&&a.chi_tiet.some(d=>d.giao_dich_goc_id===x.id)):[];
    openDialog(`Giao dịch GD-${id}`,'Giao dịch đã ghi sổ · Chỉ đọc',`${badge(x.loai_giao_dich)}${details([['Mặt hàng',itemIdentity(item(x.mat_hang_id))],['Biến động',`<span class="${x.so_luong_bien_dong>0?'positive':'negative'}">${x.so_luong_bien_dong>0?'+':''}${fmt(x.so_luong_bien_dong)} ${unit(x.mat_hang_id)}</span>`],['Người thực hiện',esc(name(x.nhan_vien_id))],['Thời điểm ghi sổ',`${date(x.posted_at)} · ${time(x.posted_at)}`],['Chứng từ nguồn',esc(x.source)],['Loại nguồn',incoming?'Chi tiết phiếu nhập':x.loai_giao_dich==='dieu_chinh_ton_kho'?'Chi tiết phiếu điều chỉnh':x.loai_giao_dich==='nhap_san_pham_san_xuat'?'Chứng từ hoàn thành':'Chi tiết phiếu xuất']])}${incoming?`<h3>Đối chiếu lượng nhập</h3><div class="notice">Lượng nhập gốc <strong>${fmt(x.so_luong_bien_dong)}</strong> → Lượng hiệu lực <strong>${fmt(effective(x.id))} ${unit(x.mat_hang_id)}</strong><br>Đã tính ${related.length} phiếu điều chỉnh được xác nhận.</div>${related.map(a=>`<p class="source-line"><a href="../dieuchinhkho/?id=${a.id}">${a.ma_phieu}</a>${badge(a.trang_thai)}</p>`).join('')}`:'<div class="notice">Loại giao dịch này không hỗ trợ điều chỉnh trực tiếp. Lượng hiệu lực không áp dụng.</div>'}`,incoming&&role==='Q'?btn('Lập phiếu điều chỉnh','adjust-from',id,'primary'):x.loai_giao_dich==='dieu_chinh_ton_kho'?`<a href="../dieuchinhkho/?id=${x.source_id}">Xem phiếu điều chỉnh</a>`:'');
  }
  function adjustLines(x){return `<div class="detail-table"><table><thead><tr><th>Mặt hàng / Giao dịch gốc</th><th class="num">Hiệu lực trước</th><th class="num">Số lượng đúng</th><th class="num">Chênh lệch</th></tr></thead><tbody>${x.chi_tiet.map(d=>`<tr><td>${itemIdentity(item(d.mat_hang_id))}<span class="subline">GD-${d.giao_dich_goc_id}</span></td><td class="num">${fmt(d.so_luong_hieu_luc_truoc)}</td><td class="num">${fmt(d.so_luong_dung)}</td><td class="num ${d.so_luong_bien_dong<0?'negative':'positive'}">${d.so_luong_bien_dong>0?'+':''}${fmt(d.so_luong_bien_dong)} ${unit(d.mat_hang_id)}</td></tr>`).join('')}</tbody></table></div>`;}
  function showAdjustment(id){
    const x=db.adjustments.find(y=>y.id===Number(id));if(!x)return;
    const ticket=db.tickets.find(t=>t.id===x.ticket_id);
    openDialog(x.ma_phieu,'Phiếu điều chỉnh số lượng nhập',`${badge(x.trang_thai)}${details([['Phiếu nhập nguồn',`PN-202611-${String(x.phieu_nhap_id).padStart(6,'0')}`],['Người lập',esc(name(x.nhan_vien_id))],['Ngày lập',date(x.created_at)],['Ngày xác nhận',date(x.confirmed_at)]])}<h3>Lý do điều chỉnh</h3><p class="inline-note">${esc(x.ly_do)}</p><h3 class="section-heading">Chi tiết điều chỉnh</h3>${adjustLines(x)}${x.trang_thai==='loi'?`<div class="notice error"><strong>Điều chỉnh thất bại. Không có thay đổi tồn kho.</strong><br>Phiếu lỗi không thể sửa hoặc xác nhận lại. Để thử lại, hãy tạo phiếu mới.</div>${ticket?`<h3>Ticket sự cố đã được lưu</h3><div class="notice"><strong>${ticket.ma_ticket}</strong> · ${text(ticket.trang_thai)}<p>${esc(ticket.mo_ta_loi)}</p><p>Ticket gắn với phiếu nhập nguồn. Đóng ticket không làm thay đổi tồn kho.</p></div>`:''}`:x.trang_thai==='da_xac_nhan'?'<div class="notice good">Đã ghi sổ toàn bộ chênh lệch. Phiếu đã chốt và không thể chỉnh sửa.</div>':'<div class="notice">Chênh lệch là dự kiến. Số lượng hiệu lực được tính lại khi xác nhận.</div>'}`,role==='Q'&&x.trang_thai==='nhap'?`${btn('Xóa phiếu nháp','adjust-delete',id,'danger')}${btn('Chỉnh sửa','adjust-edit',id)}${btn('Xác nhận điều chỉnh','adjust-confirm',id,'primary')}`:role==='Q'&&x.trang_thai==='loi'?btn('Tạo phiếu mới','adjust-new','','primary'):'');
  }
  function editAdjustment(id,sourceId){
    const x=db.adjustments.find(y=>y.id===Number(id));
    const sources=db.ledger.filter(l=>l.loai_giao_dich==='nhap_vat_tu'&&l.source_id===(x?.phieu_nhap_id||41));
    const existing=new Map(x?.chi_tiet.map(d=>[d.giao_dich_goc_id,d])||[]);
    openDialog(x?'Chỉnh sửa phiếu điều chỉnh':'Tạo phiếu điều chỉnh',x?x.ma_phieu:'Điều chỉnh một phiếu nhập đã hoàn thành',`<div class="form-grid">${field('<label for="receipt">Phiếu nhập nguồn *</label>',`<select id="receipt" name="phieu_nhap_id" ${x?'disabled':''}><option value="41">PN-202611-000041 · Đã hoàn thành</option></select>`)}${field('<label>Ngày nhập nguồn</label>','<input id="receipt-date" value="02/11/2026" readonly aria-label="Ngày nhập nguồn">')}${field('<label for="reason">Lý do điều chỉnh *</label>',`<textarea id="reason" name="ly_do" required placeholder="Ghi rõ kết quả đối soát và lý do sửa số lượng…">${esc(x?.ly_do||'')}</textarea>`,'span-2')}</div><h3 class="section-heading">Chọn dòng cần điều chỉnh</h3><p class="inline-note">Nhập số lượng đúng, không nhập số lượng tăng/giảm. Có thể điều chỉnh về 0.</p><div class="detail-table" style="margin-top:12px"><table><thead><tr><th>Chọn / Mặt hàng</th><th class="num">Hiệu lực</th><th class="num">Số lượng đúng</th><th class="num">Dự kiến</th></tr></thead><tbody>${sources.map(l=>`<tr><td><label style="display:flex;gap:10px;align-items:center"><input style="min-height:18px" type="checkbox" name="line" value="${l.id}" ${existing.has(l.id)||Number(sourceId)===l.id?'checked':''}><span>${itemIdentity(item(l.mat_hang_id))}<span class="subline">GD-${l.id} · ${unit(l.mat_hang_id)}</span></span></label></td><td class="num">${fmt(effective(l.id))}</td><td><input aria-label="Số lượng đúng ${esc(item(l.mat_hang_id).ten_mat_hang)}" name="qty-${l.id}" type="number" min="0" step="1" value="${existing.get(l.id)?.so_luong_dung??effective(l.id)}" data-source="${l.id}"></td><td class="num" id="delta-${l.id}">0</td></tr>`).join('')}</tbody></table></div><div class="notice warning">Lưu nháp chưa thay đổi tồn kho. Phiếu chỉ được ghi sổ sau khi xác nhận toàn bộ dòng hợp lệ.</div>`,submit('Lưu phiếu nháp'),fd=>{
      if(role!=='Q'||x&&x.trang_thai!=='nhap')return fail('Chỉ quản lý được chỉnh sửa phiếu nháp.');
      const reason=fd.get('ly_do').trim();if(!reason)return fail('Lý do điều chỉnh không được để trống.');
      const chosen=fd.getAll('line').map(Number);if(!chosen.length)return fail('Chọn ít nhất một dòng cần điều chỉnh.');
      const lines=chosen.map(source=>{const l=sources.find(y=>y.id===source);const raw=fd.get('qty-'+source);return {mat_hang_id:l.mat_hang_id,giao_dich_goc_id:source,so_luong_hieu_luc_truoc:effective(source),so_luong_dung:raw===''?NaN:Number(raw),so_luong_bien_dong:Number(raw)-effective(source)};});
      if(lines.some(d=>!Number.isSafeInteger(d.so_luong_dung)||d.so_luong_dung<0))return fail('Số lượng đúng phải là số nguyên không âm.');
      if(lines.some(d=>!item(d.mat_hang_id).is_active))return fail('Mặt hàng ngừng hoạt động không được dùng trong chứng từ mới.');
      if(lines.some(d=>d.so_luong_bien_dong===0))return fail('Mỗi dòng được chọn phải có chênh lệch khác 0. Bỏ chọn các dòng không thay đổi.');
      if(x)Object.assign(x,{ly_do:reason,chi_tiet:lines});else{const next=db.nextAdjustmentId++; db.adjustments.unshift({id:next,ma_phieu:`DCK-202611-${String(next-300).padStart(6,'0')}`,phieu_nhap_id:41,nhan_vien_id:10,trang_thai:'nhap',ly_do:reason,created_at:now(),confirmed_at:null,chi_tiet:lines});}
      saved('Đã lưu phiếu nháp. Tồn kho chưa thay đổi.');
    });
    document.querySelectorAll('[data-source]').forEach(el=>{const update=()=>{const delta=Number(el.value)-effective(Number(el.dataset.source));const out=$('#delta-'+el.dataset.source);out.textContent=(delta>0?'+':'')+fmt(delta);out.className='num '+(delta<0?'negative':delta>0?'positive':'muted');};el.addEventListener('input',update);update();});
  }
  function confirmAdjustment(id){
    const x=db.adjustments.find(y=>y.id===Number(id));if(!x)return;
    openDialog('Xác nhận điều chỉnh',`${x.ma_phieu} · Thao tác ghi sổ`,`${adjustLines(x)}<div class="notice warning">Hệ thống sẽ tính lại lượng hiệu lực và kiểm tra tồn kho. Thành công sẽ cập nhật toàn bộ dòng cùng lúc; phiếu sau xác nhận không thể sửa.</div>`,submit('Xác nhận và ghi sổ'),()=>{
      if(role!=='Q'||x.trang_thai!=='nhap')return fail('Chỉ được xác nhận phiếu nháp. Vui lòng tải lại phiếu.');
      const lines=x.chi_tiet.map(d=>({...d,so_luong_hieu_luc_truoc:effective(d.giao_dich_goc_id),so_luong_bien_dong:d.so_luong_dung-effective(d.giao_dich_goc_id)}));
      if(lines.some(d=>!item(d.mat_hang_id).is_active))return fail('Mặt hàng đã ngừng hoạt động. Vui lòng kiểm tra danh mục.');
      if(lines.some(d=>d.so_luong_bien_dong===0))return fail('Số lượng hiệu lực đã thay đổi, chênh lệch hiện bằng 0. Hãy sửa phiếu trước khi xác nhận.');
      x.chi_tiet=lines;
      if(lines.some(d=>stock(d.mat_hang_id)+d.so_luong_bien_dong<0)){
        x.trang_thai='loi';const ticketId=db.nextTicketId++;x.ticket_id=ticketId;
        db.tickets.push({id:ticketId,ma_ticket:`TKDC-202611-${String(ticketId-400).padStart(6,'0')}`,phieu_nhap_id:x.phieu_nhap_id,trang_thai:'cho_xu_ly',mo_ta_loi:'Không đủ tồn để điều chỉnh giảm. Toàn bộ phiếu chưa ghi sổ.',created_at:now(),chi_tiet:structuredClone(lines)});
        persist();workspace();showAdjustment(id);toast('Điều chỉnh thất bại. Đã tạo ticket; tồn kho giữ nguyên.');return;
      }
      const timestamp=now();x.trang_thai='da_xac_nhan';x.confirmed_at=timestamp;
      lines.forEach(d=>db.ledger.push({id:Math.max(...db.ledger.map(l=>l.id))+1,mat_hang_id:d.mat_hang_id,so_luong_bien_dong:d.so_luong_bien_dong,loai_giao_dich:'dieu_chinh_ton_kho',source:x.ma_phieu,source_id:x.id,nhan_vien_id:10,posted_at:timestamp}));
      saved('Đã xác nhận điều chỉnh và ghi sổ toàn bộ chênh lệch.');showAdjustment(id);
    });
  }
  function showOrder(id){
    const x=db.orders.find(y=>y.id===Number(id));if(!x||role==='N'&&x.nhan_vien_id!==21)return;
    const ready=x.vat_tu.every(d=>d.so_luong_da_cap>=d.so_luong_can);const children=db.orders.filter(y=>y.lenh_san_xuat_cha_id===x.id);
    openDialog(x.ma_lenh_san_xuat,'Lệnh sản xuất · '+esc(item(x.mat_hang_id).ten_mat_hang),`${badge(x.trang_thai)}${details([['Mặt hàng đầu ra',itemIdentity(item(x.mat_hang_id))],['Yêu cầu sản xuất',`YCSX-202611-${String(x.yeu_cau_san_xuat_id).padStart(6,'0')}`],['Định mức sử dụng',`BOM #${x.bom_id}`],['Người thực hiện',x.nhan_vien_id?esc(name(x.nhan_vien_id)):'Chưa giao'],['Đầu ra đã duyệt',`${x.so_luong_da_hoan_thanh} / ${x.so_luong} ${unit(x.mat_hang_id)}`],['Còn phải hoàn thành',`${x.so_luong-x.so_luong_da_hoan_thanh} ${unit(x.mat_hang_id)}`],['Ngày tạo',date(x.created_at)],['Bắt đầu',date(x.started_at)],['Hoàn thành',date(x.completed_at)]])}${x.lenh_san_xuat_cha_id?`<p class="source-line">Lệnh cha: ${detailLink(db.orders.find(y=>y.id===x.lenh_san_xuat_cha_id).ma_lenh_san_xuat,'order',x.lenh_san_xuat_cha_id)}</p>`:''}<h3 class="section-heading">Tình trạng cấp vật tư ${badge(ready?'hoan_thanh':'da_gui')}</h3><div class="detail-table"><table><thead><tr><th>Vật tư</th><th class="num">Cần</th><th class="num">Đã cấp</th><th class="num">Còn cấp</th><th class="num">Tồn kho</th></tr></thead><tbody>${x.vat_tu.map(d=>`<tr><td>${esc(item(d.mat_hang_id).ten_mat_hang)}<span class="subline">${unit(d.mat_hang_id)}</span></td><td class="num">${d.so_luong_can}</td><td class="num">${d.so_luong_da_cap}</td><td class="num ${d.so_luong_da_cap<d.so_luong_can?'negative':''}">${d.so_luong_can-d.so_luong_da_cap}</td><td class="num">${stock(d.mat_hang_id)}</td></tr>`).join('')}</tbody></table></div><div class="notice ${ready?'good':'warning'}">${ready?'Đã cấp đủ vật tư cho lệnh.':'Chưa cấp đủ vật tư. Lệnh vẫn được gửi nhưng chưa thể bắt đầu.'} Số đã cấp chỉ tính các phiếu xuất đã duyệt.</div>${children.length?`<h3>Lệnh con</h3>${children.map(c=>`<p class="source-line">${detailLink(c.ma_lenh_san_xuat,'order',c.id)}${badge(c.trang_thai)}</p>`).join('')}`:''}<p class="inline-note">Lệnh tự hoàn thành khi đầu ra được duyệt đạt số lượng yêu cầu. Không có thao tác hoàn tất trực tiếp.</p>`,role==='Q'?`${x.trang_thai==='nhap'?btn('Giao người thực hiện','order-assign',id)+btn('Gửi lệnh','order-send',id,'primary'):''}${!['hoan_thanh','da_huy'].includes(x.trang_thai)?btn('Hủy lệnh','order-cancel',id,'danger'):''}`:x.trang_thai==='da_gui'?btn('Bắt đầu thực hiện','order-start',id,'primary',!ready):'');
  }
  function orderAction(action,id){
    const x=db.orders.find(y=>y.id===Number(id));if(!x)return;
    if(action==='order-assign'){
      openDialog('Giao người thực hiện',x.ma_lenh_san_xuat,field('<label for="assignee">Người thực hiện</label>',`<select id="assignee" name="nhan_vien_id">${options(people.filter(([id])=>id!=='10'),x.nhan_vien_id||'','Chưa giao')}</select>`),submit('Lưu phân công'),fd=>{if(role!=='Q'||x.trang_thai!=='nhap')return fail('Chỉ quản lý được giao người khi lệnh còn nháp.');x.nhan_vien_id=fd.get('nhan_vien_id')?Number(fd.get('nhan_vien_id')):null;saved('Đã cập nhật người thực hiện.');showOrder(id);});return;
    }
    const sending=action==='order-send',starting=action==='order-start';
    openDialog(sending?'Gửi lệnh sản xuất':starting?'Bắt đầu sản xuất':'Hủy lệnh sản xuất',x.ma_lenh_san_xuat,sending?`<p>Gửi lệnh đến người thực hiện đã được giao.</p><div class="notice">Thiếu vật tư không chặn gửi lệnh. Người thực hiện chỉ bắt đầu sau khi đã được cấp đủ vật tư.</div>`:starting?'<p>Xác nhận bắt đầu công việc được giao? Thao tác này không làm thay đổi tồn kho.</p>':field('<label for="cancel-reason">Lý do hủy *</label>','<textarea id="cancel-reason" name="ly_do" required></textarea>'),submit(sending?'Xác nhận gửi':starting?'Bắt đầu thực hiện':'Xác nhận hủy'),fd=>{
      if(sending){if(role!=='Q'||x.trang_thai!=='nhap')return fail('Chỉ được gửi lệnh nháp.');if(!x.nhan_vien_id)return fail('Cần giao người thực hiện trước khi gửi lệnh.');if(!item(x.mat_hang_id).is_active)return fail('Mặt hàng đầu ra đã ngừng hoạt động.');x.trang_thai='da_gui';}
      else if(starting){if(role!=='N'||x.nhan_vien_id!==21||x.trang_thai!=='da_gui')return fail('Chỉ nhân viên được giao mới được bắt đầu lệnh đã gửi.');if(!x.vat_tu.every(d=>d.so_luong_da_cap>=d.so_luong_can))return fail('Vật tư chưa được cấp đủ.');x.trang_thai='dang_thuc_hien';x.started_at=now();}
      else{if(role!=='Q'||['da_huy','hoan_thanh'].includes(x.trang_thai))return fail('Không thể hủy lệnh ở trạng thái hiện tại.');if(!fd.get('ly_do').trim())return fail('Nhập lý do hủy.');if(x.so_luong_da_hoan_thanh||x.vat_tu.some(d=>d.so_luong_da_cap>0))return fail('Không thể hủy: lệnh đã có vật tư hoặc đầu ra được ghi sổ.');if(db.orders.some(y=>y.lenh_san_xuat_cha_id===x.id&&!['da_huy','hoan_thanh'].includes(y.trang_thai)))return fail('Không thể hủy khi vẫn còn lệnh con hoạt động.');x.trang_thai='da_huy';x.ly_do_huy=fd.get('ly_do').trim();}
      saved(sending?'Đã gửi lệnh sản xuất.':starting?'Đã bắt đầu thực hiện. Tồn kho không thay đổi.':'Đã hủy lệnh sản xuất.');showOrder(id);
    });
  }
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&$('#sidebar')?.classList.contains('open')){ $('#sidebar').classList.remove('open'); $('.mobile-menu').setAttribute('aria-expanded','false'); $('.mobile-menu').focus(); }
    const tab=e.target.closest('[role=tab]');
    if(tab&&['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){
      e.preventDefault(); const tabs=[...document.querySelectorAll('[role=tab]')]; const index=tabs.indexOf(tab);
      const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(index+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
      tabs[next].click(); tabs[next].focus();
    }
  });
  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-action]');if(!b||b.disabled)return;const {action,id}=b.dataset;
    if(action==='close'){closeDialog();return;}
    if(action==='menu'){const expanded=$('#sidebar').classList.toggle('open');b.setAttribute('aria-expanded',String(expanded));return;}
    if(action==='tab'){state.tab=id;state.page=1;document.querySelectorAll('[role=tab]').forEach(t=>t.setAttribute('aria-selected',String(t===b)));renderResults();return;}
    if(action==='page'||action==='prev'||action==='next'){state.page=action==='page'?Number(id):state.page+(action==='prev'?-1:1);renderResults();return;}
    if(action==='clear'){Object.assign(state,{q:'',tab:'all',type:'',person:'',from:'',to:'',unit:'',color:'',priceMin:'',priceMax:'',request:'',parent:'',item:'',receipt:'',page:1,scenario:'normal'});workspace();return;}
    if(action==='refresh'){state.scenario='normal';workspace();toast('Đã tải lại dữ liệu minh họa.');return;}
    if(action==='reset'){db=structuredClone(XBikeData.initial);persist();Object.assign(state,{tab:'all',page:1,scenario:'normal'});workspace();toast('Đã khôi phục dữ liệu mẫu.');return;}
    if(role==='A'||role==='N'&&['adjust','adjust-new','adjust-edit','adjust-delete','adjust-confirm','adjust-from','ledger','item-edit','item-new','item-disable','item-enable'].includes(action))return;
    if(action==='item')showItem(id);
    else if(action==='item-new'||action==='item-edit')editItem(id);
    else if(action==='item-disable')disableItem(id);
    else if(action==='item-enable'){item(id).is_active=true;saved('Đã kích hoạt lại mặt hàng.');showItem(id);}
    else if(action==='ledger')showLedger(id);
    else if(action==='adjust')showAdjustment(id);
    else if(action==='adjust-new'||action==='adjust-edit'||action==='adjust-from')editAdjustment(action==='adjust-edit'?id:null,action==='adjust-from'?id:null);
    else if(action==='adjust-confirm')confirmAdjustment(id);
    else if(action==='adjust-delete'){const x=db.adjustments.find(y=>y.id===Number(id));openDialog('Xóa phiếu nháp',x.ma_phieu,'<p>Phiếu chưa ghi sổ. Bạn muốn xóa phiếu nháp này?</p>',submit('Xóa phiếu nháp'),()=>{if(role!=='Q'||x.trang_thai!=='nhap')return fail('Chỉ được xóa phiếu nháp.');db.adjustments=db.adjustments.filter(y=>y.id!==x.id);saved('Đã xóa phiếu nháp.');});}
    else if(action==='order')showOrder(id);
    else if(action.startsWith('order-'))orderAction(action,id);
  });
  shell();
  const selected=new URLSearchParams(location.search).get('id');
  if(selected&&role!=='A'){if(page==='mathang')showItem(selected);else if(page==='dieuchinhkho'&&role==='Q')showAdjustment(selected);else if(page==='giaodichkho'&&role==='Q')showLedger(selected);else if(page==='lenhsanxuat')showOrder(selected);}
  if(!storageAvailable)toast('Trình duyệt không cho lưu phiên. Thay đổi minh họa chỉ giữ trên trang này.');
})();
