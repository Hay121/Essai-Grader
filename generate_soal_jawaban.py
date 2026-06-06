"""
Generate Soal (3 Paket) & Jawaban Siswa (5 Siswa)
===================================================
Script ini menghasilkan:
1. File HTML → PDF berisi 3 paket soal (Sejarah, Biologi, PKN)
2. File data jawaban siswa (5 siswa) untuk ke-3 paket soal

Setiap jawaban siswa dirancang untuk menghasilkan skor optimal
yang menunjukkan akurasi sistem scoring EssayGrader.
"""

import os
import subprocess
import sys
import json

# ============================================================
# DATA: 3 PAKET SOAL
# ============================================================

PAKET_SOAL = {
    "Paket 1 — Sejarah Indonesia": {
        "subject": "Sejarah",
        "questions": [
            {
                "no": 1,
                "soal": "Jelaskan peristiwa proklamasi kemerdekaan Indonesia pada tanggal 17 Agustus 1945!",
                "kunci": "Proklamasi kemerdekaan Indonesia dibacakan oleh Soekarno didampingi Mohammad Hatta pada tanggal 17 Agustus 1945 di Jalan Pegangsaan Timur nomor 56 Jakarta. Naskah proklamasi diketik oleh Sayuti Melik berdasarkan tulisan tangan Soekarno.",
                "poin": 10
            },
            {
                "no": 2,
                "soal": "Sebutkan dan jelaskan latar belakang kedatangan bangsa Eropa ke Indonesia!",
                "kunci": "Bangsa Eropa datang ke Indonesia karena mencari rempah-rempah yang sangat berharga di Eropa. Selain itu mereka ingin menyebarkan agama dan memperluas wilayah kekuasaan. Semangat ini dikenal dengan semboyan Gold, Glory, dan Gospel.",
                "poin": 10
            },
            {
                "no": 3,
                "soal": "Jelaskan peran Soekarno dalam pergerakan kemerdekaan Indonesia!",
                "kunci": "Soekarno berperan sebagai tokoh utama pergerakan kemerdekaan Indonesia. Beliau mendirikan Partai Nasional Indonesia pada tahun 1927 untuk memperjuangkan kemerdekaan. Soekarno juga menjadi proklamator yang membacakan naskah proklamasi kemerdekaan.",
                "poin": 10
            },
            {
                "no": 4,
                "soal": "Apa yang dimaksud dengan Sumpah Pemuda dan kapan peristiwa itu terjadi?",
                "kunci": "Sumpah Pemuda adalah ikrar yang diucapkan oleh para pemuda Indonesia pada tanggal 28 Oktober 1928. Isinya menyatakan satu tanah air yaitu Indonesia, satu bangsa yaitu bangsa Indonesia, dan satu bahasa yaitu bahasa Indonesia.",
                "poin": 10
            },
            {
                "no": 5,
                "soal": "Jelaskan perjuangan rakyat Indonesia melawan penjajahan Belanda!",
                "kunci": "Rakyat Indonesia melawan penjajahan Belanda melalui perlawanan bersenjata dan diplomasi. Perlawanan bersenjata dilakukan oleh para pahlawan seperti Diponegoro, Imam Bonjol, dan Cut Nyak Dhien. Perjuangan diplomasi dilakukan melalui organisasi pergerakan nasional.",
                "poin": 10
            },
            {
                "no": 6,
                "soal": "Apa dampak pendudukan Jepang terhadap kehidupan rakyat Indonesia?",
                "kunci": "Pendudukan Jepang membawa dampak buruk bagi rakyat Indonesia. Rakyat dipaksa menjadi romusha atau pekerja paksa. Hasil pertanian dirampas untuk kepentingan perang Jepang sehingga rakyat mengalami kelaparan dan penderitaan.",
                "poin": 10
            },
        ]
    },
    "Paket 2 — Biologi": {
        "subject": "Biologi",
        "questions": [
            {
                "no": 1,
                "soal": "Jelaskan proses fotosintesis pada tumbuhan hijau!",
                "kunci": "Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau menggunakan cahaya matahari. Tumbuhan menyerap air dan karbondioksida lalu mengubahnya menjadi glukosa dan oksigen. Proses ini terjadi di kloroplas yang mengandung klorofil.",
                "poin": 10
            },
            {
                "no": 2,
                "soal": "Apa perbedaan antara sel prokariotik dan sel eukariotik?",
                "kunci": "Perbedaan utamanya adalah membran inti. Sel prokariotik tidak memiliki membran inti sehingga materi genetiknya tersebar di sitoplasma. Sel eukariotik memiliki membran inti yang membungkus materi genetiknya.",
                "poin": 10
            },
            {
                "no": 3,
                "soal": "Jelaskan fungsi sistem pencernaan pada manusia!",
                "kunci": "Sistem pencernaan berfungsi untuk mengolah makanan menjadi nutrisi yang dapat diserap tubuh. Proses pencernaan dimulai dari mulut kemudian melewati kerongkongan, lambung, usus halus, dan usus besar. Nutrisi diserap di usus halus dan sisa makanan dikeluarkan melalui anus.",
                "poin": 10
            },
            {
                "no": 4,
                "soal": "Apa yang dimaksud dengan ekosistem dan sebutkan komponen-komponennya!",
                "kunci": "Ekosistem adalah kesatuan antara makhluk hidup dan lingkungannya yang saling berinteraksi. Komponen ekosistem terdiri dari komponen biotik yaitu makhluk hidup dan komponen abiotik yaitu benda mati seperti air, tanah, udara, dan cahaya matahari.",
                "poin": 10
            },
            {
                "no": 5,
                "soal": "Jelaskan proses pernapasan pada manusia!",
                "kunci": "Pernapasan adalah proses pertukaran gas oksigen dan karbondioksida. Udara masuk melalui hidung kemudian melewati tenggorokan menuju paru-paru. Di paru-paru terjadi pertukaran gas di alveolus, oksigen masuk ke darah dan karbondioksida dikeluarkan.",
                "poin": 10
            },
            {
                "no": 6,
                "soal": "Jelaskan tentang rantai makanan dan jaring-jaring makanan!",
                "kunci": "Rantai makanan adalah proses makan dan dimakan dalam urutan tertentu dari produsen ke konsumen. Produsen dimakan oleh konsumen tingkat satu, konsumen tingkat satu dimakan konsumen tingkat dua, dan seterusnya. Jaring-jaring makanan adalah kumpulan rantai makanan yang saling berhubungan.",
                "poin": 10
            },
        ]
    },
    "Paket 3 — Pendidikan Kewarganegaraan (PKN)": {
        "subject": "PKN",
        "questions": [
            {
                "no": 1,
                "soal": "Sebutkan dan jelaskan nilai-nilai yang terkandung dalam Pancasila sila pertama!",
                "kunci": "Sila pertama Pancasila yaitu Ketuhanan Yang Maha Esa mengandung nilai religius dan toleransi beragama. Setiap warga negara wajib percaya kepada Tuhan Yang Maha Esa sesuai agama dan kepercayaannya. Negara menjamin kebebasan beragama bagi seluruh rakyat Indonesia.",
                "poin": 10
            },
            {
                "no": 2,
                "soal": "Jelaskan sistem pemerintahan Indonesia berdasarkan UUD 1945!",
                "kunci": "Indonesia menganut sistem pemerintahan presidensial berdasarkan UUD 1945. Presiden berkedudukan sebagai kepala negara sekaligus kepala pemerintahan. Kekuasaan negara dibagi menjadi tiga yaitu legislatif, eksekutif, dan yudikatif.",
                "poin": 10
            },
            {
                "no": 3,
                "soal": "Apa yang dimaksud dengan demokrasi Pancasila?",
                "kunci": "Demokrasi Pancasila adalah sistem demokrasi yang didasarkan pada nilai-nilai Pancasila. Kedaulatan berada di tangan rakyat dan dilaksanakan melalui musyawarah untuk mufakat. Demokrasi Pancasila mengedepankan keseimbangan antara hak dan kewajiban warga negara.",
                "poin": 10
            },
            {
                "no": 4,
                "soal": "Jelaskan hak dan kewajiban warga negara Indonesia!",
                "kunci": "Warga negara Indonesia memiliki hak untuk mendapatkan pendidikan, pekerjaan, dan penghidupan yang layak. Kewajiban warga negara adalah membela negara, membayar pajak, dan menaati hukum serta peraturan yang berlaku.",
                "poin": 10
            },
            {
                "no": 5,
                "soal": "Jelaskan pentingnya menjaga persatuan dan kesatuan bangsa Indonesia!",
                "kunci": "Persatuan dan kesatuan bangsa Indonesia sangat penting karena Indonesia terdiri dari berbagai suku, agama, dan budaya. Persatuan menjaga keutuhan negara dari ancaman perpecahan. Dengan persatuan rakyat Indonesia dapat bekerja sama membangun bangsa yang lebih maju.",
                "poin": 10
            },
        ]
    }
}

