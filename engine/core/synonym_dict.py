"""
EssayGrader — Indonesian Synonym Dictionary
=============================================
Maps semantically equivalent Indonesian words to a single canonical form.
This enables the TF-IDF vectorizer to treat synonymous words as identical,
dramatically improving cosine similarity accuracy for essays.

Usage:
    from .synonym_dict import SynonymNormalizer
    normalizer = SynonymNormalizer()
    tokens = normalizer.normalize(["mengonsumsi", "sayur", "tiap", "hari"])
    # → ["makan", "sayur", "tiap", "hari"]

Design:
    Each synonym group has one canonical form (the first entry).
    All other entries in the group are mapped to the canonical form.
    Stemmed forms are also included to catch post-stemming matches.

References:
    Indonesian Thesaurus (Tesaurus Bahasa Indonesia, Kemendikbud)
"""

from typing import List, Dict


# ============================================================
# SYNONYM GROUPS
# Each group: first entry is the canonical form.
# All subsequent entries map to the first.
# Include both base and stemmed forms for maximum coverage.
# ============================================================
SYNONYM_GROUPS = [
    # --- Verba Umum (Common Verbs) ---
    ["makan", "mengonsumsi", "konsumsi", "santap", "menyantap", "memakan", "lahap", "melahap"],
    ["minum", "meminum", "teguk", "meneguk", "seruput", "menyeruput"],
    ["beri", "memberi", "memberikan", "menyajikan", "sajikan", "menyediakan", "sediakan",
     "menghidangkan", "hidangkan", "menyerahkan", "serahkan", "menyuguhkan"],
    ["buat", "membuat", "menciptakan", "ciptakan", "cipta", "menghasilkan", "hasilkan",
     "memproduksi", "produksi", "membikin"],
    ["guna", "menggunakan", "gunakan", "memakai", "pakai", "memanfaatkan", "manfaat",
     "mempergunakan", "utilisasi"],
    ["dapat", "memperoleh", "peroleh", "mendapatkan", "dapatkan", "meraih", "raih",
     "memperoleh", "menggapai"],
    ["bantu", "membantu", "menolong", "tolong", "mendukung", "dukung", "menunjang", "tunjang"],
    ["tahu", "mengetahui", "memahami", "paham", "mengerti", "menyadari", "sadar",
     "mengenal", "kenal", "memahami"],
    ["pikir", "berpikir", "memikirkan", "mempertimbangkan", "pertimbang", "merenungkan",
     "renungkan", "merenungkan", "merenung"],
    ["lihat", "melihat", "memandang", "pandang", "mengamati", "amati", "meninjau", "tinjau",
     "memperhatikan", "perhatikan", "mengawasi", "awasi", "observasi"],
    ["tulis", "menulis", "mencatat", "catat", "mengarang", "menuliskan"],
    ["baca", "membaca", "menelaah", "telaah", "menyimak", "simak"],
    ["jaga", "menjaga", "melindungi", "lindungi", "merawat", "rawat", "memelihara", "pelihara",
     "proteksi", "melestarikan", "lestarikan"],
    ["ubah", "mengubah", "merubah", "mengkonversi", "konversi", "transformasi",
     "mentransformasi", "modifikasi", "memodifikasi"],
    ["tambah", "menambah", "menambahkan", "meningkatkan", "tingkatkan", "memperbesar",
     "memperbanyak", "menaikkan"],
    ["kurang", "mengurangi", "menurunkan", "memperkecil", "mengurangkan", "menyusutkan"],
    ["mulai", "memulai", "mengawali", "awal", "memulakan", "merintis"],
    ["akhir", "mengakhiri", "menyelesaikan", "selesai", "berakhir", "menuntaskan", "tuntas"],
    ["tunjuk", "menunjukkan", "memperlihatkan", "membuktikan", "bukti", "mendemonstrasikan"],
    ["jelaskan", "menerangkan", "menguraikan", "mendeskripsikan", "memaparkan", "paparkan"],
    ["simpan", "menyimpan", "menaruh", "taruh", "meletakkan", "letak"],
    ["ambil", "mengambil", "memungut", "meraih", "memetik"],
    ["kirim", "mengirim", "mengirimkan", "menyampaikan", "sampaikan"],
    ["terima", "menerima", "mendapat", "memperoleh"],
    ["cegah", "mencegah", "menghindari", "hindari", "menangkal", "tangkal", "preventif"],
    ["sebab", "menyebabkan", "mengakibatkan", "akibat", "menimbulkan", "timbul", "memicu"],
    ["pengaruh", "mempengaruhi", "berdampak", "dampak", "berpengaruh", "efek", "berefek"],
    ["kerja", "bekerja", "berfungsi", "fungsi", "beroperasi", "operasi"],
    ["tumbuh", "bertumbuh", "berkembang", "kembang", "tumbuhan"],
    ["hidup", "kehidupan", "bertahan", "bernyawa", "eksistensi", "eksisten"],

    # --- Adjektiva (Adjectives) ---
    ["bagus", "baik", "indah", "elok", "cantik", "rupawan", "menawan"],
    ["besar", "raksasa", "jumbo", "luas", "lebar", "banyak", "melimpah", "berlimpah"],
    ["kecil", "mungil", "mini", "sedikit", "minim"],
    ["cepat", "kilat", "sigap", "tangkas", "laju", "gesit", "rapid"],
    ["lambat", "pelan", "perlahan", "lamban"],
    ["kuat", "kokoh", "tangguh", "solid", "teguh"],
    ["lemah", "rapuh", "rentan"],
    ["penting", "krusial", "esensial", "vital", "signifikan", "berarti", "bermakna"],
    ["utama", "primer", "pokok", "fundamental", "mendasar", "dasar", "inti"],
    ["baru", "modern", "mutakhir", "terkini", "terbaru", "kontemporer"],
    ["lama", "tua", "kuno", "purba", "antik", "usang"],
    ["sulit", "susah", "rumit", "kompleks", "pelik"],
    ["mudah", "gampang", "simpel", "sederhana", "praktis"],
    ["benar", "tepat", "akurat", "betul", "sahih", "valid"],
    ["salah", "keliru", "gagal"],
    ["tinggi", "jangkung"],
    ["rendah", "pendek"],
    ["sehat", "bugar", "segar", "prima"],
    ["sakit", "derita", "menderita", "sengsara", "nyeri"],

    # --- Nomina (Nouns) ---
    ["manfaat", "keuntungan", "faedah", "kegunaan", "khasiat", "guna", "utilitas", "benefit"],
    ["tubuh", "badan", "raga", "jasmani", "fisik", "ragawi"],
    ["orang", "manusia", "individu", "pribadi", "insan", "persona"],
    ["anak", "bocah", "balita", "siswa", "murid", "pelajar", "peserta"],
    ["guru", "pengajar", "pendidik", "dosen", "instruktur", "tenaga"],
    ["tempat", "lokasi", "area", "wilayah", "daerah", "kawasan", "zona", "posisi"],
    ["waktu", "masa", "periode", "era", "zaman", "kurun", "durasi"],
    ["cara", "metode", "teknik", "strategi", "pendekatan", "mekanisme", "prosedur", "langkah"],
    ["tujuan", "sasaran", "target", "destinasi", "objektif", "misi"],
    ["masalah", "persoalan", "kendala", "hambatan", "rintangan", "tantangan", "problem", "isu"],
    ["jawaban", "solusi", "penyelesaian", "resolusi", "pemecahan"],
    ["sebab", "alasan", "faktor", "penyebab", "akar"],
    ["akibat", "konsekuensi", "dampak", "efek", "hasil", "implikasi", "imbas"],
    ["contoh", "sampel", "ilustrasi", "misal", "demonstrasi"],
    ["jenis", "tipe", "macam", "ragam", "kategori", "klasifikasi", "golongan", "bentuk"],
    ["bagian", "komponen", "elemen", "unsur", "segmen", "porsi", "aspek"],
    ["proses", "tahapan", "prosedur", "mekanisme", "alur", "siklus"],
    ["peristiwa", "kejadian", "insiden", "fenomena", "gejala"],
    ["perubahan", "transformasi", "konversi", "transisi", "evolusi", "mutasi"],
    ["kegiatan", "aktivitas", "aksi", "tindakan", "usaha"],
    ["makanan", "pangan", "nutrisi", "gizi", "asupan", "santapan"],
    ["air", "cairan", "fluida"],
    ["tanah", "lahan", "permukaan", "daratan"],
    ["energi", "tenaga", "daya", "kekuatan", "power"],
    ["cahaya", "sinar", "kilauan", "penerangan", "iluminasi"],
    ["suhu", "temperatur", "panas", "kalor"],
    ["zat", "substansi", "material", "bahan", "senyawa"],
    ["sel", "unit"],
    ["sistem", "mekanisme", "tatanan", "struktur", "kerangka"],
    ["lingkungan", "ekosistem", "habitat", "alam"],
    ["masyarakat", "komunitas", "populasi", "warga", "penduduk", "rakyat"],
    ["pemerintah", "negara", "otoritas", "penguasa", "rezim"],
    ["hukum", "aturan", "regulasi", "peraturan", "undang", "norma", "kaidah"],
    ["ilmu", "pengetahuan", "sains", "disiplin"],
    ["penelitian", "riset", "studi", "kajian", "survei", "investigasi"],
    ["ekonomi", "finansial", "keuangan", "perekonomian"],
    ["budaya", "kebudayaan", "kultur", "tradisi", "adat"],
    ["sejarah", "riwayat", "historis", "masa"],

    # --- Adverbia (Adverbs) ---
    ["sangat", "amat", "sungguh", "betul", "sekali", "luar biasa", "ekstrem"],
    ["sering", "kerap", "acap", "rutin", "berkali", "berulang", "reguler", "rajin"],
    ["jarang", "kadang", "sesekali", "langka"],
    ["selalu", "senantiasa", "terus", "konstan", "konsisten", "tetap"],
    ["segera", "langsung", "seketika", "spontan", "instan"],
    ["biasa", "umum", "lazim", "normal", "wajar", "standar", "tipikal"],
    ["khusus", "spesial", "spesifik", "tertentu", "unik", "khas"],

    # --- Konjungsi/Penghubung Makna ---
    ["karena", "sebab", "lantaran", "disebabkan", "dikarenakan", "akibat", "oleh"],
    ["sehingga", "akibatnya", "maka", "karenanya", "olehnya"],
    ["supaya", "agar", "demi", "guna"],
    ["tetapi", "namun", "akan tetapi", "walau", "meski"],

    # --- Sains / IPA ---
    ["fotosintesis", "asimilasi"],
    ["respirasi", "pernapasan", "napas"],
    ["organ", "alat"],
    ["nutrisi", "gizi", "nutrient"],
    ["vitamin", "suplemen"],
    ["mineral", "unsur"],
    ["protein", "albumin"],
    ["oksigen", "udara"],
    ["karbondioksida", "co2"],
    ["glukosa", "gula"],
    ["reaksi", "interaksi", "respons"],
    ["larutan", "campuran"],
    ["evolusi", "perkembangan", "perubahan"],

    # --- Matematika / IPS ---
    ["hitung", "menghitung", "kalkulasi", "komputasi"],
    ["jumlah", "total", "kuantitas", "bilangan"],
    ["rumus", "formula", "persamaan"],
    ["grafik", "diagram", "bagan", "chart"],
    ["data", "informasi", "fakta", "keterangan"],
    ["analisis", "telaah", "pembahasan", "penguraian"],
    ["kesimpulan", "konklusi", "simpulan", "ringkasan", "rangkuman", "ikhtisar"],
]


