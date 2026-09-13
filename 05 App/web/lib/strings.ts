/**
 * Every user-visible string in this app comes from contracts/strings.json.
 * This module is the only place that imports the raw contract; everything
 * else imports STRINGS from here. contracts/ is frozen and read-only to A5
 * (see 05 App/README.md) -- this file only reads and renders it, never edits it.
 */
import rawStrings from "../../contracts/strings.json";

export const STRINGS = rawStrings;

/**
 * Fills a `{param}` template from contracts/strings.json with values.
 * Throws in development if a param the template declares is missing, so a
 * silently-blank placeholder in production copy is never introduced.
 */
export function renderTemplate(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    if (!(key in params)) {
      if (process.env.NODE_ENV !== "production") {
        throw new Error(`renderTemplate: missing param "${key}" for template "${template}"`);
      }
      return match;
    }
    return String(params[key]);
  });
}