# ============================================================
# DATA: JAWABAN 5 SISWA
# ============================================================

JAWABAN_SISWA = {
    # ===== SISWA A: Jawaban sangat baik (hampir identik) — Target 90-100% =====
    "Andi Pratama": {
        "Paket 1 — Sejarah Indonesia": [
            "Proklamasi kemerdekaan Indonesia dibacakan oleh Soekarno yang didampingi oleh Mohammad Hatta pada tanggal 17 Agustus 1945 di Jalan Pegangsaan Timur nomor 56 Jakarta. Naskah proklamasi diketik oleh Sayuti Melik berdasarkan tulisan tangan Soekarno.",
            "Bangsa Eropa datang ke Indonesia karena mencari rempah-rempah yang sangat berharga di Eropa. Selain itu mereka juga ingin menyebarkan agama dan memperluas wilayah kekuasaan mereka. Semangat ini dikenal dengan semboyan Gold, Glory, dan Gospel.",
            "Soekarno berperan sebagai tokoh utama pergerakan kemerdekaan Indonesia. Beliau mendirikan Partai Nasional Indonesia pada tahun 1927 untuk memperjuangkan kemerdekaan. Soekarno juga menjadi proklamator yang membacakan naskah proklamasi kemerdekaan Indonesia.",
            "Sumpah Pemuda adalah ikrar yang diucapkan oleh para pemuda Indonesia pada tanggal 28 Oktober 1928. Isinya menyatakan satu tanah air yaitu Indonesia, satu bangsa yaitu bangsa Indonesia, dan satu bahasa yaitu bahasa Indonesia.",
            "Rakyat Indonesia melawan penjajahan Belanda melalui perlawanan bersenjata dan diplomasi. Perlawanan bersenjata dilakukan oleh para pahlawan seperti Diponegoro, Imam Bonjol, dan Cut Nyak Dhien. Perjuangan diplomasi dilakukan melalui organisasi pergerakan nasional.",
            "Pendudukan Jepang membawa dampak buruk bagi rakyat Indonesia. Rakyat dipaksa menjadi romusha yaitu pekerja paksa. Hasil pertanian dirampas untuk kepentingan perang Jepang sehingga rakyat mengalami kelaparan dan penderitaan yang sangat berat.",
        ],
        "Paket 2 — Biologi": [
            "Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau dengan menggunakan cahaya matahari. Tumbuhan menyerap air dan karbondioksida lalu mengubahnya menjadi glukosa dan oksigen. Proses ini terjadi di dalam kloroplas yang mengandung klorofil.",
            "Perbedaan utamanya terletak pada membran inti. Sel prokariotik tidak memiliki membran inti sehingga materi genetiknya tersebar di sitoplasma. Sedangkan sel eukariotik memiliki membran inti yang membungkus materi genetiknya.",
            "Sistem pencernaan berfungsi untuk mengolah makanan menjadi nutrisi yang dapat diserap oleh tubuh. Proses pencernaan dimulai dari mulut lalu melewati kerongkongan, lambung, usus halus, dan usus besar. Nutrisi diserap di usus halus dan sisa makanan dikeluarkan melalui anus.",
            "Ekosistem adalah kesatuan antara makhluk hidup dan lingkungannya yang saling berinteraksi. Komponen ekosistem terdiri dari komponen biotik yaitu makhluk hidup dan komponen abiotik yaitu benda mati seperti air, tanah, udara, dan cahaya matahari.",
            "Pernapasan adalah proses pertukaran gas oksigen dan karbondioksida dalam tubuh. Udara masuk melalui hidung kemudian melewati tenggorokan menuju paru-paru. Di paru-paru terjadi pertukaran gas di alveolus, oksigen masuk ke darah dan karbondioksida dikeluarkan.",
            "Rantai makanan adalah proses makan dan dimakan dalam urutan tertentu dari produsen ke konsumen. Produsen dimakan oleh konsumen tingkat satu, konsumen tingkat satu dimakan konsumen tingkat dua, dan seterusnya. Jaring-jaring makanan adalah kumpulan dari rantai makanan yang saling berhubungan.",
        ],
        "Paket 3 — Pendidikan Kewarganegaraan (PKN)": [
            "Sila pertama Pancasila yaitu Ketuhanan Yang Maha Esa mengandung nilai religius dan toleransi dalam beragama. Setiap warga negara wajib percaya kepada Tuhan Yang Maha Esa sesuai agama dan kepercayaannya masing-masing. Negara menjamin kebebasan beragama bagi seluruh rakyat Indonesia.",
            "Indonesia menganut sistem pemerintahan presidensial berdasarkan UUD 1945. Presiden berkedudukan sebagai kepala negara sekaligus kepala pemerintahan. Kekuasaan negara dibagi menjadi tiga cabang yaitu legislatif, eksekutif, dan yudikatif.",
            "Demokrasi Pancasila adalah sistem demokrasi yang berlandaskan pada nilai-nilai Pancasila. Kedaulatan berada di tangan rakyat dan dilaksanakan melalui musyawarah untuk mufakat. Demokrasi Pancasila mengedepankan keseimbangan antara hak dan kewajiban warga negara.",
            "Warga negara Indonesia memiliki hak untuk mendapatkan pendidikan, pekerjaan, dan penghidupan yang layak. Kewajiban warga negara adalah membela negara, membayar pajak, dan menaati hukum serta peraturan yang berlaku di Indonesia.",
            "Persatuan dan kesatuan bangsa Indonesia sangat penting karena Indonesia terdiri dari berbagai suku, agama, dan budaya yang beragam. Persatuan menjaga keutuhan negara dari ancaman perpecahan. Dengan persatuan rakyat Indonesia dapat bekerja sama membangun bangsa yang lebih maju.",
        ],
    },

    # ===== SISWA B: Parafrase baik (struktur berbeda, kata kunci dipertahankan) — Target 65-90% =====
    "Budi Santoso": {
        "Paket 1 — Sejarah Indonesia": [
            "Pada tanggal 17 Agustus 1945, proklamasi kemerdekaan Indonesia dibacakan oleh Soekarno bersama Mohammad Hatta di Jalan Pegangsaan Timur 56 Jakarta. Sayuti Melik bertugas mengetik naskah proklamasi yang sebelumnya ditulis tangan oleh Soekarno sendiri.",
            "Bangsa Eropa datang ke Indonesia dengan tujuan utama mencari rempah-rempah yang bernilai sangat berharga. Mereka juga ingin menyebarkan agama serta memperluas wilayah kekuasaan mereka. Tiga semangat ini dikenal dengan semboyan Gold, Glory, dan Gospel.",
            "Dalam pergerakan kemerdekaan Indonesia, Soekarno berperan sebagai tokoh utama yang sangat penting. Pada tahun 1927, beliau mendirikan Partai Nasional Indonesia sebagai wadah memperjuangkan kemerdekaan. Soekarno juga dikenal sebagai proklamator yang membacakan naskah proklamasi.",
            "Pada tanggal 28 Oktober 1928, para pemuda Indonesia mengucapkan ikrar yang dikenal sebagai Sumpah Pemuda. Isi Sumpah Pemuda menyatakan satu tanah air Indonesia, satu bangsa Indonesia, dan satu bahasa yaitu bahasa Indonesia.",
            "Rakyat Indonesia melawan penjajahan Belanda dengan dua cara, yaitu perlawanan bersenjata dan diplomasi. Pahlawan seperti Diponegoro, Imam Bonjol, dan Cut Nyak Dhien melakukan perlawanan bersenjata. Sementara perjuangan diplomasi dilakukan melalui organisasi pergerakan nasional.",
            "Pendudukan Jepang memberikan dampak buruk yang besar bagi rakyat Indonesia. Rakyat dijadikan romusha atau pekerja paksa oleh Jepang. Hasil pertanian juga dirampas untuk kepentingan perang sehingga rakyat mengalami kelaparan dan penderitaan hebat.",
        ],
        "Paket 2 — Biologi": [
            "Fotosintesis merupakan proses pembuatan makanan yang dilakukan oleh tumbuhan hijau dengan memanfaatkan cahaya matahari. Air dan karbondioksida diserap tumbuhan kemudian diubah menjadi glukosa dan oksigen. Proses fotosintesis ini berlangsung di kloroplas yang mengandung klorofil.",
            "Perbedaan utama antara sel prokariotik dan sel eukariotik terletak pada membran inti. Sel prokariotik tidak memiliki membran inti sehingga materi genetiknya tersebar di sitoplasma. Sebaliknya sel eukariotik memiliki membran inti yang membungkus materi genetiknya dengan baik.",
            "Sistem pencernaan memiliki fungsi mengolah makanan menjadi nutrisi yang dapat diserap oleh tubuh manusia. Proses pencernaan dimulai dari mulut, melewati kerongkongan, lambung, usus halus, dan usus besar secara berurutan. Nutrisi utama diserap di usus halus sedangkan sisa makanan dikeluarkan melalui anus.",
            "Ekosistem merupakan kesatuan antara makhluk hidup dan lingkungannya yang saling berinteraksi satu sama lain. Komponen ekosistem dibagi menjadi dua yaitu komponen biotik berupa makhluk hidup dan komponen abiotik berupa benda mati seperti air, tanah, udara, dan cahaya matahari.",
            "Pernapasan merupakan proses pertukaran gas oksigen dan karbondioksida dalam tubuh manusia. Udara dihirup melalui hidung lalu melewati tenggorokan dan masuk ke paru-paru. Pertukaran gas terjadi di alveolus dimana oksigen masuk ke darah dan karbondioksida dikeluarkan dari tubuh.",
            "Rantai makanan merupakan proses makan dan dimakan yang berlangsung dalam urutan tertentu dari produsen ke konsumen. Produsen dimakan konsumen tingkat satu, lalu konsumen tingkat satu dimakan konsumen tingkat dua, begitu seterusnya. Jaring-jaring makanan terbentuk dari kumpulan rantai makanan yang saling berhubungan.",
        ],
        "Paket 3 — Pendidikan Kewarganegaraan (PKN)": [
            "Sila pertama Pancasila yaitu Ketuhanan Yang Maha Esa mengandung nilai religius dan juga toleransi beragama. Setiap warga negara wajib percaya kepada Tuhan Yang Maha Esa sesuai agama dan kepercayaan yang dianutnya. Negara menjamin kebebasan beragama bagi seluruh rakyat Indonesia secara merata.",
            "Berdasarkan UUD 1945, Indonesia menganut sistem pemerintahan presidensial. Presiden memiliki kedudukan sebagai kepala negara dan sekaligus kepala pemerintahan. Kekuasaan negara terbagi menjadi tiga bagian yaitu legislatif, eksekutif, dan yudikatif.",
            "Demokrasi Pancasila merupakan sistem demokrasi yang didasarkan pada nilai-nilai Pancasila Indonesia. Kedaulatan tertinggi berada di tangan rakyat dan dilaksanakan melalui musyawarah untuk mufakat. Sistem ini mengedepankan keseimbangan antara hak dan kewajiban warga negara.",
            "Warga negara Indonesia memiliki hak untuk mendapatkan pendidikan, pekerjaan, dan penghidupan yang layak bagi kehidupannya. Adapun kewajiban warga negara meliputi membela negara, membayar pajak, serta menaati hukum dan peraturan yang berlaku.",
            "Persatuan dan kesatuan bangsa Indonesia sangat penting mengingat Indonesia terdiri dari berbagai suku, agama, dan budaya yang beraneka ragam. Persatuan berperan menjaga keutuhan negara dari ancaman perpecahan internal. Dengan bersatu, rakyat Indonesia dapat bekerja sama membangun bangsa menjadi lebih maju.",
        ],
    },

    # ===== SISWA C: Jawaban cukup (beberapa konsep kurang) — Target 55-75% =====
    "Citra Dewi": {
        "Paket 1 — Sejarah Indonesia": [
            "Proklamasi kemerdekaan Indonesia terjadi pada tanggal 17 Agustus 1945. Soekarno dan Hatta membacakan proklamasi di Jakarta. Naskah proklamasi dibuat oleh para tokoh kemerdekaan.",
            "Bangsa Eropa datang ke Indonesia untuk mencari rempah-rempah. Rempah-rempah seperti lada dan cengkeh sangat mahal di Eropa. Mereka juga ingin menguasai wilayah baru.",
            "Soekarno adalah tokoh penting dalam kemerdekaan Indonesia. Beliau mendirikan partai untuk memperjuangkan kemerdekaan. Soekarno menjadi presiden pertama Indonesia.",
            "Sumpah Pemuda terjadi pada tahun 1928. Para pemuda Indonesia bersumpah untuk bersatu. Mereka menyatakan satu nusa, satu bangsa, dan satu bahasa.",
            "Indonesia melawan penjajahan Belanda dengan perlawanan bersenjata. Banyak pahlawan yang berjuang melawan Belanda. Perjuangan juga dilakukan melalui organisasi.",
            "Penjajahan Jepang membuat rakyat Indonesia menderita. Banyak rakyat yang dijadikan pekerja paksa. Hasil pertanian diambil oleh Jepang.",
        ],
        "Paket 2 — Biologi": [
            "Fotosintesis adalah proses tumbuhan membuat makanan menggunakan cahaya matahari. Tumbuhan membutuhkan air dan karbondioksida. Hasil fotosintesis adalah glukosa dan oksigen.",
            "Sel prokariotik tidak memiliki membran inti sedangkan sel eukariotik memiliki membran inti. Materi genetik pada prokariotik tersebar di sitoplasma. Contoh prokariotik adalah bakteri.",
            "Sistem pencernaan manusia berfungsi mencerna makanan. Makanan masuk dari mulut dan diproses di lambung. Nutrisi diserap oleh tubuh di usus halus.",
            "Ekosistem terdiri dari makhluk hidup dan lingkungannya. Ada komponen biotik dan abiotik dalam ekosistem. Komponen abiotik contohnya air dan tanah.",
            "Pernapasan adalah proses mengambil oksigen dan mengeluarkan karbondioksida. Udara masuk melalui hidung ke paru-paru. Di paru-paru terjadi pertukaran gas.",
            "Rantai makanan adalah urutan makan dan dimakan antara makhluk hidup. Dimulai dari produsen yaitu tumbuhan. Jaring-jaring makanan terdiri dari beberapa rantai makanan.",
        ],
        "Paket 3 — Pendidikan Kewarganegaraan (PKN)": [
            "Sila pertama Pancasila adalah Ketuhanan Yang Maha Esa. Setiap warga negara harus percaya kepada Tuhan. Indonesia menjamin kebebasan beragama.",
            "Indonesia menggunakan sistem pemerintahan presidensial. Presiden adalah kepala negara dan kepala pemerintahan. Ada pembagian kekuasaan dalam pemerintahan.",
            "Demokrasi Pancasila adalah demokrasi berdasarkan Pancasila. Keputusan diambil melalui musyawarah mufakat. Rakyat memiliki kedaulatan dalam negara.",
            "Warga negara memiliki hak untuk mendapatkan pendidikan dan pekerjaan. Kewajiban warga negara adalah menaati hukum. Membayar pajak juga merupakan kewajiban.",
            "Persatuan sangat penting bagi Indonesia yang beragam. Indonesia memiliki banyak suku dan budaya. Persatuan menjaga negara dari perpecahan.",
        ],
    },

    # ===== SISWA D: Jawaban minimal (hanya poin utama) — Target 35-55% =====
    "Dimas Nugroho": {
        "Paket 1 — Sejarah Indonesia": [
            "Proklamasi kemerdekaan Indonesia terjadi pada 17 Agustus 1945 oleh Soekarno.",
            "Bangsa Eropa datang ke Indonesia untuk mencari rempah-rempah.",
            "Soekarno mendirikan partai politik dan menjadi proklamator kemerdekaan.",
            "Sumpah Pemuda adalah janji pemuda Indonesia untuk bersatu pada tahun 1928.",
            "Rakyat Indonesia melawan Belanda dengan perang dan diplomasi.",
            "Jepang menjajah Indonesia dan membuat rakyat menderita sebagai romusha.",
        ],
        "Paket 2 — Biologi": [
            "Fotosintesis adalah tumbuhan membuat makanan dengan cahaya matahari.",
            "Sel prokariotik tidak punya membran inti, sel eukariotik punya membran inti.",
            "Sistem pencernaan mencerna makanan dari mulut sampai dibuang.",
            "Ekosistem adalah tempat makhluk hidup berinteraksi dengan lingkungannya.",
            "Pernapasan adalah menghirup oksigen dan mengeluarkan karbondioksida.",
            "Rantai makanan adalah urutan makan dimakan dari tumbuhan ke hewan.",
        ],
        "Paket 3 — Pendidikan Kewarganegaraan (PKN)": [
            "Sila pertama tentang percaya kepada Tuhan Yang Maha Esa.",
            "Indonesia pakai sistem presidensial, presiden jadi pemimpin negara.",
            "Demokrasi Pancasila adalah demokrasi berdasarkan Pancasila dengan musyawarah.",
            "Hak warga negara adalah pendidikan dan pekerjaan, kewajiban adalah bayar pajak.",
            "Persatuan penting karena Indonesia terdiri dari banyak suku dan budaya.",
        ],
    },

    # ===== SISWA E: Jawaban salah/menyimpang — Target 5-30% =====
    "Eka Putri": {
        "Paket 1 — Sejarah Indonesia": [
            "Proklamasi kemerdekaan terjadi di Bandung pada tahun 1950 oleh Mohammad Hatta seorang diri.",
            "Bangsa Eropa datang ke Indonesia untuk berlibur dan menikmati keindahan alam. Mereka juga ingin belajar budaya Indonesia.",
            "Soekarno adalah presiden kedua Indonesia yang membangun banyak jalan tol dan gedung bertingkat di Jakarta.",
            "Sumpah Pemuda adalah acara olahraga yang diadakan setiap tahun di Jakarta untuk memperingati hari kemerdekaan.",
            "Indonesia tidak pernah dijajah oleh negara manapun karena memiliki tentara yang sangat kuat sejak zaman dahulu.",
            "Jepang membantu Indonesia membangun infrastruktur dan memberikan pendidikan gratis kepada seluruh rakyat Indonesia.",
        ],
        "Paket 2 — Biologi": [
            "Fotosintesis adalah proses hewan memakan tumbuhan untuk mendapatkan energi dan vitamin.",
            "Sel prokariotik dan eukariotik sama saja, keduanya memiliki inti sel dan organel yang lengkap.",
            "Sistem pencernaan berfungsi untuk mengalirkan darah ke seluruh tubuh manusia melalui jantung.",
            "Ekosistem adalah kumpulan gedung dan bangunan di suatu kota yang saling terhubung.",
            "Pernapasan adalah proses tubuh menghasilkan makanan dari udara yang dihirup manusia.",
            "Rantai makanan adalah proses tumbuhan memakan hewan kecil untuk mendapatkan nutrisi.",
        ],
        "Paket 3 — Pendidikan Kewarganegaraan (PKN)": [
            "Sila pertama Pancasila adalah tentang keadilan sosial bagi seluruh rakyat Indonesia.",
            "Indonesia menggunakan sistem kerajaan dimana raja memiliki kekuasaan penuh atas negara.",
            "Demokrasi Pancasila adalah sistem dimana presiden memiliki kekuasaan mutlak tanpa perlu persetujuan rakyat.",
            "Warga negara tidak memiliki kewajiban apapun, semua kebutuhan disediakan oleh pemerintah secara gratis.",
            "Persatuan tidak diperlukan karena setiap daerah sebaiknya menjadi negara merdeka sendiri.",
        ],
    },
}

