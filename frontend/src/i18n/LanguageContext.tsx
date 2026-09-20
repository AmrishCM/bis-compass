import React, { createContext, useContext, useState, useEffect } from 'react';

export type SupportedLanguage = 'en' | 'hi' | 'ta' | 'te' | 'kn' | 'ml';

export interface LanguageOption {
  code: SupportedLanguage;
  name: string;
  nativeName: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'ml', name: 'Malayalam', nativeName: 'മലയാളം' }
];

export const STATIC_TRANSLATIONS: Record<SupportedLanguage, Record<string, string>> = {
  en: {
    app_title: "BIS-Compass",
    app_subtitle: "AI-Powered Indian Standards & BIS Compliance Intelligence Platform",
    nav_dashboard: "Dashboard",
    nav_analyze: "Compliance Analysis",
    nav_standards: "Standards Directory",
    nav_labs: "Testing Labs",
    nav_compliance: "Gap Analysis",
    nav_audit: "Audit History",
    btn_ask_advisor: "Ask Advisor",
    btn_analyze: "Analyze Product Compliance",
    btn_analyzing: "Researching BIS Knowledge...",
    btn_clear: "Clear",
    btn_clarify: "Clarify Specifications",
    product_profile: "Product Profile",
    product_family: "Product Family",
    intended_use: "Intended Use",
    materials: "Materials Identified",
    applicable_standards: "Applicable Indian Standards",
    potential_standards: "Standards Requiring Clarification",
    what_you_need_to_do: "What You Need To Do",
    mandatory_status: "Mandatory Regulatory Status",
    voluntary_status: "Voluntary Indian Standard",
    qco_not_confirmed: "Certification requirement not confirmed — verify with your local BIS office",
    qco_mandatory: "Mandatory under Quality Control Order (QCO)",
    certification_scheme: "Certification Scheme",
    testing_requirements: "Required Compliance Tests",
    step_by_step_next_actions: "Step-by-Step Next Actions",
    testing_laboratories: "Accredited Testing Laboratories",
    no_labs_found: "No BIS-recognized testing laboratories currently verified within your immediate geographic proximity. You may expand your search radius or consult the BIS National Laboratory Directory at manakonline.in.",
    not_verified: "Not Verified",
    verified: "Verified",
    scope_verified: "Scope Verified",
    distance_not_verified: "Distance not verified"
  },
  hi: {
    app_title: "BIS-कंपास",
    app_subtitle: "एआई-संचालित भारतीय मानक एवं बीआईएस अनुपालन इंटेलिजेंस प्लेटफॉर्म",
    nav_dashboard: "डैशबोर्ड",
    nav_analyze: "अनुपालन विश्लेषण",
    nav_standards: "मानक निर्देशिका",
    nav_labs: "परीक्षण प्रयोगशालाएं",
    nav_compliance: "गैप विश्लेषण",
    nav_audit: "ऑडिट इतिहास",
    btn_ask_advisor: "सलाहकार से पूछें",
    btn_analyze: "उत्पाद अनुपालन विश्लेषण करें",
    btn_analyzing: "बीआईएस डेटाबेस अनुसंधान जारी है...",
    btn_clear: "हटाएं",
    btn_clarify: "विशिष्टताएं स्पष्ट करें",
    product_profile: "उत्पाद प्रोफ़ाइल",
    product_family: "उत्पाद परिवार",
    intended_use: "लक्षित उपयोग",
    materials: "पहचानी गई सामग्री",
    applicable_standards: "लागू भारतीय मानक",
    potential_standards: "स्पष्टीकरण की आवश्यकता वाले मानक",
    what_you_need_to_do: "आपको क्या करने की आवश्यकता है",
    mandatory_status: "अनिवार्य विनियामक स्थिति",
    voluntary_status: "स्वैच्छिक भारतीय मानक",
    qco_not_confirmed: "प्रमाणन आवश्यकता की पुष्टि नहीं हुई है — अपने स्थानीय बीआईएस कार्यालय से सत्यापित करें",
    qco_mandatory: "गुणवत्ता नियंत्रण आदेश (QCO) के तहत अनिवार्य",
    certification_scheme: "प्रमाणन योजना",
    testing_requirements: "आवश्यक अनुपालन परीक्षण",
    step_by_step_next_actions: "क्रमबद्ध अगले कदम",
    testing_laboratories: "मान्यता प्राप्त परीक्षण प्रयोगशालाएं",
    no_labs_found: "आपकी भौगोलिक निकटता में कोई बीआईएस मान्यता प्राप्त प्रयोगशाला सत्यापित नहीं हुई। राष्ट्रीय निर्देशिका manakonline.in देखें।",
    not_verified: "सत्यापित नहीं",
    verified: "सत्यापित",
    scope_verified: "कार्यक्षेत्र सत्यापित",
    distance_not_verified: "दूरी सत्यापित नहीं"
  },
  ta: {
    app_title: "BIS-காம்பஸ்",
    app_subtitle: "செயற்கை நுண்ணறிவு அடிப்படையிலான இந்தியத் தரநிலைகள் மற்றும் BIS இணக்க தளம்",
    nav_dashboard: "டாஷ்போர்டு",
    nav_analyze: "இணக்க பகுப்பாய்வு",
    nav_standards: "தரநிலைகள் அடைவு",
    nav_labs: "சோதனை ஆய்வகங்கள்",
    nav_compliance: "இடைவெளி பகுப்பாய்வு",
    nav_audit: "தணிக்கை வரலாறு",
    btn_ask_advisor: "ஆலோசகரிடம் கேளுங்கள்",
    btn_analyze: "தயாரிப்பு இணக்கத்தை பகுப்பாய்வு செய்க",
    btn_analyzing: "BIS தரவுத்தளத்தில் தேடுகிறது...",
    btn_clear: "அழிக்கவும்",
    btn_clarify: "விவரங்களை தெளிவுபடுத்தவும்",
    product_profile: "தயாரிப்பு சுயவிவரம்",
    product_family: "தயாரிப்பு குடும்பம்",
    intended_use: "பயன்பாட்டு நோக்கம்",
    materials: "கண்டறியப்பட்ட பொருட்கள்",
    applicable_standards: "பொருந்தக்கூடிய இந்தியத் தரநிலைகள்",
    potential_standards: "தெளிவுபடுத்தப்பட வேண்டிய தரநிலைகள்",
    what_you_need_to_do: "நீங்கள் செய்ய வேண்டியவை",
    mandatory_status: "கட்டாய ஒழுங்குமுறை நிலை",
    voluntary_status: "தன்னார்வ இந்தியத் தரநிலை",
    qco_not_confirmed: "சான்றிதழ் தேவை உறுதிப்படுத்தப்படவில்லை — உங்கள் உள்ளூர் BIS அலுவலகத்துடன் சரிபார்க்கவும்",
    qco_mandatory: "தரக் கட்டுப்பாட்டு ஆணையின் கீழ் கட்டாயமானது (QCO)",
    certification_scheme: "சான்றிதழ் திட்டம்",
    testing_requirements: "தேவையான இணக்க சோதனைகள்",
    step_by_step_next_actions: "அடுத்த கட்ட நடைமுறைகள்",
    testing_laboratories: "அங்கீகரிக்கப்பட்ட சோதனை ஆய்வகங்கள்",
    no_labs_found: "உங்கள் அருகாமையில் BIS அங்கீகரிக்கப்பட்ட ஆய்வகங்கள் எதுவும் இல்லை. manakonline.in ஐப் பார்க்கவும்.",
    not_verified: "சரிபார்க்கப்படவில்லை",
    verified: "சரிபார்க்கப்பட்டது",
    scope_verified: "நோக்கம் சரிபார்க்கப்பட்டது",
    distance_not_verified: "தூரம் சரிபார்க்கப்படவில்லை"
  },
  te: {
    app_title: "BIS-కంపాస్",
    app_subtitle: "భారతీయ ప్రమాణాలు మరియు BIS నిబంధనల అనుకూలత ప్లాట్‌ఫారమ్",
    nav_dashboard: "డ్యాష్‌బోర్డ్",
    nav_analyze: "సమ్మతి విశ్లేషణ",
    nav_standards: "ప్రమాణాల డైరెక్టరీ",
    nav_labs: "పరీక్ష ప్రయోగశాలలు",
    nav_compliance: "గ్యాప్ విశ్లేషణ",
    nav_audit: "ఆడిట్ చరిత్ర",
    btn_ask_advisor: "సలహాదారుని అడగండి",
    btn_analyze: "ఉత్పత్తి సమ్మతిని విశ్లేషించండి",
    btn_analyzing: "పరిశోధన జరుగుతోంది...",
    btn_clear: "క్లియర్ చేయండి",
    btn_clarify: "వివరాలను స్పష్టం చేయండి",
    product_profile: "ఉత్పత్తి ప్రొఫైల్",
    product_family: "ఉత్పత్తి కుటుంబం",
    intended_use: "ఉద్దేశించిన ఉపయోగం",
    materials: "గుర్తించిన పదార్థాలు",
    applicable_standards: "వర్తించే భారతీయ ప్రమాణాలు",
    potential_standards: "స్పష్టత అవసరమైన ప్రమాణాలు",
    what_you_need_to_do: "మీరు చేయవలసిన పనులు",
    mandatory_status: "తప్పనిసరి నియంత్రణ స్థితి",
    voluntary_status: "స్వచ్ఛంద భారతీయ ప్రమాణం",
    qco_not_confirmed: "సర్టిఫికేషన్ అవసరం నిర్ధారించబడలేదు — మీ స్థానిక BIS కార్యాలయంతో ధృవీకరించండి",
    qco_mandatory: "క్వాలిటీ కంట్రోల్ ఆర్డర్ (QCO) కింద తప్పనిసరి",
    certification_scheme: "సర్టిఫికేషన్ పథకం",
    testing_requirements: "అవసరమైన పరీక్షలు",
    step_by_step_next_actions: "తదుపరి చర్యలు",
    testing_laboratories: "గుర్తింపు పొందిన ప్రయోగశాలలు",
    no_labs_found: "సమీపంలో ల్యాబ్‌లు కనుగొనబడలేదు. జాతీయ డైరెక్టరీ manakonline.in ను సంప్రదించండి.",
    not_verified: "ధృవీకరించబడలేదు",
    verified: "ధృవీకరించబడింది",
    scope_verified: "పరిధి ధృవీకరించబడింది",
    distance_not_verified: "దూరం ధృవీకరించబడలేదు"
  },
  kn: {
    app_title: "BIS-ಕಂಪಾಸ್",
    app_subtitle: "ಭಾರತೀಯ ಮಾನದಂಡಗಳು ಮತ್ತು BIS ಅನುಸರಣೆ ಇಂಟೆಲಿಜೆನ್ಸ್ ಪ್ಲಾಟ್‌ಫಾರ್ಮ್",
    nav_dashboard: "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
    nav_analyze: "ಅನುಸರಣೆ ವಿಶ್ಲೇಷಣೆ",
    nav_standards: "ಮಾನದಂಡಗಳ ಡೈರೆಕ್ಟರಿ",
    nav_labs: "ಪರೀಕ್ಷಾ ಪ್ರಯೋಗಾಲಯಗಳು",
    nav_compliance: "ಅಂತರ ವಿಶ್ಲೇಷಣೆ",
    nav_audit: "ಆಡಿಟ್ ಇತಿಹಾಸ",
    btn_ask_advisor: "ಸಲಹೆಗಾರರನ್ನು ಕೇಳಿ",
    btn_analyze: "ಉತ್ಪನ್ನ ಅನುಸರಣೆ ವಿಶ್ಲೇಷಿಸಿ",
    btn_analyzing: "ಸಂಶೋಧನೆ ನಡೆಯುತ್ತಿದೆ...",
    btn_clear: "ತೆರವುಗೊಳಿಸಿ",
    btn_clarify: "ವಿವರಣೆ ಸ್ಪಷ್ಟಪಡಿಸಿ",
    product_profile: "ಉತ್ಪನ್ನ ಪ್ರೊಫೈಲ್",
    product_family: "ಉತ್ಪನ್ನ ಕುಟುಂಬ",
    intended_use: "ಉದ್ದೇಶಿತ ಬಳಕೆ",
    materials: "ಗುರುತಿಸಲಾದ ವಸ್ತುಗಳು",
    applicable_standards: "ಅನ್ವಯವಾಗುವ ಭಾರತೀಯ ಮಾನದಂಡಗಳು",
    potential_standards: "ಸ್ಪಷ್ಟೀಕರಣ ಅಗತ್ಯವಿರುವ ಮಾನದಂಡಗಳು",
    what_you_need_to_do: "ನೀವು ಏನು ಮಾಡಬೇಕು",
    mandatory_status: "ಕಡ್ಡಾಯ ನಿಯಂತ್ರಕ ಸ್ಥಿತಿ",
    voluntary_status: "ಸ್ವಯಂಪ್ರೇರಿತ ಭಾರತೀಯ ಮಾನದಂಡ",
    qco_not_confirmed: "ಪ್ರಮಾಣೀಕರಣ ಅವಶ್ಯಕತೆ ದೃಢಪಟ್ಟಿಲ್ಲ — ನಿಮ್ಮ ಸ್ಥಳೀಯ BIS ಕಚೇರಿಯೊಂದಿಗೆ ಪರಿಶೀಲಿಸಿ",
    qco_mandatory: "ಗುಣಮಟ್ಟ ನಿಯಂತ್ರಣ ಆದೇಶದಡಿ ಕಡ್ಡಾಯವಾಗಿದೆ (QCO)",
    certification_scheme: "ಪ್ರಮಾಣೀಕರಣ ಯೋಜನೆ",
    testing_requirements: "ಅಗತ್ಯವಿರುವ ಪರೀಕ್ಷೆಗಳು",
    step_by_step_next_actions: "ಮುಂದಿನ ಹಂತಗಳು",
    testing_laboratories: "ಗುರುತಿಸಲ್ಪಟ್ಟ ಪರೀಕ್ಷಾ ಪ್ರಯೋಗಾಲಯಗಳು",
    no_labs_found: "ಹತ್ತಿರದಲ್ಲಿ ಯಾವುದೇ ಪ್ರಯೋಗಾಲಯಗಳು ಕಂಡುಬಂದಿಲ್ಲ. manakonline.in ನಲ್ಲಿ ಪರಿಶೀಲಿಸಿ.",
    not_verified: "ಪರಿಶೀಲಿಸಲಾಗಿಲ್ಲ",
    verified: "ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
    scope_verified: "ವ್ಯಾಪ್ತಿ ಪರಿಶೀಲಿಸಲಾಗಿದೆ",
    distance_not_verified: "ದೂರ ಪರಿಶೀಲಿಸಲಾಗಿಲ್ಲ"
  },
  ml: {
    app_title: "BIS-കോമ്പസ്",
    app_subtitle: "ഇന്ത്യൻ മാനദണ്ഡങ്ങളും BIS അനുവർത്തന പ്ലാറ്റ്‌ഫോമും",
    nav_dashboard: "ഡാഷ്‌ബോർഡ്",
    nav_analyze: "അനുവർത്തന വിശകലനം",
    nav_standards: "മാനദണ്ഡങ്ങൾ",
    nav_labs: "ടെസ്റ്റിംഗ് ലാബുകൾ",
    nav_compliance: "വിടവ് വിശകലനം",
    nav_audit: "ഓഡിറ്റ് ചരിത്രം",
    btn_ask_advisor: "ഉപദേശകനോട് ചോദിക്കുക",
    btn_analyze: "ഉൽപ്പന്ന അനുവർത്തനം വിശകലനം ചെയ്യുക",
    btn_analyzing: "ഡാറ്റാബേസ് പരിശോധിക്കുന്നു...",
    btn_clear: "മായ്ക്കുക",
    btn_clarify: "വിശദാംശങ്ങൾ വ്യക്തമാക്കുക",
    product_profile: "ഉൽപ്പന്ന പ്രൊഫൈൽ",
    product_family: "ഉൽപ്പന്ന കുടുംബം",
    intended_use: "ഉദ്ദേശിച്ച ഉപയോഗം",
    materials: "തിരിച്ചറിഞ്ഞ വസ്തുക്കൾ",
    applicable_standards: "ബാധകമായ ഇന്ത്യൻ മാനദണ്ഡങ്ങൾ",
    potential_standards: "വ്യക്തത ആവശ്യമായ മാനദണ്ഡങ്ങൾ",
    what_you_need_to_do: "നിങ്ങൾ ചെയ്യേണ്ട കാര്യങ്ങൾ",
    mandatory_status: "നിർബന്ധിത നിയന്ത്രണ നില",
    voluntary_status: "സ്വമേധയാ ഉള്ള ഇന്ത്യൻ മാനദണ്ഡം",
    qco_not_confirmed: "സർട്ടിഫിക്കേഷൻ ആവശ്യകത സ്ഥിരീകരിച്ചിട്ടില്ല — നിങ്ങളുടെ പ്രാദേശിക BIS ഓഫീസുമായി ബന്ധപ്പെടുക",
    qco_mandatory: "ഗുണനിലവാര നിയന്ത്രണ ഉത്തരവ് (QCO) പ്രകാരം നിർബന്ധിതം",
    certification_scheme: "സർട്ടിഫിക്കേഷൻ സ്കീം",
    testing_requirements: "ആവശ്യമായ പരിശോധനകൾ",
    step_by_step_next_actions: "അടുത്ത ഘട്ടങ്ങൾ",
    testing_laboratories: "അംഗീകൃത ടെസ്റ്റിംഗ് ലബോറട്ടറികൾ",
    no_labs_found: "നിങ്ങളുടെ സമീപത്ത് ലാബുകൾ കണ്ടെത്തിയില്ല. manakonline.in സന്ദർശിക്കുക.",
    not_verified: "സ്ഥിരീകരിച്ചിട്ടില്ല",
    verified: "സ്ഥിരീകരിച്ചു",
    scope_verified: "പരിധി സ്ഥിരീകരിച്ചു",
    distance_not_verified: "ദൂരം സ്ഥിരീകരിച്ചിട്ടില്ല"
  }
};

