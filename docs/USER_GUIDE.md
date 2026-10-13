# Panduan Pengguna Nusantara Mini ERP

Panduan ini menjelaskan cara memakai Nusantara Mini ERP sehari-hari di distributor
sembako: dari menyiapkan data, menjual, membeli, mengelola gudang, sampai menagih dan
membaca laporan. Semua menu ada di aplikasi **Nusantara ERP**.

## Daftar isi

1. [Peran dan hak akses](#1-peran-dan-hak-akses)
2. [Persiapan awal](#2-persiapan-awal)
3. [Penjualan](#3-penjualan)
4. [Pembelian](#4-pembelian)
5. [Gudang](#5-gudang)
6. [Faktur dan pembayaran](#6-faktur-dan-pembayaran)
7. [Dashboard dan laporan](#7-dashboard-dan-laporan)
8. [Pertanyaan umum](#8-pertanyaan-umum)

## 1. Peran dan hak akses

Hak akses diatur di **Settings > Users**, kategori **Nusantara ERP**:

| Area        | User                                                    | Manager                                               |
| ----------- | ------------------------------------------------------- | ----------------------------------------------------- |
| Master Data | membaca produk, pajak, termin                           | membuat dan mengubah master data                      |
| Sales       | hanya penawaran/pesanan miliknya sendiri                | semua pesanan, batas kredit, konfirmasi di atas batas |
| Purchase    | membuat RFQ dan PO di bawah batas persetujuan           | menyetujui atau menolak PO besar                      |
| Inventory   | penerimaan, pengiriman, transfer, mencatat stock opname | memvalidasi stock opname, mengatur gudang             |
| Invoicing   | membuat dan memposting faktur, mencatat pembayaran      | membatalkan faktur terposting dan pembayaran          |

Setiap pengguna hanya melihat data perusahaan yang diizinkan untuknya.

## 2. Persiapan awal

### Pengaturan perusahaan

Buka **Nusantara ERP > Configuration > Settings**:

- **Default Sales Tax / Purchase Tax**: pajak yang otomatis diisi pada produk baru
  (bawaan: PPN 11%). Kosongkan jika sebagian besar barang Anda bebas PPN.
- **Default Payment Terms**: termin pembayaran jika pelanggan/pemasok tidak punya
  termin sendiri.
- **Quotation Validity**: berapa hari penawaran berlaku.
- **Purchase Approval**: nilai PO (termasuk pajak) yang wajib disetujui manager.
  Isi 0 untuk menonaktifkan persetujuan.

### Master data

- **Produk** (_Master Data > Products_): isi nama, kode internal, jenis (_Goods_ untuk
  barang yang distok, _Service_ untuk jasa seperti ongkos kirim), kategori, satuan,
  harga jual, harga beli, dan pajak. Untuk sembako yang bebas PPN, kosongkan kolom
  pajak.
- **Pelanggan dan pemasok** (_Master Data > Customers / Vendors_): centang _Is a
  Customer_ atau _Is a Vendor_ di tab _Sales & Purchase_, isi termin pembayaran dan
  NPWP (kolom _Tax ID_, divalidasi otomatis).
- **Gudang** (_Configuration > Warehouses_): setiap gudang otomatis mendapat lokasi
  stok. Perusahaan baru otomatis mendapat satu gudang.

### Stok awal

Gunakan **Inventory > Stock Adjustments**: pilih gudang dan alasan _Opening Balance_,
tambahkan produk dengan jumlah hasil hitung dan biaya per unit, lalu manager menekan
**Validate**.

## 3. Penjualan

### Membuat penawaran

1. **Sales > Quotations > New**.
2. Pilih pelanggan. Termin pembayaran terisi otomatis.
3. Tambahkan produk. Harga dan pajak diusulkan dari produk dan masih bisa diubah,
   begitu pula diskon per baris.
4. **Send by Email** mengirim penawaran dalam bentuk PDF. Status berubah menjadi
   _Quotation Sent_.

### Batas kredit

Manager penjualan mengatur **Credit Limit Policy** dan **Credit Limit** di form
pelanggan:

- **Warn**: penawaran tetap bisa dikonfirmasi, tetapi peringatan muncul di form dan
  dicatat di chatter.
- **Block**: hanya manager penjualan yang bisa mengkonfirmasi pesanan di atas batas.

Kredit terpakai = pesanan terkonfirmasi yang belum difakturkan + sisa tagihan faktur
yang belum lunas.

### Konfirmasi dan pengiriman

1. Tekan **Confirm**. Pesanan menjadi _Sales Order_ dan pengiriman (_Delivery_) dibuat
   otomatis untuk barang (jasa tidak dikirim).
2. Tim gudang membuka pengiriman dari tombol **Delivery** atau dari
   _Inventory > Deliveries_, mencetak **Surat Jalan** (_Print_), lalu menekan
   **Validate**.
3. Kolom _Delivered_ dan status pengiriman pada pesanan diperbarui otomatis.

### Membatalkan pesanan

**Cancel** meminta alasan pembatalan. Pesanan yang barangnya sudah terkirim harus
diretur dulu (tombol **Return** pada pengiriman), dan faktur yang terkait harus
dibatalkan.

## 4. Pembelian

1. **Purchase > Requests for Quotation > New**: pilih pemasok, gudang tujuan, tanggal
   kedatangan, dan produk. Harga diambil dari harga beli produk.
2. **Send by Email** mengirim RFQ ke pemasok.
3. **Confirm Order**:
    - jika total di bawah batas persetujuan (atau Anda manager), RFQ langsung menjadi
      _Purchase Order_ dan penerimaan barang dibuat;
    - jika di atas batas, status menjadi _To Approve_ dan manager pembelian mendapat
      aktivitas **Purchase Approval**. Manager menekan **Approve** atau **Reject**
      (menu _Purchase > To Approve_).
4. Saat barang datang, gudang memvalidasi penerimaan. Biaya rata-rata produk
   diperbarui dengan harga bersih pembelian.

## 5. Gudang

| Menu               | Kegunaan                                                  |
| ------------------ | --------------------------------------------------------- |
| Receipts           | barang masuk dari pemasok                                 |
| Deliveries         | barang keluar ke pelanggan, cetak Surat Jalan             |
| Internal Transfers | memindahkan barang antar gudang (pilih gudang tujuan)     |
| Stock Adjustments  | stock opname: catat jumlah hasil hitung dan alasannya     |
| Products           | stok per produk; filter _Below Minimum Stock_             |
| Stock Ledger       | semua pergerakan stok yang sudah selesai, dengan nilainya |

- **Stok tidak bisa minus**: pengiriman ditolak jika stok di gudang tidak cukup.
- **Pergerakan yang sudah selesai tidak bisa diubah.** Koreksi dilakukan dengan
  **Return** atau stock opname.
- **Stock opname**: tombol _Load Products in Stock_ mengisi semua produk yang ada di
  gudang. Isi jumlah hasil hitung, lalu manager memvalidasi. Selisih dihitung dari stok
  saat validasi.
- **Update Quantity** di tab _Inventory_ produk adalah stock opname cepat untuk satu
  produk (manager).
- **Stok minimum**: isi _Minimum Stock_ di tab _Inventory_ produk. Setiap hari sistem
  membuat aktivitas **Low Stock** untuk manager gudang jika stok di bawah minimum.

## 6. Faktur dan pembayaran

### Faktur pelanggan

1. Dari pesanan yang sudah dikirim, tekan **Create Invoice** (atau buka
   _Invoicing > Customers > Orders to Invoice_). Barang difakturkan sesuai jumlah yang
   sudah dikirim, jasa sesuai jumlah yang dipesan.
2. Periksa faktur draft lalu tekan **Post**. Nomor faktur (`INV/2026/00001`) baru
   diberikan saat posting, sehingga nomor selalu berurutan tanpa celah.
3. **Send by Email** mengirim faktur PDF ke pelanggan.

### Tagihan pemasok

Dari PO yang barangnya sudah diterima, tekan **Create Bill**, isi nomor tagihan pemasok
di _Partner Reference_, lalu **Post** (`BILL/2026/00001`).

### Pembayaran

1. Pada faktur terposting, tekan **Register Payment**.
2. Jumlah terisi dengan sisa tagihan; ubah jika pembayaran sebagian. Pilih metode
   (transfer bank, tunai) dan tanggal.
3. Status pembayaran berubah menjadi _Partially Paid_ atau _Paid_. Pembayaran tidak
   bisa melebihi sisa tagihan.

Faktur yang lewat jatuh tempo ditandai **Overdue** setiap hari, dan salesperson
mendapat aktivitas untuk menagih.

## 7. Dashboard dan laporan

- **Dashboard** (halaman pertama aplikasi): penjualan bulan ini, pesanan yang belum
  dikirim, piutang, faktur overdue, hutang, produk di bawah stok minimum, PO yang
  menunggu persetujuan, dan grafik penjualan 6 bulan. Klik kartu untuk membuka
  datanya. Setiap pengguna hanya melihat angka sesuai hak aksesnya.
- **Reporting > Sales Analysis**: penjualan per produk, kategori, pelanggan,
  salesperson, dan bulan, termasuk **margin** barang yang sudah dikirim.
- **Reporting > Purchase Analysis**: pembelian per pemasok dan harga rata-rata.
- **Reporting > Stock by Warehouse**: jumlah dan nilai stok per gudang.
- **Invoicing > Reporting > Receivable / Payable Aging**: umur piutang dan hutang
  (belum jatuh tempo, 1-30, 31-60, 61-90, lebih dari 90 hari).
- **Reporting > Export to Excel**: unduh stok, aging, atau penjualan per produk dalam
  format Excel, atau cetak aging dalam PDF.

## 8. Pertanyaan umum

**Mengapa nomor faktur draft belum muncul?** Nomor diberikan saat faktur diposting
supaya tidak ada nomor yang terbuang.

**Mengapa saya tidak bisa menghapus pesanan atau faktur?** Dokumen yang sudah
dikonfirmasi atau bernomor hanya bisa dibatalkan, supaya jejak auditnya tetap ada.

**Bagaimana mengoreksi stok yang salah?** Buat stock opname dengan alasan yang sesuai
(rusak, hilang, kedaluwarsa, hitung ulang). Pergerakan lama tidak diubah.

**Mengapa biaya rata-rata berubah?** Setiap penerimaan barang dengan harga berbeda
menghitung ulang biaya rata-rata tertimbang. Pengiriman tidak mengubahnya.

**Bagaimana mengganti bahasa ke Bahasa Indonesia?** Aktifkan bahasa Indonesia di
**Settings > Languages**, lalu pilih bahasa di preferensi pengguna. Modul ini
menyediakan terjemahan Bahasa Indonesia.
