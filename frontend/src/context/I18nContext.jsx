/**
 * i18n — Arabic / English / Portuguese support.
 * Usage: const { t, lang, setLang, isRTL } = useI18n();
 */
import { createContext, useContext, useState, useEffect } from "react";

const I18nContext = createContext(null);

const TRANSLATIONS = {
    en: {
        // Nav
        "nav.dashboard":    "Dashboard",
        "nav.jobs":         "Jobs",
        "nav.bookmarks":    "Bookmarks",
        "nav.inbox":        "Inbox",
        "nav.insights":     "Insights",
        "nav.career_map":   "Career Map",
        "nav.cv_tailor":    "CV Tailor",
        "nav.interview":    "Interview",
        "nav.salary":       "Salary Intel",
        "nav.profile":      "Profile",
        "nav.billing":      "Billing",
        "nav.ai_tools":     "AI Tools",
        "nav.account":      "Account",
        // Dashboard
        "dashboard.title":         "Dashboard",
        "dashboard.welcome":       "Welcome back",
        "dashboard.top_picks":     "Top picks",
        "dashboard.activity":      "Your history",
        "dashboard.recent_activity": "Recent Activity",
        // Jobs
        "jobs.title":          "Jobs",
        "jobs.search":         "Search jobs…",
        "jobs.remote_only":    "Remote only",
        "jobs.find_jobs":      "Find Jobs",
        "jobs.save":           "Save",
        "jobs.saved":          "Saved",
        "jobs.page_of":        "page {page} of {pages}",
        // CV Tailor
        "cv.title":            "CV Intelligence",
        "cv.tailor":           "CV Tailoring",
        "cv.ats":              "ATS Score",
        "cv.cover_letter":     "Cover Letter",
        "cv.versions":         "Saved Versions",
        "cv.your_cv":          "Your CV",
        "cv.job_desc":         "Job Description",
        "cv.tailor_btn":       "Tailor CV for this Job",
        "cv.ats_btn":          "Check ATS Score",
        "cv.cover_btn":        "Generate Cover Letter",
        // Interview
        "interview.title":     "Interview Prep",
        "interview.questions": "Question Generator",
        "interview.practice":  "Practice Mode",
        "interview.research":  "Company Research",
        // Salary
        "salary.title":        "Salary Intelligence",
        "salary.range":        "Market Rates",
        "salary.offer":        "Evaluate Offer",
        "salary.negotiate":    "Negotiate",
        "salary.col":          "Cost of Living",
        // Common
        "common.loading":      "Loading…",
        "common.save":         "Save",
        "common.cancel":       "Cancel",
        "common.copy":         "Copy",
        "common.upgrade":      "Upgrade to Pro",
        "common.free_trial":   "Start Free Trial",
        "common.open_cos":     "Open Career OS",
        "common.quota_hit":    "Daily limit reached. Upgrade for more.",
    },

    ar: {
        // Nav
        "nav.dashboard":    "لوحة التحكم",
        "nav.jobs":         "الوظائف",
        "nav.bookmarks":    "المحفوظات",
        "nav.inbox":        "صندوق البريد",
        "nav.insights":     "التحليلات",
        "nav.career_map":   "خريطة المسار",
        "nav.cv_tailor":    "تخصيص السيرة",
        "nav.interview":    "تحضير المقابلة",
        "nav.salary":       "معلومات الراتب",
        "nav.profile":      "الملف الشخصي",
        "nav.billing":      "الاشتراك",
        "nav.ai_tools":     "أدوات الذكاء الاصطناعي",
        "nav.account":      "الحساب",
        // Dashboard
        "dashboard.title":         "لوحة التحكم",
        "dashboard.welcome":       "مرحباً",
        "dashboard.top_picks":     "أفضل الاختيارات",
        "dashboard.activity":      "سجل النشاط",
        "dashboard.recent_activity": "النشاط الأخير",
        // Jobs
        "jobs.title":          "الوظائف",
        "jobs.search":         "البحث عن وظائف…",
        "jobs.remote_only":    "عن بُعد فقط",
        "jobs.find_jobs":      "ابحث عن وظائف",
        "jobs.save":           "حفظ",
        "jobs.saved":          "محفوظ",
        "jobs.page_of":        "صفحة {page} من {pages}",
        // CV Tailor
        "cv.title":            "ذكاء السيرة الذاتية",
        "cv.tailor":           "تخصيص السيرة",
        "cv.ats":              "تقييم ATS",
        "cv.cover_letter":     "خطاب التغطية",
        "cv.versions":         "النسخ المحفوظة",
        "cv.your_cv":          "سيرتك الذاتية",
        "cv.job_desc":         "وصف الوظيفة",
        "cv.tailor_btn":       "تخصيص السيرة لهذه الوظيفة",
        "cv.ats_btn":          "تحقق من تقييم ATS",
        "cv.cover_btn":        "إنشاء خطاب تغطية",
        // Interview
        "interview.title":     "تحضير المقابلة",
        "interview.questions": "توليد الأسئلة",
        "interview.practice":  "وضع التدريب",
        "interview.research":  "بحث عن الشركة",
        // Salary
        "salary.title":        "معلومات الراتب",
        "salary.range":        "معدلات السوق",
        "salary.offer":        "تقييم العرض",
        "salary.negotiate":    "التفاوض",
        "salary.col":          "تكلفة المعيشة",
        // Common
        "common.loading":      "جاري التحميل…",
        "common.save":         "حفظ",
        "common.cancel":       "إلغاء",
        "common.copy":         "نسخ",
        "common.upgrade":      "ترقية إلى Pro",
        "common.free_trial":   "ابدأ التجربة المجانية",
        "common.open_cos":     "افتح Career OS",
        "common.quota_hit":    "وصلت للحد اليومي. قم بالترقية للمزيد.",
    },

    pt: {
        "nav.dashboard":    "Painel",
        "nav.jobs":         "Empregos",
        "nav.bookmarks":    "Favoritos",
        "nav.inbox":        "Caixa de Entrada",
        "nav.insights":     "Análises",
        "nav.career_map":   "Mapa de Carreira",
        "nav.cv_tailor":    "Personalizar CV",
        "nav.interview":    "Preparação Entrevista",
        "nav.salary":       "Salário",
        "nav.profile":      "Perfil",
        "nav.billing":      "Faturação",
        "nav.ai_tools":     "Ferramentas IA",
        "nav.account":      "Conta",
        "common.loading":   "A carregar…",
        "common.save":      "Guardar",
        "common.cancel":    "Cancelar",
        "common.upgrade":   "Atualizar para Pro",
        "common.free_trial":"Iniciar Período Experimental",
        "common.quota_hit": "Limite diário atingido. Faça upgrade para mais.",
        "jobs.title":       "Empregos",
        "jobs.search":      "Pesquisar empregos…",
        "jobs.remote_only": "Só remoto",
        "jobs.save":        "Guardar",
        "jobs.saved":       "Guardado",
        "cv.title":         "Inteligência CV",
        "cv.tailor":        "Personalizar CV",
        "cv.ats":           "Pontuação ATS",
        "cv.cover_letter":  "Carta de Apresentação",
        "salary.title":     "Inteligência Salarial",
        "interview.title":  "Preparação para Entrevista",
    },
};