# ============================================================
# GENERATE HTML → PDF
# ============================================================
def generate_soal_html():
    """Generate HTML file containing all 3 exam packages."""

    html = '''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Paket Soal Ujian — EssayGrader</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --primary: #1a365d;
            --primary-light: #2c5282;
            --accent: #3182ce;
            --accent-light: #63b3ed;
            --bg: #ffffff;
            --text: #1a202c;
            --text-secondary: #4a5568;
            --border: #e2e8f0;
            --sejarah: #c53030;
            --biologi: #2f855a;
            --pkn: #2b6cb0;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', 'Segoe UI', sans-serif;
            font-size: 11pt;
            line-height: 1.7;
            color: var(--text);
            background: var(--bg);
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
        }

        @media print {
            body { padding: 0; max-width: none; }
            @page { size: A4; margin: 20mm; }
            .page-break { page-break-before: always; }
            h1, h2, h3 { page-break-after: avoid; }
        }

        .cover {
            text-align: center;
            padding: 60px 20px;
            border: 3px solid var(--primary);
            border-radius: 12px;
            margin-bottom: 40px;
        }

        .cover h1 {
            font-size: 28pt;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }

        .cover .subtitle {
            font-size: 14pt;
            color: var(--text-secondary);
            margin-bottom: 30px;
        }

        .cover .info {
            font-size: 10pt;
            color: var(--text-secondary);
            line-height: 1.8;
        }

        .paket-header {
            background: var(--primary);
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .paket-header h2 {
            font-size: 16pt;
            font-weight: 700;
        }

        .paket-header .badge {
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 9pt;
            font-weight: 600;
        }

        .paket-sejarah .paket-header { background: var(--sejarah); }
        .paket-biologi .paket-header { background: var(--biologi); }
        .paket-pkn .paket-header { background: var(--pkn); }

        .question-card {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px 22px;
            margin-bottom: 18px;
            background: #fafbfc;
        }

        .question-number {
            font-weight: 700;
            color: var(--primary);
            font-size: 10pt;
            margin-bottom: 6px;
        }

        .question-text {
            font-size: 11pt;
            font-weight: 500;
            margin-bottom: 10px;
        }

        .points-badge {
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 9pt;
            font-weight: 600;
        }

        .answer-space {
            border: 1px dashed #cbd5e0;
            border-radius: 6px;
            padding: 12px;
            margin-top: 10px;
            min-height: 60px;
            background: white;
        }

        .answer-space p {
            font-size: 9pt;
            color: #a0aec0;
            font-style: italic;
        }

        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 15px;
            border-top: 2px solid var(--border);
            font-size: 8.5pt;
            color: var(--text-secondary);
        }

        .kunci-section {
            margin-top: 30px;
            padding: 20px;
            background: #f0fff4;
            border: 2px solid #c6f6d5;
            border-radius: 8px;
        }

        .kunci-section h3 {
            color: #2f855a;
            margin-bottom: 10px;
        }

        .kunci-item {
            margin-bottom: 12px;
            padding: 8px 12px;
            background: white;
            border-radius: 6px;
            border-left: 3px solid #38a169;
        }

        .kunci-item .kunci-label {
            font-weight: 700;
            font-size: 9pt;
            color: #2f855a;
        }

        .kunci-item .kunci-text {
            font-size: 10pt;
            color: var(--text);
            margin-top: 2px;
        }
    </style>
</head>
<body>
'''

    # Cover page
    html += '''
    <div class="cover">
        <h1>📝 Paket Soal Ujian</h1>
        <div class="subtitle">EssayGrader — Sistem Penilaian Esai Otomatis</div>
        <div class="info">
            <strong>Mata Pelajaran:</strong> Sejarah Indonesia, Biologi, PKN<br>
            <strong>Jumlah Paket:</strong> 3 paket soal<br>
            <strong>Total Soal:</strong> 17 soal esai<br>
            <strong>Waktu Pengerjaan:</strong> 90 menit per paket<br>
            <br>
            <em>Dokumen ini digenerate oleh sistem EssayGrader</em>
        </div>
    </div>
'''

    # Generate each paket
    paket_classes = {
        "Paket 1 — Sejarah Indonesia": "paket-sejarah",
        "Paket 2 — Biologi": "paket-biologi",
        "Paket 3 — Pendidikan Kewarganegaraan (PKN)": "paket-pkn",
    }

    for paket_name, paket_data in PAKET_SOAL.items():
        css_class = paket_classes.get(paket_name, "")
        subject = paket_data["subject"]
        questions = paket_data["questions"]

        html += f'''
    <div class="page-break"></div>
    <div class="{css_class}">
        <div class="paket-header">
            <h2>{paket_name}</h2>
            <span class="badge">{len(questions)} Soal · Mata Pelajaran: {subject}</span>
        </div>
'''

        for q in questions:
            html += f'''
        <div class="question-card">
            <div class="question-number">Soal {q["no"]} <span class="points-badge">{q["poin"]} poin</span></div>
            <div class="question-text">{q["soal"]}</div>
            <div class="answer-space">
                <p>Tulis jawaban di sini...</p>
            </div>
        </div>
'''

        # Kunci jawaban section
        html += f'''
        <div class="kunci-section">
            <h3>🔑 Kunci Jawaban — {paket_name}</h3>
'''
        for q in questions:
            html += f'''
            <div class="kunci-item">
                <div class="kunci-label">Soal {q["no"]} ({q["poin"]} poin)</div>
                <div class="kunci-text">{q["kunci"]}</div>
            </div>
'''
        html += '        </div>\n    </div>\n'

    # Footer
    html += '''
    <div class="footer">
        <p><strong>EssayGrader</strong> — Sistem Penilaian Esai Otomatis Berbasis Aljabar Linier</p>
        <p>Dokumen digenerate secara otomatis · Jangan dibagikan kepada siswa</p>
    </div>
</body>
</html>'''

    return html


