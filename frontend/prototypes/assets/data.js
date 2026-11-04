/* Illustrative contract-v3 data. Stock is derived from the ledger, never entered. */
window.XBikeData = (() => {
  const items = [
    [1,'AL-6061-T6','Ống nhôm hợp kim 6061','nguyen_vat_lieu','cay',185000,'bac'],
    [2,'ST-BOLT-M6','Bu lông lục giác M6 × 20','linh_kien','cai',2500,'bac'],
    [3,'WH-RIM-26','Vành bánh xe nhôm 26 inch','linh_kien','cai',245000,'den'],
    [4,'TY-URBAN-26','Lốp xe Urban 26 × 1.75','linh_kien','cai',165000,'den'],
    [5,'BR-DISC-160','Bộ phanh đĩa cơ 160 mm','linh_kien','bo',320000,'den'],
    [6,'PAINT-NV-01','Sơn phủ tĩnh điện xanh navy','nguyen_vat_lieu','kg',120000,'xanh_navy'],
    [7,'FR-URBAN-M','Khung xe Urban cỡ M','ban_thanh_pham','cai',1250000,'xanh_navy'],
    [8,'WH-URBAN-26','Cụm bánh xe Urban 26 inch','ban_thanh_pham','bo',890000,'den'],
    [9,'XB-URBAN-M','Xe đạp xBike Urban M','thanh_pham','chiec',4200000,'xanh_navy'],
    [10,'XB-CITY-S','Xe đạp xBike City S','thanh_pham','chiec',3650000,'trang'],
    [11,'CH-8S-116','Xích xe đạp 8 tốc độ','linh_kien','cai',95000,'bac'],
    [12,'SD-COMFORT','Yên xe Comfort','linh_kien','cai',185000,'den'],
    [13,'GR-URBAN','Tay nắm cao su Urban','linh_kien','bo',45000,'den'],
    [14,'FR-CITY-S','Khung xe City cỡ S','ban_thanh_pham','cai',1050000,'trang']
  ].map(([id,sku,ten_mat_hang,loai_mat_hang,don_vi_tinh,don_gia,mau_sac]) => ({id,sku,ten_mat_hang,loai_mat_hang,don_vi_tinh,don_gia,mau_sac,ma_mat_hang:`MH-${String(id).padStart(6,'0')}`,mo_ta:'Vật tư và sản phẩm thuộc danh mục xBike.',is_active:id!==13}));
  const names={10:'Nguyễn Văn An',21:'Trần Minh Tuấn',22:'Lê Thị Mai',23:'Phạm Quốc Huy'};
  const ledger=[];
  const add=(item,qty,type,source,sourceId,actor=10,day=3) => {
    const id=ledger.length+501;
    ledger.push({id,mat_hang_id:item,so_luong_bien_dong:qty,loai_giao_dich:type,source,source_id:sourceId,nhan_vien_id:actor,posted_at:`2026-11-${String(day).padStart(2,'0')}T${String(2+id%7).padStart(2,'0')}:${String(id%50).padStart(2,'0')}:00Z`});
  };
  [500,1200,160,160,90,50,80,70,24,16,200,100,0,40].forEach((qty,i)=>{
    if(qty) add(i+1,qty,i<6||i===10||i===11?'nhap_vat_tu':'nhap_san_pham_san_xuat',i<6||i===10||i===11?'PN-202611-000041':`HTSX-202611-${String(20+i).padStart(6,'0')}`,i<6||i===10||i===11?41:20+i,10,2);
  });
  add(1,-180,'xuat_vat_tu','PX-202611-000018',18);
  add(2,-480,'xuat_vat_tu','PX-202611-000018',18);
  add(3,-60,'xuat_vat_tu','PX-202611-000018',18);
  add(4,-60,'xuat_vat_tu','PX-202611-000018',18);
  add(7,-30,'xuat_vat_tu','PX-202611-000019',19);
  add(8,-30,'xuat_vat_tu','PX-202611-000019',19);
  add(9,-10,'xuat_thanh_pham','PX-202611-000020',20);
  add(1,-5,'dieu_chinh_ton_kho','DCK-202611-000001',301);
  const requirements=[{mat_hang_id:7,so_luong_can:30,so_luong_da_cap:30},{mat_hang_id:8,so_luong_can:30,so_luong_da_cap:30}];
  const orders=[
    [101,9,30,21,'dang_thuc_hien',12, null],
    [102,7,60,22,'da_gui',0,101],
    [103,8,60,21,'nhap',0,101],
    [104,10,20,23,'da_gui',0,null],
    [105,14,40,null,'nhap',0,104],
    [106,9,24,21,'hoan_thanh',24,null],
    [107,7,20,22,'da_huy',0,null],
    [108,8,12,21,'da_gui',0,null],
    [109,10,16,23,'hoan_thanh',16,null]
  ].map(([id,mat_hang_id,so_luong,nhan_vien_id,trang_thai,done,parent])=>({id,mat_hang_id,so_luong,nhan_vien_id,trang_thai,so_luong_da_hoan_thanh:done,lenh_san_xuat_cha_id:parent,yeu_cau_san_xuat_id:id<104?61:62,bom_id:mat_hang_id+10,ma_lenh_san_xuat:`LSX-202611-${String(id-100).padStart(6,'0')}`,created_at:'2026-11-03T02:00:00Z',started_at:trang_thai==='dang_thuc_hien'?'2026-11-04T01:00:00Z':null,completed_at:trang_thai==='hoan_thanh'?'2026-11-03T09:00:00Z':null,vat_tu:id===101?requirements:[{mat_hang_id:1,so_luong_can:so_luong*2,so_luong_da_cap:id===108||done>0?so_luong*2:0},{mat_hang_id:2,so_luong_can:so_luong*4,so_luong_da_cap:id===108||done>0?so_luong*4:0}]}));
  // Prior approved outputs and issues back the progress and material quantities shown.
  add(9,12,'nhap_san_pham_san_xuat','HTSX-202611-000013',13,21,4);
  add(1,-24,'xuat_vat_tu','PX-202611-000021',21,10,4);
  add(2,-48,'xuat_vat_tu','PX-202611-000021',21,10,4);
  for (const order of orders.filter(o=>o.trang_thai==='hoan_thanh')) {
    for (const line of order.vat_tu) add(line.mat_hang_id,-line.so_luong_da_cap,'xuat_vat_tu',`PX-202611-${String(order.id).padStart(6,'0')}`,order.id,10,2);
  }
  const adjustments=[
    {id:303,ma_phieu:'DCK-202611-000003',phieu_nhap_id:41,nhan_vien_id:10,trang_thai:'nhap',ly_do:'Đối chiếu số lượng nhôm nhận thực tế với phiếu nhập.',created_at:'2026-11-04T02:30:00Z',confirmed_at:null,chi_tiet:[{mat_hang_id:1,giao_dich_goc_id:501,so_luong_hieu_luc_truoc:495,so_luong_dung:490,so_luong_bien_dong:-5}]},
    {id:302,ma_phieu:'DCK-202611-000002',phieu_nhap_id:41,nhan_vien_id:10,trang_thai:'loi',ly_do:'Đối soát lại số lượng bu lông từ nhà cung cấp.',created_at:'2026-11-03T08:20:00Z',confirmed_at:null,ticket_id:401,chi_tiet:[{mat_hang_id:2,giao_dich_goc_id:502,so_luong_hieu_luc_truoc:1200,so_luong_dung:100,so_luong_bien_dong:-1100}]},
    {id:301,ma_phieu:'DCK-202611-000001',phieu_nhap_id:41,nhan_vien_id:10,trang_thai:'da_xac_nhan',ly_do:'Điều chỉnh 5 cây nhôm ghi dư khi nhập hàng.',created_at:'2026-11-03T04:00:00Z',confirmed_at:'2026-11-03T06:00:00Z',chi_tiet:[{mat_hang_id:1,giao_dich_goc_id:501,so_luong_hieu_luc_truoc:500,so_luong_dung:495,so_luong_bien_dong:-5}]}
  ];
  const initial={nextAdjustmentId:304,nextTicketId:402,items,ledger,orders,adjustments,tickets:[{id:401,ma_ticket:'TKDC-202611-000001',phieu_nhap_id:41,trang_thai:'cho_xu_ly',mo_ta_loi:'Điều chỉnh giảm vượt số lượng tồn kho.',created_at:'2026-11-03T08:21:00Z'}],names};
  const stock=(db,id)=>db.ledger.filter(x=>x.mat_hang_id===id).reduce((s,x)=>s+x.so_luong_bien_dong,0);
  const effective=(db,id)=>{const source=db.ledger.find(x=>x.id===id);return source.so_luong_bien_dong+db.adjustments.filter(x=>x.trang_thai==='da_xac_nhan').flatMap(x=>x.chi_tiet).filter(x=>x.giao_dich_goc_id===id).reduce((s,x)=>s+x.so_luong_bien_dong,0)};
  console.assert(stock(initial,1)===211,'Stock must match the posted ledger');
  console.assert(effective(initial,501)===495,'Effective receipt includes confirmed adjustments');
  console.assert(items.every(x=>stock(initial,x.id)>=0),'No negative sample stock');
  console.assert(orders.every(x=>x.so_luong_da_hoan_thanh<=x.so_luong),'Output cannot exceed order quantity');
  return {initial,stock,effective};
})();