const RTL_LANGS = new Set(["ar"]);

export function I18nProvider({ children }) {
    const stored = localStorage.getItem("career_os_lang") || "en";
    const [lang, setLangState] = useState(stored);

    const setLang = (l) => {
        setLangState(l);
        localStorage.setItem("career_os_lang", l);
        // Apply RTL direction
        document.documentElement.dir  = RTL_LANGS.has(l) ? "rtl" : "ltr";
        document.documentElement.lang = l;
    };

    useEffect(() => {
        document.documentElement.dir  = RTL_LANGS.has(lang) ? "rtl" : "ltr";
        document.documentElement.lang = lang;
    }, [lang]);

    const t = (key, vars = {}) => {
        const dict = TRANSLATIONS[lang] || TRANSLATIONS["en"];
        let str = dict[key] ?? TRANSLATIONS["en"][key] ?? key;
        // Simple interpolation: {var}
        Object.entries(vars).forEach(([k, v]) => {
            str = str.replace(`{${k}}`, v);
        });
        return str;
    };

    return (
        <I18nContext.Provider value={{ lang, setLang, t, isRTL: RTL_LANGS.has(lang) }}>
            {children}
        </I18nContext.Provider>
    );
}

export function useI18n() {
    const ctx = useContext(I18nContext);
    if (!ctx) throw new Error("useI18n must be inside I18nProvider");
    return ctx;
}
