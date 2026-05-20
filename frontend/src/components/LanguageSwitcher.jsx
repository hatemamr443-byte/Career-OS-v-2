import { useI18n } from "../context/I18nContext";

const OPTS = [
    { code: "en", flag: "🇬🇧", label: "EN" },
    { code: "ar", flag: "🇸🇦", label: "عربي" },
    { code: "pt", flag: "🇵🇹", label: "PT" },
];

export default function LanguageSwitcher() {
    const { lang, setLang } = useI18n();
    return (
        <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded-lg p-0.5">
            {OPTS.map(o => (
                <button
                    key={o.code}
                    onClick={() => setLang(o.code)}
                    className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                        lang === o.code
                            ? "bg-zinc-100 text-black"
                            : "text-zinc-500 hover:text-zinc-200"
                    }`}
                    title={o.label}
                >
                    {o.flag} {o.label}
                </button>
            ))}
        </div>
    );
}
