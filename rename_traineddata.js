const fs = require('fs');
const path = require('path');

// Define the mapping of current filenames to new ISO 3-letter language codes
const renameMapping = {
    "afr.traineddata": "afr.traineddata",  // Afrikaans
    "amh.traineddata": "amh.traineddata",  // Amharic
    "ara.traineddata": "ara.traineddata",  // Arabic
    "asm.traineddata": "asm.traineddata",  // Assamese
    "aze.traineddata": "aze.traineddata",  // Azerbaijani
    "aze_cyrl.traineddata": "aze_cyrl.traineddata",  // Azerbaijani (Cyrillic)
    "bel.traineddata": "bel.traineddata",  // Belarusian
    "ben.traineddata": "ben.traineddata",  // Bengali
    "bod.traineddata": "bod.traineddata",  // Tibetan
    "bos.traineddata": "bos.traineddata",  // Bosnian
    "bre.traineddata": "bre.traineddata",  // Breton
    "bul.traineddata": "bul.traineddata",  // Bulgarian
    "cat.traineddata": "cat.traineddata",  // Catalan
    "ceb.traineddata": "ceb.traineddata",  // Cebuano
    "ces.traineddata": "ces.traineddata",  // Czech
    "chi_sim.traineddata": "chi_sim.traineddata",  // Chinese (Simplified)
    "chi_sim_vert.traineddata": "chi_sim_vert.traineddata",  // Chinese (Simplified, Vertical)
    "chi_tra.traineddata": "chi_tra.traineddata",  // Chinese (Traditional)
    "chi_tra_vert.traineddata": "chi_tra_vert.traineddata",  // Chinese (Traditional, Vertical)
    "chr.traineddata": "chr.traineddata",  // Cherokee
    "cos.traineddata": "cos.traineddata",  // Corsican
    "cym.traineddata": "cym.traineddata",  // Welsh
    "dan.traineddata": "dan.traineddata",  // Danish
    "dan_frak.traineddata": "dan_frak.traineddata",  // Danish (Fraktur)
    "deu.traineddata": "ger.traineddata",  // German
    "deu_frak.traineddata": "deu_frak.traineddata",  // German (Fraktur)
    "deu_latf.traineddata": "deu_latf.traineddata",  // German (Latin Fraktur)
    "div.traineddata": "div.traineddata",  // Dhivehi
    "dzo.traineddata": "dzo.traineddata",  // Dzongkha
    "ell.traineddata": "ell.traineddata",  // Greek
    "eng.traineddata": "eng.traineddata",  // English
    "enm.traineddata": "enm.traineddata",  // Middle English
    "epo.traineddata": "epo.traineddata",  // Esperanto
    "equ.traineddata": "equ.traineddata",  // Mathematical Equations
    "est.traineddata": "est.traineddata",  // Estonian
    "eus.traineddata": "eus.traineddata",  // Basque
    "fao.traineddata": "fao.traineddata",  // Faroese
    "fas.traineddata": "fas.traineddata",  // Persian
    "fil.traineddata": "fil.traineddata",  // Filipino
    "fin.traineddata": "fin.traineddata",  // Finnish
    "fra.traineddata": "fra.traineddata",  // French
    "frm.traineddata": "frm.traineddata",  // Middle French
    "fry.traineddata": "fry.traineddata",  // Frisian
    "gla.traineddata": "gla.traineddata",  // Scottish Gaelic
    "gle.traineddata": "gle.traineddata",  // Irish
    "glg.traineddata": "glg.traineddata",  // Galician
    "grc.traineddata": "grc.traineddata",  // Ancient Greek
    "guj.traineddata": "guj.traineddata",  // Gujarati
    "hat.traineddata": "hat.traineddata",  // Haitian Creole
    "heb.traineddata": "heb.traineddata",  // Hebrew
    "hin.traineddata": "hin.traineddata",  // Hindi
    "hrv.traineddata": "hrv.traineddata",  // Croatian
    "hun.traineddata": "hun.traineddata",  // Hungarian
    "hye.traineddata": "hye.traineddata",  // Armenian
    "iku.traineddata": "iku.traineddata",  // Inuktitut
    "ind.traineddata": "ind.traineddata",  // Indonesian
    "isl.traineddata": "isl.traineddata",  // Icelandic
    "ita.traineddata": "ita.traineddata",  // Italian
    "ita_old.traineddata": "ita_old.traineddata",  // Old Italian
    "jav.traineddata": "jav.traineddata",  // Javanese
    "jpn.traineddata": "jpn.traineddata",  // Japanese
    "jpn_vert.traineddata": "jpn_vert.traineddata",  // Japanese (Vertical)
    "kan.traineddata": "kan.traineddata",  // Kannada
    "kat.traineddata": "kat.traineddata",  // Georgian
    "kat_old.traineddata": "kat_old.traineddata",  // Old Georgian
    "kaz.traineddata": "kaz.traineddata",  // Kazakh
    "khm.traineddata": "khm.traineddata",  // Khmer
    "kir.traineddata": "kir.traineddata",  // Kyrgyz
    "kmr.traineddata": "kmr.traineddata",  // Kurdish (Latin)
    "kor.traineddata": "kor.traineddata",  // Korean
    "kor_vert.traineddata": "kor_vert.traineddata",  // Korean (Vertical)
    "lao.traineddata": "lao.traineddata",  // Lao
    "lat.traineddata": "lat.traineddata",  // Latvian
    "lav.traineddata": "lav.traineddata",  // Latvian
    "lit.traineddata": "lit.traineddata",  // Lithuanian
    "ltz.traineddata": "ltz.traineddata",  // Luxembourgish
    "mal.traineddata": "mal.traineddata",  // Malayalam
    "mar.traineddata": "mar.traineddata",  // Marathi
    "mkd.traineddata": "mkd.traineddata",  // Macedonian
    "mlt.traineddata": "mlt.traineddata",  // Maltese
    "mon.traineddata": "mon.traineddata",  // Mongolian
    "mri.traineddata": "mri.traineddata",  // Māori
    "msa.traineddata": "msa.traineddata",  // Malay
    "mya.traineddata": "mya.traineddata",  // Burmese
    "nep.traineddata": "nep.traineddata",  // Nepali
    "nld.traineddata": "dut.traineddata",  // Dutch
    "nor.traineddata": "nor.traineddata",  // Norwegian
    "oci.traineddata": "oci.traineddata",  // Occitan
    "ori.traineddata": "ori.traineddata",  // Odia
    "osd.traineddata": "osd.traineddata",  // Old South Slavic
    "pan.traineddata": "pan.traineddata",  // Punjabi
    "pol.traineddata": "pol.traineddata",  // Polish
    "por.traineddata": "por.traineddata",  // Portuguese
    "pus.traineddata": "pus.traineddata",  // Pashto
    "que.traineddata": "que.traineddata",  // Quechua
    "ron.traineddata": "ron.traineddata",  // Romanian
    "rus.traineddata": "rus.traineddata",  // Russian
    "san.traineddata": "san.traineddata",  // Sanskrit
    "sin.traineddata": "sin.traineddata",  // Sinhalese
    "slk.traineddata": "slk.traineddata",  // Slovak
    "slk_frak.traineddata": "slk_frak.traineddata",  // Slovak (Fraktur)
    "slv.traineddata": "slv.traineddata",  // Slovenian
    "snd.traineddata": "snd.traineddata",  // Sindhi
    "spa.traineddata": "spa.traineddata",  // Spanish
    "spa_old.traineddata": "spa_old.traineddata",  // Old Spanish
    "sqi.traineddata": "sqi.traineddata",  // Albanian
    "srp.traineddata": "srp.traineddata",  // Serbian
    "srp_latn.traineddata": "srp_latn.traineddata",  // Serbian (Latin)
    "sun.traineddata": "sun.traineddata",  // Sundanese
    "swa.traineddata": "swa.traineddata",  // Swahili
    "swe.traineddata": "swe.traineddata",  // Swedish
    "syr.traineddata": "syr.traineddata",  // Syriac
    "tam.traineddata": "tam.traineddata",  // Tamil
    "tat.traineddata": "tat.traineddata",  // Tatar
    "tel.traineddata": "tel.traineddata",  // Telugu
    "tgk.traineddata": "tgk.traineddata",  // Tajik
    "tgl.traineddata": "tgl.traineddata",  // Tagalog
    "tha.traineddata": "tha.traineddata",  // Thai
    "tir.traineddata": "tir.traineddata",  // Tigrinya
    "ton.traineddata": "ton.traineddata",  // Tongan
    "tur.traineddata": "tur.traineddata",  // Turkish
    "uig.traineddata": "uig.traineddata",  // Uyghur
    "ukr.traineddata": "ukr.traineddata",  // Ukrainian
    "urd.traineddata": "urd.traineddata",  // Urdu
    "uzb.traineddata": "uzb.traineddata",  // Uzbek
    "uzb_cyrl.traineddata": "uzb_cyrl.traineddata",  // Uzbek (Cyrillic)
    "vie.traineddata": "vie.traineddata",  // Vietnamese
    "yid.traineddata": "yid.traineddata",  // Yiddish
    "yor.traineddata": "yor.traineddata",  // Yoruba
};

// Path to the directory containing the traineddata files
const directoryPath = 'c:\\Projects\\NoMercy\\tools\\nomercy-tesseract';

// Rename the files according to the mapping
for (const [oldName, newName] of Object.entries(renameMapping)) {
    const oldFilePath = path.join(directoryPath, oldName);
    const newFilePath = path.join(directoryPath, newName);
    
    // Check if the old file exists before renaming
    fs.rename(oldFilePath, newFilePath, (err) => {
        if (err) {
            console.error(`Error renaming ${oldName}:`, err);
        } else {
            console.log(`Renamed: ${oldName} -> ${newName}`);
        }
    });
}