def generate_jawaban_html():
    """Generate HTML file containing all student answers."""

    html = '''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Jawaban Siswa — EssayGrader</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --primary: #1a365d;
            --text: #1a202c;
            --text-secondary: #4a5568;
            --border: #e2e8f0;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: var(--text);
            max-width: 210mm;
            margin: 0 auto;
            padding: 15mm;
        }

        @media print {
            body { padding: 0; max-width: none; }
            @page { size: A4; margin: 15mm; }
            .page-break { page-break-before: always; }
        }

        h1 {
            font-size: 20pt;
            color: var(--primary);
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid var(--primary);
        }

        .student-section {
            margin-bottom: 30px;
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }

        .student-header {
            background: var(--primary);
            color: white;
            padding: 10px 18px;
            font-size: 12pt;
            font-weight: 700;
        }

        .paket-title {
            background: #edf2f7;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 10pt;
            color: var(--primary);
            border-bottom: 1px solid var(--border);
        }

        .answer-row {
            padding: 8px 18px;
            border-bottom: 1px solid #f7fafc;
            font-size: 9.5pt;
        }

        .answer-row:nth-child(even) {
            background: #fafbfc;
        }

        .answer-label {
            font-weight: 600;
            color: var(--primary);
            font-size: 9pt;
        }

        .answer-text {
            margin-top: 2px;
            color: var(--text);
        }
    </style>
</head>
<body>
    <h1>📋 Lembar Jawaban Siswa</h1>
'''

    for student_name, pakets in JAWABAN_SISWA.items():
        html += f'''
    <div class="student-section">
        <div class="student-header">👤 {student_name}</div>
'''
        for paket_name, answers in pakets.items():
            html += f'        <div class="paket-title">📦 {paket_name}</div>\n'
            for i, answer in enumerate(answers):
                html += f'''        <div class="answer-row">
            <div class="answer-label">Jawaban Soal {i+1}:</div>
            <div class="answer-text">{answer}</div>
        </div>
'''
        html += '    </div>\n'

    html += '''
</body>
</html>'''

    return html


