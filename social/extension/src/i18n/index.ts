/**
 * Trinity Control Center - i18n System
 * Type-safe internationalization with EN/FR support
 */

import en from './en.json';
import fr from './fr.json';

// Type inference from JSON structure
type Translations = typeof en;
type Lang = 'en' | 'fr';

const translations: Record<Lang, Translations> = { en, fr };

let currentLang: Lang = 'en';

/**
 * Set the current language
 */
export function setLanguage(lang: Lang | string): void {
    const normalized = lang.toLowerCase().substring(0, 2) as Lang;
    if (normalized === 'en' || normalized === 'fr') {
        currentLang = normalized;
    }
}

/**
 * Get the current language
 */
export function getLanguage(): Lang {
    return currentLang;
}

/**
 * Get a translation by dot-notation path
 * Example: t('modals.firewallTitle')
 */
export function t(path: string, params: Record<string, string | number> = {}): string {
    const keys = path.split('.');
    let value: unknown = translations[currentLang];

    for (const key of keys) {
        if (value && typeof value === 'object' && key in value) {
            value = (value as Record<string, unknown>)[key];
        } else {
            // Fallback to English
            value = translations.en;
            for (const k of keys) {
                if (value && typeof value === 'object' && k in value) {
                    value = (value as Record<string, unknown>)[k];
                } else {
                    return path; // Key not found
                }
            }
            break;
        }
    }

    if (typeof value !== 'string') {
        return path;
    }

    // Replace parameters like {ip}, {code}, etc.
    return value.replace(/\{(\w+)\}/g, (_, key) => {
        return params[key]?.toString() ?? `{${key}}`;
    });
}

/**
 * Get all translations for a section
 * Example: getSection('ui')
 */
export function getSection<K extends keyof Translations>(section: K): Translations[K] {
    return translations[currentLang][section];
}

/**
 * Create a scoped translator for a specific section
 * Example: const tModal = createScoped('modals');
 */
export function createScoped(section: string) {
    return (key: string, params?: Record<string, string | number>): string => {
        return t(`${section}.${key}`, params);
    };
}

export type { Translations, Lang };