class SynonymNormalizer:
    """
    Normalizes tokens by mapping synonyms to canonical forms.

    The normalizer builds a lookup dictionary from SYNONYM_GROUPS,
    mapping every synonym to the canonical (first) entry of its group.
    During normalization, each token is checked against this dictionary
    and replaced with its canonical form if found.

    This is applied AFTER stemming in the preprocessing pipeline,
    so stemmed forms should also be included in the synonym groups.
    """

    def __init__(self, extra_groups: list = None):
        """
        Initialize the synonym normalizer.

        Args:
            extra_groups: Additional synonym groups to include.
                          Each group is a list where the first entry is canonical.
        """
        self._mapping: Dict[str, str] = {}
        self._build_mapping(SYNONYM_GROUPS)
        if extra_groups:
            self._build_mapping(extra_groups)

    def _build_mapping(self, groups: list):
        """Build the synonym → canonical mapping dictionary."""
        for group in groups:
            if len(group) < 2:
                continue
            canonical = group[0]
            for synonym in group[1:]:
                # Map the synonym to the canonical form
                # Don't override if already mapped
                if synonym not in self._mapping:
                    self._mapping[synonym] = canonical

    def normalize(self, tokens: List[str]) -> List[str]:
        """
        Replace synonyms with their canonical forms.

        Args:
            tokens: List of preprocessed (stemmed) tokens

        Returns:
            List of tokens with synonyms replaced by canonical forms
        """
        return [self._mapping.get(token, token) for token in tokens]

    def get_canonical(self, word: str) -> str:
        """Get the canonical form of a word, or the word itself if not found."""
        return self._mapping.get(word, word)

    @property
    def mapping_size(self) -> int:
        """Number of synonym mappings."""
        return len(self._mapping)

    def get_group_for(self, word: str) -> List[str]:
        """Find the synonym group containing a given word."""
        canonical = self._mapping.get(word, word)
        group = [canonical]
        for syn, canon in self._mapping.items():
            if canon == canonical and syn != canonical:
                group.append(syn)
        return group if len(group) > 1 else [word]