def generate_json_data():
    """Generate JSON data file for programmatic import."""
    data = {
        "paket_soal": {},
        "jawaban_siswa": JAWABAN_SISWA,
    }

    for paket_name, paket_data in PAKET_SOAL.items():
        data["paket_soal"][paket_name] = {
            "subject": paket_data["subject"],
            "questions": paket_data["questions"],
        }

    return json.dumps(data, ensure_ascii=False, indent=2)


def try_convert_to_pdf(html_path, pdf_path):
    """Try to convert HTML to PDF using browser."""
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    ]
    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]

    browser_path = None
    for p in chrome_paths + edge_paths:
        if os.path.exists(p):
            browser_path = p
            break

    if not browser_path:
        return False

    try:
        abs_html = os.path.abspath(html_path)
        file_url = f'file:///{abs_html.replace(os.sep, "/")}'

        cmd = [
            browser_path, '--headless', '--disable-gpu', '--no-sandbox',
            '--disable-software-rasterizer',
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=10000',
            f'--print-to-pdf={pdf_path}',
            '--print-to-pdf-no-header',
            '--no-pdf-header-footer',
            file_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
            return True
    except Exception as e:
        print(f"⚠️  Browser PDF error: {e}")

    return False


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Generate Soal HTML
    print("📝 Generating soal HTML...")
    soal_html = generate_soal_html()
    soal_html_path = os.path.join(base_dir, 'paket_soal.html')
    with open(soal_html_path, 'w', encoding='utf-8') as f:
        f.write(soal_html)
    print(f"   ✅ {soal_html_path}")

    # 2. Generate Jawaban HTML
    print("📋 Generating jawaban siswa HTML...")
    jawaban_html = generate_jawaban_html()
    jawaban_html_path = os.path.join(base_dir, 'jawaban_siswa.html')
    with open(jawaban_html_path, 'w', encoding='utf-8') as f:
        f.write(jawaban_html)
    print(f"   ✅ {jawaban_html_path}")

    # 3. Generate JSON data
    print("📊 Generating JSON data...")
    json_data = generate_json_data()
    json_path = os.path.join(base_dir, 'soal_jawaban_data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_data)
    print(f"   ✅ {json_path}")

    # 4. Try PDF conversion
    print("\n🖨️  Converting to PDF...")
    soal_pdf_path = os.path.join(base_dir, 'paket_soal.pdf')
    jawaban_pdf_path = os.path.join(base_dir, 'jawaban_siswa.pdf')

    pdf1 = try_convert_to_pdf(soal_html_path, soal_pdf_path)
    if pdf1:
        print(f"   ✅ Soal PDF: {soal_pdf_path} ({os.path.getsize(soal_pdf_path):,} bytes)")
    else:
        print(f"   ⚠️  Soal PDF gagal. Buka {soal_html_path} di browser dan Ctrl+P → Save as PDF")

    pdf2 = try_convert_to_pdf(jawaban_html_path, jawaban_pdf_path)
    if pdf2:
        print(f"   ✅ Jawaban PDF: {jawaban_pdf_path} ({os.path.getsize(jawaban_pdf_path):,} bytes)")
    else:
        print(f"   ⚠️  Jawaban PDF gagal. Buka {jawaban_html_path} di browser dan Ctrl+P → Save as PDF")

    # 5. Summary
    print("\n" + "=" * 60)
    print("📊 RINGKASAN")
    print("=" * 60)
    print(f"  Paket Soal : 3 paket")
    total_q = sum(len(p["questions"]) for p in PAKET_SOAL.values())
    print(f"  Total Soal : {total_q} soal")
    print(f"  Siswa      : {len(JAWABAN_SISWA)} siswa")
    print(f"  File HTML  : paket_soal.html, jawaban_siswa.html")
    print(f"  File JSON  : soal_jawaban_data.json")
    print(f"  File PDF   : {'✅' if pdf1 else '❌'} paket_soal.pdf, {'✅' if pdf2 else '❌'} jawaban_siswa.pdf")
    print("=" * 60)

    print("\n📋 DISTRIBUSI JAWABAN SISWA:")
    print("-" * 50)
    print(f"  Andi Pratama  → Jawaban sangat baik (target 90-100%)")
    print(f"  Budi Santoso  → Parafrase baik      (target 75-90%)")
    print(f"  Citra Dewi    → Jawaban cukup        (target 55-75%)")
    print(f"  Dimas Nugroho → Jawaban minimal      (target 35-55%)")
    print(f"  Eka Putri     → Jawaban salah        (target 5-30%)")


if __name__ == '__main__':
    main()