interface LanguageContextType {
  language: SupportedLanguage;
  currentLanguage: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: string) => string;
  translateDynamic: (text: string) => Promise<string>;
}

const LanguageContext = createContext<LanguageContextType>({
  language: 'en',
  currentLanguage: 'en',
  setLanguage: () => {},
  t: (key: string) => key,
  translateDynamic: async (text: string) => text
});

const dynamicCache = new Map<string, string>();

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    const saved = localStorage.getItem('bis_compass_lang');
    if (saved && SUPPORTED_LANGUAGES.some(l => l.code === saved)) {
      return saved as SupportedLanguage;
    }
    return 'en';
  });

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    localStorage.setItem('bis_compass_lang', lang);
  };

  const t = (key: string): string => {
    const dict = STATIC_TRANSLATIONS[language] || STATIC_TRANSLATIONS.en;
    return dict[key] || STATIC_TRANSLATIONS.en[key] || key;
  };

  const translateDynamic = async (text: string): Promise<string> => {
    if (language === 'en' || !text) return text;
    const cacheKey = `${language}:${text}`;
    if (dynamicCache.has(cacheKey)) {
      return dynamicCache.get(cacheKey)!;
    }

    try {
      const response = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, target_language: language })
      });
      if (!response.ok) return text;
      const data = await response.json();
      const translated = data.translated_text || text;
      dynamicCache.set(cacheKey, translated);
      return translated;
    } catch {
      return text;
    }
  };

  return (
    <LanguageContext.Provider value={{ language, currentLanguage: language, setLanguage, t, translateDynamic }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
